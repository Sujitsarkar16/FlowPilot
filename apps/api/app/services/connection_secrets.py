"""Connector token persistence that never logs or returns ciphertext/plaintext externally."""

from dataclasses import dataclass

from app.core.crypto import SecretCipher
from app.models.connection import Connection


@dataclass(frozen=True)
class ConnectionTokens:
    access_token: str | None
    refresh_token: str | None


class ConnectionSecrets:
    """Store connector credentials as versioned authenticated ciphertext."""

    def __init__(self, cipher: SecretCipher) -> None:
        self._cipher = cipher

    def save(
        self,
        connection: Connection,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        if access_token is not None:
            connection.encrypted_access_token = self._cipher.encrypt(access_token)
        if refresh_token is not None:
            connection.encrypted_refresh_token = self._cipher.encrypt(refresh_token)
        connection.token_metadata = {
            **(connection.token_metadata or {}),
            "encryption_version": self._cipher.version,
            "encryption_key_id": self._cipher.current_key_id,
        }

    def clear(self, connection: Connection) -> None:
        """Remove credential material when a user disconnects a provider."""
        connection.encrypted_access_token = None
        connection.encrypted_refresh_token = None
        connection.token_metadata = {
            key: value
            for key, value in (connection.token_metadata or {}).items()
            if key not in {"encryption_version", "encryption_key_id"}
        }

    def load(self, connection: Connection) -> ConnectionTokens:
        return ConnectionTokens(
            access_token=(
                self._cipher.decrypt(connection.encrypted_access_token)
                if connection.encrypted_access_token
                else None
            ),
            refresh_token=(
                self._cipher.decrypt(connection.encrypted_refresh_token)
                if connection.encrypted_refresh_token
                else None
            ),
        )
