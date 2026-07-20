from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.routes.actions import router as actions_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.connections import get_connection_service
from app.api.routes.connections import router as connections_router
from app.api.routes.events import router as events_router
from app.api.routes.plans import execution_router
from app.api.routes.plans import router as plans_router
from app.api.routes.standing_orders import get_standing_order_service
from app.api.routes.standing_orders import router as orders_router
from app.core.crypto import SecretCipher
from app.db.session import get_session
from app.models.approval import Approval
from app.models.connection import Connection
from app.models.enums import ActionStatus, CompilationStatus, ConnectionProvider, PlanStatus
from app.models.standing_order import StandingOrder
from app.models.user import User
from app.services.connection_secrets import ConnectionSecrets
from app.services.connections import ConnectionService
from app.services.standing_orders import StandingOrderService
from tests.execution_helpers import action_state


@pytest.mark.asyncio
async def test_every_resource_route_hides_owned_resources_from_other_users(
    session: AsyncSession,
) -> None:
    owner, plan, action = await action_state(
        session, status=ActionStatus.WAITING_APPROVAL, plan_status=PlanStatus.WAITING_APPROVAL
    )
    intruder = User(auth_subject="security-intruder")
    connection = Connection(
        user_id=owner.id, provider=ConnectionProvider.GITHUB, provider_account_id="private"
    )
    order = StandingOrder(
        user_id=owner.id, instruction="Private instruction", compilation_status=CompilationStatus.PENDING
    )
    approval = Approval(action_id=action.id, expires_at=datetime.now(UTC) + timedelta(hours=1))
    session.add_all([intruder, connection, order, approval])
    await session.commit()

    app = FastAPI()
    for router in (
        actions_router, approvals_router, connections_router, events_router,
        plans_router, execution_router, orders_router,
    ):
        app.include_router(router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: intruder
    app.dependency_overrides[get_connection_service] = lambda: ConnectionService(
        session, ConnectionSecrets(SecretCipher("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"))
    )
    app.dependency_overrides[get_standing_order_service] = lambda: StandingOrderService(
        session, object(), object()  # type: ignore[arg-type]
    )

    event_id = plan.source_event_id
    missing = uuid4()
    requests = [
        ("DELETE", f"/api/v1/connections/{connection.id}", None),
        ("POST", f"/api/v1/connections/{connection.id}/test", None),
        ("GET", f"/api/v1/events/{event_id}", None),
        ("DELETE", f"/api/v1/events/{event_id}", None),
        ("GET", f"/api/v1/events/{event_id}/timeline", None),
        ("POST", f"/api/v1/events/{event_id}/plan", {}),
        ("GET", f"/api/v1/plans/{plan.id}", None),
        ("POST", f"/api/v1/plans/{plan.id}/execute", None),
        ("POST", f"/api/v1/plans/{plan.id}/promote", None),
        ("POST", f"/api/v1/plans/{plan.id}/cancel", None),
        ("POST", f"/api/v1/actions/{action.id}/retry", None),
        ("POST", f"/api/v1/actions/{action.id}/rollback", None),
        ("POST", f"/api/v1/approvals/{approval.id}/approve", None),
        ("POST", f"/api/v1/approvals/{approval.id}/reject", None),
        ("GET", f"/api/v1/standing-orders/{order.id}", None),
        ("PATCH", f"/api/v1/standing-orders/{order.id}", {"enabled": True}),
        ("DELETE", f"/api/v1/standing-orders/{order.id}", None),
        ("POST", f"/api/v1/standing-orders/{order.id}/compile", None),
        ("POST", f"/api/v1/standing-orders/{order.id}/simulate", {"sample_event": "Trip"}),
        ("GET", f"/api/v1/events/{missing}", None),
        ("GET", f"/api/v1/plans/{missing}", None),
        ("GET", f"/api/v1/standing-orders/{missing}", None),
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/connections")).json() == []
        assert (await client.get("/api/v1/approvals")).json() == []
        assert (await client.get("/api/v1/standing-orders")).json() == []
        for method, path, payload in requests:
            response = await client.request(method, path, json=payload)
            assert response.status_code == 404, (method, path, response.text)
