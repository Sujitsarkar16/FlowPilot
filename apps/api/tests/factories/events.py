from datetime import UTC, datetime
from uuid import uuid4

from app.models.enums import EventSource, Importance, LifeEventType, RawEventStatus
from app.models.event import LifeEvent, RawEvent
from app.models.user import User


def raw_event(user: User, **overrides: object) -> RawEvent:
    defaults: dict[str, object] = {
        "user": user,
        "source": EventSource.MANUAL,
        "event_type": "manual",
        "fingerprint": str(uuid4()),
        "status": RawEventStatus.NORMALIZED,
        "payload": {},
        "received_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return RawEvent(**defaults)  # type: ignore[arg-type]


def life_event(user: User, **overrides: object) -> LifeEvent:
    if user.id is None:
        user.id = uuid4()
    raw = overrides.pop("raw_event", raw_event(user))
    defaults: dict[str, object] = {
        "user_id": user.id,
        "raw_event": raw,
        "type": LifeEventType.TRAVEL_BOOKED,
        "confidence": 0.95,
        "importance": Importance.HIGH,
        "summary": "Booked a test trip",
        "occurred_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return LifeEvent(**defaults)  # type: ignore[arg-type]
