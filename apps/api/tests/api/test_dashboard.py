from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import get_current_user
from app.api.routes.dashboard import router
from app.api.routes.events import router as events_router
from app.db.session import get_session
from app.models.enums import ActionStatus
from app.services.audit import AuditService
from tests.execution_helpers import action_state


def app_for(session, user) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.include_router(events_router)
    app.dependency_overrides[get_current_user] = lambda: user

    async def override_session() -> AsyncIterator:
        yield session

    app.dependency_overrides[get_session] = override_session
    return app


@pytest.mark.asyncio
async def test_dashboard_is_user_scoped_and_timeline_is_paginated(session) -> None:
    user, plan, action = await action_state(session, status=ActionStatus.COMPLETED)
    ledger = AuditService(session)
    for index, name in enumerate(("event_classified", "plan_created", "action_completed")):
        entry = await ledger.append(
            user_id=user.id,
            life_event_id=plan.source_event_id,
            plan_id=plan.id,
            action_id=action.id,
            event_name=name,
            actor_type="system",
        )
        entry.created_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
    await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, user)), base_url="http://test"
    ) as client:
        summary = await client.get("/api/v1/dashboard/summary")
        timeline = await client.get(
            f"/api/v1/events/{plan.source_event_id}/timeline", params={"limit": 2}
        )
        next_page = await client.get(
            f"/api/v1/events/{plan.source_event_id}/timeline",
            params={"cursor": timeline.json()["next_cursor"], "limit": 2},
        )

    assert summary.json() == {
        "events_today": 1,
        "actions_completed": 1,
        "pending_approvals": 0,
        "failed_actions": 0,
        "time_saved_minutes": 4,
    }
    assert len(timeline.json()["items"]) == 2
    assert len(next_page.json()["items"]) == 1


@pytest.mark.asyncio
async def test_empty_dashboard_returns_zeroes(session) -> None:
    from app.models.user import User

    user = User(auth_subject="empty-dashboard")
    session.add(user)
    await session.commit()
    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, user)), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/dashboard/summary")
        feed = await client.get("/api/v1/dashboard/feed")

    assert response.json() == {
        "events_today": 0,
        "actions_completed": 0,
        "pending_approvals": 0,
        "failed_actions": 0,
        "time_saved_minutes": 0,
    }
    assert feed.json() == {"items": [], "next_cursor": None}
