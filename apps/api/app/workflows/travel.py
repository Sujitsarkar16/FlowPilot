"""Deterministic candidate-action template for travel events."""

from app.models.enums import LifeEventType
from app.models.event import LifeEvent
from app.schemas.compiled_rule import ActionTemplate, CompiledRule
from app.services.action_registry import ACTION_REGISTRY
from app.services.plan_graph import PlanGraph
from app.workflows import _build_template_graph

_TRAVEL_TYPES = {LifeEventType.TRAVEL_BOOKED, LifeEventType.TRAVEL_CHANGED}
# Uploads read the generate_documents output at run time, so the producer is a hard prerequisite.
_DOCUMENT_CONSUMERS = frozenset(
    {"travel.upload_itinerary", "travel.upload_packing_checklist"}
)
_DOCUMENT_PRODUCER = "travel.generate_documents"
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
    rule = _ensure_document_producer(rule)
    nodes = tuple(
        node for node in _NODES if node[0] != "travel.save_ticket" or _has_ticket_evidence(event)
    )
    return _build_template_graph(event, rule, nodes)


def _ensure_document_producer(rule: CompiledRule) -> CompiledRule:
    """Guarantee generate_documents whenever an upload that consumes its output was selected.

    Selecting an upload without its producer builds a graph that validates but fails at
    execution ("packing_checklist is unavailable"), because the upload reads the generated
    document from its dependency output. The producer is machinery, not a user-facing choice,
    so pull it in with registered defaults rather than dropping the requested upload.
    """
    action_types = {template.action_type for template in rule.action_templates}
    if action_types.isdisjoint(_DOCUMENT_CONSUMERS) or _DOCUMENT_PRODUCER in action_types:
        return rule
    definition = ACTION_REGISTRY.get(_DOCUMENT_PRODUCER)
    producer = ActionTemplate(
        action_type="travel.generate_documents",
        connector=definition.connector,
        input={},
        risk_level=definition.minimum_risk,
        approval_mode=definition.minimum_approval,
    )
    return rule.model_copy(update={"action_templates": [*rule.action_templates, producer]})


def _has_ticket_evidence(event: LifeEvent) -> bool:
    return any(
        entity.kind in {"pnr", "booking_reference", "confirmation", "flight", "flight_number"}
        and any(
            isinstance(value, str) and len(value.strip()) >= 3 for value in entity.value.values()
        )
        for entity in event.entities
    )


build = build_travel_workflow
