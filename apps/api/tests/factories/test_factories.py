import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action import Action
from app.models.approval import Approval
from app.models.connection import Connection
from app.models.enums import LifeEventType
from app.models.event import LifeEvent
from app.models.plan import Plan
from app.models.user import User
from tests.factories import action, approval, connection, plan, user
from tests.fixtures import client_event, flight_event, salary_event


@pytest.mark.asyncio
async def test_factories_persist_a_complete_approval_workflow(session: AsyncSession) -> None:
    actor = user()
    event = flight_event(actor)
    workflow = plan(actor, event)
    pending_action = action(workflow)
    pending_approval = approval(pending_action)
    provider_connection = connection(actor)
    session.add_all([actor, event, workflow, pending_action, pending_approval, provider_connection])
    await session.commit()

    assert await session.scalar(select(User).where(User.id == actor.id)) is actor
    assert await session.scalar(select(LifeEvent).where(LifeEvent.id == event.id)) is event
    assert await session.scalar(select(Plan).where(Plan.id == workflow.id)) is workflow
    assert await session.scalar(select(Action).where(Action.id == pending_action.id)) is pending_action
    assert await session.scalar(select(Approval).where(Approval.id == pending_approval.id)) is pending_approval
    assert await session.scalar(select(Connection).where(Connection.id == provider_connection.id)) is provider_connection


def test_scenario_fixtures_cover_the_mvp_event_types() -> None:
    actor = user()
    assert flight_event(actor).type is LifeEventType.TRAVEL_BOOKED
    assert client_event(actor).type is LifeEventType.CLIENT_CONFIRMED
    assert salary_event(actor).type is LifeEventType.SALARY_CREDITED
