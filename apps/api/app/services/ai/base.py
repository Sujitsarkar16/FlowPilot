"""Provider-neutral structured-completion interface."""

from abc import ABC, abstractmethod

from app.services.ai.schemas import StructuredResult, StructuredT


class AIProvider(ABC):
    """Produce a single schema-validated object from a system+user prompt.

    Implementations must never return free-form text to callers: output is always
    validated against the caller-supplied Pydantic schema or the call fails.
    """

    @abstractmethod
    async def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[StructuredT],
        timeout: float = 30.0,
    ) -> StructuredResult[StructuredT]:
        raise NotImplementedError
