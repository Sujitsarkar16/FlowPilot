"""Event API response schemas with intentionally compact summaries."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EventSource, Importance, LifeEventType, RawEventStatus


class EventEntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    value: dict[str, object]
    is_sensitive: bool


class LifeEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    type: LifeEventType
    confidence: float = Field(ge=0, le=1)
    importance: Importance
    summary: str
    occurred_at: datetime
    entities: list[EventEntityRead] = []


class RawEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source: EventSource
    status: RawEventStatus
    received_at: datetime
    life_event: LifeEventRead | None = None


class PlanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    objective: str
    status: str
    action_count: int


class EventListItem(BaseModel):
    """List projection with sensitive entity values masked."""

    id: UUID
    type: LifeEventType
    confidence: float = Field(ge=0, le=1)
    importance: Importance
    summary: str
    occurred_at: datetime
    entities: list[EventEntityRead] = []


class EventList(BaseModel):
    items: list[EventListItem]
    next_cursor: str | None = None


class EventDetail(LifeEventRead):
    latest_plan: PlanSummary | None = None
