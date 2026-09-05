"""Create Consumption observations hypertable.

Revision ID: 0002_consumption
Revises: 0001_bootstrap
Create Date: 2026-09-05

This revision owns only ``energy_trading.consumption_observations``.
It does not drop the application schema or the TimescaleDB extension.
Timescale chunk interval is not configured here; it is a storage-performance
choice and is not a Consumption/DAM cadence.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

revision: str = "0002_consumption"
down_revision: str | None = "0001_bootstrap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "energy_trading"
TABLE = "consumption_observations"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("consumer_id", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value_mw", DOUBLE_PRECISION(), nullable=False),
        sa.PrimaryKeyConstraint("consumer_id", "timestamp", name="pk_consumption_observations"),
        sa.CheckConstraint(
            "value_mw >= 0 AND value_mw < CAST('Infinity' AS DOUBLE PRECISION)",
            name="ck_consumption_observations_value_mw_finite_non_negative",
        ),
        schema=SCHEMA,
    )
    op.execute(f"SELECT create_hypertable('{SCHEMA}.{TABLE}', 'timestamp', if_not_exists => TRUE)")


def downgrade() -> None:
    op.drop_table(TABLE, schema=SCHEMA)
