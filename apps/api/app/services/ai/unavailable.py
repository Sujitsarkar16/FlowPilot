"""AI provider used when no API key is configured.

Callers that catch ``AIError`` (classifier/extractor) degrade to safe generic
interpretations instead of aborting ingestion workers.
"""

from app.services.ai.base import AIProvider
from app.services.ai.schemas import AIError, StructuredResult, StructuredT


class UnavailableAIProvider(AIProvider):
    async def generate_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[StructuredT],
        timeout: float = 30.0,
    ) -> StructuredResult[StructuredT]:
        raise AIError("AI provider is not configured")
