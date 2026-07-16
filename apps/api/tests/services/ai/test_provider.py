import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.services.ai import (
    AINotConfiguredError,
    OpenRouterProvider,
    build_ai_provider,
)
from app.services.ai.fake_provider import FakeAIProvider
from app.services.ai.schemas import AIValidationError


class Answer(BaseModel):
    label: str
    score: float


@pytest.mark.asyncio
async def test_fake_provider_validates_output() -> None:
    provider = FakeAIProvider(lambda system, user, schema: {"label": "travel", "score": 0.9})
    result = await provider.generate_structured(system="s", user="u", schema=Answer)
    assert result.data.label == "travel"


@pytest.mark.asyncio
async def test_fake_provider_rejects_invalid_output() -> None:
    provider = FakeAIProvider(lambda system, user, schema: {"label": "x"})
    with pytest.raises(AIValidationError):
        await provider.generate_structured(system="s", user="u", schema=Answer)


def test_build_provider_switches_on_configuration() -> None:
    with pytest.raises(AINotConfiguredError):
        build_ai_provider(Settings(_env_file=None))
    configured = build_ai_provider(Settings(_env_file=None, openrouter_api_key="secret"))
    assert isinstance(configured, OpenRouterProvider)


def test_openrouter_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert settings.openrouter_model == "google/gemini-2.5-flash"


@pytest.mark.asyncio
async def test_production_provider_parses_json_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"label": "client", "score": 0.7}'}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
        )

    provider = OpenRouterProvider(
        base_url="https://ai.test/v1",
        api_key="k",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )
    result = await provider.generate_structured(system="s", user="u", schema=Answer)
    assert result.data.score == 0.7
    assert result.usage.prompt_tokens == 10


@pytest.mark.asyncio
async def test_production_provider_rejects_unparseable_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    provider = OpenRouterProvider(
        base_url="https://ai.test/v1",
        api_key="k",
        model="m",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AIValidationError):
        await provider.generate_structured(system="s", user="u", schema=Answer)


def test_openrouter_api_key_is_loaded_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    settings = Settings(_env_file=None)
    assert settings.openrouter_api_key is not None
    assert settings.openrouter_api_key.get_secret_value() == "test-openrouter-key"


@pytest.mark.asyncio
async def test_openrouter_provider_sends_configured_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-openrouter-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"label": "travel", "score": 0.9}'}}]})

    provider = OpenRouterProvider(
        base_url="https://openrouter.ai/api/v1",
        api_key="test-openrouter-key",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )
    result = await provider.generate_structured(system="s", user="u", schema=Answer)
    assert result.data.label == "travel"
