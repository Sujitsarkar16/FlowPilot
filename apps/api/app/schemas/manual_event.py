"""Manual life-event submission schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LifeEventType, RawEventStatus
from app.schemas.raw_sources import MAX_CONTENT_CHARS, AttachmentMeta


class ManualEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    category_hint: str | None = Field(default=None, max_length=64)
    attachments: list[AttachmentMeta] = Field(default_factory=list, max_length=20)


class ManualEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    raw_event_id: UUID
    type: LifeEventType
    status: RawEventStatus
    is_duplicate: bool
