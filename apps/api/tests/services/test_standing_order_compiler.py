import pytest

from app.services.ai.fake_provider import FakeAIProvider
from app.services.standing_order_compiler import (
    StandingOrderCompilationError,
    StandingOrderCompiler,
)


def responder(system: str, user: str, schema: type) -> dict[str, object]:
    if "client confirms" in user.lower():
        assert "client.create_folder" in user
        return {
            "schema_version": "1.0",
            "trigger_event_types": ["client_confirmed"],
            "action_templates": [
                {
                    "action_type": "client.generate_documents",
                    "connector": "internal",
                    "input": {},
                    "risk_level": "green",
                    "approval_mode": "automatic",
                },
                {
                    "action_type": "client.create_folder",
                    "connector": "google",
                    "input": {},
                    "risk_level": "green",
                    "approval_mode": "automatic",
                },
                {
                    "action_type": "client.create_repository",
                    "connector": "github",
                    "input": {},
                    "risk_level": "yellow",
                    "approval_mode": "approval_required",
                },
                {
                    "action_type": "client.create_calendar_event",
                    "connector": "google",
                    "input": {},
                    "risk_level": "yellow",
                    "approval_mode": "approval_required",
                },
                {
                    "action_type": "client.notify_client",
                    "connector": "telegram",
                    "input": {},
                    "risk_level": "yellow",
                    "approval_mode": "approval_required",
                },
            ],
            "explanation": "Prepare the client launch with a gated reply.",
        }
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
async def test_compiler_compiles_a_complete_client_confirmation_workflow() -> None:
    result = await StandingOrderCompiler(FakeAIProvider(responder)).compile(
        "Whenever a client confirms a new project, extract the requirements, create a private "
        "GitHub repository, create a project folder, prepare a requirements summary, draft a "
        "proposal, prepare an invoice template, suggest kickoff times, and ask me before replying."
    )

    assert result.rule.trigger_event_types[0].value == "client_confirmed"
    assert [action.action_type for action in result.rule.action_templates] == [
        "client.generate_documents",
        "client.create_folder",
        "client.create_repository",
        "client.create_calendar_event",
        "client.notify_client",
    ]
    assert result.rule.action_templates[-1].approval_mode == "approval_required"


@pytest.mark.asyncio
async def test_compiler_rejects_automatic_financial_action() -> None:
    with pytest.raises(StandingOrderCompilationError):
        await StandingOrderCompiler(FakeAIProvider(responder)).compile(
            "Handle financial salary events"
        )
