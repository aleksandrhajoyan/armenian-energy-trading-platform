"""Chunk 99: create_app installs the Document Vector Index indexing router."""

from __future__ import annotations

import ast

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
HEALTH_ROUTER = API_ROOT / "routers" / "health.py"
REGULATORY_ROUTER = API_ROOT / "routers" / "regulatory_intelligence.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"

FORBIDDEN_APP_PREFIXES = (
    "openai",
    "qdrant_client",
    "energy_trading.ml",
    "energy_trading.application",
    "energy_trading.infrastructure",
    "energy_trading.api.schemas.document_vector_index",
    "energy_trading.api.dependencies.document_vector_index",
    "energy_trading.application.orchestration.document_vector_index_execution",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.qdrant",
    "energy_trading.shared.config.document_vector_index",
    "energy_trading.api.composition.document_vector_index_lifespan",
    "energy_trading.api.composition.document_vector_index_loaded_runtime",
    "energy_trading.api.composition.document_vector_index_managed_runtime",
    "energy_trading.api.composition.document_vector_index_configured_runtime",
    "energy_trading.api.composition.document_vector_index_runtime",
    "energy_trading.api.composition.document_vector_index_execution",
    "langgraph",
    "langchain",
    "langchain_core",
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "Container",
        "ServiceRegistry",
        "ProviderRegistry",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "SettingsRegistry",
        "SettingsAggregator",
    }
)


def _create_app_function() -> ast.FunctionDef:
    tree = ast.parse(API_APP.read_text(encoding="utf-8"), filename=str(API_APP))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_create_app_imports_document_vector_index_router_only() -> None:
    leaked = sorted(
        module
        for module in imported_modules(API_APP)
        if is_forbidden(module, FORBIDDEN_APP_PREFIXES)
    )
    assert leaked == []
    modules = imported_modules(API_APP)
    assert "energy_trading.api.routers.document_vector_index" in modules
    assert "energy_trading.api.routers.health" in modules
    assert "energy_trading.api.routers.regulatory_intelligence" in modules
    assert "energy_trading.api.schemas.document_vector_index" not in modules
    assert "energy_trading.api.dependencies.document_vector_index" not in modules
    assert "energy_trading.application.orchestration.document_vector_index_execution" not in modules
    names = imported_names(API_APP)
    assert "document_vector_index_router" in names
    assert "health_router" in names
    assert "regulatory_intelligence_router" in names
    assert "index_document_vectors" not in names
    assert "get_document_vector_index_execution_service" not in names
    assert "DocumentVectorIndexRequest" not in names
    assert "DocumentVectorIndexChunkRequest" not in names
    assert "DocumentVectorIndexExecutionService" not in names
    assert "ExtractedDocumentChunk" not in names
    assert "build_document_vector_index_execution" not in names
    assert "build_document_vector_index_provider_runtime" not in names
    assert "build_document_vector_index_configured_runtime" not in names
    assert "managed_document_vector_index_runtime" not in names
    assert "loaded_document_vector_index_runtime" not in names
    assert "build_document_vector_index_lifespan" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_document_vector_index_runtime_settings" not in names
    assert "load_qdrant_document_vector_distance_settings" not in names
    assert "ensure_configured_document_vector_index_collection_ready" not in names
    assert "map_qdrant_document_vector_distance" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "openai" not in names
    assert "qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "OpenAIDocumentEmbeddingAdapter" not in names
    assert "QdrantDocumentVectorIndex" not in names


def test_create_app_includes_document_index_router_once_with_api_prefix() -> None:
    create_app = _create_app_function()
    included: list[tuple[str, dict[str, str]]] = []
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call) or _call_name(node) != "include_router":
            continue
        assert len(node.args) == 1
        assert isinstance(node.args[0], ast.Name)
        keywords: dict[str, str] = {}
        for keyword in node.keywords:
            assert keyword.arg is not None
            keywords[keyword.arg] = ast.unparse(keyword.value)
        included.append((node.args[0].id, keywords))
    assert included == [
        ("health_router", {"prefix": "resolved_settings.api_prefix"}),
        ("regulatory_intelligence_router", {"prefix": "resolved_settings.api_prefix"}),
        ("document_vector_index_router", {"prefix": "resolved_settings.api_prefix"}),
    ]
    source = API_APP.read_text(encoding="utf-8")
    assert "/document-vector-index/index" not in source
    assert "/document-vector-index" not in source
    assert ".execute(" not in source
    assert "app.state" not in source
    assert "document_vector_index_execution_service" not in source
    assert "ExtractedDocumentChunk" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_document_vector_index_runtime_settings" not in source
    assert "load_qdrant_document_vector_distance_settings" not in source
    assert "ensure_configured_document_vector_index_collection_ready" not in source
    assert "map_qdrant_document_vector_distance" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "langgraph" not in source.lower()
    assert "build_document_vector_index_execution" not in source
    assert "build_document_vector_index_provider_runtime" not in source
    assert "build_document_vector_index_configured_runtime" not in source
    assert "managed_document_vector_index_runtime" not in source
    assert "loaded_document_vector_index_runtime" not in source
    assert "build_document_vector_index_lifespan" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []


def test_health_and_regulatory_routers_remain_installed_and_index_unaware() -> None:
    names = imported_names(API_APP)
    assert "health_router" in names
    assert "regulatory_intelligence_router" in names
    health_source = HEALTH_ROUTER.read_text(encoding="utf-8")
    assert "get_document_vector_index_execution_service" not in health_source
    assert "index_document_vectors" not in health_source
    assert "document_vector_index_execution_service" not in health_source
    regulatory_source = REGULATORY_ROUTER.read_text(encoding="utf-8")
    assert "index_document_vectors" not in regulatory_source
    assert "get_document_vector_index_execution_service" not in regulatory_source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "document_vector_index_router" not in graph_source
    assert "index_document_vectors" not in graph_source
    assert "energy_trading.api" not in graph_source


def test_provider_sdk_allowlist_excludes_create_app() -> None:
    assert DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/document_vector_index_runtime.py",
        "energy_trading/api/composition/document_vector_index_configured_runtime.py",
    )
    relative = API_APP.relative_to(SRC_ROOT).as_posix()
    assert relative not in DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(API_APP)
    assert "qdrant_client" not in imported_modules(API_APP)
