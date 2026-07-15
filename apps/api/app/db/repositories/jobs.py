"""Durable job persistence with row-level claims."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobStatus
from app.models.job import Job


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, job_id: UUID) -> Job | None:
        return cast(Job | None, await self.session.get(Job, job_id))

    async def get_by_key(self, idempotency_key: str) -> Job | None:
        return cast(
            Job | None,
            await self.session.scalar(select(Job).where(Job.idempotency_key == idempotency_key)),
        )

    async def list_due(self, now: datetime, limit: int) -> list[Job]:
        statement = select(Job).where(
            Job.status.in_((JobStatus.QUEUED, JobStatus.RETRYING)), Job.run_at <= now
        )
        return list(await self.session.scalars(statement.order_by(Job.run_at, Job.id).limit(limit)))

    async def add(self, job: Job) -> Job:
        self.session.add(job)
        await self.session.flush()
        return job

    async def claim_next(
        self, now: datetime, lock_owner: str, lock_expires_before: datetime
    ) -> Job | None:
        """Claim exactly one due or abandoned job without blocking another worker."""
        statement = (
            select(Job)
            .where(
                or_(
                    (Job.status.in_((JobStatus.QUEUED, JobStatus.RETRYING))) & (Job.run_at <= now),
                    (Job.status == JobStatus.RUNNING) & (Job.locked_at <= lock_expires_before),
                )
            )
            .order_by(Job.run_at, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = cast(Job | None, await self.session.scalar(statement))
        if job is None:
            return None
        job.status = JobStatus.RUNNING
        job.lock_owner = lock_owner
        job.locked_at = now
        job.attempts += 1
        await self.session.flush()
        return job

    async def release_abandoned_locks(self, lock_expires_before: datetime) -> int:
        """Return stale claimed work to the queue for recovery after worker loss."""
        result = await self.session.execute(
            update(Job)
            .where(Job.status == JobStatus.RUNNING, Job.locked_at <= lock_expires_before)
            .values(
                status=JobStatus.RETRYING,
                run_at=lock_expires_before,
                locked_at=None,
                lock_owner=None,
                last_error="Worker lock expired",
            )
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def cancel_for_actions(self, action_ids: list[UUID]) -> None:
        if not action_ids:
            return
        await self.session.execute(
            update(Job)
            .where(
                Job.action_id.in_(action_ids),
                Job.status.in_((JobStatus.QUEUED, JobStatus.RETRYING)),
            )
            .values(
                status=JobStatus.FAILED,
                last_error="Plan cancelled",
                locked_at=None,
                lock_owner=None,
            )
        )
