"""Authenticated user autonomy preferences."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.preferences import PreferencesRead, PreferencesUpdate

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesRead)
async def get_preferences(current_user: User = Depends(get_current_user)) -> PreferencesRead:
    return PreferencesRead.from_user(current_user)


@router.patch("", response_model=PreferencesRead)
async def update_preferences(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PreferencesRead:
    current_user.default_autonomy = payload.autonomy_level
    current_user.autonomy_preferences = payload.stored_categories()
    current_user.daily_message_cap = payload.daily_message_cap
    current_user.daily_calendar_cap = payload.daily_calendar_cap
    await session.commit()
    await session.refresh(current_user)
    return PreferencesRead.from_user(current_user)
