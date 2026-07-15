from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.routes.plans import router
from app.core.config import Settings
from app.db.session import get_session
from app.models.enums import (
    AutonomyLevel,
    CompilationStatus,
    EventSource,
    Importance,
    LifeEventType,
    RawEventStatus,
)
from app.models.event import EventEntity, LifeEvent, RawEvent
from app.models.standing_order import StandingOrder
from app.models.user import User


def weather_rule() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "entity_conditions": [{"field": "destination.name", "operator": "exists"}],
        "action_templates": [
            {
                "action_type": "travel.get_weather",
                "connector": "weather",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            }
        ],
        "explanation": "Check destination weather.",
    }


async def add_event(session: AsyncSession, user: User) -> LifeEvent:
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.MANUAL,
        event_type="manual",
        fingerprint=str(uuid4()),
        status=RawEventStatus.NORMALIZED,
        payload={},
        received_at=datetime.now(UTC),
    )
    event = LifeEvent(
        user_id=user.id,
        raw_event=raw,
        type=LifeEventType.TRAVEL_BOOKED,
        confidence=0.95,
        importance=Importance.HIGH,
        summary="Booked a trip",
        occurred_at=datetime.now(UTC),
    )
    session.add_all(
        [raw, event, EventEntity(life_event=event, kind="destination", value={"name": "Paris"})]
    )
    await session.commit()
    return event


def app_for(session: AsyncSession, user: User) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return app


@pytest.mark.asyncio
async def test_plan_endpoint_succeeds_with_template_fallback_when_ai_is_unconfigured(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.routes.plans.get_settings", lambda: Settings(_env_file=None))
    user = User(auth_subject="owner", default_autonomy=AutonomyLevel.SAFE_ACTIONS)
    session.add(user)
    await session.commit()
    event = await add_event(session, user)
    session.add(
        StandingOrder(
            user_id=user.id,
            instruction="Check weather.",
            compiled_rule=weather_rule(),
            enabled=True,
            compilation_status=CompilationStatus.COMPILED,
        )
    )
    await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, user)), base_url="http://test"
    ) as client:
        response = await client.post(f"/api/v1/events/{event.id}/plan", json={})

    assert response.status_code == 201
    body = response.json()
    assert body["source_event_id"] == str(event.id)
    assert (
        body["planner_rationale"]
        == "Plan customization was unavailable; the original validated plan is retained."
    )
    assert [
        (action["action_type"], action["status"], action["policy_reason"])
        for action in body["actions"]
    ] == [("travel.get_weather", "planned", "safe_automatic")]


@pytest.mark.asyncio
async def test_plan_endpoint_returns_404_for_another_users_event(session: AsyncSession) -> None:
    owner = User(auth_subject="owner")
    requester = User(auth_subject="requester")
    session.add_all([owner, requester])
    await session.commit()
    event = await add_event(session, owner)

    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, requester)), base_url="http://test"
    ) as client:
        response = await client.post(f"/api/v1/events/{event.id}/plan", json={})

    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}


@pytest.mark.asyncio
async def test_plan_endpoint_returns_409_when_no_enabled_compiled_rule_matches(
    session: AsyncSession,
) -> None:
    user = User(auth_subject="no-match")
    session.add(user)
    await session.commit()
    event = await add_event(session, user)

    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, user)), base_url="http://test"
    ) as client:
        response = await client.post(f"/api/v1/events/{event.id}/plan", json={})

    assert response.status_code == 409
    assert response.json() == {"detail": "No enabled standing order matches this event"}
