"""Deterministic candidate-action template for client launch events."""

from app.models.enums import LifeEventType
from app.models.event import LifeEvent
from app.schemas.compiled_rule import CompiledRule
from app.services.plan_graph import PlanGraph
from app.workflows import _build_template_graph

_CLIENT_TYPES = {LifeEventType.CLIENT_OPPORTUNITY, LifeEventType.CLIENT_CONFIRMED}
_NODES = (
    ("client.generate_documents", "client.generate_documents", ()),
    ("client.create_folder", "client.create_folder", ()),
    (
        "client.create_repository",
        "client.create_repository",
        ("client.generate_documents",),
    ),
    (
        "client.create_calendar_event",
        "client.create_calendar_event",
        ("client.generate_documents",),
    ),
    (
        "client.notify_client",
        "client.notify_client",
        ("client.create_folder", "client.create_repository", "client.create_calendar_event"),
    ),
)


def build_client_launch_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Build proposal, GitHub workspace, kickoff, and client notification actions."""
    if event.type not in _CLIENT_TYPES:
        return PlanGraph.from_actions(())
    return _build_template_graph(event, rule, _NODES)


build = build_client_launch_workflow
