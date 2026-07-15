from datetime import UTC, datetime

import pytest

from app.models.enums import EventSource, LifeEventType, RawEventStatus
from app.models.event import RawEvent
from app.models.user import User
from app.services.ai.fake_provider import FakeAIProvider
from app.services.ai.schemas import AIError
from app.services.event_classifier import EventClassifier


async def _raw_event(session: object, content: str, event_type: str = "email") -> RawEvent:
    user = User(auth_subject=f"classify-{content[:8]}-{datetime.now(UTC).timestamp()}")
    session.add(user)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.GMAIL,
        event_type=event_type,
        fingerprint=f"fp-{content[:12]}",
        payload={"trusted_metadata": {}, "untrusted_content": content},
        received_at=datetime.now(UTC),
    )
    session.add(raw)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    return raw


def _responder(system: str, user: str, schema: type) -> dict[str, object]:
    # Inspect only the wrapped content, never the prompt's enumerated type list.
    content = user.split("<untrusted_content>", 1)[-1]
    lowered = content.lower()
    if "flight" in lowered:
        return {
            "type": "travel_booked",
            "confidence": 0.95,
            "importance": "high",
            "summary": "Trip booked",
        }
    if "client" in lowered:
        return {
            "type": "client_opportunity",
            "confidence": 0.9,
            "importance": "high",
            "summary": "New client",
        }
    if "salary" in lowered:
        return {
            "type": "salary_credited",
            "confidence": 0.9,
            "importance": "medium",
            "summary": "Salary in",
        }
    return {"type": "travel_booked", "confidence": 0.2, "importance": "low", "summary": "Unsure"}


@pytest.mark.asyncio
async def test_fixtures_classify_into_expected_types(session: object) -> None:
    classifier = EventClassifier(session, FakeAIProvider(_responder))  # type: ignore[arg-type]

    flight_raw = await _raw_event(session, "Your flight AA123 is booked")
    flight = await classifier.classify(flight_raw)
    client = await classifier.classify(await _raw_event(session, "New client wants a website"))
    salary = await classifier.classify(await _raw_event(session, "Your salary has been credited"))

    assert flight.life_event.type is LifeEventType.TRAVEL_BOOKED
    assert client.life_event.type is LifeEventType.CLIENT_OPPORTUNITY
    assert salary.life_event.type is LifeEventType.SALARY_CREDITED
    assert flight_raw.status is RawEventStatus.NORMALIZED


@pytest.mark.asyncio
async def test_low_confidence_falls_back_to_generic(session: object) -> None:
    classifier = EventClassifier(session, FakeAIProvider(_responder))  # type: ignore[arg-type]
    outcome = await classifier.classify(await _raw_event(session, "something vague happened"))
    assert outcome.life_event.type is LifeEventType.GENERIC_IMPORTANT_EVENT


@pytest.mark.asyncio
async def test_ai_failure_stays_safe(session: object) -> None:
    def failing(system: str, user: str, schema: type) -> dict[str, object]:
        raise AIError("boom")

    classifier = EventClassifier(session, FakeAIProvider(failing))  # type: ignore[arg-type]
    outcome = await classifier.classify(await _raw_event(session, "flight booked"))
    assert outcome.life_event.type is LifeEventType.GENERIC_IMPORTANT_EVENT
    assert outcome.classification.confidence == 0.0
