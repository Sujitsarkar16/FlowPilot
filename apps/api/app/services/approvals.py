"""Approval decisions that safely resume only eligible action work."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.approvals import ApprovalRepository
from app.models.action import Action
from app.models.approval import Approval
from app.models.enums import ActionStatus, ApprovalDecision
from app.models.user import User
from app.services.audit import AuditService
from app.services.plan_execution import PlanExecutionService


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
        if decision not in (ApprovalDecision.APPROVED, ApprovalDecision.REJECTED):
            raise ApprovalConflictError("Approval decisions must approve or reject")
        approval = await self._approvals.get(user.id, approval_id)
        if approval is None:
            raise ApprovalNotFoundError
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
        if decision is ApprovalDecision.APPROVED:
            await execution.queue_ready_actions(action.plan)
        else:
            await self._session.commit()
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
