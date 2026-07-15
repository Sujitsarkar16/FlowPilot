"""Google Drive folder adapter with marker-backed idempotency and safe compensation."""

import json
from collections.abc import Awaitable, Callable, Mapping
from inspect import isawaitable
from typing import Any, TypeAlias
from urllib.parse import quote
from uuid import UUID

import httpx

from app.connectors.base import Connector, ConnectorExecutionError
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)

AccessTokenResolver: TypeAlias = Callable[[], str | Awaitable[str]]
_MARKER_KEY = "pulseos_idempotency_key"
_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class GoogleDriveConnector(Connector):
    """Drive adapter whose token resolver is bound to one provider connection."""

    name = "google"
    endpoint = "https://www.googleapis.com/drive/v3/files"

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
        folder_id = _existing_folder_id(input)
        owns_folder = folder_id is None
        created = False
        if folder_id is None:
            folder_name = _required_text(input, "folder_name")
            folder_id = await self._find_marked_folder(idempotency_key)
            created = folder_id is None
            if folder_id is None:
                body: dict[str, Any] = {
                    "name": folder_name,
                    "mimeType": _FOLDER_MIME_TYPE,
                    "appProperties": {_MARKER_KEY: idempotency_key},
                }
                parent_id = _parent_id(input)
                if parent_id:
                    body["parents"] = [parent_id]
                response = await self._request(
                    "POST", self.endpoint, params={"fields": _fields()}, json=body
                )
                _raise_for_status(response, "create Drive folder")
                folder_id = _identifier(_json_object(response), "id", "create Drive folder")
        file_name = _optional_text(input, "file_name")
        if file_name is None:
            return _result(folder_id, idempotency_key, created=created, owns_folder=owns_folder)
        content = _required_text(input, "content")
        file_marker = f"{idempotency_key}:file"
        file_id = await self._find_marked_file(file_marker, folder_id)
        if file_id is None:
            file_id = await self._upload_file(folder_id, file_name, content, file_marker, input)
        return _result(
            folder_id,
            idempotency_key,
            created=created,
            owns_folder=owns_folder,
            file_id=file_id,
            file_name=file_name,
            file_marker=file_marker,
        )

    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        del action_id
        folder_id = result.output.get("folder_id")
        if not isinstance(folder_id, str) or not folder_id:
            return False
        response = await self._request(
            "GET", self._file_url(folder_id), params={"fields": _fields()}
        )
        if response.status_code == 404:
            return False
        _raise_for_status(response, "verify Drive folder")
        owns_folder = (result.rollback_payload or {}).get("owns_folder") is not False
        if owns_folder and not _is_marked_folder(_json_object(response), idempotency_key):
            return False
        file_id = result.output.get("file_id")
        if not isinstance(file_id, str) or not file_id:
            return True
        response = await self._request("GET", self._file_url(file_id), params={"fields": _fields()})
        if response.status_code == 404:
            return False
        _raise_for_status(response, "verify Drive file")
        marker = result.rollback_payload.get("file_marker") if result.rollback_payload else None
        return isinstance(marker, str) and _is_marked_file(_json_object(response), marker)

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        del action_id
        folder_id, marker, file_id, file_marker, owns_folder = _rollback_identity(rollback_payload)
        if folder_id is None or marker is None:
            return ConnectorRollbackResult(
                output={"rolled_back": False, "reason": "missing_marker"}
            )
        if file_id and file_marker:
            response = await self._request(
                "GET", self._file_url(file_id), params={"fields": _fields()}
            )
            if response.status_code != 404:
                _raise_for_status(response, "read Drive file for rollback")
                if _is_marked_file(_json_object(response), file_marker):
                    response = await self._request(
                        "PATCH", self._file_url(file_id), json={"trashed": True}
                    )
                    _raise_for_status(response, "trash Drive file")
        if not owns_folder:
            return ConnectorRollbackResult(
                output={
                    "rolled_back": bool(file_id),
                    "folder_id": folder_id,
                    "trashed_file": bool(file_id),
                }
            )
        response = await self._request(
            "GET", self._file_url(folder_id), params={"fields": _fields()}
        )
        if response.status_code == 404:
            return ConnectorRollbackResult(output={"rolled_back": True, "already_absent": True})
        _raise_for_status(response, "read Drive folder for rollback")
        if not _is_marked_folder(_json_object(response), marker):
            return ConnectorRollbackResult(
                output={"rolled_back": False, "reason": "marker_mismatch"}
            )
        children = await self._children(folder_id)
        if children:
            return ConnectorRollbackResult(
                output={"rolled_back": False, "reason": "folder_not_empty"}
            )
        response = await self._request("PATCH", self._file_url(folder_id), json={"trashed": True})
        _raise_for_status(response, "trash Drive folder")
        return ConnectorRollbackResult(
            output={"rolled_back": True, "folder_id": folder_id, "trashed": True}
        )

    async def _find_marked_folder(self, marker: str) -> str | None:
        escaped = marker.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"appProperties has {{ key='{_MARKER_KEY}' and value='{escaped}' }} "
            f"and mimeType='{_FOLDER_MIME_TYPE}' and trashed = false"
        )
        response = await self._request(
            "GET",
            self.endpoint,
            params={"q": query, "fields": f"files({_fields()})", "pageSize": "1"},
        )
        _raise_for_status(response, "find Drive folder")
        files = _json_object(response).get("files")
        if not isinstance(files, list):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.PERMANENT, "invalid Drive response"
            )
        for file in files:
            if isinstance(file, Mapping) and _is_marked_folder(file, marker):
                return _identifier(file, "id", "find Drive folder")
        return None

    async def _find_marked_file(self, marker: str, folder_id: str) -> str | None:
        query = (
            f"appProperties has {{ key='{_MARKER_KEY}' and value='{_escape(marker)}' }} "
            f"and '{_escape(folder_id)}' in parents and trashed = false"
        )
        response = await self._request(
            "GET",
            self.endpoint,
            params={"q": query, "fields": f"files({_fields()})", "pageSize": "1"},
        )
        _raise_for_status(response, "find Drive file")
        files = _json_object(response).get("files")
        if not isinstance(files, list):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.PERMANENT, "invalid Drive response"
            )
        for file in files:
            if isinstance(file, Mapping) and _is_marked_file(file, marker):
                return _identifier(file, "id", "find Drive file")
        return None

    async def _upload_file(
        self,
        folder_id: str,
        file_name: str,
        content: str,
        marker: str,
        input: Mapping[str, Any],
    ) -> str:
        mime_type = _optional_text(input, "mime_type") or "text/markdown"
        metadata = {
            "name": file_name,
            "parents": [folder_id],
            "mimeType": mime_type,
            "appProperties": {_MARKER_KEY: marker},
        }
        response = await self._request(
            "POST",
            "https://www.googleapis.com/upload/drive/v3/files",
            params={"uploadType": "multipart", "fields": _fields()},
            files={
                "metadata": ("metadata.json", json.dumps(metadata), "application/json"),
                "file": (file_name, content.encode(), mime_type),
            },
        )
        _raise_for_status(response, "upload Drive file")
        return _identifier(_json_object(response), "id", "upload Drive file")

    async def _children(self, folder_id: str) -> list[object]:
        response = await self._request(
            "GET",
            self.endpoint,
            params={
                "q": f"'{_escape(folder_id)}' in parents and trashed = false",
                "fields": "files(id)",
                "pageSize": "1",
            },
        )
        _raise_for_status(response, "inspect Drive folder")
        children = _json_object(response).get("files")
        if not isinstance(children, list):
            raise ConnectorExecutionError(
                ConnectorErrorCategory.PERMANENT, "invalid Drive response"
            )
        return children

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        token = await self._access_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            if self._client is not None:
                return await self._client.request(method, url, headers=headers, **kwargs)
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                return await client.request(method, url, headers=headers, **kwargs)
        except httpx.TimeoutException:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.RETRYABLE, "Google Drive timed out"
            ) from None
        except httpx.HTTPError:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.RETRYABLE, "Google Drive request failed"
            ) from None

    async def _access_token(self) -> str:
        try:
            token = self._access_token_resolver()
            if isawaitable(token):
                token = await token
        except Exception:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Google access token unavailable"
            ) from None
        if not isinstance(token, str) or not token.strip():
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "Google access token unavailable"
            )
        return token

    def _file_url(self, folder_id: str) -> str:
        return f"{self.endpoint}/{quote(folder_id, safe='')}"


def _result(
    folder_id: str,
    marker: str,
    *,
    created: bool,
    owns_folder: bool,
    file_id: str | None = None,
    file_name: str | None = None,
    file_marker: str | None = None,
) -> ConnectorExecutionResult:
    output: dict[str, Any] = {"folder_id": folder_id, "created": created}
    rollback: dict[str, Any] = {
        "folder_id": folder_id,
        "idempotency_key": marker,
        "owns_folder": owns_folder,
    }
    if file_id and file_name and file_marker:
        output.update({"file_id": file_id, "file_name": file_name})
        rollback.update({"file_id": file_id, "file_marker": file_marker})
    return ConnectorExecutionResult(output=output, rollback_payload=rollback)


def _rollback_identity(
    payload: Mapping[str, Any] | None,
) -> tuple[str | None, str | None, str | None, str | None, bool]:
    if payload is None:
        return None, None, None, None, True
    folder_id = payload.get("folder_id")
    marker = payload.get("idempotency_key")
    file_id = payload.get("file_id")
    file_marker = payload.get("file_marker")
    return (
        folder_id if isinstance(folder_id, str) and folder_id else None,
        marker if isinstance(marker, str) and marker else None,
        file_id if isinstance(file_id, str) and file_id else None,
        file_marker if isinstance(file_marker, str) and file_marker else None,
        payload.get("owns_folder") is not False,
    )


def _is_marked_folder(file: Mapping[str, Any], marker: str) -> bool:
    properties = file.get("appProperties")
    return (
        file.get("mimeType") == _FOLDER_MIME_TYPE
        and file.get("trashed") is not True
        and isinstance(properties, Mapping)
        and properties.get(_MARKER_KEY) == marker
    )


def _is_marked_file(file: Mapping[str, Any], marker: str) -> bool:
    properties = file.get("appProperties")
    return (
        file.get("trashed") is not True
        and isinstance(properties, Mapping)
        and properties.get(_MARKER_KEY) == marker
    )


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _required_text(input: Mapping[str, Any], key: str) -> str:
    value = input.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, f"{key} is required")
    return value.strip()


def _optional_text(input: Mapping[str, Any], key: str) -> str | None:
    value = input.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConnectorExecutionError(
            ConnectorErrorCategory.VALIDATION, f"{key} must be a non-empty string"
        )
    return value.strip()


def _existing_folder_id(input: Mapping[str, Any]) -> str | None:
    value = input.get("folder_id")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConnectorExecutionError(
            ConnectorErrorCategory.VALIDATION, "folder_id must be a string"
        )
    return value.strip()


def _parent_id(input: Mapping[str, Any]) -> str | None:
    value = input.get("parent_folder_id", input.get("parent_id"))
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConnectorExecutionError(
            ConnectorErrorCategory.VALIDATION, "parent_folder_id must be a string"
        )
    return value.strip()


def _fields() -> str:
    return "id,name,mimeType,appProperties,trashed"


def _json_object(response: httpx.Response) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        raise ConnectorExecutionError(
            ConnectorErrorCategory.PERMANENT, "Google Drive returned invalid JSON"
        ) from None
    if not isinstance(payload, Mapping):
        raise ConnectorExecutionError(
            ConnectorErrorCategory.PERMANENT, "Google Drive returned invalid JSON"
        )
    return payload


def _identifier(payload: Mapping[str, Any], key: str, operation: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ConnectorExecutionError(
            ConnectorErrorCategory.PERMANENT, f"Google Drive could not {operation}"
        )
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
    raise ConnectorExecutionError(category, f"Google Drive could not {operation}")


GoogleDriveClient = GoogleDriveConnector
