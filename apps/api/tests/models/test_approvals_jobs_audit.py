from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.approval import Approval
from app.models.enums import ApprovalDecision, JobStatus
from app.models.job import Job


@pytest.mark.asyncio
async def test_one_action_has_one_active_approval(session: object) -> None:
    action_id = uuid4()
    session.add_all(
        [
            Approval(action_id=action_id, expires_at=datetime.now(UTC) + timedelta(hours=1)),
            Approval(action_id=action_id, expires_at=datetime.now(UTC) + timedelta(hours=1)),
        ]
    )  # type: ignore[attr-defined]
    with pytest.raises(IntegrityError):
        await session.commit()  # type: ignore[attr-defined]


def test_audit_is_append_only_at_repository_surface() -> None:
    from app.db.repositories.audit import AuditRepository

    assert not hasattr(AuditRepository, "update") and not hasattr(AuditRepository, "delete")


def test_job_can_be_scheduled_in_the_future() -> None:
    job = Job(
        job_type="execute_action",
        payload={},
        status=JobStatus.QUEUED,
        run_at=datetime.now(UTC) + timedelta(days=1),
        idempotency_key="future",
    )
    assert job.run_at > datetime.now(UTC)


def test_approval_decision_is_optional_until_decided() -> None:
    approval = Approval(action_id=uuid4(), expires_at=datetime.now(UTC) + timedelta(hours=1))
    assert approval.decision is None
    approval.decision = ApprovalDecision.APPROVED
    assert approval.decision is ApprovalDecision.APPROVED
