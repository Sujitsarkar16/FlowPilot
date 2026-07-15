from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import get_current_user
from app.api.routes.events import get_ai_provider, router
from app.db.session import get_session
from app.models.user import User
from app.services.ai.fake_provider import FakeAIProvider


def _travel_responder(system: str, user: str, schema: type) -> dict[str, object]:
    name = schema.__name__
    if name == "Classification":
        return {
            "type": "travel_booked",
            "confidence": 0.95,
            "importance": "high",
            "summary": "Trip",
        }
    return {"entities": [{"kind": "destination", "value": {"name": "Tokyo"}}]}


@pytest.mark.asyncio
async def test_manual_event_is_ingested_and_retrievable(session: object) -> None:
    user = User(auth_subject="manual-user")
    session.add(user)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]

    async def override_session() -> AsyncIterator[object]:
        yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(_travel_responder)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/v1/events/manual", json={"text": "Booked a flight to Tokyo on Friday"}
        )
        assert created.status_code == 201
        body = created.json()
        assert body["type"] == "travel_booked"
        assert body["is_duplicate"] is False

        detail = await client.get(f"/api/v1/events/{body['id']}")
        assert detail.status_code == 200
        assert detail.json()["type"] == "travel_booked"

        duplicate = await client.post(
            "/api/v1/events/manual", json={"text": "Booked a flight to Tokyo on Friday"}
        )
        assert duplicate.json()["is_duplicate"] is True


@pytest.mark.asyncio
async def test_empty_text_is_rejected(session: object) -> None:
    user = User(auth_subject="manual-user")

    async def override_session() -> AsyncIterator[object]:
        yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(_travel_responder)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/events/manual", json={"text": ""})
        assert response.status_code == 422
