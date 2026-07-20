"""Supabase-authenticated FastAPI dependencies."""

import asyncio
from collections.abc import Mapping
from functools import lru_cache
from time import monotonic
from typing import Any, cast

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimitExceeded, rate_limit_bucket
from app.db.repositories.users import UserRepository
from app.db.session import get_session
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
_ALLOWED_ALGORITHMS = {"RS256", "ES256", "EdDSA"}
_JWKS_CACHE_SECONDS = 600


class TokenVerificationError(Exception):
    """Raised when a bearer token cannot be trusted."""


class TokenVerificationUnavailable(Exception):
    """Raised when the configured signing keys cannot be obtained."""


class SupabaseTokenVerifier:
    """Validate Supabase JWTs against the project's rotating public JWKS."""

    def __init__(self, settings: Settings) -> None:
        if settings.supabase_url is None:
            raise TokenVerificationUnavailable("Supabase Auth is not configured")
        origin = str(settings.supabase_url).rstrip("/")
        self.issuer = f"{origin}/auth/v1"
        self.audience = settings.supabase_jwt_audience
        self.jwks_url = str(settings.supabase_jwks_url or f"{self.issuer}/.well-known/jwks.json")
        self._keys: dict[str, Any] = {}
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def verify(self, token: str) -> dict[str, object]:
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            key_id = header.get("kid")
            if algorithm not in _ALLOWED_ALGORITHMS or not isinstance(key_id, str):
                raise TokenVerificationError("Unsupported token")
            key = await self._get_key(key_id)
            if key.algorithm_name != algorithm:
                raise TokenVerificationError("Signing algorithm mismatch")
            claims = jwt.decode(
                token,
                key=key.key,
                algorithms=[algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["aud", "exp", "iss", "sub"]},
            )
        except TokenVerificationError:
            raise
        except jwt.PyJWTError as error:
            raise TokenVerificationError("Invalid token") from error
        if not isinstance(claims, dict):
            raise TokenVerificationError("Invalid token claims")
        return cast(dict[str, object], claims)

    async def _get_key(self, key_id: str) -> Any:
        if monotonic() >= self._expires_at:
            await self._refresh_keys()
        key = self._keys.get(key_id)
        if key is None:
            raise TokenVerificationError("Unknown signing key")
        return key

    async def _refresh_keys(self) -> None:
        async with self._lock:
            if monotonic() < self._expires_at:
                return
            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                    response = await client.get(self.jwks_url)
                    response.raise_for_status()
                payload = cast(dict[str, Any], response.json())
                keys = jwt.PyJWKSet.from_dict(payload).keys
            except (httpx.HTTPError, jwt.PyJWTError, ValueError, TypeError) as error:
                raise TokenVerificationUnavailable("Supabase signing keys are unavailable") from error
            self._keys = {key.key_id: key for key in keys if key.key_id}
            if not self._keys:
                raise TokenVerificationUnavailable("Supabase has no asymmetric signing keys")
            self._expires_at = monotonic() + _JWKS_CACHE_SECONDS


@lru_cache
def get_token_verifier() -> SupabaseTokenVerifier:
    return SupabaseTokenVerifier(get_settings())


async def get_verified_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, object]:
    """Return claims only after signature and standard-token validation."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await get_token_verifier().verify(credentials.credentials)
    except TokenVerificationUnavailable as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except TokenVerificationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None


def _claim_string(claims: Mapping[str, object], name: str, max_length: int) -> str | None:
    value = claims.get(name)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value and len(value) <= max_length else None


def _display_name(claims: Mapping[str, object]) -> str | None:
    metadata = claims.get("user_metadata")
    if not isinstance(metadata, Mapping):
        return None
    for field in ("full_name", "name"):
        value = metadata.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()[:120]
    return None


async def get_current_user(
    request: Request,
    claims: dict[str, object] = Depends(get_verified_claims),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Map a verified Supabase subject to its distinct local application user."""
    subject = _claim_string(claims, "sub", 255)
    email = _claim_string(claims, "email", 320)
    if subject is None or email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    bucket = rate_limit_bucket(request.url.path)
    if bucket:
        try:
            await request.app.state.rate_limiter.check(bucket, f"user:{subject}")
        except RateLimitExceeded as error:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error.detail,
                headers={"Retry-After": str(error.retry_after_seconds)},
            ) from None

    users = UserRepository(session)
    user = await users.get_by_subject(subject)
    name = _display_name(claims)
    if user is None:
        user = User(auth_subject=subject, email=email, display_name=name)
        try:
            await users.add(user)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already associated with another account",
            ) from None
        await session.refresh(user)
        return user

    changed = user.email != email or (name is not None and user.display_name != name)
    user.email = email
    if name is not None:
        user.display_name = name
    if changed:
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already associated with another account",
            ) from None
        await session.refresh(user)
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the locally assigned administrator role for privileged routes."""
    if current_user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return current_user
