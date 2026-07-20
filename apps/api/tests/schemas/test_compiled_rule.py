import pytest
from pydantic import ValidationError

from app.schemas.compiled_rule import CompiledRule


def rule(
    action_type: str, connector: str, risk_level: str, approval_mode: str
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "entity_conditions": [],
        "action_templates": [
            {
                "action_type": action_type,
                "connector": connector,
                "input": {},
                "risk_level": risk_level,
                "approval_mode": approval_mode,
            }
        ],
        "explanation": "Prepare the event safely.",
    }


def test_travel_and_client_rules_validate() -> None:
    CompiledRule.model_validate(rule("travel.create_folder", "google", "green", "automatic"))
    client = rule("client.create_repository", "github", "yellow", "approval_required")
    client["trigger_event_types"] = ["client_opportunity"]
    CompiledRule.model_validate(client)
    CompiledRule.model_validate(rule("client.create_folder", "google", "green", "automatic"))


def test_unknown_or_mismatched_actions_fail() -> None:
    with pytest.raises(ValidationError):
        CompiledRule.model_validate(rule("unknown.action", "google", "green", "automatic"))
    with pytest.raises(ValidationError, match="requires the google connector"):
        CompiledRule.model_validate(rule("travel.create_folder", "github", "green", "automatic"))


def test_red_actions_can_never_be_automatic() -> None:
    with pytest.raises(ValidationError, match="red-risk actions"):
        CompiledRule.model_validate(
            rule("salary.propose_transfer", "mock_bank", "red", "automatic")
        )
