"""Redacted audit timeline schema."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    life_event_id: UUID | None
    plan_id: UUID | None
    action_id: UUID | None
    event_name: str
    actor_type: str
    request_id: str | None
    payload: dict[str, Any]
    created_at: datetime


class AuditTimeline(BaseModel):
    items: list[AuditEntryRead]
    next_cursor: str | None = None
