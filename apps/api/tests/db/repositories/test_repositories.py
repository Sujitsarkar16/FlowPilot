from datetime import UTC, datetime

import pytest

from app.db.repositories.audit import AuditRepository
from app.db.repositories.connections import ConnectionRepository
from app.db.repositories.events import EventRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.plans import PlanRepository
from app.db.repositories.standing_orders import StandingOrderRepository
from app.db.repositories.users import UserRepository
from app.models.audit import AuditEntry
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, EventSource, Importance, JobStatus, LifeEventType
from app.models.event import LifeEvent, RawEvent
from app.models.job import Job
from app.models.plan import Plan
from app.models.standing_order import StandingOrder
from app.models.user import User


@pytest.mark.asyncio
async def test_explicit_repositories_keep_queries_user_scoped(session: object) -> None:
    users = UserRepository(session)  # type: ignore[arg-type]
    user = await users.add(User(auth_subject="repository-user"))
    await session.commit()  # type: ignore[attr-defined]
    assert await users.get_by_subject("repository-user") is user

    connection = Connection(
        user_id=user.id, provider=ConnectionProvider.GITHUB, provider_account_id="repo-user"
    )
    session.add(connection)  # type: ignore[attr-defined]
    order = await StandingOrderRepository(session).add(
        StandingOrder(user_id=user.id, instruction="Prepare trips")
    )  # type: ignore[arg-type]
    await session.flush()  # type: ignore[attr-defined]
    assert (await ConnectionRepository(session).list(user.id)) == [connection]  # type: ignore[arg-type]
    assert await StandingOrderRepository(session).get(user.id, order.id) is order  # type: ignore[arg-type]

    raw = await EventRepository(session).add_raw(
        RawEvent(  # type: ignore[arg-type]
            user_id=user.id,
            source=EventSource.MANUAL,
            event_type="text",
            fingerprint="repository-event",
            payload={},
            received_at=datetime.now(UTC),
        )
    )
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
    assert (await EventRepository(session).list_life(user.id, None, 10)) == [life]  # type: ignore[arg-type]

    plan = await PlanRepository(session).add(
        Plan(user_id=user.id, source_event_id=life.id, objective="Prepare")
    )  # type: ignore[arg-type]
    job = await JobRepository(session).add(
        Job(
            job_type="plan",
            payload={},
            status=JobStatus.QUEUED,
            run_at=datetime.now(UTC),
            idempotency_key="repository-job",
        )
    )  # type: ignore[arg-type]
    audit = await AuditRepository(session).append(
        AuditEntry(
            user_id=user.id,
            life_event_id=life.id,
            event_name="planned",
            actor_type="system",
            payload={},
        )
    )  # type: ignore[arg-type]
    await session.flush()  # type: ignore[attr-defined]

    assert await PlanRepository(session).get(user.id, plan.id) is plan  # type: ignore[arg-type]
    assert await JobRepository(session).get_by_key("repository-job") is job  # type: ignore[arg-type]
    assert (await JobRepository(session).list_due(datetime.now(UTC), 10)) == [job]  # type: ignore[arg-type]
    assert (await AuditRepository(session).list_for_event(user.id, life.id, None, 10)) == [audit]  # type: ignore[arg-type]
