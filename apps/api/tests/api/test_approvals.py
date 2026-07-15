from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.routes.approvals import router
from app.db.session import get_session
from app.models.enums import ActionStatus, PlanStatus
from app.services.approvals import ApprovalService
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
async def test_approvals_are_owned_and_can_be_approved(session: AsyncSession) -> None:
    owner, _, action = await action_state(
        session, status=ActionStatus.WAITING_APPROVAL, plan_status=PlanStatus.WAITING_APPROVAL
    )
    approval = (await ApprovalService(session).create_for_actions([action]))[0]
    await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, owner)), base_url="http://test"
    ) as client:
        listed = await client.get("/api/v1/approvals")
        decided = await client.post(f"/api/v1/approvals/{approval.id}/approve")

    assert listed.status_code == 200
    assert listed.json()[0]["action"]["id"] == str(action.id)
    assert decided.status_code == 200
    assert decided.json()["decision"] == "approved"


@pytest.mark.asyncio
async def test_user_cannot_decide_another_users_approval(session: AsyncSession) -> None:
    owner, _, action = await action_state(session, status=ActionStatus.WAITING_APPROVAL)
    approval = (await ApprovalService(session).create_for_actions([action]))[0]
    from app.models.user import User

    intruder = User(auth_subject="approval-intruder")
    session.add(intruder)
    await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app_for(session, intruder)), base_url="http://test"
    ) as client:
        response = await client.post(f"/api/v1/approvals/{approval.id}/reject")

    assert response.status_code == 404
