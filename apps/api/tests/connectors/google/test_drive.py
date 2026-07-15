import json
from uuid import uuid4

import httpx
import pytest

from app.connectors.base import ConnectorExecutionError
from app.connectors.google.drive import GoogleDriveConnector
from app.schemas.connector import ConnectorErrorCategory, ConnectorExecutionResult


@pytest.mark.asyncio
async def test_drive_folder_creation_is_marker_idempotent() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            if len([item for item in requests if item.method == "GET"]) == 1:
                return httpx.Response(200, json={"files": []})
            return httpx.Response(
                200,
                json={
                    "files": [
                        {
                            "id": "folder-1",
                            "mimeType": "application/vnd.google-apps.folder",
                            "appProperties": {"flowpilot_idempotency_key": "key-1"},
                            "trashed": False,
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"id": "folder-1"})

    connector = GoogleDriveConnector(
        access_token_resolver=lambda: "resolved-token", transport=httpx.MockTransport(handler)
    )
    first = await connector.execute(
        action_id=uuid4(),
        idempotency_key="key-1",
        input={"folder_name": "Trip", "parent_folder_id": "parent"},
    )
    second = await connector.execute(
        action_id=uuid4(), idempotency_key="key-1", input={"folder_name": "Trip"}
    )

    assert first.output == {"folder_id": "folder-1", "created": True}
    assert second.output["created"] is False
    post = next(request for request in requests if request.method == "POST")
    assert post.headers["Authorization"] == "Bearer resolved-token"
    body = json.loads(post.content)
    assert body["appProperties"] == {"flowpilot_idempotency_key": "key-1"}
    assert body["parents"] == ["parent"]
    assert (
        "appProperties has"
        in next(request for request in requests if request.method == "GET").url.params["q"]
    )
    assert len([request for request in requests if request.method == "POST"]) == 1


@pytest.mark.asyncio
async def test_drive_verify_and_rollback_only_trashes_owned_folder() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "GET" and request.url.params.get("q"):
            return httpx.Response(200, json={"files": []})
        if request.method == "PATCH":
            return httpx.Response(200, json={"id": "folder-1", "trashed": True})
        return httpx.Response(
            200,
            json={
                "id": "folder-1",
                "mimeType": "application/vnd.google-apps.folder",
                "appProperties": {"flowpilot_idempotency_key": "key-1"},
                "trashed": False,
            },
        )

    connector = GoogleDriveConnector(
        access_token_resolver=lambda: "token", transport=httpx.MockTransport(handler)
    )
    result = ConnectorExecutionResult(
        output={"folder_id": "folder-1"},
        rollback_payload={"folder_id": "folder-1", "idempotency_key": "key-1"},
    )
    assert await connector.verify(action_id=uuid4(), idempotency_key="key-1", result=result)
    assert (
        await connector.rollback(action_id=uuid4(), rollback_payload=result.rollback_payload)
    ).output["trashed"]
    assert calls == ["GET", "GET", "GET", "PATCH"]

    mismatch = GoogleDriveConnector(
        access_token_resolver=lambda: "token",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "mimeType": "application/vnd.google-apps.folder",
                    "appProperties": {"flowpilot_idempotency_key": "other"},
                    "trashed": False,
                },
            )
        ),
    )
    safe = await mismatch.rollback(action_id=uuid4(), rollback_payload=result.rollback_payload)
    assert safe.output == {"rolled_back": False, "reason": "marker_mismatch"}


@pytest.mark.asyncio
async def test_drive_validates_inputs_and_classifies_provider_failures() -> None:
    connector = GoogleDriveConnector(access_token_resolver=lambda: "token")
    with pytest.raises(ConnectorExecutionError) as invalid_name:
        await connector.execute(
            action_id=uuid4(), idempotency_key="key-1", input={"folder_name": ""}
        )
    assert invalid_name.value.category is ConnectorErrorCategory.VALIDATION

    for status, category in (
        (401, ConnectorErrorCategory.AUTHORIZATION),
        (503, ConnectorErrorCategory.RETRYABLE),
    ):
        failing = GoogleDriveConnector(
            access_token_resolver=lambda: "token",
            transport=httpx.MockTransport(lambda _: httpx.Response(status, json={"error": {}})),
        )
        with pytest.raises(ConnectorExecutionError) as error:
            await failing.execute(
                action_id=uuid4(), idempotency_key="key-1", input={"folder_name": "Trip"}
            )
        assert error.value.category is category


@pytest.mark.asyncio
async def test_drive_upload_verifies_file_and_preserves_a_nonempty_folder() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and "appProperties has" in request.url.params.get("q", ""):
            return httpx.Response(200, json={"files": []})
        if request.method == "GET" and "in parents" in request.url.params.get("q", ""):
            return httpx.Response(200, json={"files": [{"id": "user-file"}]})
        if request.method == "POST" and "upload" not in request.url.path:
            return httpx.Response(200, json={"id": "folder-1"})
        if request.method == "POST":
            return httpx.Response(200, json={"id": "file-1"})
        if request.method == "PATCH":
            return httpx.Response(200, json={"trashed": True})
        marker = "key-1:file" if request.url.path.endswith("file-1") else "key-1"
        return httpx.Response(
            200,
            json={
                "id": request.url.path.rsplit("/", 1)[-1],
                "mimeType": "application/vnd.google-apps.folder"
                if request.url.path.endswith("folder-1")
                else "text/markdown",
                "appProperties": {"flowpilot_idempotency_key": marker},
                "trashed": False,
            },
        )

    connector = GoogleDriveConnector(
        access_token_resolver=lambda: "token", transport=httpx.MockTransport(handler)
    )
    result = await connector.execute(
        action_id=uuid4(),
        idempotency_key="key-1",
        input={"folder_name": "Trip", "file_name": "itinerary.md", "content": "# Trip"},
    )

    assert result.output["file_id"] == "file-1"
    assert result.output["file_name"] == "itinerary.md"
    assert await connector.verify(action_id=uuid4(), idempotency_key="key-1", result=result)
    rollback = await connector.rollback(action_id=uuid4(), rollback_payload=result.rollback_payload)
    assert rollback.output == {"rolled_back": False, "reason": "folder_not_empty"}
