"""Validated, privacy-minimized Gmail message and polling schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.raw_sources import MAX_CONTENT_CHARS, AttachmentMeta, GmailSource

DEFAULT_SENDER_TERMS = (
    "airline",
    "booking",
    "travel",
    "hotel",
    "bank",
    "payroll",
    "billing",
    "invoice",
    "recruit",
    "client",
)
DEFAULT_SUBJECT_TERMS = (
    "booking",
    "reservation",
    "itinerary",
    "flight",
    "travel",
    "trip",
    "invoice",
    "payment",
    "salary",
    "contract",
    "offer",
    "interview",
    "renewal",
    "subscription",
    "appointment",
    "confirmation",
)


class GmailCursor(BaseModel):
    """The provider history cursor persisted in connection token metadata."""

    model_config = ConfigDict(extra="forbid")

    history_id: str = Field(min_length=1, max_length=255)


class GmailAttachment(AttachmentMeta):
    """Provider locator retained only in memory; ``as_source`` strips it before ingestion."""

    attachment_id: str | None = Field(default=None, min_length=1, max_length=1024)
    inline_data: str | None = Field(default=None, repr=False)


class GmailMessage(BaseModel):
    """A parsed Gmail message with only safe headers retained."""

    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(min_length=1, max_length=255)
    history_id: str | None = Field(default=None, max_length=255)
    sender: str = Field(default="", max_length=320)
    subject: str = Field(default="", max_length=1000)
    received_at: datetime
    body: str = Field(default="", max_length=MAX_CONTENT_CHARS)
    attachments: list[GmailAttachment] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)

    def as_source(self) -> GmailSource:
        return GmailSource(
            message_id=self.message_id,
            sender=self.sender,
            subject=self.subject,
            received_at=self.received_at,
            body=self.body,
            attachments=[
                AttachmentMeta(
                    name=attachment.name,
                    mime_type=attachment.mime_type,
                    size_bytes=attachment.size_bytes,
                )
                for attachment in self.attachments
            ],
        )


class GmailRelevanceFilter(BaseModel):
    """Case-insensitive sender-or-subject filter applied before ingestion."""

    model_config = ConfigDict(extra="forbid")

    sender_terms: tuple[str, ...] = DEFAULT_SENDER_TERMS
    subject_terms: tuple[str, ...] = DEFAULT_SUBJECT_TERMS

    def matches(self, message: GmailMessage) -> bool:
        sender = message.sender.casefold()
        subject = message.subject.casefold()
        return any(term.casefold() in sender for term in self.sender_terms) or any(
            term.casefold() in subject for term in self.subject_terms
        )

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "GmailRelevanceFilter":
        """Allow per-connection list overrides without trusting other metadata shapes."""

        def terms(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
            value = metadata.get(key)
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                return default
            return tuple(item.strip() for item in value if item.strip())

        return cls(
            sender_terms=terms("gmail_sender_terms", DEFAULT_SENDER_TERMS),
            subject_terms=terms("gmail_subject_terms", DEFAULT_SUBJECT_TERMS),
        )
