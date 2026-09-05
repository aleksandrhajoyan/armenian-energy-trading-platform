"""Live Alembic/TimescaleDB structure tests.

These tests assume the Compose ``postgres`` profile is healthy and that
``uv run alembic upgrade head`` has already been applied for the suite,
except the isolated downgrade/upgrade test which restores head in ``finally``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.persistence.postgres._support import postgres_integration_enabled

pytestmark = [
    pytest.mark.postgres_integration,
    pytest.mark.skipif(
        not postgres_integration_enabled(),
        reason="ENERGY_RUN_POSTGRES_INTEGRATION=1 is required",
    ),
]

REPO_ROOT = Path(__file__).resolve().parents[4]
HEAD_REVISION = "0002_consumption"
BOOTSTRAP_REVISION = "0001_bootstrap"
SCHEMA = "energy_trading"
TABLE = "consumption_observations"


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "alembic", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


async def _scalar(engine: AsyncEngine, statement: str) -> object:
    async with engine.connect() as connection:
        return await connection.scalar(text(statement))


async def _all(engine: AsyncEngine, statement: str) -> list[str]:
    async with engine.connect() as connection:
        result = await connection.execute(text(statement))
        return [str(row[0]) for row in result]


async def test_database_is_at_alembic_head(postgres_engine: AsyncEngine) -> None:
    current = await _scalar(postgres_engine, "SELECT version_num FROM alembic_version")
    assert current == HEAD_REVISION


async def test_runtime_postgres_and_timescaledb_versions(postgres_engine: AsyncEngine) -> None:
    server_version = await _scalar(postgres_engine, "SHOW server_version")
    assert isinstance(server_version, str)
    assert server_version.split(".")[0] == "17"
    timescale_version = await _scalar(
        postgres_engine,
        "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'",
    )
    assert timescale_version == "2.29.2"


async def test_consumption_hypertable_structure(postgres_engine: AsyncEngine) -> None:
    extension = await _scalar(
        postgres_engine,
        "SELECT extname FROM pg_extension WHERE extname = 'timescaledb'",
    )
    assert extension == "timescaledb"
    schema = await _scalar(
        postgres_engine,
        f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{SCHEMA}'",
    )
    assert schema == SCHEMA
    table = await _scalar(
        postgres_engine,
        "SELECT table_name FROM information_schema.tables "
        f"WHERE table_schema = '{SCHEMA}' AND table_name = '{TABLE}'",
    )
    assert table == TABLE
    hypertable = await _scalar(
        postgres_engine,
        "SELECT hypertable_name FROM timescaledb_information.hypertables "
        f"WHERE hypertable_schema = '{SCHEMA}' AND hypertable_name = '{TABLE}'",
    )
    assert hypertable == TABLE
    partition_column = await _scalar(
        postgres_engine,
        "SELECT column_name FROM timescaledb_information.dimensions "
        f"WHERE hypertable_schema = '{SCHEMA}' AND hypertable_name = '{TABLE}' "
        "ORDER BY dimension_number LIMIT 1",
    )
    assert partition_column == "timestamp"
    primary_key = await _all(
        postgres_engine,
        "SELECT kcu.column_name FROM information_schema.table_constraints AS tc "
        "JOIN information_schema.key_column_usage AS kcu "
        "ON tc.constraint_name = kcu.constraint_name "
        "AND tc.table_schema = kcu.table_schema "
        "WHERE tc.constraint_type = 'PRIMARY KEY' "
        f"AND tc.table_schema = '{SCHEMA}' AND tc.table_name = '{TABLE}' "
        "ORDER BY kcu.ordinal_position",
    )
    assert primary_key == ["consumer_id", "timestamp"]
    constraint = await _scalar(
        postgres_engine,
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conname = 'ck_consumption_observations_value_mw_finite_non_negative'",
    )
    assert isinstance(constraint, str)
    lowered = constraint.lower()
    assert "value_mw" in lowered
    assert ">=" in constraint
    assert "infinity" in lowered


async def test_downgrade_to_bootstrap_then_restore_head(postgres_engine: AsyncEngine) -> None:
    """Temporarily drop the Consumption table, then restore Alembic head.

    This is the only live test that removes ``consumption_observations``.
    It must not drop the ``energy_trading`` schema or the TimescaleDB extension.
    """

    try:
        current = await _scalar(postgres_engine, "SELECT version_num FROM alembic_version")
        assert current == HEAD_REVISION
        _run_alembic("downgrade", BOOTSTRAP_REVISION)
        current = await _scalar(postgres_engine, "SELECT version_num FROM alembic_version")
        assert current == BOOTSTRAP_REVISION
        table = await _scalar(
            postgres_engine,
            "SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema = '{SCHEMA}' AND table_name = '{TABLE}'",
        )
        assert table is None
        schema = await _scalar(
            postgres_engine,
            f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{SCHEMA}'",
        )
        assert schema == SCHEMA
        extension = await _scalar(
            postgres_engine,
            "SELECT extname FROM pg_extension WHERE extname = 'timescaledb'",
        )
        assert extension == "timescaledb"
    finally:
        _run_alembic("upgrade", "head")

    current = await _scalar(postgres_engine, "SELECT version_num FROM alembic_version")
    assert current == HEAD_REVISION
    hypertable = await _scalar(
        postgres_engine,
        "SELECT hypertable_name FROM timescaledb_information.hypertables "
        f"WHERE hypertable_schema = '{SCHEMA}' AND hypertable_name = '{TABLE}'",
    )
    assert hypertable == TABLE
