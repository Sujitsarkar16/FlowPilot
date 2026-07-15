import json
from uuid import uuid4

import httpx
import pytest

from app.connectors.base import ConnectorExecutionError
from app.connectors.google.calendar import GoogleCalendarConnector
from app.schemas.connector import ConnectorErrorCategory, ConnectorExecutionResult


@pytest.mark.asyncio
async def test_calendar_creation_is_marker_idempotent_and_uses_resolved_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            if len([item for item in requests if item.method == "GET"]) == 1:
                return httpx.Response(200, json={"items": []})
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "event-1",
                            "extendedProperties": {
                                "private": {"flowpilot_idempotency_key": "key-1"}
                            },
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"id": "event-1"})

    async def token() -> str:
        return "resolved-token"

    connector = GoogleCalendarConnector(
        access_token_resolver=token, transport=httpx.MockTransport(handler)
    )
    payload = {
        "calendar_title": "Flight",
        "start_at": "2026-07-15T09:00:00",
        "timezone": "America/New_York",
    }
    first = await connector.execute(action_id=uuid4(), idempotency_key="key-1", input=payload)
    second = await connector.execute(action_id=uuid4(), idempotency_key="key-1", input=payload)

    assert first.output == {"event_id": "event-1", "calendar_id": "primary", "created": True}
    assert second.output["created"] is False
    post = next(request for request in requests if request.method == "POST")
    assert post.headers["Authorization"] == "Bearer resolved-token"
    body = json.loads(post.content)
    assert body["extendedProperties"]["private"] == {"flowpilot_idempotency_key": "key-1"}
    assert body["start"]["timeZone"] == "America/New_York"
    assert len([request for request in requests if request.method == "POST"]) == 1


@pytest.mark.asyncio
async def test_calendar_verify_and_rollback_only_touch_owned_event() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(
            200,
            json={
                "id": "event-1",
                "extendedProperties": {"private": {"flowpilot_idempotency_key": "key-1"}},
            },
        )

    connector = GoogleCalendarConnector(
        access_token_resolver=lambda: "token", transport=httpx.MockTransport(handler)
    )
    result = ConnectorExecutionResult(
        output={"event_id": "event-1", "calendar_id": "primary"},
        rollback_payload={
            "event_id": "event-1",
            "calendar_id": "primary",
            "idempotency_key": "key-1",
        },
    )
    assert await connector.verify(action_id=uuid4(), idempotency_key="key-1", result=result)
    assert (
        await connector.rollback(action_id=uuid4(), rollback_payload=result.rollback_payload)
    ).output["rolled_back"]
    assert calls == ["GET", "GET", "DELETE"]

    mismatch = GoogleCalendarConnector(
        access_token_resolver=lambda: "token",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"extendedProperties": {"private": {"flowpilot_idempotency_key": "other"}}},
            )
        ),
    )
    safe = await mismatch.rollback(action_id=uuid4(), rollback_payload=result.rollback_payload)
    assert safe.output == {"rolled_back": False, "reason": "marker_mismatch"}


@pytest.mark.asyncio
async def test_calendar_validates_timezones_and_classifies_provider_failures() -> None:
    connector = GoogleCalendarConnector(access_token_resolver=lambda: "token")
    with pytest.raises(ConnectorExecutionError) as invalid_timezone:
        await connector.execute(
            action_id=uuid4(),
            idempotency_key="key-1",
            input={
                "calendar_title": "Flight",
                "start_at": "2026-01-01T09:00:00",
                "timezone": "Not/AZone",
            },
        )
    assert invalid_timezone.value.category is ConnectorErrorCategory.VALIDATION

    for status, category in (
        (401, ConnectorErrorCategory.AUTHORIZATION),
        (503, ConnectorErrorCategory.RETRYABLE),
    ):
        failing = GoogleCalendarConnector(
            access_token_resolver=lambda: "token",
            transport=httpx.MockTransport(lambda _: httpx.Response(status, json={"error": {}})),
        )
        with pytest.raises(ConnectorExecutionError) as error:
            await failing.execute(
                action_id=uuid4(),
                idempotency_key="key-1",
                input={"calendar_title": "Flight", "start_at": "2026-01-01T09:00:00"},
            )
        assert error.value.category is category
