"""Authenticated, tenant-scoped connection management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.connectors.telegram.client import TelegramClient
from app.core.config import get_settings
from app.core.crypto import SecretCipher
from app.db.session import get_session
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.models.user import User
from app.schemas.connection import ConnectionRead
from app.services.connection_secrets import ConnectionSecrets
from app.services.connections import (
    ConnectionNotFoundError,
    ConnectionRevokedError,
    ConnectionService,
)

router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


def get_connection_service(session: AsyncSession = Depends(get_session)) -> ConnectionService:
    settings = get_settings()
    if settings.encryption_key is None:
        raise HTTPException(status_code=503, detail="Connection encryption is not configured")
    cipher = SecretCipher(
        settings.encryption_key.get_secret_value(),
        [key.get_secret_value() for key in settings.encryption_previous_keys],
    )
    return ConnectionService(session, ConnectionSecrets(cipher))


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Connection not found")


@router.get("", response_model=list[ConnectionRead])
async def list_connections(
    current_user: User = Depends(get_current_user),
    connections: ConnectionService = Depends(get_connection_service),
) -> list[Connection]:
    return await connections.list_connections(current_user.id)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    connections: ConnectionService = Depends(get_connection_service),
) -> Response:
    try:
        await connections.revoke(current_user.id, connection_id)
    except ConnectionNotFoundError:
        raise not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{connection_id}/test", response_model=ConnectionRead)
async def test_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    connections: ConnectionService = Depends(get_connection_service),
) -> Connection:
    async def health_check(connection: Connection) -> bool:
        if connection.provider is not ConnectionProvider.TELEGRAM:
            return connection.encrypted_access_token is not None
        tokens = await connections.load_tokens(connection)
        chat_id = connection.token_metadata.get("chat_id")
        if not isinstance(chat_id, str):
            return False
        await TelegramClient(mock_mode=get_settings().telegram_mock_mode).send_test_message(
            tokens.access_token, chat_id
        )
        return True

    try:
        connection = await connections.test(current_user.id, connection_id, health_check)
    except ConnectionNotFoundError:
        raise not_found() from None
    except ConnectionRevokedError:
        raise HTTPException(status_code=409, detail="Revoked connections cannot be used") from None
    if connection.status is ConnectionStatus.ERROR:
        raise HTTPException(
            status_code=502, detail="Connection test failed; reconnect and try again"
        )
    return connection
