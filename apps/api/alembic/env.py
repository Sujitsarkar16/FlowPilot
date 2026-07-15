"""Alembic environment for the asynchronous FlowPilot database."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool

import app.models  # noqa: F401 - imports all model metadata
from alembic import context
from app.core.config import get_settings
from app.db.base import Base

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without opening a database connection."""
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Use Alembic's async bridge for an asyncpg database URL."""
    from sqlalchemy.ext.asyncio import async_engine_from_config

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
