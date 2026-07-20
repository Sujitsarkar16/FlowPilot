"""Create persisted, policy-evaluated plans from matching standing orders."""

import logging
from collections.abc import Iterable, Mapping
from time import perf_counter
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import metrics
from app.db.repositories.connections import ConnectionRepository
from app.db.repositories.events import EventRepository
from app.db.repositories.plans import PlanRepository
from app.db.repositories.standing_orders import StandingOrderRepository
from app.models.action import Action, ActionDependency
from app.models.enums import ActionStatus, PlanStatus
from app.models.event import EventEntity, LifeEvent
from app.models.plan import Plan
from app.models.user import User
from app.schemas.compiled_rule import CompiledRule, EntityCondition
from app.services.action_registry import ACTION_REGISTRY
from app.services.approvals import ApprovalService
from app.services.audit import AuditService
from app.services.plan_customizer import PlanCustomizer
from app.services.plan_graph import PlanGraph
from app.services.policy_engine import PolicyEngine
from app.workflows import build_workflow

logger = logging.getLogger(__name__)


class PlanningEventNotFoundError(Exception):
    """The requested event is absent or belongs to another user."""


class NoMatchingStandingOrderError(Exception):
    """No enabled compiled rule applies to the requested life event."""


class PlanningService:
    """Own the complete match, build, customize, policy, and persistence transaction."""

    def __init__(
        self,
        session: AsyncSession,
        customizer: PlanCustomizer | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._plans = PlanRepository(session)
        self._orders = StandingOrderRepository(session)
        self._connections = ConnectionRepository(session)
        self._customizer = customizer or PlanCustomizer()
        self._policy = policy_engine or PolicyEngine()

    async def create(self, user: User, event_id: UUID, *, replay: bool = False) -> Plan:
        started = perf_counter()
        event = await self._events.get_life(user.id, event_id)
        if event is None:
            metrics.observe("plans", "failed", perf_counter() - started)
            raise PlanningEventNotFoundError
        if not replay:
            existing = await self._plans.latest_for_event(user.id, event_id)
            if existing is not None:
                self._observe("existing", started, event.id, existing.id)
                return existing
        rules = await self._all_matching_rules(user.id, event)
        if not rules:
            metrics.observe("plans", "failed", perf_counter() - started)
            raise NoMatchingStandingOrderError("No enabled standing order matches this event")
        # Merge graphs from all matching standing orders.
        combined_actions: list = []
        combined_rationale_parts: list[str] = []
        any_fallback = False
        for rule in rules:
            graph = build_workflow(event, rule)
            customization = await self._customizer.customize(graph)
            combined_actions.extend(customization.graph.actions)
            combined_rationale_parts.append(customization.rationale)
            if customization.used_fallback:
                any_fallback = True
        from app.services.plan_graph import PlanGraph
        try:
            merged_graph = PlanGraph.from_actions(combined_actions)
        except Exception:
            merged_graph = build_workflow(event, rules[0])
        primary_rule = rules[0]
        return await self._persist(
            user, event, primary_rule, merged_graph, " | ".join(combined_rationale_parts), started,
            customization_fallback=any_fallback,
        )

    async def plan(self, user: User, event_id: UUID, *, replay: bool = False) -> Plan:
        """Compatibility alias for callers that name this operation ``plan``."""
        return await self.create(user, event_id, replay=replay)

    async def _all_matching_rules(self, user_id: UUID, event: LifeEvent) -> list[CompiledRule]:
        """Return ALL enabled standing orders that match this event (not just the first)."""
        matched: list[CompiledRule] = []
        for order in await self._orders.list_matchable(user_id):
            if order.compiled_rule is None:
                continue
            try:
                rule = CompiledRule.model_validate(order.compiled_rule)
            except ValidationError:
                continue
            if event.type in rule.trigger_event_types and _conditions_match(
                rule.entity_conditions, event.entities
            ):
                matched.append(rule)
        return matched

    async def _persist(
        self,
        user: User,
        event: LifeEvent,
        rule: CompiledRule,
        graph: PlanGraph,
        rationale: str,
        started: float,
        *,
        customization_fallback: bool = False,
    ) -> Plan:
        connections = await self._connections.list_connected(user.id)
        plan = Plan(
            user_id=user.id,
            source_event_id=event.id,
            objective=rule.explanation,
            summary=event.summary,
            planner_rationale=rationale,
            status=PlanStatus.POLICY_CHECKED,
            is_shadow=user.default_autonomy.value == "observe",
        )
        # Store fallback flag so the API can surface it
        if customization_fallback:
            plan.planner_rationale = f"[fallback] {rationale}"
        try:
            await self._plans.add(plan)
            actions_by_key: dict[str, Action] = {}
            actions: list[Action] = []
            for candidate in graph.ordered_actions:
                decision = self._policy.evaluate(
                    candidate,
                    user.default_autonomy,
                    connections,
                    template_mode=candidate.approval_mode,
                    category_behaviors=user.autonomy_preferences,
                )
                action = Action(
                    plan=plan,
                    action_type=candidate.action_type,
                    connector=(
                        candidate.connector or ACTION_REGISTRY.get(candidate.action_type).connector
                    ),
                    input=dict(candidate.input),
                    status=decision.status,
                    risk_level=(
                        candidate.risk_level
                        or ACTION_REGISTRY.get(candidate.action_type).default_risk
                    ),
                    requires_approval=decision.requires_approval,
                    policy_reason=decision.reason.value,
                    idempotency_key=f"plan:{plan.id}:action:{candidate.action_key}",
                )
                actions_by_key[candidate.action_key] = action
                actions.append(action)
            await self._plans.add_actions(actions)
            dependencies = [
                ActionDependency(
                    action_id=actions_by_key[action.action_key].id,
                    depends_on_action_id=actions_by_key[dependency].id,
                )
                for action in graph.ordered_actions
                for dependency in action.depends_on
            ]
            await self._plans.add_dependencies(dependencies)
            await ApprovalService(self._session).create_for_actions(actions)
            audit = AuditService(self._session)
            await audit.append(
                user_id=user.id,
                life_event_id=event.id,
                plan_id=plan.id,
                event_name="plan_created",
                actor_type="system",
                payload={"action_count": len(actions)},
            )
            for action in actions:
                await audit.append(
                    user_id=user.id,
                    life_event_id=event.id,
                    plan_id=plan.id,
                    action_id=action.id,
                    event_name="action_policy_evaluated",
                    actor_type="system",
                    payload={"status": action.status.value, "reason": action.policy_reason or ""},
                )
            if any(action.status is ActionStatus.WAITING_APPROVAL for action in actions):
                plan.status = PlanStatus.WAITING_APPROVAL
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            metrics.observe("plans", "failed", perf_counter() - started)
            raise
        persisted = await self._plans.get(user.id, plan.id) or plan
        self._observe("created", started, event.id, persisted.id)
        return persisted

    @staticmethod
    def _observe(outcome: str, started: float, event_id: UUID, plan_id: UUID) -> None:
        duration = perf_counter() - started
        metrics.observe("plans", outcome, duration)
        logger.info(
            "plan creation completed",
            extra={
                "event_id": str(event_id),
                "plan_id": str(plan_id),
                "duration_ms": duration * 1000,
            },
        )


def _conditions_match(
    conditions: Iterable[EntityCondition], entities: Iterable[EventEntity]
) -> bool:
    return all(_condition_matches(condition, entities) for condition in conditions)


def _condition_matches(condition: EntityCondition, entities: Iterable[EventEntity]) -> bool:
    values = [value for entity in entities for value in _entity_values(entity, condition.field)]
    if condition.operator == "exists":
        return bool(values)
    if condition.operator == "equals":
        return any(_contains_value(value, condition.value, exact=True) for value in values)
    return any(_contains_value(value, condition.value, exact=False) for value in values)


def _entity_values(entity: EventEntity, field: str) -> list[object]:
    parts = field.split(".")
    if entity.kind != parts[0]:
        return []
    value: object = entity.value
    for part in parts[1:]:
        if not isinstance(value, Mapping) or part not in value:
            return []
        value = value[part]
    return [value]


def _contains_value(value: object, expected: object, *, exact: bool) -> bool:
    if exact:
        if value == expected:
            return True
    elif (
        isinstance(value, str)
        and expected is not None
        and str(expected).casefold() in value.casefold()
    ):
        return True
    elif isinstance(value, list | tuple) and any(
        _contains_value(item, expected, exact=False) for item in value
    ):
        return True
    if isinstance(value, Mapping):
        return any(_contains_value(item, expected, exact=exact) for item in value.values())
    if isinstance(value, list | tuple):
        return any(_contains_value(item, expected, exact=exact) for item in value)
    return False
