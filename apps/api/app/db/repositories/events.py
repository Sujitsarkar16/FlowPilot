"""Explicit raw- and life-event queries."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import LifeEvent, RawEvent

Cursor = tuple[datetime, UUID]


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_raw(self, user_id: UUID, event_id: UUID) -> RawEvent | None:
        return cast(
            RawEvent | None,
            await self.session.scalar(
                select(RawEvent).where(RawEvent.id == event_id, RawEvent.user_id == user_id)
            ),
        )

    async def get_by_fingerprint(
        self, user_id: UUID, source: str, fingerprint: str
    ) -> RawEvent | None:
        return cast(
            RawEvent | None,
            await self.session.scalar(
                select(RawEvent).where(
                    RawEvent.user_id == user_id,
                    RawEvent.source == source,
                    RawEvent.fingerprint == fingerprint,
                )
            ),
        )

    async def get_life(self, user_id: UUID, event_id: UUID) -> LifeEvent | None:
        statement = (
            select(LifeEvent)
            .options(selectinload(LifeEvent.entities), selectinload(LifeEvent.raw_event))
            .where(LifeEvent.id == event_id, LifeEvent.user_id == user_id)
        )
        return cast(LifeEvent | None, await self.session.scalar(statement))

    async def list_life(
        self,
        user_id: UUID,
        cursor: Cursor | None,
        limit: int,
        *,
        type_: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[LifeEvent]:
        statement = (
            select(LifeEvent)
            .options(selectinload(LifeEvent.entities))
            .where(LifeEvent.user_id == user_id)
        )
        if type_ is not None:
            statement = statement.where(LifeEvent.type == type_)
        if date_from is not None:
            statement = statement.where(LifeEvent.occurred_at >= date_from)
        if date_to is not None:
            statement = statement.where(LifeEvent.occurred_at <= date_to)
        if cursor:
            created_at, event_id = cursor
            statement = statement.where(
                or_(
                    LifeEvent.created_at > created_at,
                    (LifeEvent.created_at == created_at) & (LifeEvent.id > event_id),
                )
            )
        statement = statement.order_by(LifeEvent.created_at, LifeEvent.id).limit(limit)
        return list(await self.session.scalars(statement))

    async def get_life_by_raw(self, user_id: UUID, raw_event_id: UUID) -> LifeEvent | None:
        statement = (
            select(LifeEvent)
            .options(selectinload(LifeEvent.entities))
            .where(LifeEvent.user_id == user_id, LifeEvent.raw_event_id == raw_event_id)
        )
        return cast(LifeEvent | None, await self.session.scalar(statement))

    async def add_raw(self, event: RawEvent) -> RawEvent:
        self.session.add(event)
        await self.session.flush()
        return event
