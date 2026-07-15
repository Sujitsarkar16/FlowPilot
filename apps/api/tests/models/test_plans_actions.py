from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.action import Action, ActionDependency
from app.models.enums import ActionStatus, EventSource, Importance, LifeEventType, RiskLevel
from app.models.event import LifeEvent, RawEvent
from app.models.plan import Plan
from app.models.user import User


async def make_plan(session: object) -> Plan:
    user = User(auth_subject="subject-plan")
    session.add(user)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.MANUAL,
        event_type="text",
        fingerprint="plan-fp",
        payload={},
        received_at=datetime.now(UTC),
    )
    session.add(raw)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    life = LifeEvent(
        user_id=user.id,
        raw_event_id=raw.id,
        type=LifeEventType.TRAVEL_BOOKED,
        confidence=1,
        importance=Importance.HIGH,
        summary="Trip",
        occurred_at=datetime.now(UTC),
    )
    session.add(life)  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    return Plan(user_id=user.id, source_event_id=life.id, objective="Prepare trip")


@pytest.mark.asyncio
async def test_plan_dag_rejects_duplicate_edges(session: object) -> None:
    plan = await make_plan(session)
    first = Action(
        plan=plan,
        action_type="folder",
        connector="drive",
        risk_level=RiskLevel.GREEN,
        idempotency_key="first",
    )
    second = Action(
        plan=plan,
        action_type="calendar",
        connector="calendar",
        risk_level=RiskLevel.GREEN,
        idempotency_key="second",
    )
    session.add_all([plan, first, second])  # type: ignore[attr-defined]
    await session.flush()  # type: ignore[attr-defined]
    session.add_all(
        [
            ActionDependency(action_id=second.id, depends_on_action_id=first.id),
            ActionDependency(action_id=second.id, depends_on_action_id=first.id),
        ]
    )  # type: ignore[attr-defined]
    with pytest.raises(IntegrityError):
        await session.commit()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_completed_action_requires_completion_timestamp(session: object) -> None:
    plan = await make_plan(session)
    action = Action(
        plan=plan,
        action_type="folder",
        connector="drive",
        risk_level=RiskLevel.GREEN,
        idempotency_key="complete",
        status=ActionStatus.COMPLETED,
    )
    session.add_all([plan, action])  # type: ignore[attr-defined]
    with pytest.raises(IntegrityError):
        await session.commit()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_red_action_requires_approval_and_records_completion(session: object) -> None:
    plan = await make_plan(session)
    action = Action(
        plan=plan,
        action_type="message",
        connector="telegram",
        risk_level=RiskLevel.RED,
        requires_approval=True,
        idempotency_key="red",
        status=ActionStatus.COMPLETED,
        completed_at=datetime.now(UTC),
    )
    session.add_all([plan, action])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    assert action.completed_at is not None
