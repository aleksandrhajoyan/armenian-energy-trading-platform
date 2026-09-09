"""Chunk 20 document vector indexing must stay behind the application port."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_EXECUTION_COMPOSITION_RELATIVE,
    REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_names,
)

PORTS_ROOT = SRC_ROOT / "energy_trading" / "application" / "ports"
INDEX_PORT = PORTS_ROOT / "document_vector_index.py"
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
    }
)

FORBIDDEN_DTO_FIELDS = frozenset(
    {
        "collection_name",
        "point_id",
        "payload",
        "metadata",
        "distance_metric",
        "query",
        "filter",
        "search",
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
        "search",
        "query",
        "retrieve",
        "delete",
        "list",
        "get",
        "upsert",
        "insert",
        "save",
        "create_collection",
    }
)

ALLOWED_ENTRY_FIELDS = frozenset({"chunk", "embedding"})


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


def test_document_vector_index_port_does_not_import_forbidden_layers_or_providers() -> None:
    assert collect_import_violations(INDEX_PORT.parent, FORBIDDEN_PREFIXES) == []
    leaked = sorted(name for name in imported_names(INDEX_PORT) if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []


def test_document_vector_index_port_is_nongeneric_protocol_not_abc() -> None:
    class_def = _class_def(INDEX_PORT, "DocumentVectorIndexPort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert [param.name for param in class_def.type_params] == []
    source = INDEX_PORT.read_text(encoding="utf-8")
    assert "abstractmethod" not in source


def test_index_signature_accepts_only_index_entries() -> None:
    names = annotation_type_names(INDEX_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert async_function_arg_names(INDEX_PORT, "index") == ("self", "entries")
    index_fn = _async_function(INDEX_PORT, "index")
    assert index_fn.args.vararg is None
    assert index_fn.args.kwarg is None
    assert index_fn.args.kwonlyargs == []
    entries_arg = index_fn.args.args[1]
    assert entries_arg.annotation is not None
    assert index_fn.returns is not None
    assert ast.unparse(entries_arg.annotation) == "tuple[DocumentVectorIndexEntry, ...]"
    assert ast.unparse(index_fn.returns) == "None"
    assert "DocumentVectorIndexEntry" in names
    assert "ExtractedDocumentChunk" in names
    assert "DocumentChunkEmbedding" in names


def test_index_entry_has_only_chunk_and_embedding_fields() -> None:
    fields = _annassign_field_names(INDEX_PORT, "DocumentVectorIndexEntry")
    assert fields == ALLOWED_ENTRY_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_DTO_FIELDS)
    assert leaked == []
    annotations = _annassign_field_annotations(INDEX_PORT, "DocumentVectorIndexEntry")
    assert annotations == {
        "chunk": "ExtractedDocumentChunk",
        "embedding": "DocumentChunkEmbedding",
    }


def test_document_vector_index_port_has_no_retrieval_or_search_operations() -> None:
    class_def = _class_def(INDEX_PORT, "DocumentVectorIndexPort")
    method_names = {
        item.name
        for item in class_def.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    leaked = sorted(name for name in method_names if name in FORBIDDEN_PORT_OPERATIONS)
    assert leaked == []
    assert method_names == {"index"}


def test_api_composition_does_not_import_or_construct_document_vector_index() -> None:
    assert (
        collect_import_violations(
            API_ROOT,
            (
                "energy_trading.application.ports.document_vector_index",
                "qdrant_client",
                "qdrant",
            ),
            exclude_relative_prefixes=(
                *REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
                DOCUMENT_VECTOR_INDEX_EXECUTION_COMPOSITION_RELATIVE,
            ),
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
        if path.relative_to(SRC_ROOT).as_posix() == (
            DOCUMENT_VECTOR_INDEX_EXECUTION_COMPOSITION_RELATIVE
        ):
            continue
        names = imported_names(path)
        assert "DocumentVectorIndexPort" not in names
        assert "DocumentVectorIndexEntry" not in names
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
    assert "DocumentVectorIndexPort" not in call_names
    assert "DocumentVectorIndexEntry" not in call_names
    lowered = app_source.lower()
    assert "documentvectorindex" not in lowered
    assert "qdrant" not in lowered
