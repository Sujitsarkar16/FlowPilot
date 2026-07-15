from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.enums import EventSource, Importance, LifeEventType
from app.models.event import EventEntity, LifeEvent, RawEvent
from app.models.user import User


@pytest.mark.asyncio
async def test_raw_event_has_one_life_event_and_sensitive_entities(session: object) -> None:
    user = User(auth_subject="subject-event")
    session.add(user)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    raw = RawEvent(
        user=user,
        source=EventSource.GMAIL,
        event_type="email",
        fingerprint="fingerprint",
        payload={},
        received_at=datetime.now(UTC),
    )
    life = LifeEvent(
        user_id=user.id,
        raw_event=raw,
        type=LifeEventType.TRAVEL_BOOKED,
        confidence=0.9,
        importance=Importance.HIGH,
        summary="Trip booked",
        occurred_at=datetime.now(UTC),
    )
    entity = EventEntity(life_event=life, kind="pnr", value={"value": "secret"}, is_sensitive=True)
    session.add_all([user, raw, life, entity])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    assert raw.life_event is life and life.entities == [entity] and entity.is_sensitive

    session.add(
        RawEvent(
            user=user,
            source=EventSource.GMAIL,
            event_type="email",
            fingerprint="fingerprint",
            payload={},
            received_at=datetime.now(UTC),
        )
    )  # type: ignore[attr-defined]
    with pytest.raises(IntegrityError):
        await session.commit()  # type: ignore[attr-defined]
