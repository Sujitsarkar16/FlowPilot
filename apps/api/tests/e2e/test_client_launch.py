from uuid import uuid4

from app.connectors.github.repositories import RepositoryInput
from app.models.enums import Importance, LifeEventType
from app.models.event import EventEntity, LifeEvent
from app.schemas.compiled_rule import CompiledRule
from app.services.action_registry import ACTION_REGISTRY
from app.workflows import build_client_launch_workflow


def _rule() -> CompiledRule:
    names = [
        "client.generate_documents",
        "client.create_repository",
        "client.create_calendar_event",
        "client.notify_client",
    ]
    return CompiledRule.model_validate(
        {
            "schema_version": "1.0",
            "trigger_event_types": ["client_confirmed"],
            "entity_conditions": [],
            "action_templates": [
                {
                    "action_type": name,
                    "connector": ACTION_REGISTRY.get(name).connector,
                    "input": {},
                    "risk_level": ACTION_REGISTRY.get(name).default_risk,
                    "approval_mode": ACTION_REGISTRY.get(name).minimum_approval,
                }
                for name in names
            ],
            "explanation": "Launch client work.",
        }
    )


def test_client_fixture_builds_private_workspace_and_gated_reply() -> None:
    event = LifeEvent(
        id=uuid4(),
        type=LifeEventType.CLIENT_CONFIRMED,
        confidence=1,
        importance=Importance.HIGH,
        summary="Launch Acme website",
        entities=[
            EventEntity(kind="client", value={"name": "Acme"}, is_sensitive=False),
            EventEntity(kind="requirements", value={"text": "Marketing site"}, is_sensitive=False),
        ],
    )
    graph = build_client_launch_workflow(event, _rule())

    assert {action.action_type for action in graph.ordered_actions} == {
        "client.generate_documents",
        "client.create_repository",
        "client.create_calendar_event",
        "client.notify_client",
    }
    assert graph.action_by_key["client.create_repository"].depends_on == (
        "client.generate_documents",
    )
    assert set(graph.action_by_key["client.notify_client"].depends_on) == {
        "client.create_repository",
        "client.create_calendar_event",
    }
    positions = {action.action_key: index for index, action in enumerate(graph.ordered_actions)}
    assert all(
        positions[dependency] < positions[action.action_key]
        for action in graph.ordered_actions
        for dependency in action.depends_on
    )
    assert RepositoryInput(name="acme-workspace").private is True
    assert ACTION_REGISTRY.get("client.notify_client").minimum_approval == "approval_required"
