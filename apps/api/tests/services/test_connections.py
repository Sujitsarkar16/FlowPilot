import base64

import pytest

from app.core.crypto import SecretCipher
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.models.user import User
from app.schemas.connection import ConnectionRead
from app.services.connection_secrets import ConnectionSecrets
from app.services.connections import ConnectionRevokedError, ConnectionService


def key(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


@pytest.mark.asyncio
async def test_connections_are_tenant_scoped_safe_and_revocable(session: object) -> None:
    owner = User(auth_subject="owner")
    other_user = User(auth_subject="other")
    session.add_all([owner, other_user])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    service = ConnectionService(session, ConnectionSecrets(SecretCipher(key(b"a" * 32))))  # type: ignore[arg-type]
    connection = await service.save(
        owner.id,
        ConnectionProvider.GOOGLE,
        "account-1",
        access_token="access-secret",
        refresh_token="refresh-secret",
        scopes=["scope.read"],
    )
    assert (await service.list_connections(owner.id)) == [connection]
    assert await service.list_connections(other_user.id) == []
    public = ConnectionRead.model_validate(connection).model_dump()
    assert "encrypted_access_token" not in public
    assert connection.encrypted_access_token != "access-secret"

    await service.revoke(owner.id, connection.id)
    assert connection.status is ConnectionStatus.REVOKED
    assert connection.encrypted_access_token is None
    with pytest.raises(ConnectionRevokedError):
        await service.test(owner.id, connection.id)
