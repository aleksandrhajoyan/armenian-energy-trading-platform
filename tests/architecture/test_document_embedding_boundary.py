"""Chunk 19 document embedding must stay behind the application port."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_names,
)

PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
EMBEDDING_PORT = PORTS_ROOT / "document_embedding.py"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "fastapi",
    "starlette",
    "qdrant_client",
    "qdrant",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "numpy",
    "scipy",
    "sklearn",
    "torch",
    "tensorflow",
    "transformers",
    "sentence_transformers",
    "openai",
    "langchain",
    "langchain_core",
    "langgraph",
    "pandas",
    "polars",
    "openpyxl",
    "requests",
    "httpx",
    "aiohttp",
    "pypdf",
    "PyPDF2",
    "pdfplumber",
    "fitz",
    "pymupdf",
    "pytesseract",
    "pathlib",
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
        "dict",
        "Dict",
        "Mapping",
        "MutableMapping",
        "ndarray",
        "NDArray",
        "QdrantClient",
        "Qdrant",
        "models",
        "Filter",
        "SearchParams",
        "Distance",
        "CollectionInfo",
        "PointStruct",
        "SentenceTransformer",
        "OpenAI",
        "HttpUrl",
        "AnyUrl",
        "URL",
        "Request",
        "Response",
        "BinaryIO",
        "TextIO",
    }
)

FORBIDDEN_DTO_FIELDS = frozenset(
    {
        "dimension",
        "model_name",
        "provider",
        "collection_name",
        "distance_metric",
        "metadata",
        "payload",
        "token_count",
        "raw_response",
        "query",
        "filter",
        "search",
        "path",
        "url",
        "uri",
    }
)

ALLOWED_EMBEDDING_FIELDS = frozenset({"document_id", "chunk_id", "vector"})


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


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _async_function(path: Path, function_name: str) -> ast.AsyncFunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            return node
    msg = f"async function {function_name!r} not found in {path}"
    raise AssertionError(msg)


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def test_document_embedding_port_does_not_import_forbidden_layers_or_providers() -> None:
    assert collect_import_violations(EMBEDDING_PORT.parent, FORBIDDEN_PREFIXES) == []
    leaked = sorted(name for name in imported_names(EMBEDDING_PORT) if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []


def test_document_embedding_port_is_nongeneric_protocol_not_abc() -> None:
    class_def = _class_def(EMBEDDING_PORT, "DocumentEmbeddingPort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert [param.name for param in class_def.type_params] == []
    source = EMBEDDING_PORT.read_text(encoding="utf-8")
    assert "abstractmethod" not in source


def test_embed_signature_accepts_only_extracted_chunks() -> None:
    names = annotation_type_names(EMBEDDING_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert async_function_arg_names(EMBEDDING_PORT, "embed") == ("self", "chunks")
    embed = _async_function(EMBEDDING_PORT, "embed")
    assert embed.args.vararg is None
    assert embed.args.kwarg is None
    assert embed.args.kwonlyargs == []
    chunks_arg = embed.args.args[1]
    assert chunks_arg.annotation is not None
    assert embed.returns is not None
    assert ast.unparse(chunks_arg.annotation) == "tuple[ExtractedDocumentChunk, ...]"
    assert ast.unparse(embed.returns) == "tuple[DocumentChunkEmbedding, ...]"
    assert "ExtractedDocumentChunk" in names
    assert "DocumentChunkEmbedding" in names


def test_embedding_dto_has_only_identity_and_vector_fields() -> None:
    fields = _annassign_field_names(EMBEDDING_PORT, "DocumentChunkEmbedding")
    assert fields == ALLOWED_EMBEDDING_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_DTO_FIELDS)
    assert leaked == []


def test_api_composition_does_not_import_or_construct_document_embedding() -> None:
    assert (
        collect_import_violations(
            API_ROOT,
            (
                "energy_trading.application.ports.document_embedding",
                "qdrant_client",
                "qdrant",
                "sentence_transformers",
                "transformers",
                "openai",
            ),
            exclude_relative_prefixes=REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            ("energy_trading.infrastructure.vector_store",),
            exclude_relative_prefixes=REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
        )
        == []
    )
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "DocumentEmbeddingPort" not in names
        assert "DocumentChunkEmbedding" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    tree = ast.parse(app_source, filename=str(API_APP))
    create_app = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names: set[str] = set()
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "DocumentEmbeddingPort" not in call_names
    assert "DocumentChunkEmbedding" not in call_names
    lowered = app_source.lower()
    assert "documentembedding" not in lowered
    assert "qdrant" not in lowered
