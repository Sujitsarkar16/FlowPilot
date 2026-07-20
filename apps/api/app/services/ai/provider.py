"""Production adapter for OpenRouter chat completions.

Uses the already-present ``httpx`` dependency and OpenRouter's OpenAI-compatible
``/chat/completions`` endpoint with JSON-mode output.
"""

import asyncio
import logging
import random

import httpx
from pydantic import ValidationError

from app.services.ai.base import AIProvider
from app.services.ai.schemas import (
    AIError,
    AITimeoutError,
    AIValidationError,
    StructuredResult,
    StructuredT,
    TokenUsage,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class OpenRouterProvider(AIProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._transport = transport
        self._max_retries = max_retries
        self._base_delay = base_delay_seconds

    async def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[StructuredT],
        timeout: float = 30.0,
    ) -> StructuredResult[StructuredT]:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers={"Authorization": f"Bearer {self._api_key}"},
                    )
            except httpx.TimeoutException:
                last_error = AITimeoutError("AI provider timed out")
                if attempt < self._max_retries - 1:
                    await self._backoff(attempt)
                continue
            except httpx.HTTPError as error:
                raise AIError("AI provider request failed") from error

            if response.status_code in _RETRYABLE_STATUS_CODES:
                last_error = AIError(f"AI provider returned status {response.status_code}")
                logger.warning(
                    "AI provider retryable error",
                    extra={"status": response.status_code, "attempt": attempt + 1},
                )
                if attempt < self._max_retries - 1:
                    await self._backoff(attempt)
                continue

            if not response.is_success:
                raise AIError(f"AI provider returned status {response.status_code}")

            content, usage = self._extract(response.json())
            try:
                return StructuredResult(data=schema.model_validate_json(content), usage=usage)
            except (ValidationError, ValueError) as error:
                raise AIValidationError("AI output failed schema validation") from error

        raise last_error or AIError("AI provider failed after all retries")

    async def _backoff(self, attempt: int) -> None:
        delay = self._base_delay * (2**attempt)
        jitter = random.uniform(0, delay * 0.25)
        await asyncio.sleep(delay + jitter)

    @staticmethod
    def _extract(body: object) -> tuple[str, TokenUsage]:
        if not isinstance(body, dict):
            raise AIError("AI provider returned an invalid response")
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise AIError("AI provider returned no completion") from error
        if not isinstance(content, str):
            raise AIError("AI provider returned non-text content")
        usage_obj = body.get("usage")
        raw_usage = usage_obj if isinstance(usage_obj, dict) else {}
        usage = TokenUsage(
            prompt_tokens=int(raw_usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(raw_usage.get("completion_tokens", 0) or 0),
        )
        return content, usage
