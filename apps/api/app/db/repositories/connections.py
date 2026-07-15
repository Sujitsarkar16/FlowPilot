"""Explicit user-scoped connection queries."""

from collections.abc import Sequence
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.models.enums import ConnectionProvider, ConnectionStatus


class ConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID, connection_id: UUID) -> Connection | None:
        return cast(
            Connection | None,
            await self.session.scalar(
                select(Connection).where(
                    Connection.id == connection_id, Connection.user_id == user_id
                )
            ),
        )

    async def list(self, user_id: UUID) -> list[Connection]:
        return list(
            await self.session.scalars(select(Connection).where(Connection.user_id == user_id))
        )

    async def get_provider_account(
        self, user_id: UUID, provider: ConnectionProvider, account_id: str
    ) -> Connection | None:
        return cast(
            Connection | None,
            await self.session.scalar(
                select(Connection).where(
                    Connection.user_id == user_id,
                    Connection.provider == provider,
                    Connection.provider_account_id == account_id,
                )
            ),
        )

    async def list_connected(self, user_id: UUID) -> Sequence[Connection]:
        """Return only usable external connections for policy evaluation."""
        statement = select(Connection).where(
            Connection.user_id == user_id, Connection.status == ConnectionStatus.CONNECTED
        )
        return list(await self.session.scalars(statement))
