"""Append-only audit query surface."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEntry

Cursor = tuple[datetime, UUID]


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, entry: AuditEntry) -> AuditEntry:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_for_event(
        self, user_id: UUID, event_id: UUID, cursor: Cursor | None, limit: int
    ) -> list[AuditEntry]:
        statement = select(AuditEntry).where(
            AuditEntry.user_id == user_id, AuditEntry.life_event_id == event_id
        )
        if cursor:
            created_at, entry_id = cursor
            statement = statement.where(
                or_(
                    AuditEntry.created_at > created_at,
                    (AuditEntry.created_at == created_at) & (AuditEntry.id > entry_id),
                )
            )
        return list(
            await self.session.scalars(
                statement.order_by(AuditEntry.created_at, AuditEntry.id).limit(limit)
            )
        )

    async def list_for_user(
        self, user_id: UUID, cursor: Cursor | None, limit: int
    ) -> list[AuditEntry]:
        statement = select(AuditEntry).where(AuditEntry.user_id == user_id)
        if cursor:
            created_at, entry_id = cursor
            statement = statement.where(
                or_(
                    AuditEntry.created_at > created_at,
                    (AuditEntry.created_at == created_at) & (AuditEntry.id > entry_id),
                )
            )
        return list(
            await self.session.scalars(
                statement.order_by(AuditEntry.created_at, AuditEntry.id).limit(limit)
            )
        )
