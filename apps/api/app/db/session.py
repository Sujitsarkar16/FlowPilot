"""Async SQLAlchemy engine and request-session dependency."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Build an async engine with bounded pooling for application traffic."""
    options: dict[str, object] = {"pool_pre_ping": True}
    if not settings.database_url.startswith("sqlite"):
        options.update(
            pool_size=settings.database_pool_size, max_overflow=settings.database_max_overflow
        )
    return create_async_engine(settings.database_url, **options)


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the shared application engine."""
    return create_engine(get_settings())


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return sessions that do not auto-commit service work."""
    return async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session and roll back uncommitted work on failure."""
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Release database connections during application shutdown."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
        get_engine.cache_clear()
        get_session_factory.cache_clear()
