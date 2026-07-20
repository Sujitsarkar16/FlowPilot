"""Manual event submission plus event list and detail endpoints."""

from base64 import b64decode, b64encode
from binascii import Error as BinasciiError
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.db.repositories.events import EventRepository
from app.db.session import get_session
from app.models.enums import LifeEventType
from app.models.event_attachment import EventAttachment
from app.models.user import User
from app.schemas.audit import AuditTimeline
from app.schemas.event import EventDetail, EventList
from app.schemas.event_attachment import (
    EventAttachmentContent,
    EventAttachmentRead,
    EventAttachmentUpload,
)
from app.schemas.manual_event import ManualEventInput, ManualEventResponse
from app.schemas.raw_sources import MAX_ATTACHMENTS, ManualSource
from app.services.ai import AINotConfiguredError, build_ai_provider
from app.services.ai.base import AIProvider
from app.services.audit import AuditService
from app.services.event_ingestion import EventIngestionService
from app.services.event_normalizer import normalize
from app.services.event_pipeline import EventPipelineService
from app.services.event_queries import EventFilters, EventQueryService

router = APIRouter(prefix="/api/v1/events", tags=["events"])

_ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
    "text/markdown",
    "text/plain",
}


def _attachment_read(attachment: EventAttachment) -> EventAttachmentRead:
    return EventAttachmentRead.model_validate(attachment)


def _decode_attachment(payload: EventAttachmentUpload) -> bytes:
    mime_type = payload.mime_type.lower()
    if mime_type not in _ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported attachment type")
    try:
        content = b64decode(payload.content_base64, validate=True)
    except (BinasciiError, ValueError):
        raise HTTPException(
            status_code=422, detail="Attachment content must be valid base64"
        ) from None
    if not content:
        raise HTTPException(status_code=422, detail="Attachment must not be empty")
    if len(content) > get_settings().event_attachment_max_bytes:
        raise HTTPException(status_code=413, detail="Attachment exceeds the file size limit")
    if mime_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Attachment does not match its PDF type")
    if mime_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=422, detail="Attachment does not match its PNG type")
    if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        raise HTTPException(status_code=422, detail="Attachment does not match its JPEG type")
    if (
        mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        and not content.startswith(b"PK\x03\x04")
    ):
        raise HTTPException(status_code=422, detail="Attachment does not match its DOCX type")
    return content


def get_ai_provider() -> AIProvider:
    try:
        return build_ai_provider(get_settings())
    except AINotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI interpretation is not configured",
        ) from None


@router.post("/manual", response_model=ManualEventResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_event(
    payload: ManualEventInput,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> ManualEventResponse:
    """Ingest, classify, and extract entities from a natural-language event."""
    normalized = normalize(
        ManualSource(
            text=payload.text,
            category_hint=payload.category_hint,
            attachments=payload.attachments,
        )
    )
    ingestion = await EventIngestionService(session).ingest(current_user.id, normalized)
    raw = ingestion.raw_event

    if ingestion.is_duplicate:
        existing = await EventRepository(session).get_life_by_raw(current_user.id, raw.id)
        if existing is not None:
            return ManualEventResponse(
                id=existing.id,
                raw_event_id=raw.id,
                type=existing.type,
                status=raw.status,
                is_duplicate=True,
            )

    pipeline = await EventPipelineService(session, provider).process_raw_event(raw, current_user)
    if pipeline.life_event is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event interpretation failed",
        )

    return ManualEventResponse(
        id=pipeline.life_event.id,
        raw_event_id=raw.id,
        type=pipeline.life_event.type,
        status=raw.status,
        is_duplicate=False,
        plan_id=pipeline.plan.id if pipeline.plan else None,
    )


@router.get("", response_model=EventList)
async def list_events(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    type: LifeEventType | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> EventList:
    filters = EventFilters(type_=type.value if type else None, date_from=date_from, date_to=date_to)
    try:
        return await EventQueryService(session).list_events(
            current_user.id, cursor=cursor, limit=limit, filters=filters
        )
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid cursor") from None


@router.post(
    "/{event_id}/attachments",
    response_model=EventAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_event_attachment(
    event_id: UUID,
    payload: EventAttachmentUpload,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventAttachmentRead:
    events = EventRepository(session)
    if await events.get_life(current_user.id, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    content = _decode_attachment(payload)
    digest = sha256(content).hexdigest()
    existing = await events.get_attachment_by_hash(current_user.id, event_id, digest)
    if existing is not None:
        return _attachment_read(existing)
    if await events.attachment_count(current_user.id, event_id) >= MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=409, detail="This event already has the maximum attachments"
        )

    attachment = EventAttachment(
        user_id=current_user.id,
        life_event_id=event_id,
        filename=payload.name,
        mime_type=payload.mime_type.lower(),
        size_bytes=len(content),
        sha256=digest,
        content=content,
    )
    session.add(attachment)
    await AuditService(session).append(
        user_id=current_user.id,
        life_event_id=event_id,
        event_name="event_attachment_added",
        actor_type="user",
        payload={
            "name": attachment.filename,
            "mime_type": attachment.mime_type,
            "size_bytes": attachment.size_bytes,
        },
    )
    await session.commit()
    await session.refresh(attachment)
    return _attachment_read(attachment)


@router.get("/{event_id}/attachments", response_model=list[EventAttachmentRead])
async def list_event_attachments(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EventAttachmentRead]:
    events = EventRepository(session)
    if await events.get_life(current_user.id, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return [
        _attachment_read(attachment)
        for attachment in await events.list_attachments(current_user.id, event_id)
    ]


@router.get(
    "/{event_id}/attachments/{attachment_id}/content", response_model=EventAttachmentContent
)
async def get_event_attachment_content(
    event_id: UUID,
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventAttachmentContent:
    attachment = await EventRepository(session).get_attachment(
        current_user.id, event_id, attachment_id
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return EventAttachmentContent(
        **_attachment_read(attachment).model_dump(),
        content_base64=b64encode(attachment.content).decode("ascii"),
    )


@router.get("/{event_id}/timeline", response_model=AuditTimeline)
async def event_timeline(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> AuditTimeline:
    if await EventRepository(session).get_life(current_user.id, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    try:
        return await AuditService(session).timeline(
            current_user.id, event_id, cursor=cursor, limit=limit
        )
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid cursor") from None


@router.get("/{event_id}", response_model=EventDetail)
async def get_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EventDetail:
    detail = await EventQueryService(session).get_detail(current_user.id, event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return detail


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Permanently remove an owned event aggregate when no work is active."""
    events = EventRepository(session)
    event = await events.lock_life_for_delete(current_user.id, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if await events.has_active_work(current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancel the active plan before deleting this event",
        )

    AuditService(session).append_pending(
        user_id=current_user.id,
        life_event_id=event.id,
        event_name="life_event_deleted",
        actor_type="user",
        payload={"event_type": event.type.value},
    )
    await session.flush()
    if not await events.delete_owned_aggregate(current_user.id, event.id, event.raw_event_id):
        await session.rollback()
        raise HTTPException(status_code=404, detail="Event not found")
    await session.commit()
