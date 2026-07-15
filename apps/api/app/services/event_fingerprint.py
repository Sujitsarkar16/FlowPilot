"""Stable event fingerprints for idempotent ingestion."""

from hashlib import sha256

from app.models.enums import EventSource

_SEPARATOR = "\x1f"


def compute_event_fingerprint(
    source: EventSource, source_event_id: str | None, fields: list[str]
) -> str:
    """Return a deterministic per-source fingerprint.

    A provider event id is authoritative when present; otherwise the fingerprint is
    derived from stable normalized fields so replays of the same content collapse.
    """
    material = source_event_id if source_event_id else _SEPARATOR.join(field for field in fields)
    return sha256(f"{source.value}{_SEPARATOR}{material}".encode()).hexdigest()
