import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import StringIO

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import get_current_user
from app.api.routes.events import router
from app.core.logging import JsonFormatter
from app.db.session import get_session
from app.models.enums import EventSource, Importance, LifeEventType
from app.models.event import EventEntity, LifeEvent, RawEvent
from app.models.user import User
from app.services.audit import AuditService


@pytest.mark.asyncio
async def test_sensitive_values_are_redacted_from_audits_logs_and_api_responses(session) -> None:
    values = {"token": "oauth-secret", "pnr": "PNR-123", "account": "ACCT-456", "webhook": "hook-secret"}
    user = User(auth_subject="redaction-user")
    session.add(user)
    await session.flush()
    entry = await AuditService(session).append(
        user_id=user.id,
        event_name="redaction_checked",
        actor_type="system",
        payload={"oauth": {"access_token": values["token"]}, "pnr": values["pnr"], "account_reference": values["account"], "nested": {"webhook_secret": values["webhook"]}},
    )
    raw = RawEvent(user_id=user.id, source=EventSource.MANUAL, event_type="manual", fingerprint="redaction", payload={}, received_at=datetime.now(UTC))
    event = LifeEvent(user_id=user.id, raw_event=raw, type=LifeEventType.TRAVEL_BOOKED, confidence=1, importance=Importance.HIGH, summary="Private trip", occurred_at=datetime.now(UTC))
    event.entities.append(EventEntity(kind="pnr", value={"code": values["pnr"]}, is_sensitive=True))
    session.add_all([raw, event])
    await session.commit()

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("test.redaction")
    old_handlers, old_level, old_propagate = logger.handlers, logger.level, logger.propagate
    logger.handlers, logger.level, logger.propagate = [handler], logging.INFO, False
    try:
        logger.info("webhook processed", extra={"oauth_token": values["token"], "webhook_secret": values["webhook"]})
    finally:
        logger.handlers, logger.level, logger.propagate = old_handlers, old_level, old_propagate

    async def override_session() -> AsyncIterator[object]:
        yield session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/events")

    leaked = json.dumps(entry.payload) + stream.getvalue() + response.text
    assert all(value not in leaked for value in values.values())
    assert response.json()["items"][0]["entities"][0]["value"] == {"redacted": True}
    # No SSE endpoint exists yet; this request-level projection is the available streaming boundary.
