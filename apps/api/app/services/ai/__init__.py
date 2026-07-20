"""Provider-neutral structured AI adapter."""

from app.core.config import Settings
from app.services.ai.base import AIProvider
from app.services.ai.provider import OpenRouterProvider
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
    if settings.openrouter_api_key is None:
        raise AINotConfiguredError("OPENROUTER_API_KEY is not configured")
    return OpenRouterProvider(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key.get_secret_value(),
        model=settings.openrouter_model,
    )


def build_ai_provider_optional(settings: Settings) -> AIProvider:
    """Return a real provider when configured; otherwise a no-op that yields safe fallbacks."""
    try:
        return build_ai_provider(settings)
    except AINotConfiguredError:
        from app.services.ai.unavailable import UnavailableAIProvider

        return UnavailableAIProvider()


__all__ = [
    "AIProvider",
    "AIError",
    "AITimeoutError",
    "AIValidationError",
    "AINotConfiguredError",
    "StructuredResult",
    "TokenUsage",
    "OpenRouterProvider",
    "build_ai_provider",
    "build_ai_provider_optional",
]
