"""Deterministic workflow templates built from structured life-event entities."""

import json
from collections.abc import Iterable, Mapping

from app.models.enums import LifeEventType
from app.models.event import LifeEvent
from app.schemas.compiled_rule import ActionTemplate, CompiledRule
from app.services.plan_graph import CandidateAction, PlanGraph, merge_action_inputs


class WorkflowError(ValueError):
    """Raised when a workflow template cannot be built safely."""


def _event_context(event: LifeEvent) -> dict[str, object]:
    """Expose only persisted, structured entities; raw source payloads are never inspected."""
    grouped: dict[str, list[object]] = {}
    entities = sorted(
        event.entities,
        key=lambda entity: (
            entity.kind,
            json.dumps(entity.value, sort_keys=True, separators=(",", ":")),
        ),
    )
    for entity in entities:
        grouped.setdefault(entity.kind, []).append(entity.value)
    return {
        "event_id": str(event.id),
        "event_type": event.type.value,
        "event_entities": grouped,
    }


def _build_template_graph(
    event: LifeEvent,
    rule: CompiledRule,
    nodes: Iterable[tuple[str, str, tuple[str, ...]]],
) -> PlanGraph:
    """Build registered template nodes only when the matching rule includes them."""
    templates: Mapping[str, ActionTemplate] = {
        template.action_type: template for template in rule.action_templates
    }
    context = _event_context(event)
    actions: list[CandidateAction] = []
    present_keys: set[str] = set()
    for action_key, action_type, dependencies in nodes:
        template = templates.get(action_type)
        if template is None:
            continue
        actions.append(
            CandidateAction(
                action_key=action_key,
                action_type=action_type,
                input=merge_action_inputs(template.input, context),
                depends_on=tuple(
                    dependency for dependency in dependencies if dependency in present_keys
                ),
                connector=template.connector,
                risk_level=template.risk_level,
                approval_mode=template.approval_mode,
            )
        )
        present_keys.add(action_key)
    return PlanGraph.from_actions(actions)


def build_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Dispatch an event to its deterministic MVP template, or an empty graph."""
    if event.type in {LifeEventType.TRAVEL_BOOKED, LifeEventType.TRAVEL_CHANGED}:
        return build_travel_workflow(event, rule)
    if event.type in {LifeEventType.CLIENT_OPPORTUNITY, LifeEventType.CLIENT_CONFIRMED}:
        return build_client_launch_workflow(event, rule)
    if event.type is LifeEventType.SALARY_CREDITED:
        return build_salary_workflow(event, rule)
    if event.type is LifeEventType.SUBSCRIPTION_RENEWAL:
        return build_subscription_workflow(event, rule)
    return PlanGraph.from_actions(())


def build_travel_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Build the deterministic travel template."""
    from app.workflows.travel import build_travel_workflow as build

    return build(event, rule)


def build_client_launch_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Build the deterministic client-launch template."""
    from app.workflows.client_launch import build_client_launch_workflow as build

    return build(event, rule)


def build_subscription_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Build the bounded, read-only subscription discovery template."""
    return _build_template_graph(
        event,
        rule,
        (("subscription.check_renewal", "subscription.check_renewal", ()),),
    )


def build_salary_workflow(event: LifeEvent, rule: CompiledRule) -> PlanGraph:
    """Build the deterministic salary template."""
    from app.workflows.salary import build_salary_workflow as build

    return build(event, rule)


__all__ = [
    "WorkflowError",
    "build_client_launch_workflow",
    "build_salary_workflow",
    "build_subscription_workflow",
    "build_travel_workflow",
    "build_workflow",
]
