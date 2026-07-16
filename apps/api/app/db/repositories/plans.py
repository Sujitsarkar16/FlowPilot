"""Explicit user-scoped plan queries."""

from collections.abc import Iterable
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.action import Action, ActionDependency
from app.models.plan import Plan


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID, plan_id: UUID) -> Plan | None:
        statement = (
            select(Plan)
            .options(selectinload(Plan.actions))
            .where(Plan.id == plan_id, Plan.user_id == user_id)
        )
        return cast(Plan | None, await self.session.scalar(statement))

    async def list_for_event(self, user_id: UUID, event_id: UUID) -> list[Plan]:
        statement = select(Plan).where(Plan.user_id == user_id, Plan.source_event_id == event_id)
        return list(await self.session.scalars(statement.order_by(Plan.created_at, Plan.id)))

    async def add(self, plan: Plan) -> Plan:
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def latest_for_event(self, user_id: UUID, event_id: UUID) -> Plan | None:
        statement = (
            select(Plan)
            .options(selectinload(Plan.actions))
            .where(Plan.user_id == user_id, Plan.source_event_id == event_id)
            .order_by(Plan.created_at.desc(), Plan.id.desc())
            .limit(1)
        )
        return cast(Plan | None, await self.session.scalar(statement))

    async def latest_for_events(
        self, user_id: UUID, event_ids: Iterable[UUID]
    ) -> dict[UUID, Plan]:
        ids = list(event_ids)
        if not ids:
            return {}
        ranked = (
            select(
                Plan.id,
                func.row_number()
                .over(
                    partition_by=Plan.source_event_id,
                    order_by=(Plan.created_at.desc(), Plan.id.desc()),
                )
                .label("rank"),
            )
            .where(Plan.user_id == user_id, Plan.source_event_id.in_(ids))
            .subquery()
        )
        statement = (
            select(Plan)
            .join(ranked, Plan.id == ranked.c.id)
            .options(selectinload(Plan.actions))
            .where(ranked.c.rank == 1)
        )
        return {plan.source_event_id: plan for plan in await self.session.scalars(statement)}

    async def add_actions(self, actions: Iterable[Action]) -> list[Action]:
        """Persist actions after their parent plan has been flushed."""
        items = list(actions)
        self.session.add_all(items)
        await self.session.flush()
        return items

    async def add_dependencies(
        self, dependencies: Iterable[ActionDependency]
    ) -> list[ActionDependency]:
        """Persist already-validated action dependency edges."""
        items = list(dependencies)
        self.session.add_all(items)
        await self.session.flush()
        return items
