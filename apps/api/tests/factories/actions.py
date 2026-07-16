from uuid import uuid4

from app.models.action import Action
from app.models.enums import ActionStatus, RiskLevel
from app.models.plan import Plan


def action(plan: Plan, **overrides: object) -> Action:
    defaults: dict[str, object] = {
        "plan": plan,
        "action_type": "travel.notify_family",
        "connector": "telegram",
        "input": {
            "message": "Your test trip is ready.",
            "event_id": str(plan.source_event_id or "test-event"),
            "event_type": "travel_booked",
        },
        "status": ActionStatus.WAITING_APPROVAL,
        "risk_level": RiskLevel.YELLOW,
        "requires_approval": True,
        "idempotency_key": f"test-action-{uuid4()}",
        "policy_reason": "approval_required",
    }
    defaults.update(overrides)
    return Action(**defaults)  # type: ignore[arg-type]
