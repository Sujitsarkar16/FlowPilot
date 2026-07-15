import pytest

from app.models.enums import EventSource, RawEventStatus
from app.models.user import User
from app.schemas.raw_sources import ManualSource
from app.services.event_ingestion import EventIngestionService
from app.services.event_normalizer import normalize


@pytest.mark.asyncio
async def test_replaying_the_same_event_is_idempotent(session: object) -> None:
    user = User(auth_subject="ingest-user")
    session.add(user)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    service = EventIngestionService(session)  # type: ignore[arg-type]
    normalized = normalize(ManualSource(text="Booked flight to Tokyo on Friday"))

    first = await service.ingest(user.id, normalized)
    second = await service.ingest(user.id, normalized)

    assert first.is_duplicate is False
    assert second.is_duplicate is True
    assert second.raw_event.id == first.raw_event.id
    assert first.raw_event.status is RawEventStatus.RECEIVED
    assert first.raw_event.source is EventSource.MANUAL


@pytest.mark.asyncio
async def test_same_content_is_isolated_per_user(session: object) -> None:
    owner = User(auth_subject="owner-ingest")
    other = User(auth_subject="other-ingest")
    session.add_all([owner, other])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    service = EventIngestionService(session)  # type: ignore[arg-type]
    normalized = normalize(ManualSource(text="Same note"))

    owner_result = await service.ingest(owner.id, normalized)
    other_result = await service.ingest(other.id, normalized)

    assert owner_result.is_duplicate is False
    assert other_result.is_duplicate is False
    assert owner_result.raw_event.id != other_result.raw_event.id
