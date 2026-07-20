import base64
from datetime import UTC, datetime

import pytest

from app.connectors.google.gmail import GmailClient, GmailPage
from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.schemas.connector import ConnectorExecutionResult
from app.schemas.gmail import GmailMessage
from app.services.connection_secrets import ConnectionSecrets
from app.services.runtime_connectors import RuntimeConnector
from app.services.travel_ticket import TravelTicketService
from tests.execution_helpers import action_state


@pytest.mark.asyncio
async def test_runtime_internal_connector_generates_all_travel_documents(session) -> None:
    _, _, action = await action_state(session)
    action.action_type = "travel.generate_documents"
    action.connector = "internal"
    await session.commit()

    connector = RuntimeConnector("internal", session, Settings())
    result = await connector.execute(
        action_id=action.id, idempotency_key=action.idempotency_key, input=action.input
    )

    assert {item["document_type"] for item in result.output["documents"]} == {
        "itinerary",
        "packing_checklist",
    }
    assert await connector.verify(
        action_id=action.id, idempotency_key=action.idempotency_key, result=result
    )


@pytest.mark.asyncio
async def test_runtime_ticket_action_uses_bounded_gmail_resolver(session, monkeypatch) -> None:
    _, plan, action = await action_state(session)
    event_id = plan.source_event_id
    action.action_type = "travel.save_ticket"
    action.connector = "google"
    await session.commit()
    called: list[str] = []

    async def fetch(_self, _current_action, event):
        called.append(str(event.id))
        return ConnectorExecutionResult(output={"found": False, "reason": "no_verified_match"})

    monkeypatch.setattr(TravelTicketService, "fetch", fetch)
    key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    connector = RuntimeConnector("google", session, Settings(_env_file=None, encryption_key=key))
    result = await connector.execute(
        action_id=action.id, idempotency_key=action.idempotency_key, input=action.input
    )

    assert called == [str(event_id)]
    assert await connector.verify(
        action_id=action.id, idempotency_key=action.idempotency_key, result=result
    )


@pytest.mark.asyncio
async def test_subscription_action_runs_a_bounded_gmail_search(session, monkeypatch) -> None:
    user, _, action = await action_state(session)
    action.action_type = "subscription.check_renewal"
    action.connector = "google"
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")
    connection = Connection(
        user_id=user.id,
        provider=ConnectionProvider.GOOGLE,
        provider_account_id="subscriptions",
        status=ConnectionStatus.CONNECTED,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    ConnectionSecrets(SecretCipher(key)).save(connection, "access", "refresh")
    session.add(connection)
    await session.commit()
    searches: list[tuple[str | None, int]] = []

    async def list_messages(_self, _token, *, query=None, max_results=100, **_kwargs):
        searches.append((query, max_results))
        return GmailPage(("active", "cancelled"), None)

    async def get_message(_self, _token, message_id):
        return GmailMessage(
            message_id=message_id,
            sender="StreamCo <billing@stream.example>",
            subject=(
                "Your StreamCo subscription renews soon"
                if message_id == "active"
                else "Your StreamCo subscription was cancelled"
            ),
            received_at=datetime(2026, 7, 20, tzinfo=UTC),
        )

    monkeypatch.setattr(GmailClient, "list_messages", list_messages)
    monkeypatch.setattr(GmailClient, "get_message", get_message)
    connector = RuntimeConnector("google", session, Settings(_env_file=None, encryption_key=key))

    result = await connector.execute(
        action_id=action.id, idempotency_key=action.idempotency_key, input=action.input
    )

    assert len(searches) == 1
    assert searches[0][1] == 50
    assert searches[0][0] is not None and searches[0][0].startswith("newer_than:1y")
    assert result.output["count"] == 1
    assert result.output["subscriptions"] == [
        {
            "service": "StreamCo",
            "subject": "Your StreamCo subscription renews soon",
            "received_at": "2026-07-20T00:00:00+00:00",
        }
    ]
    assert await connector.verify(
        action_id=action.id, idempotency_key=action.idempotency_key, result=result
    )
