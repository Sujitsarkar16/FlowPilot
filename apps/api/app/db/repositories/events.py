"""Explicit raw- and life-event queries."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.action import Action
from app.models.enums import ActionStatus, PlanStatus
from app.models.event import LifeEvent, RawEvent
from app.models.event_attachment import EventAttachment
from app.models.plan import Plan

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

    async def lock_life_for_delete(self, user_id: UUID, event_id: UUID) -> LifeEvent | None:
        statement = (
            select(LifeEvent)
            .where(LifeEvent.id == event_id, LifeEvent.user_id == user_id)
            .with_for_update()
        )
        return cast(LifeEvent | None, await self.session.scalar(statement))

    async def has_active_work(self, user_id: UUID, event_id: UUID) -> bool:
        active_plans = (PlanStatus.RUNNING, PlanStatus.WAITING_APPROVAL)
        active_actions = (
            ActionStatus.WAITING_APPROVAL,
            ActionStatus.APPROVED,
            ActionStatus.QUEUED,
            ActionStatus.RUNNING,
        )
        statement = (
            select(Plan.id)
            .outerjoin(Action, Action.plan_id == Plan.id)
            .where(
                Plan.user_id == user_id,
                Plan.source_event_id == event_id,
                or_(Plan.status.in_(active_plans), Action.status.in_(active_actions)),
            )
            .limit(1)
        )
        return await self.session.scalar(statement) is not None

    async def delete_owned_aggregate(
        self, user_id: UUID, event_id: UUID, raw_event_id: UUID
    ) -> bool:
        life_statement = (
            delete(LifeEvent)
            .where(
                LifeEvent.id == event_id,
                LifeEvent.user_id == user_id,
                LifeEvent.raw_event_id == raw_event_id,
            )
            .returning(LifeEvent.id)
        )
        if await self.session.scalar(life_statement) is None:
            return False
        raw_statement = (
            delete(RawEvent)
            .where(RawEvent.id == raw_event_id, RawEvent.user_id == user_id)
            .returning(RawEvent.id)
        )
        return await self.session.scalar(raw_statement) is not None

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
                    LifeEvent.created_at < created_at,
                    (LifeEvent.created_at == created_at) & (LifeEvent.id < event_id),
                )
            )
        statement = statement.order_by(LifeEvent.created_at.desc(), LifeEvent.id.desc()).limit(
            limit
        )
        return list(await self.session.scalars(statement))

    async def get_life_by_raw(self, user_id: UUID, raw_event_id: UUID) -> LifeEvent | None:
        statement = (
            select(LifeEvent)
            .options(selectinload(LifeEvent.entities))
            .where(LifeEvent.user_id == user_id, LifeEvent.raw_event_id == raw_event_id)
        )
        return cast(LifeEvent | None, await self.session.scalar(statement))

    async def list_attachments(self, user_id: UUID, event_id: UUID) -> list[EventAttachment]:
        statement = (
            select(EventAttachment)
            .where(
                EventAttachment.user_id == user_id,
                EventAttachment.life_event_id == event_id,
            )
            .order_by(EventAttachment.created_at.asc(), EventAttachment.id.asc())
        )
        return list(await self.session.scalars(statement))

    async def get_attachment(
        self, user_id: UUID, event_id: UUID, attachment_id: UUID
    ) -> EventAttachment | None:
        statement = select(EventAttachment).where(
            EventAttachment.id == attachment_id,
            EventAttachment.user_id == user_id,
            EventAttachment.life_event_id == event_id,
        )
        return cast(EventAttachment | None, await self.session.scalar(statement))

    async def get_attachment_by_hash(
        self, user_id: UUID, event_id: UUID, digest: str
    ) -> EventAttachment | None:
        statement = select(EventAttachment).where(
            EventAttachment.user_id == user_id,
            EventAttachment.life_event_id == event_id,
            EventAttachment.sha256 == digest,
        )
        return cast(EventAttachment | None, await self.session.scalar(statement))

    async def attachment_count(self, user_id: UUID, event_id: UUID) -> int:
        statement = select(func.count(EventAttachment.id)).where(
            EventAttachment.user_id == user_id,
            EventAttachment.life_event_id == event_id,
        )
        return int(await self.session.scalar(statement) or 0)

    async def add_raw(self, event: RawEvent) -> RawEvent:
        self.session.add(event)
        await self.session.flush()
        return event
