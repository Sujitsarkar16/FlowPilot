import base64

import httpx
import pytest
from sqlalchemy import select

from app.connectors.google.gmail import GmailClient
from app.core.crypto import SecretCipher
from app.models.connection import Connection
from app.models.enums import ConnectionProvider
from app.models.event import RawEvent
from app.models.user import User
from app.services.connection_secrets import ConnectionSecrets
from app.services.gmail_sync import GmailSyncError, GmailSyncService


def encrypted_secrets() -> ConnectionSecrets:
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")
    return ConnectionSecrets(SecretCipher(key))


def gmail_message(message_id: str) -> dict[str, object]:
    return {
        "id": message_id,
        "historyId": "11",
        "internalDate": "1735689600000",
        "payload": {
            "headers": [
                {"name": "From", "value": "Travel <travel@example.com>"},
                {"name": "Subject", "value": "Flight confirmation"},
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": "VHJpcCBjb25maXJtZWQ"}}],
        },
    }


async def gmail_connection(session: object) -> tuple[Connection, ConnectionSecrets]:
    secrets = encrypted_secrets()
    user = User(auth_subject="gmail-sync-user")
    connection = Connection(user=user, provider=ConnectionProvider.GOOGLE, provider_account_id="gmail")
    secrets.save(connection, access_token="access", refresh_token="refresh")
    session.add_all([user, connection])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    return connection, secrets


@pytest.mark.asyncio
async def test_sync_is_idempotent_and_only_advances_after_success(session: object) -> None:
    connection, secrets = await gmail_connection(session)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "10"})
        if path.endswith("/history"):
            return httpx.Response(
                200, json={"history": [{"messagesAdded": [{"message": {"id": "m-1"}}]}], "historyId": "11"}
            )
        if path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m-1"}]})
        return httpx.Response(200, json=gmail_message("m-1"))

    service = GmailSyncService(session, GmailClient(transport=httpx.MockTransport(handler)), secrets)  # type: ignore[arg-type]
    first = await service.sync_connection(connection)
    second = await service.sync_connection(connection)

    assert (first.ingested, first.duplicates, first.cursor) == (1, 0, "10")
    assert (second.ingested, second.duplicates, second.cursor) == (0, 1, "11")
    assert len(list(await session.scalars(select(RawEvent)))) == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_sync_does_not_advance_cursor_when_ingestion_fails(session: object) -> None:
    connection, secrets = await gmail_connection(session)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "10"})
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "broken"}]})
        return httpx.Response(500, json={"error": {"message": "provider failure"}})

    service = GmailSyncService(session, GmailClient(transport=httpx.MockTransport(handler)), secrets)  # type: ignore[arg-type]
    with pytest.raises(GmailSyncError):
        await service.sync_connection(connection)

    await session.refresh(connection)  # type: ignore[attr-defined]
    assert "gmail_history_id" not in connection.token_metadata
