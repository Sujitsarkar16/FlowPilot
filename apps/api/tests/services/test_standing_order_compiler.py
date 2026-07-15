import pytest

from app.services.ai.fake_provider import FakeAIProvider
from app.services.standing_order_compiler import (
    StandingOrderCompilationError,
    StandingOrderCompiler,
)


def responder(system: str, user: str, schema: type) -> dict[str, object]:
    if "financial" in user:
        return {
            "schema_version": "1.0",
            "trigger_event_types": ["salary_credited"],
            "action_templates": [
                {
                    "action_type": "salary.propose_transfer",
                    "connector": "mock_bank",
                    "input": {},
                    "risk_level": "red",
                    "approval_mode": "automatic",
                }
            ],
            "explanation": "Transfer money.",
        }
    return {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "entity_conditions": [],
        "action_templates": [
            {
                "action_type": "travel.create_folder",
                "connector": "google",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            },
            {
                "action_type": "travel.notify_family",
                "connector": "telegram",
                "input": {},
                "risk_level": "yellow",
                "approval_mode": "approval_required",
            },
        ],
        "explanation": "Prepare travel safely.",
    }


@pytest.mark.asyncio
async def test_compiler_returns_catalog_constrained_travel_actions() -> None:
    result = await StandingOrderCompiler(FakeAIProvider(responder)).compile(
        "Whenever I book a flight, prepare it."
    )
    assert result.rule.trigger_event_types[0].value == "travel_booked"
    assert result.rule.action_templates[-1].approval_mode == "approval_required"


@pytest.mark.asyncio
async def test_compiler_rejects_automatic_financial_action() -> None:
    with pytest.raises(StandingOrderCompilationError):
        await StandingOrderCompiler(FakeAIProvider(responder)).compile(
            "Handle financial salary events"
        )
