"""Plan queueing and cancellation, kept separate from HTTP concerns."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.jobs import JobRepository
from app.db.repositories.plans import PlanRepository
from app.models.action import Action, ActionDependency
from app.models.enums import ActionStatus, PlanStatus
from app.models.plan import Plan
from app.models.user import User
from app.services.job_queue import JobQueue


class PlanExecutionError(Exception):
    """A user-visible plan execution conflict or missing resource."""


class PlanExecutionService:
    def __init__(self, session: AsyncSession, queue: JobQueue | None = None) -> None:
        self._session = session
        self._plans = PlanRepository(session)
        self._jobs = JobRepository(session)
        self._queue = queue or JobQueue(session)

    async def execute(self, user: User, plan_id: UUID) -> Plan:
        plan = await self._plans.get(user.id, plan_id)
        if plan is None:
            raise PlanExecutionError("Plan not found")
        if plan.status is PlanStatus.CANCELLED:
            raise PlanExecutionError("Cancelled plans cannot execute")
        await self.queue_ready_actions(plan)
        return plan

    async def queue_ready_actions(self, plan: Plan) -> list[Action]:
        """Queue every eligible node whose complete dependencies are satisfied."""
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
        cancellable = [
            action
            for action in plan.actions
            if action.status in (ActionStatus.PLANNED, ActionStatus.APPROVED, ActionStatus.QUEUED)
        ]
        for action in cancellable:
            action.status = ActionStatus.CANCELLED
        await self._jobs.cancel_for_actions([action.id for action in cancellable])
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
        """Derive a durable aggregate state after approval or execution changes."""
        statuses = list(
            await self._session.scalars(select(Action.status).where(Action.plan_id == plan.id))
        )
        if statuses and all(
            status in (ActionStatus.COMPLETED, ActionStatus.ROLLED_BACK) for status in statuses
        ):
            plan.status = PlanStatus.COMPLETED
        elif any(status is ActionStatus.FAILED for status in statuses):
            plan.status = (
                PlanStatus.PARTIALLY_COMPLETED
                if any(status is ActionStatus.COMPLETED for status in statuses)
                else PlanStatus.FAILED
            )
        elif any(status is ActionStatus.WAITING_APPROVAL for status in statuses):
            plan.status = PlanStatus.WAITING_APPROVAL
        elif any(
            status in (ActionStatus.APPROVED, ActionStatus.QUEUED, ActionStatus.RUNNING)
            for status in statuses
        ):
            plan.status = PlanStatus.RUNNING
        elif statuses and all(status is ActionStatus.CANCELLED for status in statuses):
            plan.status = PlanStatus.CANCELLED
        else:
            plan.status = PlanStatus.POLICY_CHECKED
