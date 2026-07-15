"""Google Calendar adapter with marker-backed idempotency and safe compensation."""

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta
from inspect import isawaitable
from typing import Any, TypeAlias
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.connectors.base import Connector, ConnectorExecutionError
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)

AccessTokenResolver: TypeAlias = Callable[[], str | Awaitable[str]]
_MARKER_KEY = "pulseos_idempotency_key"


class GoogleCalendarConnector(Connector):
    """Calendar adapter whose token resolver is bound to one provider connection."""

    name = "google"
    endpoint = "https://www.googleapis.com/calendar/v3/calendars"

    def __init__(
        self,
        *,
        access_token_resolver: AccessTokenResolver,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if transport is not None and client is not None:
            raise ValueError("pass either transport or client, not both")
        self._access_token_resolver = access_token_resolver
        self._transport = transport
        self._client = client

    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        del action_id
        title = _required_text(input, "calendar_title")
        timezone = _timezone(input)
        start = _datetime(input, "start_at", timezone)
        if start is None:
            raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, "start_at is required")
        end = _datetime(input, "end_at", timezone, required=False)
        if end is None:
            end = start + timedelta(hours=1)
        if end <= start:
            raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, "end_at must follow start_at")
        calendar_id = _optional_text(input, "calendar_id") or "primary"
        existing = await self._find_marked_event(calendar_id, idempotency_key)
        if existing:
            return _result(existing, calendar_id, idempotency_key, created=False)
        response = await self._request(
            "POST",
            self._events_url(calendar_id),
            json={
                "summary": title,
                "start": {"dateTime": start.isoformat(), "timeZone": timezone},
                "end": {"dateTime": end.isoformat(), "timeZone": timezone},
                "extendedProperties": {"private": {_MARKER_KEY: idempotency_key}},
            },
        )
        _raise_for_status(response, "create calendar event")
        event_id = _identifier(_json_object(response), "id", "create calendar event")
        return _result(event_id, calendar_id, idempotency_key, created=True)

    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        del action_id
        event_id, calendar_id = _result_identity(result)
        if event_id is None:
            return False
        response = await self._request("GET", self._event_url(calendar_id, event_id))
        if response.status_code == 404:
            return False
        _raise_for_status(response, "verify calendar event")
        return _marker_matches(_json_object(response), idempotency_key)

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        del action_id
        event_id, calendar_id, marker = _rollback_identity(rollback_payload)
        if event_id is None or marker is None:
            return ConnectorRollbackResult(output={"rolled_back": False, "reason": "missing_marker"})
        response = await self._request("GET", self._event_url(calendar_id, event_id))
        if response.status_code == 404:
            return ConnectorRollbackResult(output={"rolled_back": True, "already_absent": True})
        _raise_for_status(response, "read calendar event for rollback")
        if not _marker_matches(_json_object(response), marker):
            return ConnectorRollbackResult(output={"rolled_back": False, "reason": "marker_mismatch"})
        response = await self._request("DELETE", self._event_url(calendar_id, event_id))
        if response.status_code != 404:
            _raise_for_status(response, "delete calendar event")
        return ConnectorRollbackResult(output={"rolled_back": True, "event_id": event_id})

    async def _find_marked_event(self, calendar_id: str, marker: str) -> str | None:
        response = await self._request(
            "GET",
            self._events_url(calendar_id),
            params={"privateExtendedProperty": f"{_MARKER_KEY}={marker}", "maxResults": "1"},
        )
        _raise_for_status(response, "find calendar event")
        items = _json_object(response).get("items")
        if not isinstance(items, list):
            raise ConnectorExecutionError(ConnectorErrorCategory.PERMANENT, "invalid Calendar response")
        for item in items:
            if isinstance(item, Mapping) and _marker_matches(item, marker):
                return _identifier(item, "id", "find calendar event")
        return None

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        token = await self._access_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            if self._client is not None:
                return await self._client.request(method, url, headers=headers, **kwargs)
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                return await client.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException:
            raise ConnectorExecutionError(ConnectorErrorCategory.RETRYABLE, "Google Calendar timed out") from None
        except httpx.HTTPError:
            raise ConnectorExecutionError(ConnectorErrorCategory.RETRYABLE, "Google Calendar request failed") from None

    async def _access_token(self) -> str:
        try:
            token = self._access_token_resolver()
            if isawaitable(token):
                token = await token
        except Exception:
            raise ConnectorExecutionError(ConnectorErrorCategory.AUTHORIZATION, "Google access token unavailable") from None
        if not isinstance(token, str) or not token.strip():
            raise ConnectorExecutionError(ConnectorErrorCategory.AUTHORIZATION, "Google access token unavailable")
        return token

    def _events_url(self, calendar_id: str) -> str:
        return f"{self.endpoint}/{quote(calendar_id, safe='')}/events"

    def _event_url(self, calendar_id: str, event_id: str) -> str:
        return f"{self._events_url(calendar_id)}/{quote(event_id, safe='')}"


def _result(event_id: str, calendar_id: str, marker: str, *, created: bool) -> ConnectorExecutionResult:
    return ConnectorExecutionResult(
        output={"event_id": event_id, "calendar_id": calendar_id, "created": created},
        rollback_payload={"event_id": event_id, "calendar_id": calendar_id, "idempotency_key": marker},
    )


def _result_identity(result: ConnectorExecutionResult) -> tuple[str | None, str]:
    event_id = result.output.get("event_id")
    calendar_id = result.output.get("calendar_id", "primary")
    return (event_id if isinstance(event_id, str) and event_id else None, calendar_id if isinstance(calendar_id, str) and calendar_id else "primary")


def _rollback_identity(payload: Mapping[str, Any] | None) -> tuple[str | None, str, str | None]:
    if payload is None:
        return None, "primary", None
    event_id = payload.get("event_id")
    calendar_id = payload.get("calendar_id", "primary")
    marker = payload.get("idempotency_key")
    return (
        event_id if isinstance(event_id, str) and event_id else None,
        calendar_id if isinstance(calendar_id, str) and calendar_id else "primary",
        marker if isinstance(marker, str) and marker else None,
    )


def _marker_matches(event: Mapping[str, Any], marker: str) -> bool:
    properties = event.get("extendedProperties")
    private = properties.get("private") if isinstance(properties, Mapping) else None
    return isinstance(private, Mapping) and private.get(_MARKER_KEY) == marker


def _timezone(input: Mapping[str, Any]) -> str:
    value = input.get("timezone", input.get("time_zone", "UTC"))
    if not isinstance(value, str) or not value:
        raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, "timezone must be an IANA timezone")
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        # Windows deployments may not ship the IANA database; Google resolves valid regional names.
        if value != "UTC" and not value.startswith(_IANA_REGIONS):
            raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, "timezone must be an IANA timezone") from None
    return value


_IANA_REGIONS = (
    "Africa/", "America/", "Antarctica/", "Arctic/", "Asia/", "Atlantic/", "Australia/",
    "Europe/", "Indian/", "Pacific/", "Etc/",
)


def _datetime(input: Mapping[str, Any], key: str, timezone: str, *, required: bool = True) -> datetime | None:
    value = input.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value:
        raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, f"{key} must be an ISO-8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, f"{key} must be an ISO-8601 datetime") from None
    if parsed.tzinfo is not None:
        return parsed
    try:
        return parsed.replace(tzinfo=ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        return parsed


def _required_text(input: Mapping[str, Any], key: str) -> str:
    value = _optional_text(input, key)
    if value is None:
        raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, f"{key} is required")
    return value


def _optional_text(input: Mapping[str, Any], key: str) -> str | None:
    value = input.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, f"{key} must be a non-empty string")
    return value.strip()


def _json_object(response: httpx.Response) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        raise ConnectorExecutionError(ConnectorErrorCategory.PERMANENT, "Google Calendar returned invalid JSON") from None
    if not isinstance(payload, Mapping):
        raise ConnectorExecutionError(ConnectorErrorCategory.PERMANENT, "Google Calendar returned invalid JSON")
    return payload


def _identifier(payload: Mapping[str, Any], key: str, operation: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ConnectorExecutionError(ConnectorErrorCategory.PERMANENT, f"Google Calendar could not {operation}")
    return value


def _raise_for_status(response: httpx.Response, operation: str) -> None:
    if response.is_success:
        return
    if response.status_code in {401, 403}:
        category = ConnectorErrorCategory.AUTHORIZATION
    elif response.status_code in {408, 429} or response.status_code >= 500:
        category = ConnectorErrorCategory.RETRYABLE
    else:
        category = ConnectorErrorCategory.PERMANENT
    raise ConnectorExecutionError(category, f"Google Calendar could not {operation}")


GoogleCalendarClient = GoogleCalendarConnector
