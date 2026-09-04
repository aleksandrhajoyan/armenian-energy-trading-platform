"""Chunk 10 gap types must stay infrastructure-local."""

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_import_violations,
    imported_names,
)

TIME_SERIES_ROOT = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "adapters" / "structured" / "time_series"
)
INGESTION_PORT = SRC_ROOT / "energy_trading" / "application" / "ports" / "structured_ingestion.py"

FORBIDDEN_PREFIXES = (
    "openai",
    "langchain",
    "langchain_core",
    "langgraph",
    "pandas",
    "polars",
    "numpy",
    "openpyxl",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "redis",
    "qdrant_client",
    "httpx",
    "requests",
    "aiohttp",
    "energy_trading.application",
    "energy_trading.api",
    "energy_trading.ml",
)

FORBIDDEN_GAP_TYPES = frozenset(
    {
        "ConsumptionGap",
        "missing_count",
        "first_missing_timestamp",
        "last_missing_timestamp",
        "coverage_window",
        "IntervalGrid",
    }
)


def test_time_series_package_still_has_no_outer_layer_imports() -> None:
    assert collect_import_violations(TIME_SERIES_ROOT, FORBIDDEN_PREFIXES) == []


def test_application_ingestion_port_has_no_gap_or_coverage_surface() -> None:
    names = annotation_type_names(INGESTION_PORT) | imported_names(INGESTION_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_GAP_TYPES)
    assert leaked == []
