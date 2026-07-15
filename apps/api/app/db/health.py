"""Database health probes."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database(session: AsyncSession) -> bool:
    """Return whether the current connection can execute a trivial query."""
    result = await session.execute(text("SELECT 1"))
    return bool(result.scalar_one() == 1)
