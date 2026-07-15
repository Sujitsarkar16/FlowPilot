import base64
from uuid import uuid4

from app.core.crypto import SecretCipher
from app.models.connection import Connection
from app.models.enums import ConnectionProvider
from app.services.connection_secrets import ConnectionSecrets


def test_connection_secrets_encrypts_tokens_and_records_version() -> None:
    key = base64.urlsafe_b64encode(b"d" * 32).decode().rstrip("=")
    cipher = SecretCipher(key)
    connection = Connection(
        user_id=uuid4(),
        provider=ConnectionProvider.GOOGLE,
        provider_account_id="account",
    )
    secrets = ConnectionSecrets(cipher)
    secrets.save(connection, access_token="access-secret", refresh_token="refresh-secret")
    assert (
        connection.encrypted_access_token
        and "access-secret" not in connection.encrypted_access_token
    )
    assert connection.token_metadata == {
        "encryption_version": "v1",
        "encryption_key_id": cipher.current_key_id,
    }
    assert secrets.load(connection).access_token == "access-secret"
    assert secrets.load(connection).refresh_token == "refresh-secret"
