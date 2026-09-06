"""Chunk 21 document vector retrieval must stay behind the application port."""

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
SEARCH_PORT = PORTS_ROOT / "document_vector_search.py"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "qdrant",
    "qdrant_client",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "fastapi",
    "starlette",
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
        "PointStruct",
        "PointId",
        "Filter",
        "SearchParams",
        "Distance",
        "CollectionInfo",
        "SentenceTransformer",
        "OpenAI",
        "HttpUrl",
        "AnyUrl",
        "URL",
        "Request",
        "Response",
        "BinaryIO",
        "TextIO",
        "VectorStore",
        "Score",
        "ScoredPoint",
    }
)

FORBIDDEN_DTO_FIELDS = frozenset(
    {
        "text",
        "query_text",
        "query_string",
        "collection_name",
        "namespace",
        "tenant",
        "point_id",
        "payload",
        "metadata",
        "distance_metric",
        "score",
        "score_threshold",
        "filter",
        "offset",
        "cursor",
        "path",
        "url",
        "uri",
        "provider",
        "model_name",
        "dimension",
        "raw_response",
    }
)

FORBIDDEN_PORT_OPERATIONS = frozenset(
    {
        "index",
        "embed",
        "upsert",
        "insert",
        "save",
        "delete",
        "list",
        "get",
        "create_collection",
        "retrieve",
    }
)

ALLOWED_QUERY_FIELDS = frozenset({"vector", "limit"})


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


def _annassign_field_annotations(path: Path, class_name: str) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            annotations: dict[str, str] = {}
            for item in node.body:
                if (
                    isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and item.annotation is not None
                ):
                    annotations[item.target.id] = ast.unparse(item.annotation)
            return annotations
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


def test_document_vector_search_port_does_not_import_forbidden_layers_or_providers() -> None:
    assert collect_import_violations(SEARCH_PORT.parent, FORBIDDEN_PREFIXES) == []
    names = imported_names(SEARCH_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "DocumentEmbeddingPort" not in names
    assert "DocumentChunkEmbedding" not in names
    assert "DocumentVectorIndexPort" not in names
    assert "DocumentVectorIndexEntry" not in names


def test_document_vector_search_port_is_nongeneric_protocol_not_abc() -> None:
    class_def = _class_def(SEARCH_PORT, "DocumentVectorSearchPort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert [param.name for param in class_def.type_params] == []
    source = SEARCH_PORT.read_text(encoding="utf-8")
    assert "abstractmethod" not in source


def test_search_signature_accepts_only_search_query() -> None:
    names = annotation_type_names(SEARCH_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert async_function_arg_names(SEARCH_PORT, "search") == ("self", "query")
    search_fn = _async_function(SEARCH_PORT, "search")
    assert search_fn.args.vararg is None
    assert search_fn.args.kwarg is None
    assert search_fn.args.kwonlyargs == []
    query_arg = search_fn.args.args[1]
    assert query_arg.annotation is not None
    assert search_fn.returns is not None
    assert ast.unparse(query_arg.annotation) == "DocumentVectorSearchQuery"
    assert ast.unparse(search_fn.returns) == "tuple[ExtractedDocumentChunk, ...]"
    assert "DocumentVectorSearchQuery" in names
    assert "ExtractedDocumentChunk" in names


def test_search_query_has_only_vector_and_limit_fields() -> None:
    fields = _annassign_field_names(SEARCH_PORT, "DocumentVectorSearchQuery")
    assert fields == ALLOWED_QUERY_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_DTO_FIELDS)
    assert leaked == []
    annotations = _annassign_field_annotations(SEARCH_PORT, "DocumentVectorSearchQuery")
    assert annotations == {"vector": "tuple[float, ...]", "limit": "int"}
    assert "str" not in annotations.values()


def test_document_vector_search_port_has_no_indexing_or_embedding_operations() -> None:
    class_def = _class_def(SEARCH_PORT, "DocumentVectorSearchPort")
    method_names = {
        item.name
        for item in class_def.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    leaked = sorted(name for name in method_names if name in FORBIDDEN_PORT_OPERATIONS)
    assert leaked == []
    assert method_names == {"search"}


def test_api_composition_does_not_import_or_construct_document_vector_search() -> None:
    forbidden_wiring = (
        "energy_trading.application.ports.document_vector_search",
        "energy_trading.infrastructure.vector_store",
        "qdrant_client",
        "qdrant",
        "sentence_transformers",
        "openai",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "DocumentVectorSearchPort" not in names
        assert "DocumentVectorSearchQuery" not in names
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
    assert "DocumentVectorSearchPort" not in call_names
    assert "DocumentVectorSearchQuery" not in call_names
    lowered = app_source.lower()
    assert "documentvectorsearch" not in lowered
    assert "qdrant" not in lowered
