from datetime import datetime

import pytest

from app.models.enums import EventSource
from app.schemas.raw_sources import (
    GmailSource,
    ManualSource,
    MockBankSource,
    NormalizedEvent,
    WebhookSource,
)
from app.services.event_normalizer import EventNormalizationError, normalize


def test_all_sources_produce_the_canonical_shape() -> None:
    naive = datetime(2026, 7, 15, 9, 30)
    sources = [
        ManualSource(text="Book a flight"),
        GmailSource(
            message_id="m1", subject="Trip", sender="a@b.com", received_at=naive, body="hi"
        ),
        WebhookSource(event_type="custom", body={"k": "v"}),
        MockBankSource(transaction_id="t1", amount=5000, currency="usd", occurred_at=naive),
    ]
    for source in sources:
        normalized = normalize(source)
        assert isinstance(normalized, NormalizedEvent)
        assert normalized.occurred_at.tzinfo is not None


def test_naive_timestamps_become_utc() -> None:
    normalized = normalize(
        GmailSource(message_id="m", received_at=datetime(2026, 1, 1, 12, 0), body="x")
    )
    assert normalized.occurred_at.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_untrusted_content_is_separated_from_trusted_metadata() -> None:
    normalized = normalize(
        GmailSource(
            message_id="m",
            subject="Subj",
            sender="s@x.com",
            received_at=datetime.now(),
            body="body text",
        )
    )
    assert normalized.untrusted_content == "body text"
    assert normalized.trusted_metadata["subject"] == "Subj"
    assert normalized.source is EventSource.GMAIL


def test_unsupported_source_raises() -> None:
    with pytest.raises(EventNormalizationError):
        normalize(object())
