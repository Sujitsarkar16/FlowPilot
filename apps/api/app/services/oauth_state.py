"""Signed, expiring OAuth state backed by durable single-use nonces."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.oauth_states import OAuthStateRepository
from app.models.oauth_state import OAuthState


class OAuthStateError(Exception):
    """Raised when OAuth state cannot safely bind a callback to its starter."""


class OAuthStateService:
    def __init__(
        self, signing_key: str, session: AsyncSession, lifetime_seconds: int = 600
    ) -> None:
        self._signing_key = signing_key
        self._states = OAuthStateRepository(session)
        self._session = session
        self._lifetime_seconds = lifetime_seconds

    async def issue(self, user_id: UUID, provider: str) -> str:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._lifetime_seconds)
        nonce = token_urlsafe(24)
        await self._states.prune_expired(now)
        await self._states.add(
            OAuthState(
                user_id=user_id,
                provider=provider,
                nonce_hash=self._hash(nonce),
                expires_at=expires_at,
            )
        )
        await self._session.commit()
        return jwt.encode(
            {
                "sub": str(user_id),
                "provider": provider,
                "jti": nonce,
                "iat": now,
                "exp": expires_at,
                "iss": "pulseos-oauth",
            },
            self._signing_key,
            algorithm="HS256",
        )

    async def consume(self, state: str, provider: str) -> UUID:
        now = datetime.now(UTC)
        try:
            payload = jwt.decode(
                state,
                self._signing_key,
                algorithms=["HS256"],
                issuer="pulseos-oauth",
                options={"require": ["exp", "iat", "iss", "jti", "sub", "provider"]},
            )
        except InvalidTokenError as error:
            raise OAuthStateError("Invalid or expired OAuth state") from error
        subject = payload.get("sub")
        nonce = payload.get("jti")
        if (
            not isinstance(subject, str)
            or not isinstance(nonce, str)
            or payload.get("provider") != provider
        ):
            raise OAuthStateError("OAuth state does not match this connection")
        try:
            user_id = UUID(subject)
        except ValueError as error:
            raise OAuthStateError("Invalid OAuth state") from error
        consumed_user = await self._states.consume(self._hash(nonce), provider, now)
        await self._session.commit()
        if consumed_user is None or consumed_user != user_id:
            raise OAuthStateError("OAuth state has already been used or expired")
        return user_id

    @staticmethod
    def _hash(nonce: str) -> str:
        return sha256(nonce.encode()).hexdigest()
