"""Verification of Auth0 access tokens using cached JWKS keys."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError

from app.core.config import Settings

JwksFetcher = Callable[[], Awaitable[dict[str, Any]]]
_ALLOWED_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
# Namespace for custom claims added via an Auth0 post-login Action (access tokens omit
# profile fields by default). Standard claims are still checked first as a fallback.
_CLAIM_NAMESPACE = "https://flowpilot.app/"


class AuthenticationError(Exception):
    """Raised when an access token cannot be trusted."""


@dataclass(frozen=True)
class AuthClaims:
    subject: str
    email: str | None
    display_name: str | None


class JWTVerifier:
    """Verify Auth0 JWTs without trusting any client-provided identity fields."""

    def __init__(
        self, settings: Settings, fetch_jwks: JwksFetcher | None = None, cache_seconds: int = 300
    ) -> None:
        if not settings.auth0_domain or not settings.auth0_audience:
            raise AuthenticationError("Authentication is unavailable")
        self.audience = settings.auth0_audience
        domain = settings.auth0_domain.removeprefix("https://").removeprefix("http://").strip("/")
        self.issuer = f"https://{domain}/"
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self._fetch_jwks = fetch_jwks or self._fetch_remote_jwks
        self._cache_seconds = cache_seconds
        self._keys: dict[str, jwt.PyJWK] = {}
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    async def verify(self, token: str) -> AuthClaims:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            key_id = header.get("kid")
            if algorithm not in _ALLOWED_ALGORITHMS or not isinstance(key_id, str):
                raise AuthenticationError("Invalid token")
            key = await self._get_key(key_id)
            payload = jwt.decode(
                token,
                key.key,
                algorithms=[key.algorithm_name],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
            subject = payload.get("sub")
            if not isinstance(subject, str) or not subject:
                raise AuthenticationError("Invalid token")
        except (AuthenticationError, InvalidTokenError, KeyError, TypeError, ValueError):
            raise AuthenticationError("Invalid or expired access token") from None
        email = payload.get("email") or payload.get(f"{_CLAIM_NAMESPACE}email")
        display_name = (
            payload.get("name")
            or payload.get("nickname")
            or payload.get(f"{_CLAIM_NAMESPACE}name")
        )
        return AuthClaims(
            subject=subject,
            email=email if isinstance(email, str) else None,
            display_name=display_name if isinstance(display_name, str) else None,
        )

    async def _get_key(self, key_id: str) -> jwt.PyJWK:
        await self._refresh_keys()
        if key := self._keys.get(key_id):
            return key
        await self._refresh_keys(force=True)
        if key := self._keys.get(key_id):
            return key
        raise AuthenticationError("Invalid token")

    async def _refresh_keys(self, force: bool = False) -> None:
        if not force and self._keys and monotonic() - self._loaded_at < self._cache_seconds:
            return
        async with self._lock:
            if not force and self._keys and monotonic() - self._loaded_at < self._cache_seconds:
                return
            payload = await self._fetch_jwks()
            keys = payload.get("keys")
            if not isinstance(keys, list):
                raise AuthenticationError("Authentication is unavailable")
            self._keys = {
                key["kid"]: jwt.PyJWK.from_dict(key)
                for key in keys
                if isinstance(key, dict) and isinstance(key.get("kid"), str)
            }
            if not self._keys:
                raise AuthenticationError("Authentication is unavailable")
            self._loaded_at = monotonic()

    async def _fetch_remote_jwks(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            raise AuthenticationError("Authentication is unavailable") from None
        if not isinstance(payload, dict):
            raise AuthenticationError("Authentication is unavailable")
        return payload
