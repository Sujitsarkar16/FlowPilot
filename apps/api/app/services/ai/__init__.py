"""Provider-neutral structured AI adapter."""

from app.core.config import Settings
from app.services.ai.base import AIProvider
from app.services.ai.provider import OpenAICompatibleProvider
from app.services.ai.schemas import (
    AIError,
    AITimeoutError,
    AIValidationError,
    StructuredResult,
    TokenUsage,
)


class AINotConfiguredError(AIError):
    """Raised when structured AI is required but no API key is configured."""


def build_ai_provider(settings: Settings) -> AIProvider:
    """Return the configured production provider or fail loudly if unconfigured."""
    if settings.ai_api_key is None:
        raise AINotConfiguredError("AI_API_KEY is not configured")
    return OpenAICompatibleProvider(
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key.get_secret_value(),
        model=settings.ai_model,
    )


__all__ = [
    "AIProvider",
    "AIError",
    "AITimeoutError",
    "AIValidationError",
    "AINotConfiguredError",
    "StructuredResult",
    "TokenUsage",
    "OpenAICompatibleProvider",
    "build_ai_provider",
]
