"""Telegram plain-text delivery connector with safe mock behavior."""

import hashlib
import html
import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.connectors.base import Connector, ConnectorExecutionError
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)
from app.services.content_safety import sanitize_untrusted_content


class TelegramMessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat_id: str = Field(min_length=1, max_length=128)
    message: str = Field(default="", max_length=4096)
    allow_sensitive: bool = False
    sensitive_message: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def require_delivery_text(self) -> "TelegramMessageInput":
        text = self.sensitive_message if self.allow_sensitive and self.sensitive_message else self.message
        if not text.strip():
            raise ValueError("message is required")
        return self

    @property
    def text(self) -> str:
        return self.sensitive_message if self.allow_sensitive and self.sensitive_message else self.message


_HTML_TAG = re.compile(r"<[^>]+>")


class TelegramActionConnector(Connector):
    """Send only plain text and report delivery as explicitly non-reversible."""

    name = "telegram"

    def __init__(
        self,
        *,
        bot_token: str | None = None,
        mock_mode: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._bot_token = bot_token
        self._mock_mode = mock_mode
        self._transport = transport
        self.delivered_messages: list[dict[str, str]] = []
        self._deliveries: dict[str, ConnectorExecutionResult] = {}

    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        request = self._input(input)
        if existing := self._deliveries.get(idempotency_key):
            return existing
        text = self._plain_text(request.text)
        message_id: str
        if self._mock_mode:
            message_id = f"mock-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:12]}"
        else:
            response = await self._send(request.chat_id, text)
            raw_message_id = response.get("message_id")
            if not isinstance(raw_message_id, int | str):
                raise ConnectorExecutionError(
                    ConnectorErrorCategory.RETRYABLE, "Telegram returned an invalid delivery response"
                )
            message_id = str(raw_message_id)
        delivery = ConnectorExecutionResult(
            output={
                "chat_id": request.chat_id,
                "message_id": message_id,
                "delivered": True,
                "mock": self._mock_mode,
                "reversible": False,
            }
        )
        self._deliveries[idempotency_key] = delivery
        self.delivered_messages.append(
            {"chat_id": request.chat_id, "text": text, "message_id": message_id}
        )
        return delivery

    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        return result.output.get("delivered") is True and isinstance(result.output.get("message_id"), str)

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        return ConnectorRollbackResult(
            output={"rolled_back": False, "reversible": False, "reason": "telegram_delivery"}
        )

    @staticmethod
    def _input(input: Mapping[str, Any]) -> TelegramMessageInput:
        try:
            return TelegramMessageInput.model_validate(dict(input))
        except ValidationError as error:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "Invalid Telegram message input"
            ) from error

    async def _send(self, chat_id: str, text: str) -> dict[str, Any]:
        if not self._bot_token:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Telegram bot token is required"
            )
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                    data={"chat_id": chat_id, "text": text},
                )
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise ConnectorExecutionError(ConnectorErrorCategory.RETRYABLE, "Telegram request failed") from None
        if not response.is_success or not isinstance(payload, dict) or payload.get("ok") is not True:
            category = ConnectorErrorCategory.PERMANENT if 400 <= response.status_code < 500 else ConnectorErrorCategory.RETRYABLE
            raise ConnectorExecutionError(category, "Telegram rejected the message")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.RETRYABLE, "Telegram returned an invalid delivery response"
            )
        return result

    @staticmethod
    def _plain_text(text: str) -> str:
        clean = sanitize_untrusted_content(html.unescape(_HTML_TAG.sub(" ", text)), max_chars=4096).text
        return clean
