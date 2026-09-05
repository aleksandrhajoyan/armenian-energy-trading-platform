"""Bootstrap PostgreSQL/TimescaleDB extension and application schema.

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-09-05

This revision owns only infrastructure bootstrap:
TimescaleDB extension enablement and the dedicated ``energy_trading`` schema.

It does not create canonical business tables. Downgrade drops the empty
application schema without CASCADE. The TimescaleDB extension is left
installed because it may be shared by other schemas or workloads.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APPLICATION_SCHEMA = "energy_trading"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {APPLICATION_SCHEMA}")


def downgrade() -> None:
    # Shared database extensions remain installed; this revision does not
    # uninstall them. No CASCADE: fails if later objects exist in the schema.
    op.execute(f"DROP SCHEMA IF EXISTS {APPLICATION_SCHEMA}")
