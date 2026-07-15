"""Narrow Telegram Bot API client used only for setup and explicit test sends."""

from dataclasses import dataclass
from typing import Any

import httpx


class TelegramError(Exception):
    """A sanitized Telegram setup or test-message failure."""


@dataclass(frozen=True)
class TelegramBot:
    id: str
    username: str | None


class TelegramClient:
    def __init__(
        self, *, mock_mode: bool = False, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._mock_mode = mock_mode
        self._transport = transport

    async def get_me(self, bot_token: str | None) -> TelegramBot:
        if self._mock_mode:
            return TelegramBot(id="mock-telegram-bot", username="pulseos_demo_bot")
        payload = await self._request(bot_token, "getMe")
        return self._bot(payload)

    async def send_test_message(self, bot_token: str | None, chat_id: str) -> None:
        if self._mock_mode:
            return
        await self._request(
            bot_token,
            "sendMessage",
            {"chat_id": chat_id, "text": "PulseOS connection test successful."},
        )

    async def _request(
        self, bot_token: str | None, method: str, data: dict[str, str] | None = None
    ) -> dict[str, Any]:
        if not bot_token:
            raise TelegramError("Telegram bot token is required")
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/{method}", data=data
                )
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise TelegramError("Telegram request failed") from None
        if (
            not response.is_success
            or not isinstance(payload, dict)
            or payload.get("ok") is not True
        ):
            raise TelegramError("Telegram rejected the connection")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise TelegramError("Telegram returned an invalid response")
        return result

    @staticmethod
    def _bot(result: dict[str, Any]) -> TelegramBot:
        bot_id = result.get("id")
        username = result.get("username")
        if bot_id is None:
            raise TelegramError("Telegram returned an invalid bot")
        return TelegramBot(id=str(bot_id), username=username if isinstance(username, str) else None)
