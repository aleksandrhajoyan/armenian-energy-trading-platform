"""Chunk 64 document query-text embedding must stay behind the application port."""

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
PORTS_ROOT = PRODUCTION_ROOT / "application" / "ports"
QUERY_EMBEDDING_PORT = PORTS_ROOT / "document_query_embedding.py"
AGENT_MODULE = PRODUCTION_ROOT / "application" / "agents" / "regulatory_intelligence.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
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
    "anthropic",
    "google.generativeai",
    "google.genai",
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
    "n8n",
    "xgboost",
    "lightgbm",
    "prophet",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
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
        "DataFrame",
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
        "Anthropic",
        "HttpUrl",
        "AnyUrl",
        "URL",
        "Request",
        "Response",
        "BinaryIO",
        "TextIO",
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "DocumentEmbeddingPort",
        "DocumentChunkEmbedding",
        "DocumentVectorSearchPort",
        "DocumentVectorSearchQuery",
        "ExtractedDocumentChunk",
        "RegulatoryIntelligenceAgent",
        "RegulatoryConstraintInferencePort",
    }
)

FORBIDDEN_DTO_FIELDS = frozenset(
    {
        "query_text",
        "query",
        "text",
        "dimension",
        "model_name",
        "provider",
        "collection_name",
        "distance_metric",
        "metadata",
        "payload",
        "token_count",
        "token_usage",
        "cost",
        "raw_response",
        "filter",
        "search",
        "score",
        "path",
        "url",
        "uri",
        "document_id",
        "chunk_id",
    }
)

FORBIDDEN_PORT_OPERATIONS = frozenset(
    {
        "embed",
        "search",
        "index",
        "upsert",
        "insert",
        "save",
        "delete",
        "infer",
        "retrieve",
        "create_collection",
    }
)

GENERIC_EMBEDDING_CLASS_NAMES = frozenset(
    {
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "GenericEmbeddingPort",
    }
)

ALLOWED_EMBEDDING_FIELDS = frozenset({"vector"})
ALLOWED_MODULE_IMPORTS = frozenset({"dataclasses", "math", "typing"})


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


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _public_function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def test_document_query_embedding_port_does_not_import_forbidden_layers_or_providers() -> None:
    leaked = sorted(
        module
        for module in imported_modules(QUERY_EMBEDDING_PORT)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(QUERY_EMBEDDING_PORT) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(QUERY_EMBEDDING_PORT) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []


def test_document_query_embedding_public_surface_is_port_and_result_dto() -> None:
    assert _module_class_names(QUERY_EMBEDDING_PORT) == [
        "DocumentQueryEmbedding",
        "DocumentQueryEmbeddingPort",
    ]
    assert _public_function_names(QUERY_EMBEDDING_PORT) == []


def test_document_query_embedding_port_is_nongeneric_protocol_not_abc() -> None:
    class_def = _class_def(QUERY_EMBEDDING_PORT, "DocumentQueryEmbeddingPort")
    bases = _base_names(class_def)
    assert bases == {"Protocol"}
    assert "ABC" not in bases
    assert "DocumentEmbeddingPort" not in bases
    assert "EmbeddingPort" not in bases
    assert "LLMPort" not in bases
    assert [param.name for param in class_def.type_params] == []
    source = QUERY_EMBEDDING_PORT.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "TypeVar" not in source
    assert "Generic[" not in source


def test_embed_query_signature_accepts_only_query_text() -> None:
    names = annotation_type_names(QUERY_EMBEDDING_PORT)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert async_function_arg_names(QUERY_EMBEDDING_PORT, "embed_query") == ("self", "query_text")
    embed_query = _async_function(QUERY_EMBEDDING_PORT, "embed_query")
    assert embed_query.args.vararg is None
    assert embed_query.args.kwarg is None
    assert embed_query.args.kwonlyargs == []
    query_arg = embed_query.args.args[1]
    assert query_arg.annotation is not None
    assert embed_query.returns is not None
    assert ast.unparse(query_arg.annotation) == "str"
    assert ast.unparse(embed_query.returns) == "DocumentQueryEmbedding"
    assert "DocumentQueryEmbedding" in names


def test_document_query_embedding_port_has_exactly_one_async_operation() -> None:
    class_def = _class_def(QUERY_EMBEDDING_PORT, "DocumentQueryEmbeddingPort")
    method_names = {
        item.name
        for item in class_def.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    leaked = sorted(name for name in method_names if name in FORBIDDEN_PORT_OPERATIONS)
    assert leaked == []
    assert method_names == {"embed_query"}
    operations = [
        item for item in class_def.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert len(operations) == 1
    assert isinstance(operations[0], ast.AsyncFunctionDef)


def test_query_embedding_dto_has_only_vector_field() -> None:
    fields = _annassign_field_names(QUERY_EMBEDDING_PORT, "DocumentQueryEmbedding")
    assert fields == ALLOWED_EMBEDDING_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_DTO_FIELDS)
    assert leaked == []
    annotations = _annassign_field_annotations(QUERY_EMBEDDING_PORT, "DocumentQueryEmbedding")
    assert annotations == {"vector": "tuple[float, ...]"}


def test_query_embedding_module_has_no_provider_implementation() -> None:
    call_names = _call_names(QUERY_EMBEDDING_PORT)
    assert "OpenAI" not in call_names
    assert "Anthropic" not in call_names
    assert "SentenceTransformer" not in call_names
    assert "QdrantClient" not in call_names
    assert "AsyncQdrantClient" not in call_names
    imported = imported_modules(QUERY_EMBEDDING_PORT)
    assert "openai" not in imported
    assert "anthropic" not in imported
    assert "sentence_transformers" not in imported
    assert "qdrant_client" not in imported
    assert "qdrant" not in imported
    assert "httpx" not in imported
    assert "numpy" not in imported
    class_names = set(_module_class_names(QUERY_EMBEDDING_PORT))
    assert class_names == {"DocumentQueryEmbedding", "DocumentQueryEmbeddingPort"}


def test_no_generic_embedding_or_llm_port_hierarchy() -> None:
    leaked: list[str] = []
    for path in sorted(PORTS_ROOT.rglob("*.py")):
        for name in _module_class_names(path):
            if name in GENERIC_EMBEDDING_CLASS_NAMES:
                leaked.append(f"{path.name}:{name}")
    assert leaked == []
    query_classes = set(_module_class_names(QUERY_EMBEDDING_PORT))
    assert "EmbeddingPort" not in query_classes
    assert "LLMPort" not in query_classes
    assert "AIProviderPort" not in query_classes


def test_regulatory_agent_does_not_import_or_inject_query_embedding() -> None:
    names = imported_names(AGENT_MODULE)
    modules = imported_modules(AGENT_MODULE)
    assert "DocumentQueryEmbeddingPort" not in names
    assert "DocumentQueryEmbedding" not in names
    assert "energy_trading.application.ports.document_query_embedding" not in modules
    agent_class = _class_def(AGENT_MODULE, "RegulatoryIntelligenceAgent")
    init_fn = next(
        node
        for node in agent_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    injected = tuple(arg.arg for arg in init_fn.args.kwonlyargs)
    assert injected == ("search", "inference")
    assert "query_embedding" not in injected
    agent_operations = {
        item.name
        for item in agent_class.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "embed_query" not in agent_operations


def test_graph_module_does_not_import_query_embedding() -> None:
    names = imported_names(GRAPH_MODULE)
    modules = imported_modules(GRAPH_MODULE)
    assert "DocumentQueryEmbeddingPort" not in names
    assert "DocumentQueryEmbedding" not in names
    assert "energy_trading.application.ports.document_query_embedding" not in modules
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "DocumentQueryEmbedding" not in graph_source
    assert "embed_query" not in graph_source


def test_api_composition_does_not_import_or_construct_document_query_embedding() -> None:
    forbidden_wiring = (
        "energy_trading.application.ports.document_query_embedding",
        "qdrant_client",
        "qdrant",
        "sentence_transformers",
        "transformers",
        "openai",
        "anthropic",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "DocumentQueryEmbeddingPort" not in names
        assert "DocumentQueryEmbedding" not in names
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
    assert "DocumentQueryEmbeddingPort" not in call_names
    assert "DocumentQueryEmbedding" not in call_names
    lowered = app_source.lower()
    assert "documentqueryembedding" not in lowered
    assert "qdrant" not in lowered


def test_no_production_langgraph_imports_outside_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
