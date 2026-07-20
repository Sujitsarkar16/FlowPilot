import base64

import httpx
import pytest
from sqlalchemy import select

from app.connectors.google.gmail import GmailClient
from app.core.crypto import SecretCipher
from app.models.connection import Connection
from app.models.enums import (
    CompilationStatus,
    ConnectionProvider,
    ConnectionStatus,
    LifeEventType,
)
from app.models.event import LifeEvent, RawEvent
from app.models.plan import Plan
from app.models.standing_order import StandingOrder
from app.models.user import User
from app.services.ai.fake_provider import FakeAIProvider
from app.services.connection_secrets import ConnectionSecrets
from app.services.gmail_sync import GmailSyncError, GmailSyncService


def encrypted_secrets() -> ConnectionSecrets:
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")
    return ConnectionSecrets(SecretCipher(key))


def gmail_message(message_id: str) -> dict[str, object]:
    return {
        "id": message_id,
        "historyId": "11",
        "internalDate": "1735689600000",
        "payload": {
            "headers": [
                {"name": "From", "value": "Travel <travel@example.com>"},
                {"name": "Subject", "value": "Flight confirmation"},
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": "VHJpcCBjb25maXJtZWQ"}}],
        },
    }


def travel_ai() -> FakeAIProvider:
    def responder(_system: str, _user: str, schema: type) -> dict[str, object]:
        if schema.__name__ == "Classification":
            return {
                "type": "travel_booked",
                "confidence": 0.97,
                "importance": "high",
                "summary": "Flight confirmation to Lisbon",
                "reason": "airline booking email",
            }
        return {
            "entities": [
                {"kind": "destination", "value": {"name": "Lisbon"}},
                {"kind": "ticket", "value": {"name": "booking.pdf"}},
            ]
        }

    return FakeAIProvider(responder)


def travel_rule() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "trigger_event_types": ["travel_booked"],
        "entity_conditions": [],
        "action_templates": [
            {
                "action_type": "travel.get_weather",
                "connector": "weather",
                "input": {},
                "risk_level": "green",
                "approval_mode": "automatic",
            },
            {
                "action_type": "travel.notify_family",
                "connector": "telegram",
                "input": {},
                "risk_level": "yellow",
                "approval_mode": "approval_required",
            },
        ],
        "explanation": "Prepare booked travel.",
    }


async def gmail_connection(session: object) -> tuple[Connection, ConnectionSecrets]:
    secrets = encrypted_secrets()
    user = User(auth_subject="gmail-sync-user")
    connection = Connection(user=user, provider=ConnectionProvider.GOOGLE, provider_account_id="gmail")
    secrets.save(connection, access_token="access", refresh_token="refresh")
    session.add_all([user, connection])  # type: ignore[attr-defined]
    await session.commit()  # type: ignore[attr-defined]
    return connection, secrets


def mock_gmail_handler() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "10"})
        if path.endswith("/history"):
            return httpx.Response(
                200,
                json={
                    "history": [{"messagesAdded": [{"message": {"id": "m-1"}}]}],
                    "historyId": "11",
                },
            )
        if path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m-1"}]})
        return httpx.Response(200, json=gmail_message("m-1"))

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_sync_is_idempotent_and_only_advances_after_success(session: object) -> None:
    connection, secrets = await gmail_connection(session)
    service = GmailSyncService(
        session, GmailClient(transport=mock_gmail_handler()), secrets, ai_provider=travel_ai()
    )  # type: ignore[arg-type]
    first = await service.sync_connection(connection)
    second = await service.sync_connection(connection)

    assert (first.ingested, first.duplicates, first.cursor) == (1, 0, "10")
    assert (second.ingested, second.duplicates, second.cursor) == (0, 1, "11")
    assert len(list(await session.scalars(select(RawEvent)))) == 1  # type: ignore[attr-defined]
    assert len(list(await session.scalars(select(LifeEvent)))) == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_sync_classifies_and_plans_travel_email_with_standing_order(
    session: object,
) -> None:
    connection, secrets = await gmail_connection(session)
    session.add_all(  # type: ignore[attr-defined]
        [
            StandingOrder(
                user_id=connection.user_id,
                instruction="Whenever I book travel, prepare my trip.",
                compiled_rule=travel_rule(),
                enabled=True,
                compilation_status=CompilationStatus.COMPILED,
            ),
            Connection(
                user_id=connection.user_id,
                provider=ConnectionProvider.TELEGRAM,
                provider_account_id="family-bot",
                status=ConnectionStatus.CONNECTED,
                scopes=["bot.send_messages"],
            ),
        ]
    )
    await session.commit()  # type: ignore[attr-defined]

    service = GmailSyncService(
        session, GmailClient(transport=mock_gmail_handler()), secrets, ai_provider=travel_ai()
    )  # type: ignore[arg-type]
    result = await service.sync_connection(connection)

    assert (result.ingested, result.interpreted, result.planned) == (1, 1, 1)
    life = (await session.scalars(select(LifeEvent))).one()  # type: ignore[attr-defined]
    plan = (await session.scalars(select(Plan))).one()  # type: ignore[attr-defined]
    assert life.type is LifeEventType.TRAVEL_BOOKED
    assert plan.source_event_id == life.id
    assert {action.action_type for action in plan.actions} == {
        "travel.get_weather",
        "travel.notify_family",
    }
    notify = next(action for action in plan.actions if action.action_type == "travel.notify_family")
    assert notify.requires_approval is True
    assert notify.policy_reason == "action_requires_approval"


@pytest.mark.asyncio
async def test_sync_does_not_advance_cursor_when_ingestion_fails(session: object) -> None:
    connection, secrets = await gmail_connection(session)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"historyId": "10"})
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "broken"}]})
        return httpx.Response(500, json={"error": {"message": "provider failure"}})

    service = GmailSyncService(session, GmailClient(transport=httpx.MockTransport(handler)), secrets)  # type: ignore[arg-type]
    with pytest.raises(GmailSyncError):
        await service.sync_connection(connection)

    await session.refresh(connection)  # type: ignore[attr-defined]
    assert "gmail_history_id" not in connection.token_metadata
