"""Authenticated retry and rollback controls for owned actions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_session
from app.models.action import Action
from app.models.user import User
from app.schemas.action import ActionRead
from app.services.retry_policy import RetryNotAllowedError, RetryService
from app.services.rollback import RollbackError, RollbackService
from app.services.runtime_connectors import build_runtime_connector_registry

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])


@router.post("/{action_id}/retry", response_model=ActionRead)
async def retry_action(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Action:
    try:
        return await RetryService(session).retry(current_user, action_id)
    except RetryNotAllowedError as error:
        if str(error) == "Action not found":
            raise HTTPException(status_code=404, detail=str(error)) from None
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/{action_id}/rollback", response_model=ActionRead)
async def rollback_action(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Action:
    try:
        return await RollbackService(
            session, connectors=build_runtime_connector_registry(session)
        ).rollback(current_user, action_id)
    except RollbackError as error:
        if str(error) == "Action not found":
            raise HTTPException(status_code=404, detail=str(error)) from None
        raise HTTPException(status_code=409, detail=str(error)) from None
