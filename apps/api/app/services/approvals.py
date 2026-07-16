"""Approval decisions that safely resume only eligible action work."""

import logging
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import metrics
from app.db.repositories.approvals import ApprovalRepository
from app.models.action import Action
from app.models.approval import Approval
from app.models.enums import ActionStatus, ApprovalDecision
from app.models.user import User
from app.services.audit import AuditService
from app.services.plan_execution import PlanExecutionService

logger = logging.getLogger(__name__)


class ApprovalNotFoundError(Exception):
    """The requested approval is absent or belongs to another user."""


class ApprovalConflictError(Exception):
    """The approval is already decided, expired, or otherwise not actionable."""


class ApprovalService:
    def __init__(
        self, session: AsyncSession, *, expires_in: timedelta = timedelta(hours=24)
    ) -> None:
        self._session = session
        self._approvals = ApprovalRepository(session)
        self._audit = AuditService(session)
        self._expires_in = expires_in

    async def create_for_actions(self, actions: list[Action]) -> list[Approval]:
        """Create durable pending decisions for policy-paused actions in the current transaction."""
        created: list[Approval] = []
        for action in actions:
            if action.status is not ActionStatus.WAITING_APPROVAL:
                continue
            approval = await self._approvals.add(
                Approval(action=action, expires_at=datetime.now(UTC) + self._expires_in)
            )
            await self._audit.append(
                user_id=action.plan.user_id,
                life_event_id=action.plan.source_event_id,
                plan_id=action.plan_id,
                action_id=action.id,
                event_name="approval_requested",
                actor_type="system",
                payload={"policy_reason": action.policy_reason or "approval_required"},
            )
            created.append(approval)
        return created

    async def list_pending(self, user_id: UUID) -> list[Approval]:
        await self._expire_pending(user_id)
        return await self._approvals.list_pending(user_id, datetime.now(UTC))

    async def decide(self, user: User, approval_id: UUID, decision: ApprovalDecision) -> Approval:
        started = perf_counter()
        if decision not in (ApprovalDecision.APPROVED, ApprovalDecision.REJECTED):
            raise ApprovalConflictError("Approval decisions must approve or reject")
        approval = await self._approvals.get(user.id, approval_id)
        if approval is None:
            raise ApprovalNotFoundError
        if approval.action.status is not ActionStatus.WAITING_APPROVAL:
            raise ApprovalConflictError("This approval is no longer required")
        now = datetime.now(UTC)
        if not await self._approvals.decide_if_pending(approval.id, decision, user.id, now):
            await self._session.refresh(approval)
            if await self._approvals.expire_if_pending(approval.id, now):
                await self._finish_expired(approval)
                await self._session.commit()
            if approval.decision is ApprovalDecision.EXPIRED:
                raise ApprovalConflictError("This approval has expired")
            raise ApprovalConflictError("This approval has already been decided")
        await self._session.refresh(approval)
        action = approval.action
        action.status = (
            ActionStatus.APPROVED
            if decision is ApprovalDecision.APPROVED
            else ActionStatus.CANCELLED
        )
        await self._audit.append(
            user_id=user.id,
            life_event_id=action.plan.source_event_id,
            plan_id=action.plan_id,
            action_id=action.id,
            event_name=f"approval_{decision.value}",
            actor_type="user",
            payload={"approval_id": str(approval.id), "policy_reason": action.policy_reason},
        )
        execution = PlanExecutionService(self._session)
        await execution.refresh_status(action.plan)
        should_queue = decision is ApprovalDecision.APPROVED and (
            action.plan.execution_requested
            or (
                user.default_autonomy.value == "safe_actions"
                and not action.plan.is_shadow
            )
        )
        if should_queue:
            action.plan.execution_requested = True
            await execution.queue_ready_actions(action.plan)
        else:
            await self._session.commit()
        duration = perf_counter() - started
        metrics.observe("approvals", decision.value, duration)
        logger.info(
            "approval decided",
            extra={
                "event_id": str(action.plan.source_event_id),
                "plan_id": str(action.plan_id),
                "action_id": str(action.id),
                "duration_ms": duration * 1000,
            },
        )
        return approval

    async def _expire_pending(self, user_id: UUID) -> None:
        now = datetime.now(UTC)
        expired = await self._approvals.list_expired(user_id, now)
        changed = False
        for approval in expired:
            if await self._approvals.expire_if_pending(approval.id, now):
                await self._finish_expired(approval)
                changed = True
        if changed:
            await self._session.commit()

    async def _finish_expired(self, approval: Approval) -> None:
        await self._session.refresh(approval)
        action = approval.action
        action.status = ActionStatus.CANCELLED
        await self._audit.append(
            user_id=action.plan.user_id,
            life_event_id=action.plan.source_event_id,
            plan_id=action.plan_id,
            action_id=action.id,
            event_name="approval_expired",
            actor_type="system",
            payload={"approval_id": str(approval.id)},
        )
        await PlanExecutionService(self._session).refresh_status(action.plan)
