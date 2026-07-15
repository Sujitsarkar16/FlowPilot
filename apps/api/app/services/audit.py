"""Append-only, redacted audit ledger service."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import request_id_context
from app.db.repositories.audit import AuditRepository
from app.db.repositories.events import Cursor
from app.models.audit import AuditEntry
from app.schemas.audit import AuditEntryRead, AuditTimeline
from app.services.audit_redaction import redact


def _encode_cursor(entry: AuditEntry) -> str:
    return urlsafe_b64encode(f"{entry.created_at.isoformat()}|{entry.id}".encode()).decode()


def _decode_cursor(cursor: str) -> Cursor:
    raw = urlsafe_b64decode(cursor.encode()).decode()
    created_at, entry_id = raw.split("|", 1)
    return datetime.fromisoformat(created_at), UUID(entry_id)


class AuditService:
    """Writes are append-only; callers own the surrounding transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditRepository(session)

    def append_pending(
        self,
        *,
        user_id: UUID,
        event_name: str,
        actor_type: str,
        payload: dict[str, object] | None = None,
        life_event_id: UUID | None = None,
        plan_id: UUID | None = None,
        action_id: UUID | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            user_id=user_id,
            life_event_id=life_event_id,
            plan_id=plan_id,
            action_id=action_id,
            event_name=event_name,
            actor_type=actor_type,
            request_id=request_id_context.get(),
            payload=redact(payload or {}),
        )
        self._session.add(entry)
        return entry

    async def append(
        self,
        *,
        user_id: UUID,
        event_name: str,
        actor_type: str,
        payload: dict[str, object] | None = None,
        life_event_id: UUID | None = None,
        plan_id: UUID | None = None,
        action_id: UUID | None = None,
    ) -> AuditEntry:
        entry = self.append_pending(
            user_id=user_id,
            event_name=event_name,
            actor_type=actor_type,
            payload=payload,
            life_event_id=life_event_id,
            plan_id=plan_id,
            action_id=action_id,
        )
        await self._session.flush()
        return entry

    async def timeline(
        self, user_id: UUID, event_id: UUID, *, cursor: str | None, limit: int
    ) -> AuditTimeline:
        parsed = _decode_cursor(cursor) if cursor else None
        entries = await self._audit.list_for_event(user_id, event_id, parsed, limit + 1)
        return self._page(entries, limit)

    async def activity(self, user_id: UUID, *, cursor: str | None, limit: int) -> AuditTimeline:
        parsed = _decode_cursor(cursor) if cursor else None
        entries = await self._audit.list_for_user(user_id, parsed, limit + 1)
        return self._page(entries, limit)

    @staticmethod
    def _page(entries: list[AuditEntry], limit: int) -> AuditTimeline:
        page = entries[:limit]
        return AuditTimeline(
            items=[AuditEntryRead.model_validate(entry) for entry in page],
            next_cursor=_encode_cursor(page[-1]) if len(entries) > limit and page else None,
        )
