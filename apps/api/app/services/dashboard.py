"""User-scoped count and activity projections for the dashboard."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action import Action
from app.models.approval import Approval
from app.models.enums import ActionStatus
from app.models.event import LifeEvent
from app.models.plan import Plan
from app.schemas.audit import AuditTimeline
from app.schemas.dashboard import DashboardSummary
from app.services.audit import AuditService

_ACTION_MINUTES = {
    "travel.create_calendar_event": 5,
    "travel.create_folder": 3,
    "travel.get_weather": 4,
    "travel.generate_itinerary": 12,
    "travel.generate_packing_checklist": 8,
}
_DEFAULT_ACTION_MINUTES = 5


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditService(session)

    async def summary(self, user_id: UUID) -> DashboardSummary:
        start_today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        events_today = await self._count(
            select(func.count())
            .select_from(LifeEvent)
            .where(LifeEvent.user_id == user_id, LifeEvent.created_at >= start_today)
        )
        actions_completed = await self._count_actions(user_id, ActionStatus.COMPLETED)
        failed_actions = await self._count_actions(user_id, ActionStatus.FAILED)
        pending_approvals = await self._count(
            select(func.count())
            .select_from(Approval)
            .join(Action)
            .join(Plan)
            .where(
                Plan.user_id == user_id,
                Approval.decision.is_(None),
                Approval.expires_at > datetime.now(UTC),
            )
        )
        time_saved = await self._time_saved(user_id)
        return DashboardSummary(
            events_today=events_today,
            actions_completed=actions_completed,
            pending_approvals=pending_approvals,
            failed_actions=failed_actions,
            time_saved_minutes=time_saved,
        )

    async def activity(self, user_id: UUID, *, cursor: str | None, limit: int) -> AuditTimeline:
        return await self._audit.activity(user_id, cursor=cursor, limit=limit)

    async def _count_actions(self, user_id: UUID, status: ActionStatus) -> int:
        return await self._count(
            select(func.count())
            .select_from(Action)
            .join(Plan)
            .where(Plan.user_id == user_id, Action.status == status)
        )

    async def _time_saved(self, user_id: UUID) -> int:
        rows = await self._session.execute(
            select(Action.action_type, func.count())
            .join(Plan)
            .where(Plan.user_id == user_id, Action.status == ActionStatus.COMPLETED)
            .group_by(Action.action_type)
        )
        return sum(
            _ACTION_MINUTES.get(action_type, _DEFAULT_ACTION_MINUTES) * count
            for action_type, count in rows
        )

    async def _count(self, statement: Select[tuple[int]]) -> int:
        return int((await self._session.scalar(statement)) or 0)
