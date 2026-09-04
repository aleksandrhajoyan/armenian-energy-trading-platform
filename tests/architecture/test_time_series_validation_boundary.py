"""Chunk 9 time-series validation must stay an infrastructure ACL utility."""

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_names,
)

TIME_SERIES_ROOT = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "adapters" / "structured" / "time_series"
)
INGESTION_PORT = SRC_ROOT / "energy_trading" / "application" / "ports" / "structured_ingestion.py"
PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"

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

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "IntervalGrid",
        "IntervalGridPolicy",
        "ConsumptionRecordCandidate",
        "ConsumptionSeriesIssue",
        "ConsumptionSeriesIssueCode",
        "ConsumptionGap",
        "timedelta",
        "PowerUnit",
        "ZoneInfo",
        "Path",
        "Workbook",
        "Worksheet",
        "Cell",
        "DataFrame",
        "bytes",
        "dict",
        "Mapping",
        "Any",
    }
)

FORBIDDEN_PORT_IMPORTS = frozenset(
    {
        "IntervalGrid",
        "IntervalGridPolicy",
        "ConsumptionRecordCandidate",
        "ConsumptionGap",
        "timedelta",
        "anchor",
        "source_position",
        "missing_count",
        "first_missing_timestamp",
    }
)


def test_time_series_package_does_not_import_outer_layers_or_file_readers() -> None:
    violations = collect_import_violations(TIME_SERIES_ROOT, FORBIDDEN_PREFIXES)
    assert violations == []


def test_structured_ingestion_port_has_no_time_series_config_surface() -> None:
    names = annotation_type_names(INGESTION_PORT)
    violations = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert violations == []
    imported = imported_names(INGESTION_PORT)
    leaked = sorted(name for name in imported if name in FORBIDDEN_PORT_IMPORTS)
    assert leaked == []
    assert async_function_arg_names(INGESTION_PORT, "ingest") == ("self",)


def test_application_ports_have_no_interval_grid_or_duplicate_policy_surface() -> None:
    for path in sorted(PORTS_ROOT.glob("*.py")):
        names = annotation_type_names(path)
        violations = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
        assert violations == [], path.name
        imported = imported_names(path)
        leaked = sorted(name for name in imported if name in FORBIDDEN_PORT_IMPORTS)
        assert leaked == [], path.name
