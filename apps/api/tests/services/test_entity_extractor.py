from datetime import UTC, datetime

import pytest

from app.models.enums import EventSource, Importance, LifeEventType
from app.models.event import LifeEvent, RawEvent
from app.models.user import User
from app.services.ai.fake_provider import FakeAIProvider
from app.services.entity_extractor import EntityExtractor


async def _life_event(session: object) -> LifeEvent:
    user = User(auth_subject=f"extract-{datetime.now(UTC).timestamp()}")
    session.add(user)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.GMAIL,
        event_type="email",
        fingerprint=f"fp-{datetime.now(UTC).timestamp()}",
        payload={},
        received_at=datetime.now(UTC),
    )
    session.add(raw)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    life = LifeEvent(
        user_id=user.id,
        raw_event_id=raw.id,
        type=LifeEventType.TRAVEL_BOOKED,
        confidence=0.9,
        importance=Importance.HIGH,
        summary="Trip",
        occurred_at=datetime.now(UTC),
    )
    session.add(life)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    return life


@pytest.mark.asyncio
async def test_extracts_and_marks_sensitive_entities(session: object) -> None:
    def responder(system: str, user: str, schema: type) -> dict[str, object]:
        return {
            "entities": [
                {
                    "kind": "flight",
                    "value": {"number": "AA123", "datetime": "2026-08-01T09:00:00Z"},
                },
                {"kind": "pnr", "value": {"code": "XYZ789"}},
                {"kind": "bogus", "value": {"date": "not-a-date"}},
            ]
        }

    extractor = EntityExtractor(session, FakeAIProvider(responder))  # type: ignore[arg-type]
    entities = await extractor.extract(await _life_event(session), "flight AA123 pnr XYZ789")

    kinds = {entity.kind for entity in entities}
    assert kinds == {"flight", "pnr"}  # invalid-date entity dropped
    pnr = next(entity for entity in entities if entity.kind == "pnr")
    assert pnr.is_sensitive is True


@pytest.mark.asyncio
async def test_no_entities_when_model_returns_none(session: object) -> None:
    extractor = EntityExtractor(session, FakeAIProvider(lambda s, u, schema: {"entities": []}))  # type: ignore[arg-type]
    assert await extractor.extract(await _life_event(session), "nothing") == []
