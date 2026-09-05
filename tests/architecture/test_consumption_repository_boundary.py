"""Consumption PostgreSQL persistence must stay behind the application port."""

from __future__ import annotations

import ast

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
CONSUMPTION_PORT = PORTS_ROOT / "consumption_repository.py"
POSTGRES_ROOT = SRC_ROOT / "energy_trading" / "infrastructure" / "persistence" / "postgres"
REPOSITORY = POSTGRES_ROOT / "consumption_repository.py"
TABLES = POSTGRES_ROOT / "tables.py"
DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"
APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
DLQ_ADAPTER = SRC_ROOT / "energy_trading" / "infrastructure" / "persistence" / "dlq.py"

FORBIDDEN_PORT_LAYERS = (
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "fastapi",
    "starlette",
    "pandas",
    "polars",
    "openpyxl",
    "redis",
    "qdrant_client",
    "langchain",
    "langchain_core",
    "langgraph",
    "openai",
    "xgboost",
    "lightgbm",
    "prophet",
)

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "Any",
        "AsyncSession",
        "Session",
        "Engine",
        "AsyncEngine",
        "Table",
        "MetaData",
        "Column",
        "Connection",
        "Path",
        "bytes",
        "bytearray",
        "dict",
        "Dict",
        "Mapping",
        "DataFrame",
        "Workbook",
    }
)

FORBIDDEN_REPOSITORY_IMPORTS = (
    "fastapi",
    "starlette",
    "pandas",
    "polars",
    "openpyxl",
    "redis",
    "qdrant_client",
    "langchain",
    "langchain_core",
    "langgraph",
    "openai",
    "xgboost",
    "lightgbm",
    "prophet",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.ml",
    "energy_trading.infrastructure.adapters",
)

FORBIDDEN_DB_LIBRARIES = (
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
)


def test_consumption_port_does_not_import_database_or_raw_source_surface() -> None:
    assert collect_import_violations(CONSUMPTION_PORT.parent, FORBIDDEN_PORT_LAYERS) == []
    names = imported_names(CONSUMPTION_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert leaked == []
    annotations = annotation_type_names(CONSUMPTION_PORT)
    leaked_types = sorted(name for name in annotations if name in FORBIDDEN_PORT_TYPES)
    assert leaked_types == []
    assert async_function_arg_names(CONSUMPTION_PORT, "save_many") == ("self", "records")


def test_postgres_consumption_repository_imports_are_constrained() -> None:
    for path in (REPOSITORY, TABLES):
        leaked = [
            f"{path.name} imports {module}"
            for module in sorted(imported_modules(path))
            if is_forbidden(module, FORBIDDEN_REPOSITORY_IMPORTS)
        ]
        assert leaked == []
    names = imported_names(REPOSITORY)
    assert "ConsumptionRecord" in names
    assert "ConflictError" in names
    assert "DependencyUnavailableError" in names


def test_domain_still_imports_no_database_library() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_DB_LIBRARIES) == []


def test_application_still_imports_no_sqlalchemy_implementation() -> None:
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_DB_LIBRARIES) == []


def test_api_still_has_no_db_wiring() -> None:
    assert collect_import_violations(API_ROOT, FORBIDDEN_DB_LIBRARIES) == []


def test_filesystem_dlq_is_not_postgres_backed() -> None:
    source = DLQ_ADAPTER.read_text(encoding="utf-8")
    assert "sqlalchemy" not in source
    assert "psycopg" not in source
    names = imported_names(DLQ_ADAPTER)
    assert "PostgresConsumptionRepository" not in names
    assert "consumption_observations" not in names


def test_no_generic_repository_or_unit_of_work() -> None:
    hits: list[str] = []
    for path in sorted((SRC_ROOT / "energy_trading").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in {"Repository", "UnitOfWork"}:
                hits.append(f"{path.relative_to(SRC_ROOT)}:{node.name}")
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id in {"Repository", "UnitOfWork"}:
                    hits.append(f"{path.relative_to(SRC_ROOT)}:{node.target.id}")
    assert hits == []


def test_no_other_canonical_observation_tables() -> None:
    source = TABLES.read_text(encoding="utf-8")
    forbidden_tables = (
        "weather",
        "hydro",
        "generation",
        "market_price",
        "forecast",
        "settlement",
        "market_bid",
        "dlq",
        "outbox",
    )
    for token in forbidden_tables:
        assert f"{token}_" not in source
        assert f'Table("{token}' not in source
        assert f"Table('{token}'" not in source
