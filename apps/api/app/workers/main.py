"""Bounded-concurrency durable action worker."""

import asyncio
import logging
import signal
from collections.abc import Callable
from time import perf_counter
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import bind_log_context
from app.core.metrics import metrics
from app.db.session import get_session_factory
from app.models.enums import JobStatus
from app.services.action_executor import ActionExecutor
from app.services.connector_registry import ConnectorRegistry
from app.services.job_queue import JobQueue
from app.services.runtime_connectors import build_runtime_connector_registry
from app.workers.heartbeat import emit_heartbeat

logger = logging.getLogger(__name__)


class DurableWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str | None = None,
        poll_interval_seconds: float = 1.0,
        concurrency: int = 4,
        connector_factory: Callable[[AsyncSession], ConnectorRegistry] = build_runtime_connector_registry,
    ) -> None:
        self._sessions = session_factory
        self._connector_factory = connector_factory
        self.worker_id = worker_id or f"worker-{uuid4()}"
        self._poll_interval = poll_interval_seconds
        self._concurrency = concurrency
        self._stopping = False

    def stop(self) -> None:
        """Stop claiming new work and let currently claimed jobs finish."""
        self._stopping = True

    async def run_once(self) -> bool:
        async with self._sessions() as session:
            queue = JobQueue(session)
            job = await queue.claim_next(self.worker_id)
            if job is None:
                return False
            started = perf_counter()
            with bind_log_context(job_id=str(job.id)):
                try:
                    await ActionExecutor(
                        session, queue=queue, connectors=self._connector_factory(session)
                    ).execute(job)
                    outcome = (
                        "succeeded"
                        if job.status is JobStatus.COMPLETED
                        else "retried"
                        if job.status is JobStatus.RETRYING
                        else "failed"
                    )
                    metrics.observe("executions", outcome, perf_counter() - started)
                    logger.info("worker job completed", extra={"duration_ms": (perf_counter() - started) * 1000})
                except Exception:
                    metrics.observe("executions", "failed", perf_counter() - started)
                    logger.exception("worker job failed")
                    if job.status is JobStatus.RUNNING:
                        await queue.dead_letter(job, "Worker execution failed")
            return True

    async def run(self) -> None:
        while not self._stopping:

            async def consume_available() -> int:
                completed = 0
                while not self._stopping and await self.run_once():
                    completed += 1
                return completed

            completed = await asyncio.gather(
                *(consume_available() for _ in range(self._concurrency)), return_exceptions=True
            )
            emit_heartbeat(self.worker_id)
            if not self._stopping and not any(
                isinstance(result, int) and result for result in completed
            ):
                await asyncio.sleep(self._poll_interval)


def _install_signal_handlers(worker: DurableWorker) -> None:
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, worker.stop)
        except NotImplementedError:
            signal.signal(signal_name, lambda _signum, _frame: worker.stop())


async def _main() -> None:
    worker = DurableWorker(get_session_factory())
    _install_signal_handlers(worker)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())
