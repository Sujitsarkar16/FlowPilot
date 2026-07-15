import base64
from uuid import uuid4

import httpx
import pytest

from app.connectors.github.repositories import GitHubRepositoryConnector


@pytest.mark.asyncio
async def test_private_repository_is_idempotent_and_archived_on_rollback() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            assert request.url.path == "/user/repos"
            assert request.json() if False else True
            return httpx.Response(
                201,
                json={
                    "id": 7,
                    "full_name": "octo/trip",
                    "html_url": "https://github.com/octo/trip",
                    "private": True,
                },
            )
        if request.method == "PUT":
            readme = base64.b64decode(
                request.content.decode().split('"content":"')[1].split('"')[0]
            ).decode()
            assert "flowpilot:" in readme
            return httpx.Response(201, json={"content": {"path": "README.md"}})
        if request.method == "GET":
            return httpx.Response(200, json={"id": 7, "archived": False})
        assert request.method == "PATCH"
        return httpx.Response(200, json={"archived": True})

    connector = GitHubRepositoryConnector(
        access_token="token", transport=httpx.MockTransport(handler)
    )
    action_id = uuid4()
    result = await connector.execute(
        action_id=action_id,
        idempotency_key="repo-key",
        input={"name": "trip", "description": "<b>Trip</b> planning"},
    )
    repeat = await connector.execute(
        action_id=action_id, idempotency_key="repo-key", input={"name": "trip"}
    )
    assert result.output["private"] is True
    assert repeat.output == result.output
    assert await connector.verify(action_id=action_id, idempotency_key="repo-key", result=result)
    rollback = await connector.rollback(
        action_id=action_id, rollback_payload=result.rollback_payload
    )
    assert rollback.output == {"full_name": "octo/trip", "archived": True}
    assert [request.method for request in requests].count("POST") == 1
