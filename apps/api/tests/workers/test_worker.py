import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.action import Action
from app.models.enums import ActionStatus
from app.services.connector_registry import DEFAULT_CONNECTOR_REGISTRY
from app.workers.main import DurableWorker
from tests.execution_helpers import action_state


@pytest.mark.asyncio
async def test_worker_processes_a_queued_mock_action(session: AsyncSession) -> None:
    _, _, action = await action_state(session)
    from app.services.job_queue import JobQueue

    await JobQueue(session).enqueue_action(action)
    bind = session.bind
    assert bind is not None
    factory = async_sessionmaker(bind, expire_on_commit=False)
    worker = DurableWorker(
        factory, worker_id="test-worker", connector_factory=lambda _: DEFAULT_CONNECTOR_REGISTRY
    )

    assert await worker.run_once()
    status = await session.scalar(select(Action.status).where(Action.id == action.id))
    assert status is ActionStatus.COMPLETED
