"""User-scoped count and activity projections for the dashboard."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, select
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
    # Travel actions
    "travel.create_calendar_event": 5,
    "travel.create_folder": 3,
    "travel.get_weather": 4,
    "travel.generate_itinerary": 12,
    "travel.generate_packing_checklist": 8,
    "travel.generate_documents": 15,
    "travel.save_ticket": 3,
    "travel.upload_itinerary": 4,
    "travel.upload_packing_checklist": 4,
    "travel.notify_family": 5,
    # Client actions
    "client.create_folder": 3,
    "client.create_calendar_event": 5,
    "client.generate_documents": 20,
    "client.create_repository": 10,
    "client.notify_client": 8,
    "client.send_proposal": 12,
    # Salary / finance actions
    "salary.create_budget_spreadsheet": 15,
    "salary.notify_allocations": 5,
    "salary.generate_summary": 10,
    # Subscription actions
    "subscription.cancel": 8,
    "subscription.check_renewal": 5,
}
_DEFAULT_ACTION_MINUTES = 5


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditService(session)

    async def summary(self, user_id: UUID) -> DashboardSummary:
        now = datetime.now(UTC)
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        action_totals = (
            select(
                func.coalesce(
                    func.sum(
                        case((Action.status == ActionStatus.COMPLETED, 1), else_=0)
                    ),
                    0,
                ).label("actions_completed"),
                func.coalesce(
                    func.sum(case((Action.status == ActionStatus.FAILED, 1), else_=0)), 0
                ).label("failed_actions"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Action.status == ActionStatus.COMPLETED,
                                case(
                                    _ACTION_MINUTES,
                                    value=Action.action_type,
                                    else_=_DEFAULT_ACTION_MINUTES,
                                ),
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("time_saved_minutes"),
            )
            .select_from(Action)
            .join(Plan)
            .where(Plan.user_id == user_id)
            .subquery()
        )
        events_today = (
            select(func.count())
            .select_from(LifeEvent)
            .where(LifeEvent.user_id == user_id, LifeEvent.created_at >= start_today)
            .scalar_subquery()
        )
        pending_approvals = (
            select(func.count())
            .select_from(Approval)
            .join(Action)
            .join(Plan)
            .where(
                Plan.user_id == user_id,
                Approval.decision.is_(None),
                Approval.expires_at > now,
            )
            .scalar_subquery()
        )
        result = (
            await self._session.execute(
                select(
                    events_today.label("events_today"),
                    action_totals.c.actions_completed,
                    pending_approvals.label("pending_approvals"),
                    action_totals.c.failed_actions,
                    action_totals.c.time_saved_minutes,
                )
            )
        ).one()
        return DashboardSummary(
            events_today=int(result.events_today),
            actions_completed=int(result.actions_completed),
            pending_approvals=int(result.pending_approvals),
            failed_actions=int(result.failed_actions),
            time_saved_minutes=int(result.time_saved_minutes),
        )

    async def activity(self, user_id: UUID, *, cursor: str | None, limit: int) -> AuditTimeline:
        return await self._audit.activity(user_id, cursor=cursor, limit=limit)
