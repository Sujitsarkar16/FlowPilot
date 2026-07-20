"""Deterministic candidate-action template for travel events."""

from app.models.enums import LifeEventType
from app.models.event import LifeEvent
from app.schemas.compiled_rule import CompiledRule
from app.services.plan_graph import PlanGraph
from app.workflows import _build_template_graph

_TRAVEL_TYPES = {LifeEventType.TRAVEL_BOOKED, LifeEventType.TRAVEL_CHANGED}
_NODES = (
    ("travel.create_folder", "travel.create_folder", ()),
    ("travel.save_ticket", "travel.save_ticket", ()),
    ("travel.get_weather", "travel.get_weather", ()),
    (
        "travel.create_calendar_event",
        "travel.create_calendar_event",
        ("travel.create_folder",),
    ),
    (
        "travel.generate_documents",
        "travel.generate_documents",
        ("travel.create_folder", "travel.get_weather"),
    ),
    (
        "travel.upload_itinerary",
        "travel.upload_itinerary",
        ("travel.create_folder", "travel.generate_documents"),
    ),
    (
        "travel.upload_packing_checklist",
        "travel.upload_packing_checklist",
        ("travel.create_folder", "travel.generate_documents"),
    ),
    (
        "travel.notify_family",
        "travel.notify_family",
        (
            "travel.create_calendar_event",
            "travel.upload_itinerary",
            "travel.upload_packing_checklist",
        ),
    ),
)


def build_travel_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Build the ticket-aware travel DAG from structured booking entities."""
    if event.type not in _TRAVEL_TYPES:
        return PlanGraph.from_actions(())
    nodes = tuple(
        node for node in _NODES if node[0] != "travel.save_ticket" or _has_ticket_evidence(event)
    )
    return _build_template_graph(event, rule, nodes)


def _has_ticket_evidence(event: LifeEvent) -> bool:
    return any(
        entity.kind in {"pnr", "booking_reference", "confirmation", "flight", "flight_number"}
        and any(
            isinstance(value, str) and len(value.strip()) >= 3 for value in entity.value.values()
        )
        for entity in event.entities
    )


build = build_travel_workflow
