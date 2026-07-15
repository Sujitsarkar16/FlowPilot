"""Safe, idempotent GitHub repository creation and archive rollback."""

import base64
import binascii
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.connectors.base import Connector, ConnectorExecutionError
from app.schemas.connector import (
    ConnectorErrorCategory,
    ConnectorExecutionResult,
    ConnectorRollbackResult,
)
from app.services.content_safety import sanitize_untrusted_content


class RepositoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
    description: str = Field(default="", max_length=350)
    private: bool = True
    owner: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")
    readme: str | None = Field(default=None, max_length=20_000)


@dataclass(frozen=True, slots=True)
class _Repository:
    identifier: str
    full_name: str
    url: str | None
    private: bool


class GitHubRepositoryConnector(Connector):
    """Create private repositories without exposing the OAuth token in results."""

    name = "github"
    _api_url = "https://api.github.com"

    def __init__(
        self, *, access_token: str | None, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._access_token = access_token
        self._transport = transport
        self._created: dict[str, _Repository] = {}
        self._results: dict[str, ConnectorExecutionResult] = {}

    async def execute(
        self, *, action_id: UUID, idempotency_key: str, input: Mapping[str, Any]
    ) -> ConnectorExecutionResult:
        if result := self._results.get(idempotency_key):
            return result
        request = self._input(input)
        repository = self._created.get(idempotency_key)
        created = False
        if repository is None:
            repository = await self._find_marked_repository(request, idempotency_key)
        if repository is None:
            repository = await self._create(request)
            created = True
        self._created[idempotency_key] = repository
        if created:
            await self._ensure_readme(repository, request, idempotency_key)
        result = self._result(repository)
        self._results[idempotency_key] = result
        return result

    async def verify(
        self, *, action_id: UUID, idempotency_key: str, result: ConnectorExecutionResult
    ) -> bool:
        full_name = result.output.get("full_name")
        repository_id = result.output.get("repository_id")
        if not isinstance(full_name, str) or not isinstance(repository_id, str):
            return False
        response = await self._request("GET", f"/repos/{full_name}")
        if response.status_code == 404:
            return False
        payload = self._payload(response)
        return response.is_success and str(payload.get("id")) == repository_id and not payload.get(
            "archived", False
        )

    async def rollback(
        self, *, action_id: UUID, rollback_payload: Mapping[str, Any] | None
    ) -> ConnectorRollbackResult:
        full_name = (rollback_payload or {}).get("full_name")
        if not isinstance(full_name, str) or not full_name:
            raise ConnectorExecutionError(ConnectorErrorCategory.VALIDATION, "Repository is required")
        response = await self._request("PATCH", f"/repos/{full_name}", json={"archived": True})
        payload = self._payload(response)
        if not response.is_success or payload.get("archived") is not True:
            self._raise_response(response, "GitHub repository archive failed")
        return ConnectorRollbackResult(output={"full_name": full_name, "archived": True})

    def _input(self, input: Mapping[str, Any]) -> RepositoryInput:
        try:
            return RepositoryInput.model_validate(dict(input))
        except ValidationError as error:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.VALIDATION, "Invalid GitHub repository input"
            ) from error

    async def _create(self, request: RepositoryInput) -> _Repository:
        description = sanitize_untrusted_content(request.description, max_chars=350).text
        endpoint = f"/orgs/{request.owner}/repos" if request.owner else "/user/repos"
        response = await self._request(
            "POST", endpoint, json={"name": request.name, "description": description, "private": request.private}
        )
        payload = self._payload(response)
        if not response.is_success:
            self._raise_response(response, "GitHub repository creation failed")
        repository_id = payload.get("id")
        full_name = payload.get("full_name")
        if repository_id is None or not isinstance(full_name, str) or not full_name:
            raise ConnectorExecutionError(ConnectorErrorCategory.RETRYABLE, "GitHub returned an invalid repository")
        return _Repository(
            identifier=str(repository_id),
            full_name=full_name,
            url=payload.get("html_url") if isinstance(payload.get("html_url"), str) else None,
            private=bool(payload.get("private", request.private)),
        )

    async def _ensure_readme(
        self, repository: _Repository, request: RepositoryInput, idempotency_key: str
    ) -> None:
        marker = hashlib.sha256(idempotency_key.encode()).hexdigest()
        body = request.readme or f"# {request.name}\n\n{request.description}".strip()
        content = sanitize_untrusted_content(body, max_chars=20_000).text
        encoded = base64.b64encode(f"{content}\n\n<!-- pulseos:{marker} -->\n".encode()).decode()
        response = await self._request(
            "PUT",
            f"/repos/{repository.full_name}/contents/README.md",
            json={"message": "Initialize repository with PulseOS README", "content": encoded},
        )
        if not response.is_success:
            self._raise_response(response, "GitHub README creation failed")

    async def _find_marked_repository(
        self, request: RepositoryInput, idempotency_key: str
    ) -> _Repository | None:
        """Find a prior durable execution before attempting a second create."""
        endpoint = f"/orgs/{request.owner}/repos" if request.owner else "/user/repos"
        response = await self._request("GET", endpoint)
        if not response.is_success:
            self._raise_response(response, "GitHub repository lookup failed")
        repositories = self._payload_list(response)
        marker = f"pulseos:{hashlib.sha256(idempotency_key.encode()).hexdigest()}"
        for repository in repositories:
            if repository.get("name") != request.name:
                continue
            full_name = repository.get("full_name")
            if not isinstance(full_name, str) or not full_name:
                continue
            readme = await self._request("GET", f"/repos/{full_name}/readme")
            if readme.status_code == 404:
                continue
            if not readme.is_success:
                self._raise_response(readme, "GitHub README lookup failed")
            content = self._payload(readme).get("content")
            if not isinstance(content, str):
                continue
            try:
                decoded = base64.b64decode(content).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError, ValueError):
                continue
            if marker in decoded:
                return _Repository(
                    identifier=str(repository.get("id")),
                    full_name=full_name,
                    url=repository.get("html_url")
                    if isinstance(repository.get("html_url"), str)
                    else None,
                    private=bool(repository.get("private", True)),
                )
        return None

    @staticmethod
    def _result(repository: _Repository) -> ConnectorExecutionResult:
        return ConnectorExecutionResult(
            output={
                "repository_id": repository.identifier,
                "full_name": repository.full_name,
                "url": repository.url,
                "private": repository.private,
                "archived": False,
            },
            rollback_payload={"full_name": repository.full_name},
        )


    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        if not self._access_token:
            raise ConnectorExecutionError(
                ConnectorErrorCategory.AUTHORIZATION, "GitHub access token is required"
            )
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                return await client.request(
                    method,
                    f"{self._api_url}{path}",
                    json=json,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {self._access_token}",
                    },
                )
        except httpx.HTTPError:
            raise ConnectorExecutionError(ConnectorErrorCategory.RETRYABLE, "GitHub request failed") from None

    @staticmethod
    def _payload(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _payload_list(response: httpx.Response) -> list[dict[str, Any]]:
        try:
            payload = response.json()
        except ValueError:
            return []
        return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []

    @staticmethod
    def _raise_response(response: httpx.Response, message: str) -> None:
        if response.status_code in (401, 403):
            category = ConnectorErrorCategory.AUTHORIZATION
        elif 400 <= response.status_code < 500:
            category = ConnectorErrorCategory.PERMANENT
        else:
            category = ConnectorErrorCategory.RETRYABLE
        raise ConnectorExecutionError(category, message)
