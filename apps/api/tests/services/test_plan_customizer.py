import pytest

from app.services.ai.fake_provider import FakeAIProvider
from app.services.plan_customizer import PlanCustomizer
from app.services.plan_graph import CandidateAction, PlanGraph


def graph() -> PlanGraph:
    return PlanGraph.from_actions(
        [
            CandidateAction(
                "travel.weather",
                "travel.get_weather",
                input={"event_id": "event-1", "location": "Paris"},
            ),
            CandidateAction(
                "travel.documents",
                "travel.generate_documents",
                input={"event_id": "event-1"},
                depends_on=("travel.weather",),
            ),
        ]
    )


@pytest.mark.asyncio
async def test_customizer_applies_only_safe_optional_input_overrides() -> None:
    provider = FakeAIProvider(
        lambda _system, _user, _schema: {
            "rationale": "Use the event destination for weather.",
            "overrides": {"travel.weather": {"location": "Lisbon"}},
        }
    )

    result = await PlanCustomizer(provider).customize(graph())

    assert not result.used_fallback
    assert result.graph.action_by_key["travel.weather"].input == {
        "event_id": "event-1",
        "location": "Lisbon",
    }
    assert result.graph.action_by_key["travel.documents"].depends_on == ("travel.weather",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"new.action": {"location": "Lisbon"}},
        {"travel.weather": {"event_id": "spoofed"}},
    ],
)
async def test_customizer_falls_back_for_unknown_actions_or_unsafe_fields(
    overrides: dict[str, dict[str, str]],
) -> None:
    provider = FakeAIProvider(
        lambda _system, _user, _schema: {
            "rationale": "Attempt an unsafe change.",
            "overrides": overrides,
        }
    )
    original = graph()

    result = await PlanCustomizer(provider).customize(original)

    assert result.used_fallback
    assert result.graph is original
    assert "original validated plan" in result.rationale


@pytest.mark.asyncio
async def test_customizer_falls_back_when_ai_output_is_not_the_strict_contract() -> None:
    provider = FakeAIProvider(
        lambda _system, _user, _schema: {"rationale": "No schema", "overrides": {}, "extra": True}
    )

    result = await PlanCustomizer(provider).customize(graph())

    assert result.used_fallback
