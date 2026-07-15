"""Verification of Supabase access tokens using cached JWKS keys."""

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


class AuthenticationError(Exception):
    """Raised when an access token cannot be trusted."""


@dataclass(frozen=True)
class AuthClaims:
    subject: str
    email: str | None
    display_name: str | None


class JWTVerifier:
    """Verify Supabase JWTs without trusting any client-provided identity fields."""

    def __init__(
        self, settings: Settings, fetch_jwks: JwksFetcher | None = None, cache_seconds: int = 300
    ) -> None:
        self.audience = settings.supabase_jwt_audience or "authenticated"
        if not settings.supabase_url:
            raise AuthenticationError("Authentication is unavailable")
        base_url = str(settings.supabase_url).rstrip("/")
        self.issuer = str(settings.supabase_jwt_issuer or f"{base_url}/auth/v1")
        self.jwks_url = str(
            settings.supabase_jwks_url or f"{base_url}/auth/v1/.well-known/jwks.json"
        )
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
        metadata = payload.get("user_metadata")
        display_name = (
            metadata.get("full_name") or metadata.get("name")
            if isinstance(metadata, dict)
            else None
        )
        return AuthClaims(
            subject=subject,
            email=payload.get("email") if isinstance(payload.get("email"), str) else None,
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
