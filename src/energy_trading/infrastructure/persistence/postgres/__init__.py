"""Async PostgreSQL/TimescaleDB persistence.

This package exposes engine/session factories and the Consumption repository.
It does not create a global engine or connect on import. Future composition
roots own engine lifecycle and wiring.
"""

from energy_trading.infrastructure.persistence.postgres.consumption_repository import (
    PostgresConsumptionRepository,
)
from energy_trading.infrastructure.persistence.postgres.engine import (
    build_postgres_url,
    create_postgres_engine,
    create_session_factory,
)

__all__ = [
    "PostgresConsumptionRepository",
    "build_postgres_url",
    "create_postgres_engine",
    "create_session_factory",
]
