from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.approval import Approval
from app.models.enums import ActionStatus, ApprovalDecision, PlanStatus
from app.models.job import Job
from app.services.approvals import ApprovalConflictError, ApprovalService
from tests.execution_helpers import action_state


@pytest.mark.asyncio
async def test_approval_queues_once_and_second_decision_loses(session) -> None:
    user, plan, action = await action_state(
        session, status=ActionStatus.WAITING_APPROVAL, plan_status=PlanStatus.WAITING_APPROVAL
    )
    service = ApprovalService(session)
    approval = (await service.create_for_actions([action]))[0]
    await session.commit()

    approved = await service.decide(user, approval.id, ApprovalDecision.APPROVED)

    assert approved.decision is ApprovalDecision.APPROVED
    assert action.status is ActionStatus.QUEUED
    assert plan.status is PlanStatus.RUNNING
    assert len(list(await session.scalars(select(Job)))) == 1
    with pytest.raises(ApprovalConflictError):
        await service.decide(user, approval.id, ApprovalDecision.REJECTED)


@pytest.mark.asyncio
async def test_rejected_and_expired_approvals_cannot_execute(session) -> None:
    user, plan, action = await action_state(
        session, status=ActionStatus.WAITING_APPROVAL, plan_status=PlanStatus.WAITING_APPROVAL
    )
    service = ApprovalService(session)
    rejected = (await service.create_for_actions([action]))[0]
    await session.commit()

    await service.decide(user, rejected.id, ApprovalDecision.REJECTED)
    assert action.status is ActionStatus.CANCELLED
    assert plan.status is PlanStatus.CANCELLED

    expiring_user, _, expiring_action = await action_state(
        session, status=ActionStatus.WAITING_APPROVAL, plan_status=PlanStatus.WAITING_APPROVAL
    )
    expired = Approval(action=expiring_action, expires_at=datetime.now(UTC) - timedelta(seconds=1))
    session.add(expired)
    await session.commit()
    with pytest.raises(ApprovalConflictError, match="expired"):
        await service.decide(expiring_user, expired.id, ApprovalDecision.APPROVED)
    await session.refresh(expired)
    assert expired.decision is ApprovalDecision.EXPIRED
