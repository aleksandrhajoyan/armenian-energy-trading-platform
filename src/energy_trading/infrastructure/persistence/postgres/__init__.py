"""Async PostgreSQL/TimescaleDB persistence foundation.

This package exposes factories only. It does not create a global engine or
connect on import. Future composition roots own engine lifecycle.
"""

from energy_trading.infrastructure.persistence.postgres.engine import (
    build_postgres_url,
    create_postgres_engine,
    create_session_factory,
)

__all__ = [
    "build_postgres_url",
    "create_postgres_engine",
    "create_session_factory",
]
