"""Plan promotion, explicit execution, queueing, and cancellation."""

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.connections import ConnectionRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.plans import PlanRepository
from app.models.action import Action, ActionDependency
from app.models.enums import ActionStatus, PlanStatus
from app.models.plan import Plan
from app.models.user import User
from app.services.audit import AuditService
from app.services.job_queue import JobQueue
from app.services.plan_graph import CandidateAction
from app.services.policy_engine import PolicyEngine


class PlanExecutionError(Exception):
    """A user-visible plan execution conflict or missing resource."""


class PlanExecutionService:
    def __init__(self, session: AsyncSession, queue: JobQueue | None = None) -> None:
        self._session = session
        self._plans = PlanRepository(session)
        self._jobs = JobRepository(session)
        self._connections = ConnectionRepository(session)
        self._policy = PolicyEngine()
        self._queue = queue or JobQueue(session)

    async def execute(self, user: User, plan_id: UUID) -> Plan:
        plan = await self._plans.get(user.id, plan_id)
        if plan is None:
            raise PlanExecutionError("Plan not found")
        if plan.status is PlanStatus.CANCELLED:
            raise PlanExecutionError("Cancelled plans cannot execute")
        if plan.is_shadow:
            raise PlanExecutionError("Observe plans must be promoted before execution")
        plan.execution_requested = True
        await self.queue_ready_actions(plan)
        return plan

    async def promote(self, user: User, plan_id: UUID) -> Plan:
        """Promote an Observe plan only after fresh connector and policy checks."""
        plan = await self._plans.get(user.id, plan_id)
        if plan is None:
            raise PlanExecutionError("Plan not found")
        if plan.status is PlanStatus.CANCELLED:
            raise PlanExecutionError("Cancelled plans cannot execute")
        if not plan.is_shadow:
            raise PlanExecutionError("Only Observe plans can be promoted")
        connections = await self._connections.list_connected(user.id)
        newly_waiting: list[Action] = []
        for index, action in enumerate(plan.actions):
            if action.status in (ActionStatus.COMPLETED, ActionStatus.ROLLED_BACK, ActionStatus.CANCELLED):
                continue
            previous = action.status
            template_mode: Literal["automatic", "approval_required", "blocked"] | None = (
                "blocked" if action.policy_reason == "template_blocked" else None
            )
            candidate = CandidateAction(
                action_key=f"promotion.{index}",
                action_type=action.action_type,
                input=action.input,
                risk_level=action.risk_level,
                approval_mode=template_mode,
            )
            decision = self._policy.evaluate(
                candidate,
                user.default_autonomy,
                connections,
                template_mode=template_mode,
                category_behaviors=user.autonomy_preferences,
            )
            action.status = decision.status
            action.requires_approval = decision.requires_approval
            action.policy_reason = decision.reason.value
            if previous is not ActionStatus.WAITING_APPROVAL and decision.status is ActionStatus.WAITING_APPROVAL:
                newly_waiting.append(action)
        if newly_waiting:
            # Imported lazily to avoid the approval service's execution-service dependency cycle.
            from app.services.approvals import ApprovalService

            await ApprovalService(self._session).create_for_actions(newly_waiting)
        plan.is_shadow = False
        plan.execution_requested = True
        await AuditService(self._session).append(
            user_id=user.id,
            life_event_id=plan.source_event_id,
            plan_id=plan.id,
            event_name="shadow_plan_promoted",
            actor_type="user",
            payload={"action_count": len(plan.actions)},
        )
        await self.queue_ready_actions(plan)
        return plan

    async def queue_ready_actions(self, plan: Plan) -> list[Action]:
        """Queue every eligible node whose complete dependencies are satisfied."""
        if plan.is_shadow or not plan.execution_requested:
            return []
        dependencies = await self._dependency_statuses(plan.id)
        ready = [
            action
            for action in plan.actions
            if action.status in (ActionStatus.PLANNED, ActionStatus.APPROVED)
            and all(status is ActionStatus.COMPLETED for status in dependencies.get(action.id, ()))
        ]
        if not ready:
            await self.refresh_status(plan)
            await self._session.commit()
            return []
        for action in ready:
            action.status = ActionStatus.QUEUED
        plan.status = PlanStatus.RUNNING
        await self._session.flush()
        for action in ready:
            await self._queue.enqueue_action(action)
        return ready

    async def cancel(self, user: User, plan_id: UUID) -> Plan:
        plan = await self._plans.get(user.id, plan_id)
        if plan is None:
            raise PlanExecutionError("Plan not found")
        if any(action.status is ActionStatus.COMPLETED for action in plan.actions):
            raise PlanExecutionError("Plans with completed external actions cannot be cancelled")
        if any(action.status is ActionStatus.RUNNING for action in plan.actions):
            raise PlanExecutionError("Wait for running actions to finish before cancelling this plan")
        cancellable = [
            action
            for action in plan.actions
            if action.status
            in (
                ActionStatus.PLANNED,
                ActionStatus.WAITING_APPROVAL,
                ActionStatus.APPROVED,
                ActionStatus.QUEUED,
            )
        ]
        for action in cancellable:
            action.status = ActionStatus.CANCELLED
        await self._jobs.cancel_for_actions([action.id for action in cancellable])
        plan.execution_requested = False
        plan.status = PlanStatus.CANCELLED
        await self._session.commit()
        return plan

    async def _dependency_statuses(self, plan_id: UUID) -> dict[UUID, tuple[ActionStatus, ...]]:
        rows = await self._session.execute(
            select(ActionDependency.action_id, Action.status)
            .join(Action, Action.id == ActionDependency.depends_on_action_id)
            .join(Plan, Plan.id == Action.plan_id)
            .where(Plan.id == plan_id)
        )
        statuses: dict[UUID, list[ActionStatus]] = {}
        for action_id, status in rows:
            statuses.setdefault(action_id, []).append(status)
        return {action_id: tuple(values) for action_id, values in statuses.items()}

    async def refresh_status(self, plan: Plan) -> None:
        statuses = list(await self._session.scalars(select(Action.status).where(Action.plan_id == plan.id)))
        if statuses and all(status in (ActionStatus.COMPLETED, ActionStatus.ROLLED_BACK) for status in statuses):
            plan.status = PlanStatus.COMPLETED
        elif any(status is ActionStatus.FAILED for status in statuses):
            plan.status = PlanStatus.PARTIALLY_COMPLETED if any(status is ActionStatus.COMPLETED for status in statuses) else PlanStatus.FAILED
        elif any(status is ActionStatus.WAITING_APPROVAL for status in statuses):
            plan.status = PlanStatus.WAITING_APPROVAL
        elif any(status in (ActionStatus.APPROVED, ActionStatus.QUEUED, ActionStatus.RUNNING) for status in statuses):
            plan.status = PlanStatus.RUNNING
        elif statuses and all(status is ActionStatus.CANCELLED for status in statuses):
            plan.status = PlanStatus.CANCELLED
        else:
            plan.status = PlanStatus.POLICY_CHECKED
