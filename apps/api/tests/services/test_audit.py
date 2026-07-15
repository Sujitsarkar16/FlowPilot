from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import ActionStatus
from app.services.audit import AuditService
from app.services.audit_redaction import redact
from tests.execution_helpers import action_state


def test_redaction_masks_nested_connector_and_financial_data() -> None:
    assert redact({"token": "secret", "nested": {"pnr": "ABC123", "safe": "value"}}) == {
        "token": "[redacted]",
        "nested": {"pnr": "[redacted]", "safe": "value"},
    }


@pytest.mark.asyncio
async def test_audit_entries_are_redacted_append_only_and_cursor_paginated(session) -> None:
    user, plan, action = await action_state(session, status=ActionStatus.COMPLETED)
    ledger = AuditService(session)
    for index, event_name in enumerate(("action_started", "action_completed", "action_verified")):
        entry = await ledger.append(
            user_id=user.id,
            life_event_id=plan.source_event_id,
            plan_id=plan.id,
            action_id=action.id,
            event_name=event_name,
            actor_type="system",
            payload={"account_reference": "bank-secret", "at": datetime.now(UTC).isoformat()},
        )
        entry.created_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
    await session.commit()

    first = await ledger.timeline(user.id, plan.source_event_id, cursor=None, limit=2)
    second = await ledger.timeline(user.id, plan.source_event_id, cursor=first.next_cursor, limit=2)

    assert len(first.items) == 2
    assert first.items[0].payload["account_reference"] == "[redacted]"
    assert len(second.items) == 1
