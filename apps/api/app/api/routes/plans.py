"""Authenticated plan creation, explicit execution, and safe cancellation."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_session
from app.models.plan import Plan
from app.models.user import User
from app.schemas.plan import PlanRead
from app.services.ai import AINotConfiguredError, build_ai_provider
from app.services.plan_customizer import PlanCustomizer
from app.services.plan_execution import PlanExecutionError, PlanExecutionService
from app.services.planning import (
    NoMatchingStandingOrderError,
    PlanningEventNotFoundError,
    PlanningService,
)

router = APIRouter(prefix="/api/v1/events", tags=["plans"])
execution_router = APIRouter(prefix="/api/v1/plans", tags=["plans"])


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    replay: bool = False


def get_plan_customizer() -> PlanCustomizer:
    """AI is optional: unavailable AI retains the deterministic template."""
    try:
        return PlanCustomizer(build_ai_provider(get_settings()))
    except AINotConfiguredError:
        return PlanCustomizer()


def get_planning_service(
    session: AsyncSession = Depends(get_session),
    customizer: PlanCustomizer = Depends(get_plan_customizer),
) -> PlanningService:
    return PlanningService(session, customizer)


def get_plan_execution_service(
    session: AsyncSession = Depends(get_session),
) -> PlanExecutionService:
    return PlanExecutionService(session)


@router.post("/{event_id}/plan", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    event_id: UUID,
    payload: PlanCreate,
    current_user: User = Depends(get_current_user),
    service: PlanningService = Depends(get_planning_service),
) -> Plan:
    """Create (or return) the latest plan for an owned life event."""
    try:
        return await service.create(current_user, event_id, replay=payload.replay)
    except PlanningEventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except NoMatchingStandingOrderError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@execution_router.post("/{plan_id}/execute", response_model=PlanRead)
async def execute_plan(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PlanExecutionService = Depends(get_plan_execution_service),
) -> Plan:
    """Explicitly queue ready safe actions, including promoted suggestion plans."""
    try:
        return await service.execute(current_user, plan_id)
    except PlanExecutionError as error:
        if str(error) == "Plan not found":
            raise HTTPException(status_code=404, detail=str(error)) from None
        raise HTTPException(status_code=409, detail=str(error)) from None


@execution_router.post("/{plan_id}/cancel", response_model=PlanRead)
async def cancel_plan(
    plan_id: UUID,
    current_user: User = Depends(get_current_user),
    service: PlanExecutionService = Depends(get_plan_execution_service),
) -> Plan:
    try:
        return await service.cancel(current_user, plan_id)
    except PlanExecutionError as error:
        if str(error) == "Plan not found":
            raise HTTPException(status_code=404, detail=str(error)) from None
        raise HTTPException(status_code=409, detail=str(error)) from None
