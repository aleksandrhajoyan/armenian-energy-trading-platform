"""Alembic environment for PostgreSQL/TimescaleDB migrations.

Does not construct a FastAPI application or import application agents.
A connection is opened only when a migration command executes this file.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from energy_trading.infrastructure.persistence.postgres import build_postgres_url
from energy_trading.shared.config.database import load_database_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = None


def _create_migration_engine() -> AsyncEngine:
    settings = load_database_settings()
    return create_async_engine(
        build_postgres_url(settings),
        echo=False,
        pool_pre_ping=True,
        poolclass=pool.NullPool,
    )


def run_migrations_offline() -> None:
    """Emit SQL without a live connection."""

    settings = load_database_settings()
    url = build_postgres_url(settings)
    context.configure(
        url=url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = _create_migration_engine()
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
