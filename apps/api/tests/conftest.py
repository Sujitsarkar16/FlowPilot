import os
from collections.abc import AsyncIterator, Callable

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Application settings accept Supabase URLs only. Database-focused tests inject their own
# in-memory SQLite session below, so this URL is never contacted by the test suite.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@db.example.supabase.co:5432/postgres",
)

import app.models  # noqa: F401
from app.connectors.base import MockConnector
from app.db.base import Base
from app.services.ai.fake_provider import FakeAIProvider
from app.services.connector_registry import ConnectorRegistry


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with factory() as database_session:
            yield database_session
        await transaction.rollback()
    await engine.dispose()


@pytest.fixture
def fake_ai() -> Callable[[Callable[[str, str, type], dict[str, object]]], FakeAIProvider]:
    return FakeAIProvider


@pytest.fixture
def fake_connectors() -> ConnectorRegistry:
    return ConnectorRegistry(
        tuple(
            MockConnector(name)
            for name in ("github", "internal", "mock_bank", "telegram", "weather")
        )
    )
