from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.routes.connections import get_connection_service, router
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.models.user import User


class StubConnections:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    async def list_connections(self, user_id: object) -> list[Connection]:
        assert user_id == self.connection.user_id
        return [self.connection]


def test_connections_list_returns_only_safe_fields() -> None:
    user = User(id=uuid4(), auth_subject="trusted-subject")
    now = datetime.now(UTC)
    connection = Connection(
        id=uuid4(),
        user_id=user.id,
        provider=ConnectionProvider.GOOGLE,
        provider_account_id="account-1",
        status=ConnectionStatus.CONNECTED,
        scopes=["scope.read"],
        encrypted_access_token="ciphertext",
        encrypted_refresh_token="more-ciphertext",
        created_at=now,
        updated_at=now,
    )
    app = FastAPI()

    async def current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_connection_service] = lambda: StubConnections(connection)
    app.include_router(router)
    response = TestClient(app).get("/api/v1/connections")
    assert response.status_code == 200
    assert response.json() == [{
        "id": str(connection.id), "provider": "google", "provider_account_id": "account-1",
        "status": "connected", "scopes": ["scope.read"],
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    }]
