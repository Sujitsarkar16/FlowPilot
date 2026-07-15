"""Idempotent ingestion of normalized events into ``raw_events``."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.events import EventRepository
from app.models.enums import RawEventStatus
from app.models.event import RawEvent
from app.schemas.raw_sources import NormalizedEvent
from app.services.audit import AuditService
from app.services.event_fingerprint import compute_event_fingerprint


@dataclass(frozen=True)
class IngestionResult:
    raw_event: RawEvent
    is_duplicate: bool


class EventIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)

    async def ingest(
        self,
        user_id: UUID,
        normalized: NormalizedEvent,
        *,
        idempotency_key: str | None = None,
    ) -> IngestionResult:
        """Insert one raw event per unique fingerprint; replays are no-ops."""
        fingerprint = compute_event_fingerprint(
            normalized.source, normalized.source_event_id, normalized.fingerprint_fields
        )
        existing = await self._events.get_by_fingerprint(
            user_id, normalized.source.value, fingerprint
        )
        if existing is not None:
            return IngestionResult(existing, is_duplicate=True)

        raw = RawEvent(
            user_id=user_id,
            source=normalized.source,
            source_event_id=normalized.source_event_id,
            event_type=normalized.event_type,
            fingerprint=fingerprint,
            status=RawEventStatus.RECEIVED,
            payload={
                "trusted_metadata": normalized.trusted_metadata,
                "untrusted_content": normalized.untrusted_content,
                "attachments": [attachment.model_dump() for attachment in normalized.attachments],
            },
            received_at=normalized.occurred_at,
            idempotency_key=idempotency_key,
        )
        try:
            await self._events.add_raw(raw)
            await AuditService(self._session).append(
                user_id=user_id,
                event_name="event_ingested",
                actor_type="system",
                payload={"raw_event_id": str(raw.id), "source": normalized.source.value},
            )
            await self._session.commit()
        except IntegrityError:
            # A concurrent request won the unique (user, source, fingerprint) race.
            await self._session.rollback()
            duplicate = await self._events.get_by_fingerprint(
                user_id, normalized.source.value, fingerprint
            )
            if duplicate is None:
                raise
            return IngestionResult(duplicate, is_duplicate=True)
        await self._session.refresh(raw)
        return IngestionResult(raw, is_duplicate=False)
