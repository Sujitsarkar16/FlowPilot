from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import get_current_user
from app.api.routes.standing_orders import get_ai_provider, router
from app.db.session import get_session
from app.models.user import User
from app.services.ai.fake_provider import FakeAIProvider


def responder(system: str, user: str, schema: type) -> dict[str, object]:
    if schema.__name__ == "Classification":
        return {"type": "travel_booked", "confidence": 0.9, "importance": "high", "summary": "Trip"}
    return {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "entity_conditions": [],
        "action_templates": [
            {
                "action_type": "travel.create_folder",
                "connector": "google",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            }
        ],
        "explanation": "Prepare travel.",
    }


@pytest.mark.asyncio
async def test_user_can_create_enable_simulate_and_delete_their_order(session: object) -> None:
    user = User(auth_subject="standing-order-user")
    session.add(user)  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]

    async def override_session() -> AsyncIterator[object]:
        yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(responder)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/standing-orders", json={"instruction": "Prepare flights"}
        )
        assert created.status_code == 201
        order = created.json()
        assert order["compilation_status"] == "compiled" and not order["enabled"]
        enabled = await client.patch(
            f"/api/v1/standing-orders/{order['id']}", json={"enabled": True}
        )
        assert enabled.json()["enabled"]
        simulation = await client.post(
            f"/api/v1/standing-orders/{order['id']}/simulate",
            json={"sample_event": "Flight booked"},
        )
        assert simulation.json()["matched"] is True
        assert (await client.delete(f"/api/v1/standing-orders/{order['id']}")).status_code == 204


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_order(session: object) -> None:
    user, other = User(auth_subject="owner"), User(auth_subject="other")
    session.add_all([user, other])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: other
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(responder)

    async def override_session() -> AsyncIterator[object]:
        yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/v1/standing-orders", json={"instruction": "Prepare flights"}
        )
        assert created.status_code == 201
        app.dependency_overrides[get_current_user] = lambda: user
        assert (
            await client.get(f"/api/v1/standing-orders/{created.json()['id']}")
        ).status_code == 404
