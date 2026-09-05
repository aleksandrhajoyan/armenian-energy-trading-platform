"""SQLAlchemy Core metadata for Consumption observations."""

from __future__ import annotations

import ast

from sqlalchemy import CheckConstraint, DateTime, MetaData, PrimaryKeyConstraint, Table, Text
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

from energy_trading.infrastructure.persistence.postgres.tables import (
    APPLICATION_SCHEMA,
    CONSUMPTION_TABLE_NAME,
    consumption_observations,
    metadata,
)
from tests.architecture.import_inspection import SRC_ROOT

TABLES_PATH = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "persistence" / "postgres" / "tables.py"
)

FORBIDDEN_COLUMNS = frozenset(
    {
        "id",
        "uuid",
        "source_name",
        "adapter_name",
        "source_row",
        "filename",
        "created_by",
        "payload",
        "raw_payload",
        "metadata",
        "diagnostics",
        "correlation_id",
    }
)


def test_consumption_table_is_schema_qualified_core_table() -> None:
    assert isinstance(consumption_observations, Table)
    assert isinstance(metadata, MetaData)
    assert consumption_observations.schema == APPLICATION_SCHEMA == "energy_trading"
    assert consumption_observations.name == CONSUMPTION_TABLE_NAME == "consumption_observations"


def test_consumption_table_has_exactly_canonical_columns() -> None:
    assert tuple(consumption_observations.c.keys()) == ("consumer_id", "timestamp", "value_mw")
    leaked = sorted(name for name in consumption_observations.c.keys() if name in FORBIDDEN_COLUMNS)
    assert leaked == []


def test_consumer_id_is_non_null_text() -> None:
    column = consumption_observations.c.consumer_id
    assert column.nullable is False
    assert isinstance(column.type, Text)


def test_timestamp_is_timezone_aware_and_non_null() -> None:
    column = consumption_observations.c.timestamp
    assert column.nullable is False
    assert isinstance(column.type, DateTime)
    assert column.type.timezone is True


def test_value_mw_is_double_precision_and_non_null() -> None:
    column = consumption_observations.c.value_mw
    assert column.nullable is False
    assert isinstance(column.type, DOUBLE_PRECISION)


def test_primary_key_is_consumer_id_and_timestamp() -> None:
    primary_keys = [
        constraint
        for constraint in consumption_observations.constraints
        if isinstance(constraint, PrimaryKeyConstraint)
    ]
    assert len(primary_keys) == 1
    assert tuple(primary_keys[0].columns.keys()) == ("consumer_id", "timestamp")


def test_non_negative_finite_mw_constraint_exists() -> None:
    checks = [
        constraint
        for constraint in consumption_observations.constraints
        if isinstance(constraint, CheckConstraint)
    ]
    assert checks
    sql = " ".join(str(constraint.sqltext) for constraint in checks).lower()
    assert "value_mw" in sql
    assert ">=" in sql
    assert "infinity" in sql


def test_table_metadata_has_no_orm_model_class() -> None:
    tree = ast.parse(TABLES_PATH.read_text(encoding="utf-8"), filename=str(TABLES_PATH))
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == []
    source = TABLES_PATH.read_text(encoding="utf-8")
    assert "declarative_base" not in source
    assert "mapped_column" not in source
    assert "registry" not in source
