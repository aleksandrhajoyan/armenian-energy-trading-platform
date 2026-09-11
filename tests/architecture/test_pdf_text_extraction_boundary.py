"""Chunk 100 PDF text extraction stays an unwired infrastructure ACL adapter."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
GRAPH_MODULE = APPLICATION_ROOT / "orchestration" / "graph.py"
EXTRACTION_PORT = APPLICATION_ROOT / "ports" / "document_extraction.py"
ADAPTER_ROOT = PRODUCTION_ROOT / "infrastructure" / "adapters" / "unstructured"
ADAPTER_MODULE = ADAPTER_ROOT / "pdf_text_extraction.py"
INDEX_EXECUTION = APPLICATION_ROOT / "orchestration" / "document_vector_index_execution.py"

FORBIDDEN_ADAPTER_PREFIXES = (
    "fastapi",
    "starlette",
    "energy_trading.api",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "qdrant_client",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "xgboost",
    "lightgbm",
    "prophet",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports.document_embedding",
    "energy_trading.application.ports.document_query_embedding",
    "energy_trading.application.ports.document_vector_index",
    "energy_trading.application.ports.document_vector_search",
    "energy_trading.application.ports.regulatory_constraint_inference",
    "pytesseract",
    "easyocr",
    "PIL",
    "pillow",
    "pdfminer",
    "pdfplumber",
    "fitz",
    "pymupdf",
    "unstructured",
    "langchain_community",
)

FORBIDDEN_PORT_TYPES = frozenset(
    {
        "Path",
        "PurePath",
        "PosixPath",
        "WindowsPath",
        "bytes",
        "bytearray",
        "memoryview",
        "BinaryIO",
        "TextIO",
        "dict",
        "Dict",
        "Mapping",
        "Any",
        "PdfReader",
        "PdfWriter",
        "PageObject",
        "HttpUrl",
        "AnyUrl",
        "URL",
    }
)

FORBIDDEN_DTO_FIELDS = frozenset(
    {
        "metadata",
        "extra",
        "embedding",
        "embeddings",
        "vector",
        "vectors",
        "path",
        "file_path",
        "filepath",
        "url",
        "uri",
        "payload",
        "raw_payload",
        "raw_bytes",
        "ocr_response",
    }
)

ALLOWED_CHUNK_FIELDS = frozenset({"document_id", "chunk_id", "ordinal", "text", "page_number"})
ALLOWED_RESULT_FIELDS = frozenset(
    {"source_name", "document_id", "chunks", "diagnostics", "dlq_records"}
)

ALLOWED_ADAPTER_IMPORTS = frozenset(
    {
        "__future__",
        "asyncio",
        "collections.abc",
        "datetime",
        "pathlib",
        "pypdf",
        "pypdf.errors",
        "energy_trading.application.errors",
        "energy_trading.application.ports.document_extraction",
        "energy_trading.domain.models.ingestion",
    }
)


def _annassign_field_names(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            names: set[str] = set()
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    names.add(item.target.id)
            return names
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _module_class_defs(path: Path) -> list[ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node for node in tree.body if isinstance(node, ast.ClassDef)]


def test_application_extraction_boundary_remains_unchanged() -> None:
    assert async_function_arg_names(EXTRACTION_PORT, "extract") == ("self",)
    names = annotation_type_names(EXTRACTION_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_PORT_TYPES)
    assert leaked == []
    imported = imported_modules(EXTRACTION_PORT)
    assert "pypdf" not in imported
    assert "energy_trading.infrastructure" not in imported
    chunk_fields = _annassign_field_names(EXTRACTION_PORT, "ExtractedDocumentChunk")
    result_fields = _annassign_field_names(EXTRACTION_PORT, "DocumentExtractionResult")
    assert chunk_fields == ALLOWED_CHUNK_FIELDS
    assert result_fields == ALLOWED_RESULT_FIELDS
    leaked_chunk = sorted(name for name in chunk_fields if name in FORBIDDEN_DTO_FIELDS)
    leaked_result = sorted(name for name in result_fields if name in FORBIDDEN_DTO_FIELDS)
    assert leaked_chunk == []
    assert leaked_result == []


def test_pdf_adapter_does_not_import_forbidden_providers_or_layers() -> None:
    violations = collect_import_violations(ADAPTER_ROOT, FORBIDDEN_ADAPTER_PREFIXES)
    assert violations == []
    extras = imported_modules(ADAPTER_MODULE) - ALLOWED_ADAPTER_IMPORTS
    assert extras == set()
    names = imported_names(ADAPTER_MODULE)
    assert "pypdf" in names
    assert "PdfReader" in names
    assert "DocumentExtractionPort" not in names
    assert "create_app" not in names
    assert "FastAPI" not in names
    assert "OpenAI" not in names
    assert "Qdrant" not in names


def test_pdf_adapter_structurally_satisfies_port_without_subclassing() -> None:
    classes = _module_class_defs(ADAPTER_MODULE)
    assert [node.name for node in classes] == ["PdfTextExtractionAdapter"]
    adapter = classes[0]
    assert adapter.bases == []
    extract = next(
        node
        for node in ast.walk(adapter)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "extract"
    )
    assert tuple(arg.arg for arg in extract.args.args) == ("self",)
    assert extract.args.vararg is None
    assert extract.args.kwarg is None
    assert ast.unparse(extract.returns) == "DocumentExtractionResult"
    init = next(
        node
        for node in adapter.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init.args.kwonlyargs) == (
        "path",
        "document_id",
        "source_name",
        "clock",
    )


def test_pdf_extract_offloads_with_to_thread() -> None:
    tree = ast.parse(ADAPTER_MODULE.read_text(encoding="utf-8"), filename=str(ADAPTER_MODULE))
    extract = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "extract"
    )
    calls_to_thread = False
    for node in ast.walk(extract):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "to_thread":
                calls_to_thread = True
    assert calls_to_thread


def test_create_app_and_langgraph_remain_unwired_from_pdf_extraction() -> None:
    for path in (API_APP, GRAPH_MODULE, INDEX_EXECUTION):
        modules = imported_modules(path)
        names = imported_names(path)
        assert "pypdf" not in modules
        assert not any(
            module == "energy_trading.infrastructure.adapters.unstructured"
            or module.startswith("energy_trading.infrastructure.adapters.unstructured.")
            for module in modules
        )
        assert "PdfTextExtractionAdapter" not in names
        assert "pdf_text_extraction" not in names


def test_api_and_application_do_not_gain_pdf_library_imports() -> None:
    assert collect_import_violations(APPLICATION_ROOT, ("pypdf",)) == []
    assert collect_import_violations(API_ROOT, ("pypdf",)) == []
    leaked = sorted(
        f"{path.relative_to(SRC_ROOT)} imports {module}"
        for path in sorted(PRODUCTION_ROOT.rglob("*.py"))
        if path.resolve() != ADAPTER_MODULE.resolve()
        for module in imported_modules(path)
        if is_forbidden(module, ("pypdf",))
    )
    assert leaked == []
    assert "pypdf" in imported_modules(ADAPTER_MODULE)
