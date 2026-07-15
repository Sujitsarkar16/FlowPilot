import base64

import httpx
import pytest

from app.connectors.google.gmail import GmailClient
from app.core.config import Settings
from app.schemas.raw_sources import MAX_ATTACHMENT_BYTES


def encoded(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


@pytest.mark.asyncio
async def test_gmail_reader_parses_bounded_multipart_and_redacts_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer access-token"
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m-1"}]})
        return httpx.Response(
            200,
            json={
                "id": "m-1",
                "historyId": "123",
                "internalDate": "1735689600000",
                "payload": {
                    "mimeType": "multipart/mixed",
                    "headers": [
                        {"name": "From", "value": "Travel Desk <travel@example.com>"},
                        {"name": "Subject", "value": "=?utf-8?q?Flight_confirmation?="},
                        {"name": "To", "value": "private@example.com"},
                        {"name": "Bcc", "value": "secret@example.com"},
                        {"name": "Date", "value": "Wed, 01 Jan 2025 00:00:00 +0000"},
                    ],
                    "parts": [
                        {"mimeType": "text/html", "body": {"data": encoded("<b>Ignored fallback</b>")}},
                        {"mimeType": "text/plain", "body": {"data": encoded("Flight confirmed")}},
                        {"filename": "ticket.pdf", "mimeType": "application/pdf", "body": {"size": 12}},
                        {"filename": "large.zip", "body": {"size": MAX_ATTACHMENT_BYTES + 1}},
                    ],
                },
            },
        )

    client = GmailClient(transport=httpx.MockTransport(handler))
    page = await client.list_messages("access-token")
    message = await client.get_message("access-token", page.message_ids[0])

    assert message.body == "Flight confirmed"
    assert message.subject == "Flight confirmation"
    assert message.headers == {
        "from": "Travel Desk <travel@example.com>",
        "subject": "Flight confirmation",
        "date": "Wed, 01 Jan 2025 00:00:00 +0000",
    }
    assert [attachment.name for attachment in message.attachments] == ["ticket.pdf"]


@pytest.mark.asyncio
async def test_gmail_refreshes_access_token_with_injected_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://oauth2.googleapis.com/token")
        assert b"grant_type=refresh_token" in request.content
        return httpx.Response(200, json={"access_token": "fresh-access", "refresh_token": "fresh-refresh"})

    client = GmailClient(
        Settings(google_client_id="client", google_client_secret="secret"),
        transport=httpx.MockTransport(handler),
    )
    tokens = await client.refresh_access_token("old-refresh")

    assert tokens.access_token == "fresh-access"
    assert tokens.refresh_token == "fresh-refresh"
