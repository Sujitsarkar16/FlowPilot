from uuid import uuid4

from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.models.user import User


def connection(user: User, **overrides: object) -> Connection:
    defaults: dict[str, object] = {
        "user": user,
        "provider": ConnectionProvider.TELEGRAM,
        "provider_account_id": f"test-account-{uuid4()}",
        "status": ConnectionStatus.CONNECTED,
        "scopes": ["bot.send_messages"],
        "token_metadata": {},
    }
    defaults.update(overrides)
    return Connection(**defaults)  # type: ignore[arg-type]
