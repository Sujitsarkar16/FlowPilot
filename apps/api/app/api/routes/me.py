"""Current authenticated user endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.dependencies.auth import get_current_user
from app.models.enums import AutonomyLevel, UserRole
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["auth"])


class CurrentUserResponse(BaseModel):
    """Safe profile projection that intentionally excludes authentication secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    display_name: str | None
    role: UserRole
    default_autonomy: AutonomyLevel


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the profile bound to the authenticated local session."""
    return current_user
