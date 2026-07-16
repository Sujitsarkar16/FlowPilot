from collections.abc import Callable

from app.services.ai.fake_provider import FakeAIProvider


def fake_ai(responder: Callable[[str, str, type], dict[str, object]]) -> FakeAIProvider:
    """Build a deterministic schema-validating AI provider for one scenario."""
    return FakeAIProvider(responder)
