"""Chunk 7 Excel adapter may use openpyxl but not pandas or outer layers."""

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_modules,
    is_forbidden,
)

EXCEL_ADAPTER_ROOT = (
    SRC_ROOT / "energy_trading" / "infrastructure" / "adapters" / "structured" / "excel"
)
MAPPING_FILE = (
    SRC_ROOT
    / "energy_trading"
    / "infrastructure"
    / "adapters"
    / "structured"
    / "consumption_mapping.py"
)
VALUES_FILE = (
    SRC_ROOT
    / "energy_trading"
    / "infrastructure"
    / "adapters"
    / "structured"
    / "consumption_values.py"
)
PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
INGESTION_PORT = PORTS_ROOT / "structured_ingestion.py"

FORBIDDEN_PREFIXES = (
    "pandas",
    "polars",
    "pyarrow",
    "xlrd",
    "pyxlsb",
    "requests",
    "aiohttp",
    "httpx",
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
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
    "energy_trading.ml",
)

FORBIDDEN_MAPPING_PREFIXES = (
    *FORBIDDEN_PREFIXES,
    "openpyxl",
    "energy_trading.application",
    "energy_trading.domain",
)

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "Path",
        "PurePath",
        "PosixPath",
        "WindowsPath",
        "Workbook",
        "Worksheet",
        "ReadOnlyWorksheet",
        "Cell",
        "openpyxl",
        "DataFrame",
        "IntervalGrid",
        "ConsumptionGap",
        "timedelta",
        "bytes",
        "dict",
        "Mapping",
        "Any",
    }
)


def test_excel_adapter_does_not_import_forbidden_providers_or_layers() -> None:
    violations = collect_import_violations(EXCEL_ADAPTER_ROOT, FORBIDDEN_PREFIXES)
    assert violations == []


def test_consumption_helpers_stay_provider_and_layer_free() -> None:
    violations = sorted(
        f"{path.name} imports {module}"
        for path in (MAPPING_FILE, VALUES_FILE)
        for module in imported_modules(path)
        if is_forbidden(module, FORBIDDEN_MAPPING_PREFIXES)
    )
    assert violations == []


def test_structured_ingestion_port_still_has_no_excel_or_path_surface() -> None:
    names = annotation_type_names(INGESTION_PORT)
    violations = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert violations == []
    assert async_function_arg_names(INGESTION_PORT, "ingest") == ("self",)
