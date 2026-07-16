from datetime import UTC, datetime, timedelta

from app.models.action import Action
from app.models.approval import Approval


def approval(action: Action, **overrides: object) -> Approval:
    defaults: dict[str, object] = {
        "action": action,
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
    }
    defaults.update(overrides)
    return Approval(**defaults)  # type: ignore[arg-type]
