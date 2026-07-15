"""User-scoped standing-order lifecycle and compilation service."""

from dataclasses import replace
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.standing_orders import StandingOrderRepository
from app.models.enums import CompilationStatus
from app.models.standing_order import StandingOrder
from app.schemas.compiled_rule import CompiledRule
from app.schemas.standing_order import StandingOrderSimulationInput, StandingOrderUpdate
from app.services.rule_simulator import RuleSimulator, SimulationResult
from app.services.standing_order_compiler import (
    StandingOrderCompilationError,
    StandingOrderCompiler,
)


class StandingOrderNotFoundError(Exception):
    """The order does not belong to the requesting user."""


class StandingOrderCannotEnableError(Exception):
    """Only a valid compilation may be enabled."""


class StandingOrderService:
    def __init__(
        self, session: AsyncSession, compiler: StandingOrderCompiler, simulator: RuleSimulator
    ) -> None:
        self._session = session
        self._orders = StandingOrderRepository(session)
        self._compiler = compiler
        self._simulator = simulator

    async def list(self, user_id: UUID) -> list[StandingOrder]:
        return await self._orders.list(user_id)

    async def get(self, user_id: UUID, order_id: UUID) -> StandingOrder:
        order = await self._orders.get(user_id, order_id)
        if order is None:
            raise StandingOrderNotFoundError
        return order

    async def create(self, user_id: UUID, instruction: str) -> StandingOrder:
        order = await self._orders.add(StandingOrder(user_id=user_id, instruction=instruction))
        await self._compile(order)
        return order

    async def update(
        self, user_id: UUID, order_id: UUID, update: StandingOrderUpdate
    ) -> StandingOrder:
        order = await self.get(user_id, order_id)
        if update.instruction is not None and update.instruction != order.instruction:
            order.instruction = update.instruction
            await self._compile(order)
        if update.enabled is not None:
            self._set_enabled(order, update.enabled)
            await self._session.commit()
            await self._session.refresh(order)
        return order

    async def compile(self, user_id: UUID, order_id: UUID) -> StandingOrder:
        order = await self.get(user_id, order_id)
        await self._compile(order)
        return order

    async def delete(self, user_id: UUID, order_id: UUID) -> None:
        order = await self.get(user_id, order_id)
        await self._session.delete(order)
        await self._session.commit()

    async def simulate(
        self, user_id: UUID, order_id: UUID, payload: StandingOrderSimulationInput
    ) -> SimulationResult:
        order = await self.get(user_id, order_id)
        if (
            order.compiled_rule is None
            or order.compilation_status is not CompilationStatus.COMPILED
        ):
            raise StandingOrderCannotEnableError
        result = await self._simulator.simulate(
            CompiledRule.model_validate(order.compiled_rule), payload.sample_event
        )
        if order.enabled:
            return result
        return replace(
            result,
            matched=False,
            proposed_actions=[],
            warnings=[*result.warnings, "Disabled standing orders cannot match events."],
        )

    async def _compile(self, order: StandingOrder) -> None:
        order.compilation_status = CompilationStatus.PENDING
        order.last_error = None
        try:
            result = await self._compiler.compile(order.instruction)
        except StandingOrderCompilationError as error:
            order.compilation_status = CompilationStatus.FAILED
            order.enabled = False
            order.compiled_rule = None
            order.last_error = str(error)
        else:
            order.compiled_rule = result.rule.model_dump(mode="json")
            order.compilation_status = CompilationStatus.COMPILED
        await self._session.commit()
        await self._session.refresh(order)

    @staticmethod
    def _set_enabled(order: StandingOrder, enabled: bool) -> None:
        if enabled and (
            order.compilation_status is not CompilationStatus.COMPILED
            or order.compiled_rule is None
        ):
            raise StandingOrderCannotEnableError("Compile this standing order successfully first")
        order.enabled = enabled
