"""Chunk 108 Qdrant collection ensure stays a compose-only infrastructure seam."""

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
ENSURE_MODULE = QDRANT_ROOT / "collection_ensure.py"
CREATION_MODULE = QDRANT_ROOT / "collection_creation.py"
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
        "energy_trading.infrastructure.vector_store.qdrant.collection_creation",
        "energy_trading.infrastructure.vector_store.qdrant.collection_readiness",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "get_collection",
        "get_collections",
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
        "VectorParams",
        "create_qdrant_client",
        "QdrantSettings",
        "load_qdrant_settings",
        "create_app",
        "build_workflow_graph",
        "CollectionManager",
        "CollectionProvisioner",
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

FORBIDDEN_SOURCE_FRAGMENTS = (
    "get_collection",
    "get_collections",
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
    "VectorParams",
    "Distance.COSINE",
    "Distance.DOT",
    "Distance.EUCLID",
    "Distance.MANHATTAN",
    "tenacity",
    "backoff",
)

GENERIC_TYPE_NAMES = frozenset(
    {
        "CollectionManager",
        "CollectionProvisioner",
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
    }
)

DISTANCE_MEMBERS = frozenset({"COSINE", "DOT", "EUCLID", "MANHATTAN"})
DELEGATE_KEYWORDS = ("client", "config", "distance")


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


def _distance_member_attrs(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "Distance"
        ):
            names.add(node.attr)
    return names


def _named_calls(node: ast.AST, name: str) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id == name:
            calls.append(child)
        elif isinstance(func, ast.Attribute) and func.attr == name:
            calls.append(child)
    return calls


def _keyword_values(call: ast.Call) -> dict[str, ast.AST]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}


def _is_name(node: ast.AST, expected: str) -> bool:
    return isinstance(node, ast.Name) and node.id == expected


def _assert_delegate_keywords(call: ast.Call) -> None:
    keywords = _keyword_values(call)
    assert set(keywords) == set(DELEGATE_KEYWORDS)
    for name in DELEGATE_KEYWORDS:
        assert _is_name(keywords[name], name)


def test_ensure_module_lives_in_qdrant_infrastructure() -> None:
    assert ENSURE_MODULE.is_relative_to(QDRANT_ROOT)
    assert ENSURE_MODULE.name == "collection_ensure.py"
    leaked = sorted(
        module
        for module in imported_modules(ENSURE_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []


def test_ensure_imports_are_narrow() -> None:
    modules = imported_modules(ENSURE_MODULE)
    names = imported_names(ENSURE_MODULE)
    assert modules == ALLOWED_MODULES
    assert "AsyncQdrantClient" in names
    assert "Distance" in names
    assert "QdrantDocumentVectorConfig" in names
    assert "DependencyUnavailableError" in names
    assert "create_qdrant_document_collection" in names
    assert "verify_qdrant_document_collection_ready" in names
    assert "VectorParams" not in names
    assert "create_qdrant_client" not in names
    assert "QdrantSettings" not in names


def test_ensure_public_operation_is_the_narrow_orchestrator() -> None:
    functions = _module_functions(ENSURE_MODULE)
    assert [node.name for node in functions] == ["ensure_qdrant_document_collection_ready"]
    orchestrator = functions[0]
    assert isinstance(orchestrator, ast.AsyncFunctionDef)
    assert [arg.arg for arg in orchestrator.args.args] == []
    assert [arg.arg for arg in orchestrator.args.kwonlyargs] == ["client", "config", "distance"]
    assert orchestrator.args.vararg is None
    assert orchestrator.args.kwarg is None
    assert orchestrator.args.defaults == []
    assert all(default is None for default in orchestrator.args.kw_defaults)
    annotations = annotation_type_names(ENSURE_MODULE)
    assert "AsyncQdrantClient" in annotations
    assert "QdrantDocumentVectorConfig" in annotations
    assert "Distance" in annotations
    assert annotations.isdisjoint(GENERIC_TYPE_NAMES)
    tree = ast.parse(ENSURE_MODULE.read_text(encoding="utf-8"), filename=str(ENSURE_MODULE))
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)


def test_ensure_probes_existence_once_then_branches_to_create_or_verify() -> None:
    functions = _module_functions(ENSURE_MODULE)
    orchestrator = functions[0]
    call_names = _call_names(orchestrator)
    assert "collection_exists" in call_names
    assert "create_qdrant_document_collection" in call_names
    assert "verify_qdrant_document_collection_ready" in call_names
    assert call_names.isdisjoint(FORBIDDEN_IDENTIFIERS)
    exists_calls = _named_calls(orchestrator, "collection_exists")
    assert len(exists_calls) == 1
    exists_keywords = _keyword_values(exists_calls[0])
    assert set(exists_keywords) == {"collection_name"}
    collection_name = exists_keywords["collection_name"]
    assert isinstance(collection_name, ast.Attribute)
    assert isinstance(collection_name.value, ast.Name)
    assert collection_name.value.id == "config"
    assert collection_name.attr == "collection_name"
    create_calls = _named_calls(orchestrator, "create_qdrant_document_collection")
    verify_calls = _named_calls(orchestrator, "verify_qdrant_document_collection_ready")
    assert len(create_calls) == 1
    assert len(verify_calls) == 1
    _assert_delegate_keywords(create_calls[0])
    _assert_delegate_keywords(verify_calls[0])
    false_branches = [
        node
        for node in ast.walk(orchestrator)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "exists"
        and any(isinstance(op, ast.Is) for op in node.test.ops)
        and any(
            isinstance(comparator, ast.Constant) and comparator.value is False
            for comparator in node.test.comparators
        )
    ]
    assert len(false_branches) == 1
    create_branch = false_branches[0]
    create_in_false_body = _named_calls(
        ast.Module(body=create_branch.body, type_ignores=[]),
        "create_qdrant_document_collection",
    )
    verify_in_false_body = _named_calls(
        ast.Module(body=create_branch.body, type_ignores=[]),
        "verify_qdrant_document_collection_ready",
    )
    assert create_in_false_body == create_calls
    assert verify_in_false_body == []
    verify_in_orelse = _named_calls(
        ast.Module(body=create_branch.orelse, type_ignores=[]),
        "verify_qdrant_document_collection_ready",
    )
    verify_after_false_branch = [
        call
        for statement in orchestrator.body
        if statement is not create_branch
        for call in _named_calls(statement, "verify_qdrant_document_collection_ready")
    ]
    assert verify_in_orelse == verify_calls or verify_after_false_branch == verify_calls


def test_ensure_source_has_no_metadata_mutation_hardcoded_distance_or_retry() -> None:
    source = ENSURE_MODULE.read_text(encoding="utf-8")
    for fragment in FORBIDDEN_SOURCE_FRAGMENTS:
        assert fragment not in source
    stripped = source.replace("create_qdrant_document_collection", "")
    assert "create_collection" not in stripped
    assert "VectorParams" not in source
    assert "Distance" in source
    assert "collection_exists" in source
    tree = ast.parse(source, filename=str(ENSURE_MODULE))
    assert not any(isinstance(node, (ast.For, ast.While, ast.AsyncFor)) for node in ast.walk(tree))
    assert _distance_member_attrs(tree).isdisjoint(DISTANCE_MEMBERS)
    except_handlers = [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]
    assert len(except_handlers) == 1
    handler = except_handlers[0]
    assert not (
        isinstance(handler.type, ast.Name) and handler.type.id in {"Exception", "BaseException"}
    )


def test_creation_and_readiness_do_not_import_ensure() -> None:
    for path in (CREATION_MODULE, READINESS_MODULE, DOCUMENT_VECTOR, CLIENT_MODULE):
        names = imported_names(path)
        modules = imported_modules(path)
        source = path.read_text(encoding="utf-8")
        assert "ensure_qdrant_document_collection_ready" not in names
        assert "collection_ensure" not in modules
        assert "ensure_qdrant_document_collection_ready" not in source


def test_ensure_remains_unwired_from_runtime_and_http() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert "ensure_qdrant_document_collection_ready" not in names
        assert "collection_ensure" not in imported_modules(path)
        assert "ensure_qdrant_document_collection_ready" not in source
