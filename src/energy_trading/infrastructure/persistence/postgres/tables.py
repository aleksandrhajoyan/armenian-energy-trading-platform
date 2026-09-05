"""SQLAlchemy Core table metadata for PostgreSQL/TimescaleDB.

These definitions are infrastructure mapping only. They are not domain models
and are not SQLAlchemy ORM declarative classes.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

APPLICATION_SCHEMA = "energy_trading"
CONSUMPTION_TABLE_NAME = "consumption_observations"
VALUE_MW_FINITE_NON_NEGATIVE = "value_mw >= 0 AND value_mw < CAST('Infinity' AS DOUBLE PRECISION)"

metadata = MetaData()

consumption_observations = Table(
    CONSUMPTION_TABLE_NAME,
    metadata,
    Column("consumer_id", Text, nullable=False),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("value_mw", DOUBLE_PRECISION, nullable=False),
    PrimaryKeyConstraint("consumer_id", "timestamp", name="pk_consumption_observations"),
    CheckConstraint(
        VALUE_MW_FINITE_NON_NEGATIVE,
        name="ck_consumption_observations_value_mw_finite_non_negative",
    ),
    schema=APPLICATION_SCHEMA,
)
