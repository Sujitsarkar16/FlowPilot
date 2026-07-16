from app.models.enums import PlanStatus
from app.models.event import LifeEvent
from app.models.plan import Plan
from app.models.user import User


def plan(user: User, event: LifeEvent, **overrides: object) -> Plan:
    defaults: dict[str, object] = {
        "user": user,
        "source_event": event,
        "objective": "Complete the test workflow",
        "status": PlanStatus.POLICY_CHECKED,
        "is_shadow": False,
        "execution_requested": False,
    }
    defaults.update(overrides)
    return Plan(**defaults)  # type: ignore[arg-type]
