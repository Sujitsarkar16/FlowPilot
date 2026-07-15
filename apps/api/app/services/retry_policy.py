"""Bounded, deterministic retry scheduling and manual retry handling."""

from datetime import UTC, datetime, timedelta
from random import Random
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.action import Action
from app.models.enums import ActionStatus
from app.models.plan import Plan
from app.models.user import User
from app.schemas.connector import ConnectorErrorCategory
from app.services.audit import AuditService
from app.services.job_queue import JobQueue


class RetryNotAllowedError(Exception):
    """The requested action cannot be manually retried."""


class RetryPolicy:
    def __init__(self, *, maximum_attempts: int = 3, base_delay_seconds: int = 5) -> None:
        self.maximum_attempts = maximum_attempts
        self.base_delay_seconds = base_delay_seconds

    def should_retry(self, category: ConnectorErrorCategory, attempts: int) -> bool:
        return category is ConnectorErrorCategory.RETRYABLE and attempts < self.maximum_attempts

    def next_run_at(self, job_key: str, attempts: int, now: datetime | None = None) -> datetime:
        now = now or datetime.now(UTC)
        delay = self.base_delay_seconds * (2 ** max(attempts - 1, 0))
        jitter = Random(f"{job_key}:{attempts}").uniform(0, delay * 0.2)
        return now + timedelta(seconds=delay + jitter)


class RetryService:
    def __init__(self, session: AsyncSession, queue: JobQueue | None = None) -> None:
        self._session = session
        self._queue = queue or JobQueue(session)

    async def retry(self, user: User, action_id: UUID) -> Action:
        action = await self._owned_action(user.id, action_id)
        if action is None:
            raise RetryNotAllowedError("Action not found")
        if action.status not in (ActionStatus.FAILED, ActionStatus.CANCELLED):
            raise RetryNotAllowedError("Only failed or cancelled actions can be retried")
        action.status = ActionStatus.QUEUED
        action.last_error = None
        action.completed_at = None
        await AuditService(self._session).append(
            user_id=user.id,
            life_event_id=action.plan.source_event_id,
            plan_id=action.plan_id,
            action_id=action.id,
            event_name="action_retry_requested",
            actor_type="user",
        )
        await self._session.flush()
        await self._queue.enqueue(
            job_type="execute_action",
            action_id=action.id,
            payload={"action_id": str(action.id)},
            idempotency_key=f"execute:{action.idempotency_key}:manual:{action.version}",
        )
        return action

    async def _owned_action(self, user_id: UUID, action_id: UUID) -> Action | None:
        return cast(
            Action | None,
            await self._session.scalar(
                select(Action)
                .join(Plan)
                .options(joinedload(Action.plan))
                .where(Action.id == action_id, Plan.user_id == user_id)
            ),
        )
