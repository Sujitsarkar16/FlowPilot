"""Contracts for event-scoped attachment metadata and bounded binary content."""

from datetime import datetime
from pathlib import PurePath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventAttachmentUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=128)
    content_base64: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def reject_paths_and_controls(cls, value: str) -> str:
        if (
            PurePath(value).name != value
            or "/" in value
            or "\\" in value
            or any(ord(char) < 32 for char in value)
        ):
            raise ValueError("attachment name must be a plain filename")
        return value


class EventAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class EventAttachmentContent(EventAttachmentRead):
    content_base64: str
