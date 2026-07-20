from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    CompilationStatus,
    EventSource,
    LifeEventType,
    RawEventStatus,
)
from app.models.event import RawEvent
from app.models.standing_order import StandingOrder
from app.models.user import User
from app.services.ai.fake_provider import FakeAIProvider
from app.services.event_pipeline import EventPipelineService


def travel_ai() -> FakeAIProvider:
    def responder(_system: str, _user: str, schema: type) -> dict[str, object]:
        if schema.__name__ == "Classification":
            return {
                "type": "travel_booked",
                "confidence": 0.96,
                "importance": "high",
                "summary": "Booked flight to Paris",
                "reason": "confirmation email",
            }
        if schema.__name__ == "PlanCustomizationOutput":
            return {"rationale": "Use the confirmed trip details.", "overrides": {}}
        return {"entities": [{"kind": "destination", "value": {"name": "Paris"}}]}

    return FakeAIProvider(responder)


@pytest.mark.asyncio
async def test_pipeline_classifies_extracts_and_plans(session: AsyncSession) -> None:
    user = User(auth_subject="pipeline-user")
    session.add(user)
    await session.flush()
    session.add(
        StandingOrder(
            user_id=user.id,
            instruction="Prepare travel",
            compiled_rule={
                "schema_version": "1.0",
                "trigger_event_types": ["travel_booked"],
                "entity_conditions": [],
                "action_templates": [
                    {
                        "action_type": "travel.get_weather",
                        "connector": "weather",
                        "input": {},
                        "risk_level": "green",
                        "approval_mode": "automatic",
                    }
                ],
                "explanation": "Prepare travel",
            },
            enabled=True,
            compilation_status=CompilationStatus.COMPILED,
        )
    )
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.GMAIL,
        event_type="email",
        fingerprint=str(uuid4()),
        status=RawEventStatus.RECEIVED,
        payload={
            "trusted_metadata": {"subject": "Flight confirmation"},
            "untrusted_content": "Your flight to Paris is confirmed.",
            "attachments": [],
        },
        received_at=datetime.now(UTC),
    )
    session.add(raw)
    await session.commit()

    first = await EventPipelineService(session, travel_ai()).process_raw_event(raw, user)
    second = await EventPipelineService(session, travel_ai()).process_raw_event(raw, user)

    assert first.already_processed is False
    assert first.life_event is not None
    assert first.life_event.type is LifeEventType.TRAVEL_BOOKED
    assert first.plan is not None
    assert first.plan.planner_rationale == "Use the confirmed trip details."
    assert second.already_processed is True
    assert second.life_event is not None
    assert second.plan is not None
    assert second.plan.id == first.plan.id


@pytest.mark.asyncio
async def test_pipeline_without_standing_order_still_classifies(session: AsyncSession) -> None:
    user = User(auth_subject="pipeline-no-rule")
    session.add(user)
    await session.flush()
    raw = RawEvent(
        user_id=user.id,
        source=EventSource.GMAIL,
        event_type="email",
        fingerprint=str(uuid4()),
        status=RawEventStatus.RECEIVED,
        payload={
            "trusted_metadata": {},
            "untrusted_content": "Hello",
            "attachments": [],
        },
        received_at=datetime.now(UTC),
    )
    session.add(raw)
    await session.commit()

    result = await EventPipelineService(session, travel_ai()).process_raw_event(raw, user)

    assert result.life_event is not None
    assert result.plan is None
