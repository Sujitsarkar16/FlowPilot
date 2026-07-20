import base64

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.connectors.google.gmail import GmailClient
from app.core.config import Settings
from app.core.crypto import SecretCipher
from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus
from app.models.event import EventEntity, LifeEvent
from app.models.event_attachment import EventAttachment
from app.services.connection_secrets import ConnectionSecrets
from app.services.travel_ticket import TravelTicketService
from tests.execution_helpers import action_state

_GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _encoded(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


@pytest.mark.asyncio
async def test_ticket_search_is_bounded_ranked_and_saved_to_owned_event(session) -> None:
    user, plan, action = await action_state(session)
    event = await session.scalar(
        select(LifeEvent)
        .options(selectinload(LifeEvent.entities))
        .where(LifeEvent.id == plan.source_event_id)
    )
    assert event is not None
    event.entities.extend(
        [
            EventEntity(kind="pnr", value={"code": "ABC123"}, is_sensitive=True),
            EventEntity(kind="destination", value={"name": "Lisbon"}),
        ]
    )
    action.action_type = "travel.save_ticket"
    action.connector = "google"
    key = base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("=")
    secrets = ConnectionSecrets(SecretCipher(key))
    connection = Connection(
        user_id=user.id,
        provider=ConnectionProvider.GOOGLE,
        provider_account_id="gmail-account",
        status=ConnectionStatus.CONNECTED,
        scopes=[_GMAIL_SCOPE],
    )
    secrets.save(connection, "access-token", "refresh-token")
    session.add(connection)
    await session.commit()
    pdf = b"%PDF-1.7\nverified ticket"
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/messages"):
            queries.append(request.url.params["q"])
            return httpx.Response(200, json={"messages": [{"id": "wrong"}, {"id": "right"}]})
        if request.url.path.endswith("/messages/wrong"):
            return httpx.Response(200, json=_message("wrong", "ZZ999 Rome", len(pdf)))
        if request.url.path.endswith("/messages/right"):
            return httpx.Response(200, json=_message("right", "ABC123 Lisbon", len(pdf)))
        if request.url.path.endswith("/attachments/pdf-1"):
            return httpx.Response(200, json={"data": _encoded(pdf)})
        raise AssertionError(f"unexpected Gmail request: {request.url}")

    settings = Settings(_env_file=None, encryption_key=key)
    result = await TravelTicketService(
        session,
        settings,
        gmail=GmailClient(settings, httpx.MockTransport(handler)),
        secrets=secrets,
    ).fetch(action, event)
    attachment = await session.scalar(
        select(EventAttachment).where(
            EventAttachment.user_id == user.id,
            EventAttachment.life_event_id == event.id,
        )
    )

    assert queries and all(query.startswith("newer_than:2m") for query in queries)
    assert all("ABC123" in query for query in queries)
    assert result.output["found"] is True
    assert attachment is not None
    assert attachment.filename == "ticket.pdf"
    assert attachment.content == pdf
    assert "ABC123" not in str(result.output)


def _message(message_id: str, body: str, pdf_size: int) -> dict[str, object]:
    return {
        "id": message_id,
        "internalDate": "1767225600000",
        "payload": {
            "headers": [
                {"name": "From", "value": "Airline <tickets@example.com>"},
                {"name": "Subject", "value": "Flight ticket confirmation"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _encoded(body.encode())}},
                {
                    "filename": "ticket.pdf",
                    "mimeType": "application/pdf",
                    "body": {"size": pdf_size, "attachmentId": "pdf-1"},
                },
            ],
        },
    }
