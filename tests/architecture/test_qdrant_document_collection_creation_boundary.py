"""Chunk 106 Qdrant collection creation stays a create-only infrastructure seam."""

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
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "get_collection",
        "get_collections",
        "collection_exists",
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
        "verify_qdrant_document_collection_ready",
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
    "collection_exists",
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
    "Distance.COSINE",
    "Distance.DOT",
    "Distance.EUCLID",
    "Distance.MANHATTAN",
    "verify_qdrant_document_collection_ready",
    "ensure_qdrant_document_collection",
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


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def test_creation_module_lives_in_qdrant_infrastructure() -> None:
    assert CREATION_MODULE.is_relative_to(QDRANT_ROOT)
    assert CREATION_MODULE.name == "collection_creation.py"
    leaked = sorted(
        module
        for module in imported_modules(CREATION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []


def test_creation_imports_are_narrow() -> None:
    modules = imported_modules(CREATION_MODULE)
    names = imported_names(CREATION_MODULE)
    assert modules == ALLOWED_MODULES
    assert "AsyncQdrantClient" in names
    assert "VectorParams" in names
    assert "Distance" in names
    assert "QdrantDocumentVectorConfig" in names
    assert "DependencyUnavailableError" in names
    assert "create_qdrant_client" not in names
    assert "QdrantSettings" not in names
    assert "verify_qdrant_document_collection_ready" not in names
    assert "collection_readiness" not in modules


def test_creation_public_operation_is_the_narrow_creator() -> None:
    functions = _module_functions(CREATION_MODULE)
    assert [node.name for node in functions] == ["create_qdrant_document_collection"]
    creator = functions[0]
    assert isinstance(creator, ast.AsyncFunctionDef)
    assert [arg.arg for arg in creator.args.args] == []
    assert [arg.arg for arg in creator.args.kwonlyargs] == ["client", "config", "distance"]
    assert creator.args.vararg is None
    assert creator.args.kwarg is None
    assert creator.args.defaults == []
    assert all(default is None for default in creator.args.kw_defaults)
    annotations = annotation_type_names(CREATION_MODULE)
    assert "AsyncQdrantClient" in annotations
    assert "QdrantDocumentVectorConfig" in annotations
    assert "Distance" in annotations
    assert annotations.isdisjoint(GENERIC_TYPE_NAMES)
    tree = ast.parse(CREATION_MODULE.read_text(encoding="utf-8"), filename=str(CREATION_MODULE))
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)


def test_creation_constructs_one_vectorparams_and_calls_create_collection_once() -> None:
    functions = _module_functions(CREATION_MODULE)
    creator = functions[0]
    call_names = _call_names(creator)
    assert "create_collection" in call_names
    assert "VectorParams" in call_names
    assert call_names.isdisjoint(FORBIDDEN_IDENTIFIERS)
    vector_params_calls = [
        node
        for node in ast.walk(creator)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "VectorParams")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "VectorParams")
        )
    ]
    assert len(vector_params_calls) == 1
    vector_keywords = {
        keyword.arg: keyword.value for keyword in vector_params_calls[0].keywords if keyword.arg
    }
    assert set(vector_keywords) == {"size", "distance"}
    size = vector_keywords["size"]
    assert isinstance(size, ast.Attribute)
    assert isinstance(size.value, ast.Name)
    assert size.value.id == "config"
    assert size.attr == "vector_size"
    distance = vector_keywords["distance"]
    assert isinstance(distance, ast.Name)
    assert distance.id == "distance"
    create_calls = [
        node
        for node in ast.walk(creator)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_collection"
    ]
    assert len(create_calls) == 1
    create_keywords = {
        keyword.arg: keyword.value for keyword in create_calls[0].keywords if keyword.arg
    }
    assert set(create_keywords) == {"collection_name", "vectors_config"}
    collection_name = create_keywords["collection_name"]
    assert isinstance(collection_name, ast.Attribute)
    assert isinstance(collection_name.value, ast.Name)
    assert collection_name.value.id == "config"
    assert collection_name.attr == "collection_name"
    vectors_config = create_keywords["vectors_config"]
    assert vectors_config is vector_params_calls[0]


def test_creation_consumes_create_collection_result_and_fails_closed() -> None:
    functions = _module_functions(CREATION_MODULE)
    creator = functions[0]
    parents = _parents(creator)
    create_calls = [
        node
        for node in ast.walk(creator)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "create_collection"
    ]
    assert len(create_calls) == 1
    awaited = parents[create_calls[0]]
    assert isinstance(awaited, ast.Await)
    assignment = parents[awaited]
    assert isinstance(assignment, (ast.Assign, ast.AnnAssign))
    assert not isinstance(assignment, ast.Expr)
    target = assignment.targets[0] if isinstance(assignment, ast.Assign) else assignment.target
    assert isinstance(target, ast.Name)
    captured = target.id
    fail_closed: list[ast.If] = []
    for node in ast.walk(creator):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)):
            continue
        operand = test.operand
        if not (isinstance(operand, ast.Name) and operand.id == captured):
            continue
        if any(isinstance(child, ast.Raise) for child in node.body):
            fail_closed.append(node)
    assert len(fail_closed) == 1
    raises = [child for child in fail_closed[0].body if isinstance(child, ast.Raise)]
    assert len(raises) == 1
    exception = raises[0].exc
    assert isinstance(exception, ast.Call)
    func = exception.func
    assert isinstance(func, ast.Name)
    assert func.id == "DependencyUnavailableError"
    assert raises[0].cause is None


def test_creation_source_has_no_lookup_hardcoded_distance_or_retry() -> None:
    source = CREATION_MODULE.read_text(encoding="utf-8")
    for fragment in FORBIDDEN_SOURCE_FRAGMENTS:
        assert fragment not in source
    assert "VectorParams" in source
    assert "Distance" in source
    assert "create_collection" in source
    tree = ast.parse(source, filename=str(CREATION_MODULE))
    assert not any(isinstance(node, (ast.For, ast.While, ast.AsyncFor)) for node in ast.walk(tree))
    assert _distance_member_attrs(tree).isdisjoint(DISTANCE_MEMBERS)


def test_readiness_and_adapters_do_not_invoke_creation() -> None:
    readiness_names = imported_names(READINESS_MODULE)
    readiness_modules = imported_modules(READINESS_MODULE)
    readiness_source = READINESS_MODULE.read_text(encoding="utf-8")
    assert "create_qdrant_document_collection" not in readiness_names
    assert "collection_creation" not in readiness_modules
    assert "create_qdrant_document_collection" not in readiness_source
    assert "create_collection" not in readiness_source
    names = imported_names(DOCUMENT_VECTOR)
    modules = imported_modules(DOCUMENT_VECTOR)
    source = DOCUMENT_VECTOR.read_text(encoding="utf-8")
    assert "create_qdrant_document_collection" not in names
    assert "collection_creation" not in modules
    assert "create_qdrant_document_collection" not in source
    assert "create_collection" not in source
    client_source = CLIENT_MODULE.read_text(encoding="utf-8")
    assert "create_qdrant_document_collection" not in client_source
    assert "create_collection" not in client_source
    creation_source = CREATION_MODULE.read_text(encoding="utf-8")
    assert "verify_qdrant_document_collection_ready" not in creation_source
    assert "collection_readiness" not in imported_modules(CREATION_MODULE)


def test_creation_remains_unwired_from_runtime_and_http() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert "create_qdrant_document_collection" not in names
        assert "collection_creation" not in imported_modules(path)
        assert "create_qdrant_document_collection" not in source
