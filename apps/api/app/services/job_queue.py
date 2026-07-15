"""Transactional PostgreSQL-backed durable job queue."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.jobs import JobRepository
from app.models.action import Action
from app.models.enums import JobStatus
from app.models.job import Job


class JobQueue:
    def __init__(self, session: AsyncSession, *, lock_timeout_seconds: int = 300) -> None:
        self._session = session
        self._jobs = JobRepository(session)
        self._lock_timeout = timedelta(seconds=lock_timeout_seconds)

    async def enqueue_action(
        self, action: Action, *, run_at: datetime | None = None, retry_key: str | None = None
    ) -> Job:
        suffix = f":{retry_key}" if retry_key else ""
        return await self.enqueue(
            job_type="execute_action",
            action_id=action.id,
            payload={"action_id": str(action.id)},
            idempotency_key=f"execute:{action.idempotency_key}{suffix}",
            run_at=run_at,
        )

    async def enqueue(
        self,
        *,
        job_type: str,
        idempotency_key: str,
        action_id: UUID | None = None,
        payload: dict[str, object] | None = None,
        run_at: datetime | None = None,
    ) -> Job:
        existing = await self._jobs.get_by_key(idempotency_key)
        if existing is not None:
            return existing
        job = Job(
            job_type=job_type,
            action_id=action_id,
            payload=payload or {},
            status=JobStatus.QUEUED,
            run_at=run_at or datetime.now(UTC),
            idempotency_key=idempotency_key,
        )
        try:
            async with self._session.begin_nested():
                await self._jobs.add(job)
        except IntegrityError:
            existing = await self._jobs.get_by_key(idempotency_key)
            if existing is None:
                raise
            return existing
        await self._session.commit()
        return job

    async def claim_next(self, lock_owner: str, *, now: datetime | None = None) -> Job | None:
        now = now or datetime.now(UTC)
        job = await self._jobs.claim_next(now, lock_owner, now - self._lock_timeout)
        await self._session.commit()
        return job

    async def complete(self, job: Job) -> None:
        job.status = JobStatus.COMPLETED
        job.lock_owner = None
        job.locked_at = None
        job.last_error = None
        await self._session.commit()

    async def schedule_retry(self, job: Job, run_at: datetime, error: str) -> None:
        job.status = JobStatus.RETRYING
        job.run_at = run_at
        job.lock_owner = None
        job.locked_at = None
        job.last_error = error
        await self._session.commit()

    async def dead_letter(self, job: Job, error: str) -> None:
        job.status = JobStatus.DEAD_LETTER
        job.lock_owner = None
        job.locked_at = None
        job.last_error = error
        await self._session.commit()

    async def recover_abandoned_locks(self, *, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        count = await self._jobs.release_abandoned_locks(now - self._lock_timeout)
        await self._session.commit()
        return count
