"""Durable one-time OAuth state queries."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_state import OAuthState


class OAuthStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, state: OAuthState) -> None:
        self.session.add(state)
        await self.session.flush()

    async def consume(self, nonce_hash: str, provider: str, now: datetime) -> UUID | None:
        statement = (
            update(OAuthState)
            .where(
                OAuthState.nonce_hash == nonce_hash,
                OAuthState.provider == provider,
                OAuthState.used_at.is_(None),
                OAuthState.expires_at > now,
            )
            .values(used_at=now)
            .returning(OAuthState.user_id)
        )
        return cast(UUID | None, await self.session.scalar(statement))

    async def prune_expired(self, now: datetime) -> None:
        await self.session.execute(delete(OAuthState).where(OAuthState.expires_at <= now))
