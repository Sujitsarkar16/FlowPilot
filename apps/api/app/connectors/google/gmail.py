"""Small Gmail API reader with bounded MIME parsing and injectable HTTP transport."""

import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.gmail import GmailMessage
from app.schemas.raw_sources import (
    MAX_ATTACHMENT_BYTES,
    MAX_ATTACHMENTS,
    MAX_CONTENT_CHARS,
    AttachmentMeta,
)

MAX_MIME_DEPTH = 12
MAX_MIME_PARTS = 100
MAX_ENCODED_BODY_BYTES = MAX_CONTENT_CHARS * 8
SAFE_HEADERS = frozenset({"from", "subject", "date"})
SUPPORTED_ATTACHMENT_MIME_TYPES = frozenset(
    {"application/pdf", "image/jpeg", "image/png", "text/csv", "text/plain"}
)


class GmailError(Exception):
    """Sanitized Gmail provider failure."""


class GmailAuthenticationError(GmailError):
    """Raised only when a bearer token can be refreshed and retried."""


class GmailCursorExpired(GmailError):
    """Raised when Gmail no longer retains the stored history cursor."""


@dataclass(frozen=True)
class GmailPage:
    message_ids: tuple[str, ...]
    next_page_token: str | None
    history_id: str | None = None


@dataclass(frozen=True)
class GmailAccessToken:
    access_token: str
    refresh_token: str | None = None


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.chunks.append(data)


class GmailClient:
    messages_endpoint = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    history_endpoint = "https://gmail.googleapis.com/gmail/v1/users/me/history"
    profile_endpoint = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
    token_endpoint = "https://oauth2.googleapis.com/token"

    def __init__(
        self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._transport = transport

    async def list_messages(
        self, access_token: str, *, page_token: str | None = None, query: str | None = None
    ) -> GmailPage:
        params: dict[str, str | int] = {"maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        if query:
            params["q"] = query
        payload = await self._request("GET", self.messages_endpoint, access_token, params=params)
        return GmailPage(self._message_ids(payload.get("messages")), self._token(payload))

    async def list_history(
        self, access_token: str, start_history_id: str, *, page_token: str | None = None
    ) -> GmailPage:
        params: dict[str, str | int] = {"startHistoryId": start_history_id, "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        try:
            payload = await self._request("GET", self.history_endpoint, access_token, params=params)
        except GmailError as error:
            if str(error) == "Gmail history cursor expired":
                raise GmailCursorExpired(str(error)) from None
            raise
        message_ids: list[str] = []
        histories = payload.get("history", [])
        if not isinstance(histories, list):
            raise GmailError("Gmail returned an invalid history response")
        for history in histories:
            if not isinstance(history, dict):
                continue
            added = history.get("messagesAdded", [])
            if not isinstance(added, list):
                continue
            for entry in added:
                message = entry.get("message") if isinstance(entry, dict) else None
                message_id = message.get("id") if isinstance(message, dict) else None
                if isinstance(message_id, str) and message_id:
                    message_ids.append(message_id)
        history_id = payload.get("historyId")
        return GmailPage(tuple(dict.fromkeys(message_ids)), self._token(payload), history_id if isinstance(history_id, str) else None)

    async def get_message(self, access_token: str, message_id: str) -> GmailMessage:
        payload = await self._request(
            "GET", f"{self.messages_endpoint}/{message_id}", access_token, params={"format": "full"}
        )
        return self._parse_message(payload)

    async def profile_history_id(self, access_token: str) -> str:
        payload = await self._request("GET", self.profile_endpoint, access_token)
        history_id = payload.get("historyId")
        if not isinstance(history_id, str) or not history_id:
            raise GmailError("Gmail returned an invalid profile")
        return history_id


    async def refresh_access_token(self, refresh_token: str) -> GmailAccessToken:
        settings = self._settings
        secret = settings.google_client_secret if settings else None
        if not settings or not settings.google_client_id or not secret:
            raise GmailError("Google OAuth is not configured")
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "client_id": settings.google_client_id,
                        "client_secret": secret.get_secret_value(),
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError):
            raise GmailError("Google token refresh failed") from None
        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        new_refresh_token = payload.get("refresh_token") if isinstance(payload, dict) else None
        if not response.is_success or not isinstance(access_token, str) or not access_token:
            raise GmailError("Google token refresh failed")
        return GmailAccessToken(
            access_token=access_token,
            refresh_token=new_refresh_token if isinstance(new_refresh_token, str) else None,
        )

    async def _request(
        self,
        method: str,
        url: str,
        access_token: str,
        *,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.request(
                    method, url, params=params, headers={"Authorization": f"Bearer {access_token}"}
                )
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError):
            raise GmailError("Gmail request failed") from None
        if response.status_code == 401:
            raise GmailAuthenticationError("Gmail access token was rejected")
        if response.status_code == 404 and url == self.history_endpoint:
            raise GmailError("Gmail history cursor expired")
        if not response.is_success or not isinstance(payload, dict):
            raise GmailError("Gmail request failed")
        return payload

    @staticmethod
    def _token(payload: dict[str, Any]) -> str | None:
        value = payload.get("nextPageToken")
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _message_ids(value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise GmailError("Gmail returned an invalid message list")
        return tuple(
            item["id"] for item in value if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]
        )


    def _parse_message(self, payload: dict[str, Any]) -> GmailMessage:
        message_id = payload.get("id")
        part = payload.get("payload")
        if not isinstance(message_id, str) or not message_id or not isinstance(part, dict):
            raise GmailError("Gmail returned an invalid message")
        headers = self._safe_headers(part.get("headers"))
        received_at = self._received_at(payload.get("internalDate"), headers.get("date"))
        text_parts: list[str] = []
        html_parts: list[str] = []
        attachments: list[AttachmentMeta] = []
        self._parse_part(part, text_parts, html_parts, attachments, depth=0, parts_seen=[0])
        body = "\n".join(text_parts or html_parts)[:MAX_CONTENT_CHARS]
        return GmailMessage(
            message_id=message_id,
            history_id=payload.get("historyId") if isinstance(payload.get("historyId"), str) else None,
            sender=headers.get("from", "")[:320],
            subject=headers.get("subject", "")[:1000],
            received_at=received_at,
            body=body,
            attachments=attachments,
            # Recipients, routing, and arbitrary provider headers are intentionally discarded.
            headers=headers,
        )

    @staticmethod
    def _safe_headers(value: object) -> dict[str, str]:
        if not isinstance(value, list):
            return {}
        headers: dict[str, str] = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            name, raw_value = item.get("name"), item.get("value")
            if not isinstance(name, str) or not isinstance(raw_value, str):
                continue
            normalized = name.casefold()
            if normalized in SAFE_HEADERS and normalized not in headers:
                headers[normalized] = GmailClient._decode_header(raw_value)
        return headers

    @staticmethod
    def _decode_header(value: str) -> str:
        try:
            return str(make_header(decode_header(value))).strip()
        except (UnicodeError, ValueError):
            return value.strip()

    @staticmethod
    def _received_at(internal_date: object, date_header: str | None) -> datetime:
        if isinstance(internal_date, str) and internal_date.isdigit():
            try:
                return datetime.fromtimestamp(int(internal_date) / 1000, UTC)
            except (OverflowError, OSError, ValueError):
                pass
        if date_header:
            try:
                value = parsedate_to_datetime(date_header)
                return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
            except (TypeError, ValueError, IndexError):
                pass
        raise GmailError("Gmail returned a message without a valid received time")


    def _parse_part(
        self,
        part: dict[str, Any],
        text_parts: list[str],
        html_parts: list[str],
        attachments: list[AttachmentMeta],
        *,
        depth: int,
        parts_seen: list[int],
    ) -> None:
        if depth > MAX_MIME_DEPTH or parts_seen[0] >= MAX_MIME_PARTS:
            return
        parts_seen[0] += 1
        filename = part.get("filename")
        body = part.get("body")
        raw_mime_type = part.get("mimeType")
        mime_type = raw_mime_type if isinstance(raw_mime_type, str) else "application/octet-stream"
        if isinstance(filename, str) and filename.strip():
            size = body.get("size") if isinstance(body, dict) else None
            if (
                isinstance(size, int)
                and 0 <= size <= MAX_ATTACHMENT_BYTES
                and mime_type.casefold() in SUPPORTED_ATTACHMENT_MIME_TYPES
                and len(attachments) < MAX_ATTACHMENTS
            ):
                attachments.append(
                    AttachmentMeta(name=filename.strip()[:255], mime_type=mime_type[:128], size_bytes=size)
                )
            return
        if isinstance(body, dict) and isinstance(body.get("data"), str):
            text = self._body_text(body["data"])
            if text:
                if mime_type.casefold() == "text/plain":
                    text_parts.append(text)
                elif mime_type.casefold() == "text/html":
                    html_parts.append(self._html_to_text(text))
        children = part.get("parts")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    self._parse_part(
                        child, text_parts, html_parts, attachments, depth=depth + 1, parts_seen=parts_seen
                    )

    @staticmethod
    def _body_text(value: str) -> str:
        if len(value) > MAX_ENCODED_BODY_BYTES:
            return ""
        try:
            padding = "=" * (-len(value) % 4)
            decoded = base64.b64decode((value + padding).encode("ascii"), altchars=b"-_", validate=True)
        except (ValueError, UnicodeEncodeError, binascii.Error):
            return ""
        return decoded.decode("utf-8", errors="replace")[:MAX_CONTENT_CHARS]

    @staticmethod
    def _html_to_text(value: str) -> str:
        parser = _HtmlTextExtractor()
        try:
            parser.feed(value)
            parser.close()
        except ValueError:
            return ""
        return " ".join(" ".join(parser.chunks).split())
