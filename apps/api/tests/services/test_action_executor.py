import pytest
from sqlalchemy import select

from app.connectors.base import MockConnector
from app.core.config import Settings
from app.models.enums import ActionStatus, JobStatus, PlanStatus
from app.models.event_attachment import EventAttachment
from app.schemas.connector import ConnectorErrorCategory
from app.services.action_executor import ActionExecutor
from app.services.connector_registry import ConnectorRegistry
from app.services.job_queue import JobQueue
from app.services.runtime_connectors import build_runtime_connector_registry
from tests.execution_helpers import action_state


@pytest.mark.asyncio
async def test_executor_completes_once_and_updates_plan(session) -> None:
    _, plan, action = await action_state(session)
    queue = JobQueue(session)
    job = await queue.enqueue_action(action)
    claimed = await queue.claim_next("worker")
    assert claimed is not None

    await ActionExecutor(session, queue=queue).execute(claimed)
    action_status = await session.scalar(
        select(type(action).status).where(type(action).id == action.id)
    )
    plan_status = await session.scalar(select(type(plan).status).where(type(plan).id == plan.id))
    job_status = await session.scalar(select(type(job).status).where(type(job).id == job.id))

    assert action_status is ActionStatus.COMPLETED
    assert plan_status is PlanStatus.COMPLETED
    assert job_status is JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_executor_schedules_retryable_connector_failure(session) -> None:
    _, plan, action = await action_state(session)
    queue = JobQueue(session)
    job = await queue.enqueue_action(action)
    claimed = await queue.claim_next("worker")
    assert claimed is not None
    connectors = ConnectorRegistry((MockConnector("weather", (ConnectorErrorCategory.RETRYABLE,)),))

    await ActionExecutor(session, queue=queue, connectors=connectors).execute(claimed)
    await session.refresh(action)
    await session.refresh(job)

    assert action.status is ActionStatus.QUEUED
    assert plan.status is PlanStatus.RUNNING
    assert job.status is JobStatus.RETRYING


@pytest.mark.asyncio
async def test_waiting_approval_action_is_never_executed(session) -> None:
    _, _, action = await action_state(session, status=ActionStatus.WAITING_APPROVAL)
    queue = JobQueue(session)
    await queue.enqueue_action(action)
    claimed = await queue.claim_next("worker")
    assert claimed is not None
    connector = MockConnector("weather")

    await ActionExecutor(session, queue=queue, connectors=ConnectorRegistry((connector,))).execute(
        claimed
    )

    assert connector.executions == []


@pytest.mark.asyncio
async def test_executor_saves_generated_documents_in_event_folder(session) -> None:
    user, plan, action = await action_state(session)
    action.action_type = "travel.generate_documents"
    action.connector = "internal"
    await session.commit()
    queue = JobQueue(session)
    await queue.enqueue_action(action)
    claimed = await queue.claim_next("worker")
    assert claimed is not None

    await ActionExecutor(
        session,
        queue=queue,
        connectors=build_runtime_connector_registry(session, Settings(_env_file=None)),
    ).execute(claimed)
    await session.refresh(action)
    assert action.status is ActionStatus.COMPLETED, action.last_error
    documents = list(
        await session.scalars(
            select(EventAttachment)
            .where(
                EventAttachment.user_id == user.id,
                EventAttachment.life_event_id == plan.source_event_id,
            )
            .order_by(EventAttachment.filename)
        )
    )

    assert [document.mime_type for document in documents] == [
        "text/markdown",
        "text/markdown",
    ]
    assert {document.filename.split("-", 1)[0] for document in documents} == {
        "itinerary",
        "packing_checklist",
    }
    assert all(document.content for document in documents)
