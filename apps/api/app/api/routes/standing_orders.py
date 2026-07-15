"""Authenticated CRUD, compilation, and simulation for standing orders."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.db.session import get_session
from app.models.standing_order import StandingOrder
from app.models.user import User
from app.schemas.standing_order import (
    StandingOrderCreate,
    StandingOrderRead,
    StandingOrderSimulation,
    StandingOrderSimulationInput,
    StandingOrderUpdate,
)
from app.services.ai import AINotConfiguredError, build_ai_provider
from app.services.ai.base import AIProvider
from app.services.rule_simulator import RuleSimulator
from app.services.standing_order_compiler import StandingOrderCompiler
from app.services.standing_orders import (
    StandingOrderCannotEnableError,
    StandingOrderNotFoundError,
    StandingOrderService,
)

router = APIRouter(prefix="/api/v1/standing-orders", tags=["standing-orders"])


def get_ai_provider() -> AIProvider:
    try:
        return build_ai_provider(get_settings())
    except AINotConfiguredError:
        raise HTTPException(status_code=503, detail="AI compilation is not configured") from None


def get_standing_order_service(
    session: AsyncSession = Depends(get_session), provider: AIProvider = Depends(get_ai_provider)
) -> StandingOrderService:
    return StandingOrderService(session, StandingOrderCompiler(provider), RuleSimulator(provider))


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Standing order not found")


@router.get("", response_model=list[StandingOrderRead])
async def list_orders(
    current_user: User = Depends(get_current_user),
    service: StandingOrderService = Depends(get_standing_order_service),
) -> list[StandingOrder]:
    return await service.list(current_user.id)


@router.post("", response_model=StandingOrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: StandingOrderCreate,
    current_user: User = Depends(get_current_user),
    service: StandingOrderService = Depends(get_standing_order_service),
) -> StandingOrder:
    return await service.create(current_user.id, payload.instruction)


@router.post("/{order_id}/compile", response_model=StandingOrderRead)
async def compile_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StandingOrderService = Depends(get_standing_order_service),
) -> StandingOrder:
    try:
        return await service.compile(current_user.id, order_id)
    except StandingOrderNotFoundError:
        raise not_found() from None


@router.post("/{order_id}/simulate", response_model=StandingOrderSimulation)
async def simulate_order(
    order_id: UUID,
    payload: StandingOrderSimulationInput,
    current_user: User = Depends(get_current_user),
    service: StandingOrderService = Depends(get_standing_order_service),
) -> StandingOrderSimulation:
    try:
        result = await service.simulate(current_user.id, order_id, payload)
    except StandingOrderNotFoundError:
        raise not_found() from None
    except StandingOrderCannotEnableError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return StandingOrderSimulation(**result.__dict__)


@router.get("/{order_id}", response_model=StandingOrderRead)
async def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StandingOrderService = Depends(get_standing_order_service),
) -> StandingOrder:
    try:
        return await service.get(current_user.id, order_id)
    except StandingOrderNotFoundError:
        raise not_found() from None


@router.patch("/{order_id}", response_model=StandingOrderRead)
async def update_order(
    order_id: UUID,
    payload: StandingOrderUpdate,
    current_user: User = Depends(get_current_user),
    service: StandingOrderService = Depends(get_standing_order_service),
) -> StandingOrder:
    try:
        return await service.update(current_user.id, order_id, payload)
    except StandingOrderNotFoundError:
        raise not_found() from None
    except StandingOrderCannotEnableError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    service: StandingOrderService = Depends(get_standing_order_service),
) -> Response:
    try:
        await service.delete(current_user.id, order_id)
    except StandingOrderNotFoundError:
        raise not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
