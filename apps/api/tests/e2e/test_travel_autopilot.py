from uuid import uuid4

from app.models.enums import Importance, LifeEventType
from app.models.event import EventEntity, LifeEvent
from app.schemas.compiled_rule import CompiledRule
from app.services.action_registry import ACTION_REGISTRY
from app.workflows import build_travel_workflow


def _rule() -> CompiledRule:
    names = [
        "travel.create_folder",
        "travel.save_ticket",
        "travel.get_weather",
        "travel.create_calendar_event",
        "travel.generate_documents",
        "travel.upload_itinerary",
        "travel.upload_packing_checklist",
        "travel.notify_family",
    ]
    return CompiledRule.model_validate(
        {
            "schema_version": "1.0",
            "trigger_event_types": ["travel_booked"],
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
            "explanation": "Prepare booked travel.",
        }
    )


def test_booking_fixture_builds_an_idempotent_ticket_aware_dag() -> None:
    event = LifeEvent(
        id=uuid4(),
        type=LifeEventType.TRAVEL_BOOKED,
        confidence=1,
        importance=Importance.HIGH,
        summary="Booking email: Lisbon",
        entities=[
            EventEntity(kind="destination", value={"name": "Lisbon"}, is_sensitive=False),
            EventEntity(kind="ticket", value={"name": "booking.pdf"}, is_sensitive=False),
        ],
    )
    first = build_travel_workflow(event, _rule())
    second = build_travel_workflow(event, _rule())

    assert {action.action_type for action in first.ordered_actions} == {
        "travel.create_folder",
        "travel.save_ticket",
        "travel.get_weather",
        "travel.create_calendar_event",
        "travel.generate_documents",
        "travel.upload_itinerary",
        "travel.upload_packing_checklist",
        "travel.notify_family",
    }
    assert first.action_by_key["travel.upload_itinerary"].depends_on == (
        "travel.create_folder",
        "travel.generate_documents",
    )
    assert first.action_by_key["travel.notify_family"].depends_on == (
        "travel.create_calendar_event",
        "travel.upload_itinerary",
        "travel.upload_packing_checklist",
    )
    positions = {action.action_key: index for index, action in enumerate(first.ordered_actions)}
    assert all(
        positions[dependency] < positions[action.action_key]
        for action in first.ordered_actions
        for dependency in action.depends_on
    )
    assert [action.action_key for action in first.ordered_actions] == [
        action.action_key for action in second.ordered_actions
    ]
    assert ACTION_REGISTRY.get("travel.notify_family").minimum_approval == "approval_required"
