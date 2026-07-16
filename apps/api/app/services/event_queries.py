"""Read-side queries and sensitive-value redaction for events."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.events import EventRepository
from app.db.repositories.plans import PlanRepository
from app.models.event import EventEntity, LifeEvent
from app.models.plan import Plan
from app.schemas.event import (
    EventDetail,
    EventEntityRead,
    EventList,
    EventListItem,
    PlanSummary,
)

_MASKED: dict[str, object] = {"redacted": True}


def _mask(entity: EventEntity) -> EventEntityRead:
    """Hide sensitive values in list projections while keeping the kind visible."""
    value = _MASKED if entity.is_sensitive else entity.value
    return EventEntityRead(kind=entity.kind, value=value, is_sensitive=entity.is_sensitive)


def _encode_cursor(event: LifeEvent) -> str:
    return urlsafe_b64encode(f"{event.created_at.isoformat()}|{event.id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    raw = urlsafe_b64decode(cursor.encode()).decode()
    created_at, event_id = raw.split("|", 1)
    return datetime.fromisoformat(created_at), UUID(event_id)


@dataclass(frozen=True)
class EventFilters:
    type_: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class EventQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._events = EventRepository(session)
        self._plans = PlanRepository(session)

    async def list_events(
        self, user_id: UUID, *, cursor: str | None, limit: int, filters: EventFilters
    ) -> EventList:
        parsed = decode_cursor(cursor) if cursor else None
        events = await self._events.list_life(
            user_id,
            parsed,
            limit + 1,
            type_=filters.type_,
            date_from=filters.date_from,
            date_to=filters.date_to,
        )
        has_more = len(events) > limit
        page = events[:limit]
        latest_plans = await self._plans.latest_for_events(user_id, (event.id for event in page))
        items = [
            EventListItem(
                id=event.id,
                type=event.type,
                confidence=event.confidence,
                importance=event.importance,
                summary=event.summary,
                occurred_at=event.occurred_at,
                entities=[_mask(entity) for entity in event.entities],
                latest_plan=(
                    _plan_summary(latest_plans[event.id]) if event.id in latest_plans else None
                ),
            )
            for event in page
        ]
        next_cursor = _encode_cursor(page[-1]) if has_more and page else None
        return EventList(items=items, next_cursor=next_cursor)

    async def get_detail(self, user_id: UUID, event_id: UUID) -> EventDetail | None:
        event = await self._events.get_life(user_id, event_id)
        if event is None:
            return None
        plans = await self._plans.list_for_event(user_id, event_id)
        latest = None
        if plans:
            # Re-fetch with actions eagerly loaded so the count is safe under async.
            loaded = await self._plans.get(user_id, plans[-1].id)
            if loaded is not None:
                latest = _plan_summary(loaded)
        return EventDetail(
            id=event.id,
            type=event.type,
            confidence=event.confidence,
            importance=event.importance,
            summary=event.summary,
            occurred_at=event.occurred_at,
            entities=[_mask(entity) for entity in event.entities],
            source=event.raw_event.source,
            latest_plan=latest,
        )


def _plan_summary(plan: Plan) -> PlanSummary:
    return PlanSummary(
        id=plan.id,
        objective=plan.objective,
        status=plan.status.value,
        action_count=len(plan.actions),
        completed_actions=sum(action.status.value == "completed" for action in plan.actions),
        pending_actions=sum(action.status.value in {"planned", "waiting_approval", "approved", "queued", "running"} for action in plan.actions),
        failed_actions=sum(action.status.value == "failed" for action in plan.actions),
        is_shadow=plan.is_shadow,
    )
