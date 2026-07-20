from uuid import uuid4

from app.models.enums import Importance, LifeEventType
from app.models.event import EventEntity, LifeEvent
from app.schemas.compiled_rule import CompiledRule
from app.services.action_registry import ACTION_REGISTRY
from app.workflows import (
    build_client_launch_workflow,
    build_salary_workflow,
    build_subscription_workflow,
    build_travel_workflow,
)


def rule(event_type: LifeEventType, action_types: list[str]) -> CompiledRule:
    return CompiledRule.model_validate(
        {
            "schema_version": "1.0",
            "trigger_event_types": [event_type],
            "entity_conditions": [],
            "action_templates": [
                {
                    "action_type": name,
                    "connector": ACTION_REGISTRY.get(name).connector,
                    "input": {},
                    "risk_level": ACTION_REGISTRY.get(name).default_risk,
                    "approval_mode": ACTION_REGISTRY.get(name).minimum_approval,
                }
                for name in action_types
            ],
            "explanation": "Use the deterministic template.",
        }
    )


def event(event_type: LifeEventType) -> LifeEvent:
    return LifeEvent(
        id=uuid4(),
        type=event_type,
        confidence=1,
        importance=Importance.HIGH,
        summary="ignored",
        entities=[EventEntity(kind="destination", value={"name": "Lisbon"}, is_sensitive=False)],
    )


def test_templates_only_emit_matching_actions_with_explicit_dependencies() -> None:
    travel = build_travel_workflow(
        event(LifeEventType.TRAVEL_BOOKED),
        rule(
            LifeEventType.TRAVEL_BOOKED,
            ["travel.create_folder", "travel.get_weather", "travel.generate_documents"],
        ),
    )
    client = build_client_launch_workflow(
        event(LifeEventType.CLIENT_CONFIRMED),
        rule(
            LifeEventType.CLIENT_CONFIRMED,
            ["client.generate_documents", "client.create_repository", "client.notify_client"],
        ),
    )
    salary = build_salary_workflow(
        event(LifeEventType.SALARY_CREDITED),
        rule(LifeEventType.SALARY_CREDITED, ["salary.update_budget", "salary.propose_transfer"]),
    )
    subscription = build_subscription_workflow(
        event(LifeEventType.SUBSCRIPTION_RENEWAL),
        rule(LifeEventType.SUBSCRIPTION_RENEWAL, ["subscription.check_renewal"]),
    )

    assert [action.action_type for action in travel.ordered_actions] == [
        "travel.create_folder",
        "travel.get_weather",
        "travel.generate_documents",
    ]
    assert client.action_by_key["client.notify_client"].depends_on == ("client.create_repository",)
    assert salary.action_by_key["salary.propose_transfer"].depends_on == ("salary.update_budget",)
    assert [action.action_type for action in subscription.ordered_actions] == [
        "subscription.check_renewal"
    ]
