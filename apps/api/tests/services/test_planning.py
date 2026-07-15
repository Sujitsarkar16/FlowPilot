from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.plans import PlanRepository
from app.models.connection import Connection
from app.models.enums import (
    ActionStatus,
    AutonomyLevel,
    CompilationStatus,
    ConnectionProvider,
    ConnectionStatus,
    EventSource,
    Importance,
    LifeEventType,
    RawEventStatus,
)
from app.models.event import EventEntity, LifeEvent, RawEvent
from app.models.standing_order import StandingOrder
from app.models.user import User
from app.services.ai.fake_provider import FakeAIProvider
from app.services.plan_customizer import PlanCustomizer
from app.services.planning import NoMatchingStandingOrderError, PlanningService


def rule(event_type: str, templates: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "trigger_event_types": [event_type],
        "entity_conditions": [{"field": "destination.name", "operator": "exists"}],
        "action_templates": templates,
        "explanation": "Prepare the event safely.",
    }


async def add_event(session: AsyncSession, user: User, event_type: LifeEventType) -> LifeEvent:
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
        type=event_type,
        confidence=0.95,
        importance=Importance.HIGH,
        summary="Booked a trip",
        occurred_at=datetime.now(UTC),
    )
    session.add_all(
        [raw, event, EventEntity(life_event=event, kind="destination", value={"name": "Paris"})]
    )
    await session.commit()
    return event


async def add_order(
    session: AsyncSession, user: User, event_type: str, templates: list[dict[str, object]]
) -> None:
    session.add(
        StandingOrder(
            user_id=user.id,
            instruction="Prepare matching events.",
            compiled_rule=rule(event_type, templates),
            enabled=True,
            compilation_status=CompilationStatus.COMPILED,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_create_is_idempotent_replays_and_persists_ai_rationale(
    session: AsyncSession,
) -> None:
    user = User(auth_subject="planner", default_autonomy=AutonomyLevel.SAFE_ACTIONS)
    session.add(user)
    await session.commit()
    event = await add_event(session, user, LifeEventType.TRAVEL_BOOKED)
    await add_order(
        session,
        user,
        "travel_booked",
        [
            {
                "action_type": "travel.get_weather",
                "connector": "weather",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            }
        ],
    )
    customizer = PlanCustomizer(
        FakeAIProvider(
            lambda _system, _user, _schema: {"rationale": "Use the destination.", "overrides": {}}
        )
    )
    service = PlanningService(session, customizer)

    first = await service.create(user, event.id)
    repeated = await service.create(user, event.id)
    replayed = await service.create(user, event.id, replay=True)

    assert repeated.id == first.id
    assert replayed.id != first.id
    assert first.planner_rationale == "Use the destination."
    assert len(await PlanRepository(session).list_for_event(user.id, event.id)) == 2


@pytest.mark.asyncio
async def test_create_raises_when_no_enabled_compiled_rule_matches(session: AsyncSession) -> None:
    user = User(auth_subject="no-match")
    session.add(user)
    await session.commit()
    event = await add_event(session, user, LifeEventType.TRAVEL_BOOKED)

    with pytest.raises(NoMatchingStandingOrderError, match="No enabled standing order"):
        await PlanningService(session).create(user, event.id)


@pytest.mark.asyncio
async def test_policy_persists_safe_weather_and_blocks_disconnected_external_provider(
    session: AsyncSession,
) -> None:
    user = User(auth_subject="policy", default_autonomy=AutonomyLevel.SAFE_ACTIONS)
    session.add(user)
    await session.commit()
    event = await add_event(session, user, LifeEventType.TRAVEL_BOOKED)
    await add_order(
        session,
        user,
        "travel_booked",
        [
            {
                "action_type": "travel.get_weather",
                "connector": "weather",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            },
            {
                "action_type": "travel.create_folder",
                "connector": "google",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            },
        ],
    )
    session.add(
        Connection(
            user_id=user.id,
            provider=ConnectionProvider.GOOGLE,
            provider_account_id="revoked",
            status=ConnectionStatus.REVOKED,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
    )
    await session.commit()

    plan = await PlanningService(session).create(user, event.id)
    actions = {action.action_type: action for action in plan.actions}

    assert (actions["travel.get_weather"].status, actions["travel.get_weather"].policy_reason) == (
        ActionStatus.PLANNED,
        "safe_automatic",
    )
    assert (
        actions["travel.create_folder"].status,
        actions["travel.create_folder"].policy_reason,
    ) == (ActionStatus.BLOCKED, "connection_missing")


@pytest.mark.asyncio
async def test_red_action_waits_for_approval_when_its_provider_is_connected(
    session: AsyncSession,
) -> None:
    user = User(auth_subject="salary", default_autonomy=AutonomyLevel.SAFE_ACTIONS)
    session.add(user)
    await session.commit()
    event = await add_event(session, user, LifeEventType.SALARY_CREDITED)
    await add_order(
        session,
        user,
        "salary_credited",
        [
            {
                "action_type": "salary.propose_transfer",
                "connector": "mock_bank",
                "input": {},
                "risk_level": "red",
                "approval_mode": "approval_required",
            }
        ],
    )
    session.add(
        Connection(
            user_id=user.id,
            provider=ConnectionProvider.MOCK_BANK,
            provider_account_id="account",
            status=ConnectionStatus.CONNECTED,
            scopes=["transfers:write"],
        )
    )
    await session.commit()

    plan = await PlanningService(session).create(user, event.id)
    action = plan.actions[0]

    assert plan.status.value == "waiting_approval"
    assert (action.status, action.requires_approval, action.policy_reason) == (
        ActionStatus.WAITING_APPROVAL,
        True,
        "red_requires_approval",
    )
