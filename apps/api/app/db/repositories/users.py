"""Explicit queries for users."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_subject(self, subject: str) -> User | None:
        return cast(
            User | None, await self.session.scalar(select(User).where(User.auth_subject == subject))
        )

    async def get_by_email(self, email: str) -> User | None:
        return cast(User | None, await self.session.scalar(select(User).where(User.email == email)))

    async def get_by_google_subject(self, subject: str) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(select(User).where(User.google_subject == subject)),
        )

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
