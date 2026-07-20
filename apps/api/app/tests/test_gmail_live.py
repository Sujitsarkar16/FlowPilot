import pytest
from sqlalchemy import select

from app.connectors.google.gmail import GmailClient
from app.core.config import get_settings
from app.core.crypto import SecretCipher
from app.db.session import get_session_factory
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.services.connection_secrets import ConnectionSecrets


@pytest.mark.asyncio
async def test_fetch_latest_10_gmails() -> None:
    settings = get_settings()

    # Check if encryption_key is available
    assert settings.encryption_key is not None, "Encryption key is not set in settings"

    # Init cipher and secrets
    cipher = SecretCipher(settings.encryption_key.get_secret_value())
    secrets = ConnectionSecrets(cipher)

    # Init DB Session
    session_maker = get_session_factory()
    async with session_maker() as session:
        # Get a valid Google connection
        stmt = select(Connection).where(
            Connection.provider == ConnectionProvider.GOOGLE,
            Connection.status == ConnectionStatus.CONNECTED,
        ).limit(1)
        result = await session.execute(stmt)
        connection = result.scalar_one_or_none()

        assert connection is not None, "No active Google connection found in the database"

        # Load tokens
        tokens = secrets.load(connection)
        assert tokens.access_token or tokens.refresh_token, "No credentials found for connection"

        gmail = GmailClient(settings)
        access_token = tokens.access_token

        # Refresh if necessary
        try:
            if access_token:
                await gmail.profile_history_id(access_token)
        except Exception:
            assert tokens.refresh_token is not None, "No refresh token available to renew credentials"
            refreshed = await gmail.refresh_access_token(tokens.refresh_token)
            access_token = refreshed.access_token
            # Save back to DB
            secrets.save(connection, access_token, refreshed.refresh_token)
            await session.commit()

        assert access_token is not None, "Failed to obtain access token"

        # Fetch latest messages
        print("\nFetching latest 10 emails from Gmail...")
        page = await gmail.list_messages(access_token)
        message_ids = page.message_ids[:10]

        assert len(message_ids) > 0, "No emails found in the inbox"

        for idx, message_id in enumerate(message_ids):
            message = await gmail.get_message(access_token, message_id)
            # Encode and decode with replace to handle characters not in cp1252 on Windows console
            subject = message.subject.encode("ascii", errors="replace").decode("ascii")
            sender = message.sender.encode("ascii", errors="replace").decode("ascii")
            print(f"[{idx+1}] {subject} (From: {sender}) - {message.received_at}")

        print("Successfully fetched 10 emails.")
