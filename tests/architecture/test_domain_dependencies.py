"""Domain layer must not depend on outer packages or FastAPI."""

from .import_inspection import SRC_ROOT, collect_import_violations

DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.application",
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.shared",
    "fastapi",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
)


def test_domain_does_not_import_outer_layers_or_fastapi() -> None:
    violations = collect_import_violations(DOMAIN_ROOT, FORBIDDEN_PREFIXES)
    assert violations == []
