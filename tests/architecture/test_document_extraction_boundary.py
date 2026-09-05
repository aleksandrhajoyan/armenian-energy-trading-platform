"""Chunk 12 document extraction must stay behind the application port."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_names,
)

PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
EXTRACTION_PORT = PORTS_ROOT / "document_extraction.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "fastapi",
    "starlette",
    "pathlib",
    "pandas",
    "polars",
    "openpyxl",
    "pypdf",
    "PyPDF2",
    "fitz",
    "pymupdf",
    "pdfplumber",
    "pdfminer",
    "unstructured",
    "pytesseract",
    "easyocr",
    "PIL",
    "pillow",
    "requests",
    "httpx",
    "aiohttp",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "redis",
    "qdrant_client",
    "langchain",
    "langchain_core",
    "langgraph",
    "llama_index",
    "openai",
    "sentence_transformers",
    "transformers",
    "xgboost",
    "lightgbm",
    "prophet",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
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
        "MutableMapping",
        "DataFrame",
        "HttpUrl",
        "AnyUrl",
        "URL",
        "Request",
        "Response",
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
        "token_ids",
        "tokens",
        "confidence",
        "ocr_confidence",
        "bounding_box",
        "bounding_boxes",
        "bbox",
        "path",
        "file_path",
        "filepath",
        "url",
        "uri",
        "payload",
        "raw_payload",
        "raw_bytes",
        "ocr_response",
        "provider_response",
    }
)

ALLOWED_CHUNK_FIELDS = frozenset({"document_id", "chunk_id", "ordinal", "text", "page_number"})
ALLOWED_RESULT_FIELDS = frozenset(
    {"source_name", "document_id", "chunks", "diagnostics", "dlq_records"}
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


def test_document_extraction_port_does_not_import_forbidden_layers_or_providers() -> None:
    assert collect_import_violations(PORTS_ROOT, FORBIDDEN_PREFIXES) == []
    names = imported_names(EXTRACTION_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []


def test_document_extraction_signatures_exclude_raw_document_surface() -> None:
    names = annotation_type_names(EXTRACTION_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert async_function_arg_names(EXTRACTION_PORT, "extract") == ("self",)
    tree = ast.parse(EXTRACTION_PORT.read_text(encoding="utf-8"), filename=str(EXTRACTION_PORT))
    extract = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "extract"
    )
    assert extract.args.vararg is None
    assert extract.args.kwarg is None


def test_extraction_dtos_have_only_normalized_provenance_fields() -> None:
    chunk_fields = _annassign_field_names(EXTRACTION_PORT, "ExtractedDocumentChunk")
    result_fields = _annassign_field_names(EXTRACTION_PORT, "DocumentExtractionResult")
    assert chunk_fields == ALLOWED_CHUNK_FIELDS
    assert result_fields == ALLOWED_RESULT_FIELDS
    leaked_chunk = sorted(name for name in chunk_fields if name in FORBIDDEN_DTO_FIELDS)
    leaked_result = sorted(name for name in result_fields if name in FORBIDDEN_DTO_FIELDS)
    assert leaked_chunk == []
    assert leaked_result == []
