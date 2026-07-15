from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.routes.actions import router
from app.db.session import get_session
from app.models.enums import ActionStatus
from tests.execution_helpers import action_state


def app_for(session: AsyncSession, user) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return app


@pytest.mark.asyncio
async def test_rollback_endpoint_exposes_rolled_back_state(session: AsyncSession) -> None:
    user, _, action = await action_state(session, status=ActionStatus.COMPLETED)
    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, user)), base_url="http://test"
    ) as client:
        response = await client.post(f"/api/v1/actions/{action.id}/rollback")

    assert response.status_code == 200
    assert response.json()["status"] == "rolled_back"
