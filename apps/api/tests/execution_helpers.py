from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action import Action
from app.models.enums import (
    ActionStatus,
    AutonomyLevel,
    EventSource,
    Importance,
    LifeEventType,
    PlanStatus,
    RawEventStatus,
    RiskLevel,
)
from app.models.event import LifeEvent, RawEvent
from app.models.plan import Plan
from app.models.user import User


async def action_state(
    session: AsyncSession,
    *,
    status: ActionStatus = ActionStatus.QUEUED,
    plan_status: PlanStatus = PlanStatus.RUNNING,
) -> tuple[User, Plan, Action]:
    user = User(auth_subject=f"execution-{uuid4()}", default_autonomy=AutonomyLevel.SAFE_ACTIONS)
    session.add(user)
    await session.flush()
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.MANUAL,
        event_type="manual",
        fingerprint=str(uuid4()),
        status=RawEventStatus.NORMALIZED,
        payload={},
        received_at=datetime.now(UTC),
    )
    event = LifeEvent(
        user_id=user.id,
        raw_event=raw,
        type=LifeEventType.TRAVEL_BOOKED,
        confidence=0.9,
        importance=Importance.HIGH,
        summary="Trip",
        occurred_at=datetime.now(UTC),
    )
    session.add_all([user, raw, event])
    await session.flush()
    plan = Plan(
        user_id=user.id, source_event_id=event.id, objective="Prepare trip", status=plan_status
    )
    action = Action(
        plan=plan,
        action_type="travel.get_weather",
        connector="weather",
        input={"event_id": str(event.id), "event_type": "travel_booked"},
        status=status,
        risk_level=RiskLevel.GREEN,
        requires_approval=False,
        idempotency_key=f"action-{uuid4()}",
        completed_at=datetime.now(UTC) if status is ActionStatus.COMPLETED else None,
    )
    session.add_all([plan, action])
    await session.commit()
    return user, plan, action
