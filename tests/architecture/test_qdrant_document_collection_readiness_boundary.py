"""Chunk 105 Qdrant collection readiness stays a verify-only infrastructure seam."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
QDRANT_ROOT = PRODUCTION_ROOT / "infrastructure" / "vector_store" / "qdrant"
READINESS_MODULE = QDRANT_ROOT / "collection_readiness.py"
DOCUMENT_VECTOR = QDRANT_ROOT / "document_vector.py"
CLIENT_MODULE = QDRANT_ROOT / "client.py"
COMPOSITION_ROOT = API_ROOT / "composition"

UNWIRED_MODULES = (
    API_APP,
    GRAPH_MODULE,
    COMPOSITION_ROOT / "production_lifespan.py",
    COMPOSITION_ROOT / "document_vector_index_lifespan.py",
    COMPOSITION_ROOT / "document_vector_index_loaded_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_managed_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_configured_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py",
    COMPOSITION_ROOT / "regulatory_intelligence_loaded_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_managed_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_configured_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_runtime.py",
    COMPOSITION_ROOT / "pdf_document_extraction_index_execute.py",
    API_ROOT / "routers" / "document_vector_index.py",
    API_ROOT / "routers" / "regulatory_intelligence.py",
)

FORBIDDEN_PREFIXES = (
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.shared.config",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "pandas",
    "polars",
    "openpyxl",
    "numpy",
    "scipy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "torch",
    "tensorflow",
    "n8n",
    "tenacity",
    "backoff",
    "os",
    "sys",
    "dotenv",
    "pypdf",
    "fastembed",
)

ALLOWED_MODULES = frozenset(
    {
        "typing",
        "qdrant_client",
        "qdrant_client.common.client_exceptions",
        "qdrant_client.http.exceptions",
        "qdrant_client.http.models",
        "energy_trading.application.errors",
        "energy_trading.infrastructure.vector_store.qdrant.document_vector",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Distance",
        "create_collection",
        "recreate_collection",
        "delete_collection",
        "update_collection",
        "create_payload_index",
        "delete_payload_index",
        "upsert",
        "upload_points",
        "set_payload",
        "query_points",
        "scroll",
        "count",
        "retrieve",
        "create_qdrant_client",
        "QdrantSettings",
        "load_qdrant_settings",
        "create_app",
        "build_workflow_graph",
        "CollectionManager",
        "VectorStoreManager",
        "QdrantManager",
        "CollectionRepository",
        "CollectionRegistry",
        "CollectionLifecycleService",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "ServiceRegistry",
        "ProviderRegistry",
        "getenv",
        "environ",
        "FastAPI",
        "AsyncOpenAI",
    }
)

MUTATION_FRAGMENTS = (
    "create_collection",
    "recreate_collection",
    "delete_collection",
    "update_collection",
    "create_payload_index",
    "delete_payload_index",
    "upsert",
    "upload_points",
    "set_payload",
    "query_points",
    "scroll",
    "count",
    "retrieve",
    "create_qdrant_client",
    "load_qdrant_settings",
    "QdrantSettings",
    "Distance",
    "tenacity",
    "backoff",
)

GENERIC_TYPE_NAMES = frozenset(
    {
        "CollectionManager",
        "VectorStoreManager",
        "QdrantManager",
        "CollectionRepository",
        "CollectionRegistry",
        "CollectionLifecycleService",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "ServiceRegistry",
        "ProviderRegistry",
        "FastAPI",
        "Distance",
    }
)


def _module_functions(path: Path) -> list[ast.AsyncFunctionDef | ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node for node in tree.body if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))]


def _call_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def test_readiness_module_lives_in_qdrant_infrastructure() -> None:
    assert READINESS_MODULE.is_relative_to(QDRANT_ROOT)
    assert READINESS_MODULE.name == "collection_readiness.py"
    leaked = sorted(
        module
        for module in imported_modules(READINESS_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []


def test_readiness_imports_are_narrow() -> None:
    modules = imported_modules(READINESS_MODULE)
    names = imported_names(READINESS_MODULE)
    assert modules == ALLOWED_MODULES
    assert "AsyncQdrantClient" in names
    assert "VectorParams" in names
    assert "QdrantDocumentVectorConfig" in names
    assert "DependencyUnavailableError" in names
    assert "Distance" not in names
    assert "create_qdrant_client" not in names
    assert "QdrantSettings" not in names


def test_readiness_public_operation_is_the_narrow_verifier() -> None:
    functions = _module_functions(READINESS_MODULE)
    assert [node.name for node in functions] == ["verify_qdrant_document_collection_ready"]
    verifier = functions[0]
    assert isinstance(verifier, ast.AsyncFunctionDef)
    assert [arg.arg for arg in verifier.args.args] == []
    assert [arg.arg for arg in verifier.args.kwonlyargs] == ["client", "config"]
    assert verifier.args.vararg is None
    assert verifier.args.kwarg is None
    annotations = annotation_type_names(READINESS_MODULE)
    assert "AsyncQdrantClient" in annotations
    assert "QdrantDocumentVectorConfig" in annotations
    assert annotations.isdisjoint(GENERIC_TYPE_NAMES)
    tree = ast.parse(READINESS_MODULE.read_text(encoding="utf-8"), filename=str(READINESS_MODULE))
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)


def test_readiness_performs_one_get_collection_and_inspects_vectorparams() -> None:
    functions = _module_functions(READINESS_MODULE)
    verifier = functions[0]
    call_names = _call_names(verifier)
    assert "get_collection" in call_names
    assert call_names.isdisjoint(FORBIDDEN_IDENTIFIERS)
    vector_params_calls = [
        node
        for node in ast.walk(verifier)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "VectorParams")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "VectorParams")
        )
    ]
    assert vector_params_calls == []
    get_collection_calls = [
        node
        for node in ast.walk(verifier)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_collection"
    ]
    assert len(get_collection_calls) == 1
    keywords = {keyword.arg for keyword in get_collection_calls[0].keywords if keyword.arg}
    assert keywords == {"collection_name"}


def test_readiness_source_has_no_mutation_distance_or_retry() -> None:
    source = READINESS_MODULE.read_text(encoding="utf-8")
    for fragment in MUTATION_FRAGMENTS:
        assert fragment not in source
    assert "VectorParams" in source
    assert "get_collection" in source
    tree = ast.parse(source, filename=str(READINESS_MODULE))
    assert not any(isinstance(node, (ast.For, ast.While, ast.AsyncFor)) for node in ast.walk(tree))


def test_index_and_search_adapters_do_not_invoke_readiness() -> None:
    names = imported_names(DOCUMENT_VECTOR)
    modules = imported_modules(DOCUMENT_VECTOR)
    source = DOCUMENT_VECTOR.read_text(encoding="utf-8")
    assert "verify_qdrant_document_collection_ready" not in names
    assert "collection_readiness" not in modules
    assert "verify_qdrant_document_collection_ready" not in source
    assert "get_collection" not in source
    client_source = CLIENT_MODULE.read_text(encoding="utf-8")
    assert "verify_qdrant_document_collection_ready" not in client_source
    assert "get_collection" not in client_source


def test_readiness_remains_unwired_from_runtime_and_http() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert "verify_qdrant_document_collection_ready" not in names
        assert "collection_readiness" not in imported_modules(path)
        assert "verify_qdrant_document_collection_ready" not in source
