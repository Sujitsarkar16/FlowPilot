from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import JobStatus
from app.services.job_queue import JobQueue


@pytest.mark.asyncio
async def test_enqueue_is_idempotent_and_two_claims_do_not_receive_the_same_job(session) -> None:
    queue = JobQueue(session)
    first = await queue.enqueue(job_type="execute_action", idempotency_key="same")
    repeated = await queue.enqueue(job_type="execute_action", idempotency_key="same")

    claimed = await queue.claim_next("worker-one")
    other = await queue.claim_next("worker-two")

    assert repeated.id == first.id
    assert claimed is not None and claimed.id == first.id
    assert other is None


@pytest.mark.asyncio
async def test_abandoned_lock_is_recovered_and_claimable(session) -> None:
    queue = JobQueue(session, lock_timeout_seconds=1)
    job = await queue.enqueue(job_type="execute_action", idempotency_key="stale")
    claimed = await queue.claim_next("lost-worker")
    assert claimed is not None
    claimed.locked_at = datetime.now(UTC) - timedelta(seconds=2)
    await session.commit()

    assert await queue.recover_abandoned_locks() == 1
    recovered = await queue.claim_next("replacement")

    assert recovered is not None and recovered.id == job.id
    assert recovered.status is JobStatus.RUNNING
