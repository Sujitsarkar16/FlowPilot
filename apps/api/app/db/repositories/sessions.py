"""Queries for revocable local browser sessions."""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user_session import UserSession


class UserSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, session: UserSession) -> UserSession:
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_active_by_token_hash(self, token_hash: str) -> UserSession | None:
        return cast(
            UserSession | None,
            await self.session.scalar(
                select(UserSession)
                .options(selectinload(UserSession.user))
                .where(
                    UserSession.token_hash == token_hash,
                    UserSession.expires_at > datetime.now(UTC),
                    UserSession.revoked_at.is_(None),
                )
            ),
        )

    async def revoke_by_token_hash(self, token_hash: str) -> None:
        record = await self.get_active_by_token_hash(token_hash)
        if record is not None:
            record.revoked_at = datetime.now(UTC)
