from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.routes.plans import execution_router
from app.db.session import get_session
from app.models.enums import ActionStatus, PlanStatus
from app.models.job import Job
from tests.execution_helpers import action_state


def app_for(session: AsyncSession, user) -> FastAPI:
    app = FastAPI()
    app.include_router(execution_router)
    app.dependency_overrides[get_current_user] = lambda: user

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return app


@pytest.mark.asyncio
async def test_execute_queues_ready_actions_idempotently(session: AsyncSession) -> None:
    user, plan, action = await action_state(
        session, status=ActionStatus.PLANNED, plan_status=PlanStatus.POLICY_CHECKED
    )
    app = app_for(session, user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(f"/api/v1/plans/{plan.id}/execute")
        repeated = await client.post(f"/api/v1/plans/{plan.id}/execute")

    assert first.status_code == 200
    assert first.json()["status"] == "running"
    assert first.json()["actions"][0]["status"] == "queued"
    assert repeated.status_code == 200
    assert len(list(await session.scalars(select(Job)))) == 1
