from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import get_current_user
from app.api.routes.events import router
from app.db.session import get_session
from app.models.enums import EventSource, Importance, LifeEventType
from app.models.event import EventEntity, LifeEvent, RawEvent
from app.models.user import User


async def _seed_event(session: object, user: User, summary: str) -> LifeEvent:
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.MANUAL,
        event_type="manual_note",
        fingerprint=f"fp-{summary}",
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
        summary=summary,
        occurred_at=datetime.now(UTC),
    )
    session.add(life)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    session.add(  # type: ignore[attr-defined]
        EventEntity(life_event_id=life.id, kind="pnr", value={"code": "SECRET"}, is_sensitive=True)
    )
    await session.commit()  # type: ignore[attr-defined]
    return life


def _client(session: object, user: User) -> AsyncClient:
    async def override_session() -> AsyncIterator[object]:
        yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_list_masks_sensitive_values(session: object) -> None:
    user = User(auth_subject="query-owner")
    session.add(user)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    await _seed_event(session, user, "Trip to Tokyo")

    async with _client(session, user) as client:
        response = await client.get("/api/v1/events")
        assert response.status_code == 200
        item = response.json()["items"][0]
        entity = item["entities"][0]
        assert entity["is_sensitive"] is True
        assert entity["value"] == {"redacted": True}


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_event(session: object) -> None:
    owner = User(auth_subject="query-owner-2")
    intruder = User(auth_subject="query-intruder")
    session.add_all([owner, intruder])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    event = await _seed_event(session, owner, "Private trip")

    async with _client(session, intruder) as client:
        response = await client.get(f"/api/v1/events/{event.id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_type_filter_narrows_results(session: object) -> None:
    user = User(auth_subject="query-filter")
    session.add(user)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    await _seed_event(session, user, "Trip")

    async with _client(session, user) as client:
        match = await client.get("/api/v1/events", params={"type": "travel_booked"})
        miss = await client.get("/api/v1/events", params={"type": "salary_credited"})
        assert len(match.json()["items"]) == 1
        assert miss.json()["items"] == []
