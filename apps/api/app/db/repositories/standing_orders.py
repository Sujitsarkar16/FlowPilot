"""Explicit user-scoped standing-order queries."""

from collections.abc import Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CompilationStatus
from app.models.standing_order import StandingOrder


class StandingOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID, order_id: UUID) -> StandingOrder | None:
        return cast(
            StandingOrder | None,
            await self.session.scalar(
                select(StandingOrder).where(
                    StandingOrder.id == order_id, StandingOrder.user_id == user_id
                )
            ),
        )

    async def list(self, user_id: UUID, *, enabled_only: bool = False) -> list[StandingOrder]:
        statement = select(StandingOrder).where(StandingOrder.user_id == user_id)
        if enabled_only:
            statement = statement.where(StandingOrder.enabled.is_(True))
        return list(
            await self.session.scalars(
                statement.order_by(StandingOrder.created_at, StandingOrder.id)
            )
        )

    async def add(self, order: StandingOrder) -> StandingOrder:
        self.session.add(order)
        await self.session.flush()
        return order

    async def list_matchable(self, user_id: UUID) -> Sequence[StandingOrder]:
        """Return enabled, successfully compiled rules in deterministic match order."""
        statement = (
            select(StandingOrder)
            .where(
                StandingOrder.user_id == user_id,
                StandingOrder.enabled.is_(True),
                StandingOrder.compilation_status == CompilationStatus.COMPILED,
                StandingOrder.compiled_rule.is_not(None),
            )
            .order_by(StandingOrder.created_at, StandingOrder.id)
        )
        return list(await self.session.scalars(statement))
