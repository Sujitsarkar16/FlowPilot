"""Deterministic AI provider for tests and offline demos.

The responder receives the system prompt, user content, and target schema and returns
a plain dict, which is then validated exactly like real provider output. This keeps
tests free of network calls while still exercising schema validation.
"""

from collections.abc import Callable

from pydantic import ValidationError

from app.services.ai.base import AIProvider
from app.services.ai.schemas import AIValidationError, StructuredResult, StructuredT

Responder = Callable[[str, str, type], dict[str, object]]


class FakeAIProvider(AIProvider):
    def __init__(self, responder: Responder) -> None:
        self._responder = responder

    async def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[StructuredT],
        timeout: float = 30.0,
    ) -> StructuredResult[StructuredT]:
        raw = self._responder(system, user, schema)
        try:
            return StructuredResult(data=schema.model_validate(raw))
        except ValidationError as error:
            raise AIValidationError(str(error)) from error
