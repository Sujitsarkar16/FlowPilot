"""GitHub OAuth authorization, token exchange, and identity lookup."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings

GITHUB_SCOPES = ("repo",)


class GitHubOAuthError(Exception):
    """A provider failure that is safe to expose as a generic connection error."""


@dataclass(frozen=True)
class GitHubIdentity:
    account_id: str
    login: str


class GitHubOAuthClient:
    authorize_endpoint = "https://github.com/login/oauth/authorize"
    token_endpoint = "https://github.com/login/oauth/access_token"
    identity_endpoint = "https://api.github.com/user"

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._transport = transport

    def authorization_url(self, state: str) -> str:
        if not self._settings.github_client_id:
            raise GitHubOAuthError("GitHub OAuth is not configured")
        query = urlencode(
            {
                "client_id": self._settings.github_client_id,
                "redirect_uri": str(self._settings.github_redirect_uri),
                "scope": " ".join(GITHUB_SCOPES),
                "state": state,
            }
        )
        return f"{self.authorize_endpoint}?{query}"

    async def exchange_code(self, code: str) -> str:
        secret = self._settings.github_client_secret
        if not secret:
            raise GitHubOAuthError("GitHub OAuth is not configured")
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "code": code,
                        "client_id": self._settings.github_client_id,
                        "client_secret": secret.get_secret_value(),
                        "redirect_uri": str(self._settings.github_redirect_uri),
                    },
                    headers={"Accept": "application/json"},
                )
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise GitHubOAuthError("GitHub token exchange failed") from None
        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        if not response.is_success or not isinstance(access_token, str) or not access_token:
            raise GitHubOAuthError("GitHub token exchange failed")
        return access_token

    async def identity(self, access_token: str) -> GitHubIdentity:
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.get(
                    self.identity_endpoint,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError):
            raise GitHubOAuthError("GitHub identity lookup failed") from None
        account_id = payload.get("id") if isinstance(payload, dict) else None
        login = payload.get("login") if isinstance(payload, dict) else None
        if not response.is_success or account_id is None or not isinstance(login, str) or not login:
            raise GitHubOAuthError("GitHub identity lookup failed")
        return GitHubIdentity(account_id=str(account_id), login=login)
