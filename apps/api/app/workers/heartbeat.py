"""Minimal worker heartbeat logging."""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def emit_heartbeat(worker_id: str) -> None:
    logger.info(
        "worker heartbeat", extra={"worker_id": worker_id, "at": datetime.now(UTC).isoformat()}
    )
