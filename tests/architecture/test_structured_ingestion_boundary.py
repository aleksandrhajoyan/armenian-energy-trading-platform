"""Structured ingestion ports must not expose raw source types."""

from .import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_names,
)

PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
INGESTION_PORT = PORTS_ROOT / "structured_ingestion.py"
DLQ_PORT = PORTS_ROOT / "dlq.py"

FORBIDDEN_LAYER_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "fastapi",
    "starlette",
)

FORBIDDEN_RAW_MODULES = (
    "pandas",
    "openpyxl",
    "csv",
    "requests",
    "httpx",
    "aiohttp",
    "bs4",
    "bs4.BeautifulSoup",
    "beautifulsoup4",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "BeautifulSoup",
        "DataFrame",
        "Mapping",
        "MutableMapping",
        "bytes",
        "bytearray",
        "dict",
        "Dict",
    }
)


def test_application_ports_do_not_import_outer_layers_or_http_frameworks() -> None:
    violations = collect_import_violations(PORTS_ROOT, FORBIDDEN_LAYER_PREFIXES)
    assert violations == []


def test_structured_ingestion_port_has_no_raw_source_imports() -> None:
    names = imported_names(INGESTION_PORT)
    violations = sorted(
        name for name in names if name in FORBIDDEN_TYPE_NAMES or name in FORBIDDEN_RAW_MODULES
    )
    assert violations == []
    assert collect_import_violations(PORTS_ROOT, FORBIDDEN_RAW_MODULES) == []


def test_structured_ingestion_port_annotations_exclude_raw_escape_hatches() -> None:
    names = annotation_type_names(INGESTION_PORT)
    violations = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert violations == []


def test_structured_ingestion_ingest_accepts_no_payload_argument() -> None:
    assert async_function_arg_names(INGESTION_PORT, "ingest") == ("self",)


def test_dlq_port_has_no_raw_source_imports_or_annotations() -> None:
    import_violations = sorted(
        name
        for name in imported_names(DLQ_PORT)
        if name in FORBIDDEN_TYPE_NAMES or name in FORBIDDEN_RAW_MODULES
    )
    annotation_violations = sorted(
        name for name in annotation_type_names(DLQ_PORT) if name in FORBIDDEN_TYPE_NAMES
    )
    assert import_violations == []
    assert annotation_violations == []
    assert async_function_arg_names(DLQ_PORT, "enqueue") == ("self", "record")
