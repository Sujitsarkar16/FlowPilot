"""Periodic Gmail ingestion worker, kept separate from action-only durable jobs."""

import asyncio
import logging
import signal
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.connectors.google.gmail import GmailClient
from app.core.config import get_settings
from app.core.crypto import SecretCipher
from app.db.session import get_session_factory
from app.services.ai import build_ai_provider_optional
from app.services.connection_secrets import ConnectionSecrets
from app.services.gmail_sync import GmailSyncService
from app.workers.heartbeat import emit_heartbeat

logger = logging.getLogger(__name__)
SyncFactory = Callable[[AsyncSession], GmailSyncService]


class GmailPollWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        sync_factory: SyncFactory | None = None,
        worker_id: str | None = None,
        poll_interval_seconds: float = 60.0,
    ) -> None:
        self._sessions = session_factory
        self._sync_factory = sync_factory or self._default_sync_factory
        self.worker_id = worker_id or f"gmail-poll-{uuid4()}"
        self._poll_interval = poll_interval_seconds
        self._stopping = False

    def stop(self) -> None:
        self._stopping = True

    async def run_once(self) -> int:
        async with self._sessions() as session:
            try:
                results = await self._sync_factory(session).sync_all()
            except Exception:
                logger.exception("gmail polling failed")
                return 0
            return sum(result.ingested for result in results)

    async def run(self) -> None:
        while not self._stopping:
            await self.run_once()
            emit_heartbeat(self.worker_id)
            if not self._stopping:
                await asyncio.sleep(self._poll_interval)


    @staticmethod
    def _default_sync_factory(session: AsyncSession) -> GmailSyncService:
        settings = get_settings()
        if settings.encryption_key is None:
            raise RuntimeError("Connection encryption is not configured")
        cipher = SecretCipher(
            settings.encryption_key.get_secret_value(),
            [key.get_secret_value() for key in settings.encryption_previous_keys],
        )
        return GmailSyncService(
            session,
            GmailClient(settings),
            ConnectionSecrets(cipher),
            ai_provider=build_ai_provider_optional(settings),
        )


def _install_signal_handlers(worker: GmailPollWorker) -> None:
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, worker.stop)
        except NotImplementedError:
            signal.signal(signal_name, lambda _signum, _frame: worker.stop())


async def _main() -> None:
    worker = GmailPollWorker(get_session_factory())
    _install_signal_handlers(worker)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())
