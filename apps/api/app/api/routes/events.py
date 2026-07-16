"""Manual event submission plus event list and detail endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.db.repositories.events import EventRepository
from app.db.session import get_session
from app.models.enums import LifeEventType
from app.models.user import User
from app.schemas.audit import AuditTimeline
from app.schemas.event import EventDetail, EventList
from app.schemas.manual_event import ManualEventInput, ManualEventResponse
from app.schemas.raw_sources import ManualSource
from app.services.ai import AINotConfiguredError, build_ai_provider
from app.services.ai.base import AIProvider
from app.services.audit import AuditService
from app.services.entity_extractor import EntityExtractor
from app.services.event_classifier import EventClassifier
from app.services.event_ingestion import EventIngestionService
from app.services.event_normalizer import normalize
from app.services.event_queries import EventFilters, EventQueryService
from app.services.planning import NoMatchingStandingOrderError, PlanningService

router = APIRouter(prefix="/api/v1/events", tags=["events"])


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

    outcome = await EventClassifier(session, provider).classify(raw)
    await EntityExtractor(session, provider).extract(outcome.life_event, outcome.sanitized.text)

    plan_id = None
    try:
        plan = await PlanningService(session).create(current_user, outcome.life_event.id)
        plan_id = plan.id
    except NoMatchingStandingOrderError:
        pass  # No compiled standing order yet; the UI will show "No action plan yet"

    return ManualEventResponse(
        id=outcome.life_event.id,
        raw_event_id=raw.id,
        type=outcome.life_event.type,
        status=raw.status,
        is_duplicate=False,
        plan_id=plan_id,
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
