"""Per-source input schemas and the canonical normalized-event shape.

Every external source is coerced into :class:`NormalizedEvent`, which keeps trusted
metadata separate from untrusted free-form content so later stages can label the
trust boundary before any content reaches the model.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EventSource

# ponytail: fixed in-code limits; move to settings if a source needs per-tenant tuning.
MAX_CONTENT_CHARS = 20_000
MAX_ATTACHMENTS = 20
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


class AttachmentMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(ge=0, le=MAX_ATTACHMENT_BYTES)


class ManualSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["manual"] = "manual"
    text: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    category_hint: str | None = Field(default=None, max_length=64)
    attachments: list[AttachmentMeta] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)


class GmailSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["gmail"] = "gmail"
    message_id: str = Field(min_length=1, max_length=255)
    subject: str = Field(default="", max_length=1000)
    sender: str = Field(default="", max_length=320)
    received_at: datetime
    body: str = Field(default="", max_length=MAX_CONTENT_CHARS)
    attachments: list[AttachmentMeta] = Field(default_factory=list, max_length=MAX_ATTACHMENTS)


class WebhookSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["webhook"] = "webhook"
    event_id: str | None = Field(default=None, max_length=255)
    event_type: str = Field(min_length=1, max_length=128)
    occurred_at: datetime | None = None
    body: dict[str, object] = Field(default_factory=dict)


class MockBankSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["banking_mock"] = "banking_mock"
    transaction_id: str = Field(min_length=1, max_length=255)
    amount: float
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(default="", max_length=1000)
    occurred_at: datetime


class NormalizedEvent(BaseModel):
    """Canonical raw-event shape produced for every supported source."""

    model_config = ConfigDict(extra="forbid")
    source: EventSource
    event_type: str = Field(min_length=1, max_length=128)
    source_event_id: str | None = None
    occurred_at: datetime
    fingerprint_fields: list[str]
    trusted_metadata: dict[str, object] = Field(default_factory=dict)
    untrusted_content: str = ""
    attachments: list[AttachmentMeta] = Field(default_factory=list)
