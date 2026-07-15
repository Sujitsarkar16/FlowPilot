"""Deterministic candidate-action template for salary events."""

from app.models.enums import LifeEventType
from app.models.event import LifeEvent
from app.schemas.compiled_rule import CompiledRule
from app.services.plan_graph import PlanGraph
from app.workflows import _build_template_graph

_NODES = (
    ("salary.update_budget", "salary.update_budget", ()),
    (
        "salary.propose_transfer",
        "salary.propose_transfer",
        ("salary.update_budget",),
    ),
)


def build_salary_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Build the budget update and approval-gated transfer proposal when templated."""
    if event.type is not LifeEventType.SALARY_CREDITED:
        return PlanGraph.from_actions(())
    return _build_template_graph(event, rule, _NODES)


build = build_salary_workflow
