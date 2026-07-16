from uuid import uuid4

from app.models.enums import AutonomyLevel
from app.models.user import User


def user(**overrides: object) -> User:
    """Build an unsaved user with safe, unique defaults."""
    defaults: dict[str, object] = {
        "auth_subject": f"test-user-{uuid4()}",
        "email": f"test-{uuid4()}@example.test",
        "display_name": "Test User",
        "default_autonomy": AutonomyLevel.SAFE_ACTIONS,
    }
    defaults.update(overrides)
    return User(**defaults)  # type: ignore[arg-type]
