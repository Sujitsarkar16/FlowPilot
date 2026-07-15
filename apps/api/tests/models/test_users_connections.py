import pytest
from sqlalchemy.exc import IntegrityError

from app.models.connection import Connection
from app.models.enums import ConnectionProvider
from app.models.user import User


@pytest.mark.asyncio
async def test_user_connection_relationship_and_unique_account(session: object) -> None:
    user = User(auth_subject="supabase-1", email="user@example.com")
    connection = Connection(
        user=user, provider=ConnectionProvider.GOOGLE, provider_account_id="google-1"
    )
    session.add_all([user, connection])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    assert user.connections == [connection]
    assert connection.encrypted_access_token is None

    session.add(
        Connection(user=user, provider=ConnectionProvider.GOOGLE, provider_account_id="google-1")
    )  # type: ignore[attr-defined]
    with pytest.raises(IntegrityError):
        await session.commit()  # type: ignore[attr-defined]
    await session.rollback()  # type: ignore[attr-defined]
