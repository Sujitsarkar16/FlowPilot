"""Authenticated plan creation, promotion, execution, and cancellation."""

import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.db.repositories.plans import PlanRepository
from app.db.session import get_session, get_session_factory
from app.models.action import ActionDependency
from app.models.enums import PlanStatus
from app.models.plan import Plan
from app.models.user import User
from app.schemas.action import ActionRead
from app.schemas.plan import PlanRead
from app.services.action_registry import ACTION_REGISTRY
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

_TERMINAL_PLAN_STATUSES = {
    PlanStatus.COMPLETED,
    PlanStatus.PARTIALLY_COMPLETED,
    PlanStatus.FAILED,
    PlanStatus.CANCELLED,
}


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    replay: bool = False


def get_plan_customizer() -> PlanCustomizer:
    try:
        return PlanCustomizer(build_ai_provider(get_settings()))
    except AINotConfiguredError:
        return PlanCustomizer()


def get_planning_service(
    session: AsyncSession = Depends(get_session),
    customizer: PlanCustomizer = Depends(get_plan_customizer),
) -> PlanningService:
    return PlanningService(session, customizer)


def get_plan_execution_service(session: AsyncSession = Depends(get_session)) -> PlanExecutionService:
    return PlanExecutionService(session)


async def get_stream_user(current_user: User = Depends(get_current_user)) -> User:
    """Use normal bearer authentication for the SSE endpoint."""
    return current_user


async def _read_plan(session: AsyncSession, user: User, plan_id: UUID) -> PlanRead | None:
    plan = await PlanRepository(session).get(user.id, plan_id)
    if plan is None:
        return None
    action_ids = [action.id for action in plan.actions]
    dependencies: dict[UUID, list[UUID]] = {}
    if action_ids:
        result = await session.execute(
            select(ActionDependency.action_id, ActionDependency.depends_on_action_id).where(
                ActionDependency.action_id.in_(action_ids)
            )
        )
        for action_id, depends_on in result:
            dependencies.setdefault(action_id, []).append(depends_on)
    actions = [
        ActionRead.model_validate(action).model_copy(update={
            "depends_on": dependencies.get(action.id, []),
            "rollback_supported": action.status.value == "completed" and ACTION_REGISTRY.get(action.action_type).reversible,
        })
        for action in plan.actions
    ]
    return PlanRead.model_validate(plan).model_copy(update={"actions": actions})


@router.post("/{event_id}/plan", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(event_id: UUID, payload: PlanCreate, current_user: User = Depends(get_current_user), service: PlanningService = Depends(get_planning_service)) -> Plan:
    try:
        return await service.create(current_user, event_id, replay=payload.replay)
    except PlanningEventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found") from None
    except NoMatchingStandingOrderError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@execution_router.get("/{plan_id}", response_model=PlanRead)
async def get_plan(plan_id: UUID, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> PlanRead:
    plan = await _read_plan(session, current_user, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


async def _execute_operation(operation: str, user: User, plan_id: UUID, service: PlanExecutionService) -> Plan:
    try:
        if operation == "execute":
            return await service.execute(user, plan_id)
        if operation == "promote":
            return await service.promote(user, plan_id)
        return await service.cancel(user, plan_id)
    except PlanExecutionError as error:
        raise HTTPException(status_code=404 if str(error) == "Plan not found" else 409, detail=str(error)) from None


@execution_router.post("/{plan_id}/execute", response_model=PlanRead)
async def execute_plan(plan_id: UUID, current_user: User = Depends(get_current_user), service: PlanExecutionService = Depends(get_plan_execution_service)) -> Plan:
    return await _execute_operation("execute", current_user, plan_id, service)


@execution_router.post("/{plan_id}/promote", response_model=PlanRead)
async def promote_plan(plan_id: UUID, current_user: User = Depends(get_current_user), service: PlanExecutionService = Depends(get_plan_execution_service)) -> Plan:
    return await _execute_operation("promote", current_user, plan_id, service)


@execution_router.post("/{plan_id}/cancel", response_model=PlanRead)
async def cancel_plan(plan_id: UUID, current_user: User = Depends(get_current_user), service: PlanExecutionService = Depends(get_plan_execution_service)) -> Plan:
    return await _execute_operation("cancel", current_user, plan_id, service)


@execution_router.get("/{plan_id}/stream")
async def stream_plan_status(
    plan_id: UUID,
    request: Request,
    current_user: User = Depends(get_stream_user),
) -> StreamingResponse:
    """SSE stream of plan + action status updates. Closes when plan reaches a terminal state."""

    async def event_generator() -> AsyncIterator[str]:
        session_factory = get_session_factory()
        poll_interval = 2.0
        max_polls = 300  # 10-minute hard cap
        polls = 0
        while polls < max_polls:
            if await request.is_disconnected():
                break
            try:
                async with session_factory() as session:
                    plan_data = await _read_plan(session, current_user, plan_id)
            except Exception:
                yield "event: error\ndata: {\"error\": \"plan read failed\"}\n\n"
                break
            if plan_data is None:
                yield "event: error\ndata: {\"error\": \"not found\"}\n\n"
                break
            payload = plan_data.model_dump(mode="json")
            yield f"data: {json.dumps(payload)}\n\n"
            if PlanStatus(plan_data.status) in _TERMINAL_PLAN_STATUSES:
                yield "event: done\ndata: {}\n\n"
                break
            polls += 1
            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
