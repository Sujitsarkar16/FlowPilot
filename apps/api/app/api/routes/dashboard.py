"""Dashboard summaries and recent user activity."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.audit import AuditTimeline
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def get_dashboard_service(session: AsyncSession = Depends(get_session)) -> DashboardService:
    return DashboardService(session)


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    return await service.summary(current_user.id)


@router.get("/feed", response_model=AuditTimeline)
@router.get("/activity", response_model=AuditTimeline)
async def activity(
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> AuditTimeline:
    try:
        return await service.activity(current_user.id, cursor=cursor, limit=limit)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid cursor") from None
