"""Google OAuth authorization, token exchange, and identity lookup."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings

GOOGLE_SCOPES = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.file",
)


class OAuthProviderError(Exception):
    """A provider failure that is safe to show as a generic connection error."""


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    scopes: list[str]


@dataclass(frozen=True)
class OAuthIdentity:
    account_id: str
    email: str | None


class GoogleOAuthClient:
    authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    identity_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._settings = settings
        self._transport = transport

    def authorization_url(self, state: str) -> str:
        if not self._settings.google_client_id:
            raise OAuthProviderError("Google OAuth is not configured")
        query = urlencode(
            {
                "client_id": self._settings.google_client_id,
                "redirect_uri": str(self._settings.google_redirect_uri),
                "response_type": "code",
                "scope": " ".join(GOOGLE_SCOPES),
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
            }
        )
        return f"{self.authorize_endpoint}?{query}"

    async def exchange_code(self, code: str) -> OAuthTokens:
        secret = self._settings.google_client_secret
        if not secret:
            raise OAuthProviderError("Google OAuth is not configured")
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "code": code,
                        "client_id": self._settings.google_client_id,
                        "client_secret": secret.get_secret_value(),
                        "redirect_uri": str(self._settings.google_redirect_uri),
                        "grant_type": "authorization_code",
                    },
                )
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise OAuthProviderError("Google token exchange failed") from None
        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        if not response.is_success or not isinstance(access_token, str) or not access_token:
            raise OAuthProviderError("Google token exchange failed")
        refresh_token = payload.get("refresh_token") if isinstance(payload, dict) else None
        scope_value = payload.get("scope") if isinstance(payload, dict) else None
        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token if isinstance(refresh_token, str) else None,
            scopes=scope_value.split() if isinstance(scope_value, str) else list(GOOGLE_SCOPES),
        )

    async def identity(self, access_token: str) -> OAuthIdentity:
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.get(
                    self.identity_endpoint, headers={"Authorization": f"Bearer {access_token}"}
                )
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError):
            raise OAuthProviderError("Google identity lookup failed") from None
        account_id = payload.get("id") if isinstance(payload, dict) else None
        email = payload.get("email") if isinstance(payload, dict) else None
        if not response.is_success or not isinstance(account_id, str) or not account_id:
            raise OAuthProviderError("Google identity lookup failed")
        return OAuthIdentity(account_id=account_id, email=email if isinstance(email, str) else None)

    async def refresh_access_token(self, refresh_token: str) -> str:
        """Exchange a refresh token for a fresh access token."""
        secret = self._settings.google_client_secret
        if not secret:
            raise OAuthProviderError("Google OAuth is not configured")
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self._transport) as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "client_id": self._settings.google_client_id,
                        "client_secret": secret.get_secret_value(),
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise OAuthProviderError("Google token refresh failed") from None
        access_token = payload.get("access_token") if isinstance(payload, dict) else None
        if not response.is_success or not isinstance(access_token, str) or not access_token:
            raise OAuthProviderError("Google token refresh failed")
        return access_token
