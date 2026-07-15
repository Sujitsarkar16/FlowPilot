from app.models.enums import EventSource
from app.services.event_fingerprint import compute_event_fingerprint


def test_provider_id_is_authoritative_and_stable() -> None:
    first = compute_event_fingerprint(EventSource.GMAIL, "msg-1", ["ignored"])
    second = compute_event_fingerprint(EventSource.GMAIL, "msg-1", ["different"])
    assert first == second


def test_same_id_different_source_differs() -> None:
    gmail = compute_event_fingerprint(EventSource.GMAIL, "id", [])
    webhook = compute_event_fingerprint(EventSource.WEBHOOK, "id", [])
    assert gmail != webhook


def test_field_fallback_collapses_identical_content() -> None:
    a = compute_event_fingerprint(EventSource.MANUAL, None, ["Book flight to Tokyo"])
    b = compute_event_fingerprint(EventSource.MANUAL, None, ["Book flight to Tokyo"])
    c = compute_event_fingerprint(EventSource.MANUAL, None, ["Book flight to Paris"])
    assert a == b and a != c
