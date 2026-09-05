"""Async PostgreSQL engine and session factories.

Factories do not connect on import or construction. Lifecycle is owned by a
future composition root, not by this module.
"""

from __future__ import annotations

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from energy_trading.shared.config.database import DatabaseSettings


def build_postgres_url(settings: DatabaseSettings) -> URL:
    """Build a structured SQLAlchemy URL for the psycopg 3 driver.

    Credentials are stored on the URL object for connection use. Callers must
    not log ``render_as_string(hide_password=False)``.
    """

    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.username,
        password=settings.password.get_secret_value(),
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )


def create_postgres_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Return an async engine without opening a connection.

    Pool sizing follows ``DatabaseSettings``. SQL echo is disabled.
    """

    return create_async_engine(
        build_postgres_url(settings),
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout_seconds,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async session factory bound to ``engine``."""

    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
