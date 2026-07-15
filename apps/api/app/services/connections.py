"""Tenant-scoped connection lifecycle and credential handling."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.connections import ConnectionRepository
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.services.connection_secrets import ConnectionSecrets, ConnectionTokens

HealthCheck = Callable[[Connection], Awaitable[bool]]


class ConnectionNotFoundError(Exception):
    pass


class ConnectionRevokedError(Exception):
    pass


class ConnectionService:
    def __init__(self, session: AsyncSession, secrets: ConnectionSecrets) -> None:
        self._session = session
        self._connections = ConnectionRepository(session)
        self._secrets = secrets

    async def list_connections(self, user_id: UUID) -> list[Connection]:
        return await self._connections.list(user_id)

    async def save(
        self,
        user_id: UUID,
        provider: ConnectionProvider,
        provider_account_id: str,
        *,
        access_token: str | None,
        refresh_token: str | None = None,
        scopes: list[str] | None = None,
        token_metadata: dict[str, object] | None = None,
    ) -> Connection:
        connection = await self._connections.get_provider_account(
            user_id, provider, provider_account_id
        )
        if connection is None:
            connection = Connection(
                user_id=user_id, provider=provider, provider_account_id=provider_account_id
            )
            self._session.add(connection)
        connection.status = ConnectionStatus.CONNECTED
        connection.scopes = scopes or []
        connection.token_metadata = token_metadata or {}
        self._secrets.save(connection, access_token, refresh_token)
        await self._session.commit()
        await self._session.refresh(connection)
        return connection

    async def require_active(self, user_id: UUID, connection_id: UUID) -> Connection:
        connection = await self._connections.get(user_id, connection_id)
        if connection is None:
            raise ConnectionNotFoundError
        if connection.status is ConnectionStatus.REVOKED:
            raise ConnectionRevokedError
        return connection

    async def load_tokens(self, connection: Connection) -> ConnectionTokens:
        return self._secrets.load(connection)

    async def mark_health(self, user_id: UUID, connection_id: UUID, healthy: bool) -> Connection:
        connection = await self.require_active(user_id, connection_id)
        connection.status = ConnectionStatus.CONNECTED if healthy else ConnectionStatus.ERROR
        await self._session.commit()
        await self._session.refresh(connection)
        return connection

    async def test(
        self, user_id: UUID, connection_id: UUID, health_check: HealthCheck | None = None
    ) -> Connection:
        connection = await self.require_active(user_id, connection_id)
        if health_check is None:
            healthy = connection.encrypted_access_token is not None
        else:
            try:
                healthy = await health_check(connection)
            except Exception:
                healthy = False
        return await self.mark_health(user_id, connection_id, healthy)

    async def revoke(self, user_id: UUID, connection_id: UUID) -> None:
        connection = await self._connections.get(user_id, connection_id)
        if connection is None:
            raise ConnectionNotFoundError
        connection.status = ConnectionStatus.REVOKED
        self._secrets.clear(connection)
        await self._session.commit()
