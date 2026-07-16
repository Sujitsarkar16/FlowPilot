"""Small JSON-compatible logging configuration."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.services.audit_redaction import redact

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
route_context: ContextVar[str | None] = ContextVar("route", default=None)
trace_context: ContextVar[dict[str, str]] = ContextVar("trace_context", default={})
_TRACE_FIELDS = frozenset({"event_id", "plan_id", "action_id", "job_id"})
_RECORD_FIELDS = _TRACE_FIELDS | {"duration_ms"}


@contextmanager
def bind_log_context(**values: object) -> Iterator[None]:
    """Temporarily attach safe execution identifiers to nested log records."""
    context = {**trace_context.get()}
    context.update(
        {name: str(value) for name, value in values.items() if name in _TRACE_FIELDS and value}
    )
    token = trace_context.set(context)
    try:
        yield
    finally:
        trace_context.reset(token)


class JsonFormatter(logging.Formatter):
    """Emit redacted, allowlisted structured log records without a logging dependency."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }
        if request_id := request_id_context.get():
            payload["request_id"] = request_id
        if route := route_context.get():
            payload["route"] = route
        context = {**trace_context.get()}
        context.update(
            {name: record.__dict__[name] for name in _RECORD_FIELDS if name in record.__dict__}
        )
        payload.update(redact(context))
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception_type"] = type(record.exc_info[1]).__name__
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure the root logger once for JSON-compatible application logs."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
