"""Read models for user-scoped dashboard projections."""

from pydantic import BaseModel

from app.schemas.audit import AuditTimeline


class DashboardSummary(BaseModel):
    events_today: int
    actions_completed: int
    pending_approvals: int
    failed_actions: int
    time_saved_minutes: int


DashboardActivity = AuditTimeline
