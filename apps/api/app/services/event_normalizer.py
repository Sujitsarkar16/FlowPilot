"""Normalize supported external sources into a single canonical event."""

from datetime import UTC, datetime

from app.models.enums import EventSource
from app.schemas.raw_sources import (
    GmailSource,
    ManualSource,
    MockBankSource,
    NormalizedEvent,
    WebhookSource,
)


class EventNormalizationError(Exception):
    """Raised when a source payload cannot be normalized safely."""


def _as_utc(moment: datetime) -> datetime:
    """Coerce naive timestamps to UTC and convert aware ones to UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def normalize_manual(source: ManualSource) -> NormalizedEvent:
    return NormalizedEvent(
        source=EventSource.MANUAL,
        event_type=source.category_hint or "manual_note",
        source_event_id=None,
        occurred_at=datetime.now(UTC),
        # Manual notes have no provider id, so the text itself anchors deduplication.
        fingerprint_fields=[source.text.strip()],
        trusted_metadata={"category_hint": source.category_hint},
        untrusted_content=source.text,
        attachments=source.attachments,
    )


def normalize_gmail(source: GmailSource) -> NormalizedEvent:
    return NormalizedEvent(
        source=EventSource.GMAIL,
        event_type="email",
        source_event_id=source.message_id,
        occurred_at=_as_utc(source.received_at),
        fingerprint_fields=[source.message_id],
        trusted_metadata={"subject": source.subject, "sender": source.sender},
        untrusted_content=source.body,
        attachments=source.attachments,
    )


def normalize_webhook(source: WebhookSource) -> NormalizedEvent:
    occurred = _as_utc(source.occurred_at) if source.occurred_at else datetime.now(UTC)
    return NormalizedEvent(
        source=EventSource.WEBHOOK,
        event_type=source.event_type,
        source_event_id=source.event_id,
        occurred_at=occurred,
        fingerprint_fields=[source.event_type, repr(sorted(source.body.items()))],
        trusted_metadata={"event_type": source.event_type},
        untrusted_content="",
    )


def normalize_mock_bank(source: MockBankSource) -> NormalizedEvent:
    return NormalizedEvent(
        source=EventSource.BANKING_MOCK,
        event_type="salary_credit",
        source_event_id=source.transaction_id,
        occurred_at=_as_utc(source.occurred_at),
        fingerprint_fields=[source.transaction_id],
        trusted_metadata={
            "amount": source.amount,
            "currency": source.currency.upper(),
            "description": source.description,
        },
        untrusted_content=source.description,
    )


def normalize(source: object) -> NormalizedEvent:
    """Dispatch a validated source model to its normalizer."""
    if isinstance(source, ManualSource):
        return normalize_manual(source)
    if isinstance(source, GmailSource):
        return normalize_gmail(source)
    if isinstance(source, WebhookSource):
        return normalize_webhook(source)
    if isinstance(source, MockBankSource):
        return normalize_mock_bank(source)
    raise EventNormalizationError(f"Unsupported source type: {type(source).__name__}")
