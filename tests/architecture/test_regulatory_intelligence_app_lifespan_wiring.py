"""Chunk 77/82/94: create_app installs the composite lifespan and query router."""

from __future__ import annotations

import ast

from tests.architecture.import_inspection import (
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
HEALTH_ROUTER = API_ROOT / "routers" / "health.py"
COMPOSITION_ROOT = API_ROOT / "composition"
LIFESPAN_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py"
LOADED_RUNTIME_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_loaded_runtime.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_APP_PREFIXES = (
    "openai",
    "qdrant_client",
    "energy_trading.ml",
    "energy_trading.application",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.qdrant",
    "energy_trading.shared.config.regulatory_intelligence",
    "energy_trading.shared.config.document_vector_index",
    "energy_trading.infrastructure",
    "energy_trading.api.composition.regulatory_intelligence_lifespan",
    "energy_trading.api.composition.regulatory_intelligence_loaded_runtime",
    "energy_trading.api.composition.regulatory_intelligence_managed_runtime",
    "energy_trading.api.composition.regulatory_intelligence_configured_runtime",
    "energy_trading.api.composition.regulatory_intelligence_runtime",
    "energy_trading.api.composition.regulatory_intelligence",
    "energy_trading.api.composition.document_vector_index_lifespan",
    "energy_trading.api.composition.document_vector_index_loaded_runtime",
    "energy_trading.api.composition.document_vector_index_managed_runtime",
    "energy_trading.api.composition.document_vector_index_configured_runtime",
    "energy_trading.api.composition.document_vector_index_runtime",
    "energy_trading.api.composition.document_vector_index_execution",
    "langgraph",
    "langchain",
    "langchain_core",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "httpx",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "Container",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "SettingsRegistry",
        "ServiceRegistry",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
        "DocumentVectorIndexRuntimeSettings",
        "RegulatoryIntelligenceQueryExecutionService",
        "DocumentVectorIndexExecutionService",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIDocumentEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "QdrantDocumentVectorIndex",
        "QdrantDocumentVectorConfig",
    }
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

ALLOWED_APP_IMPORTS = frozenset(
    {
        "collections.abc",
        "contextlib",
        "fastapi",
        "energy_trading",
        "energy_trading.api.composition.production_lifespan",
        "energy_trading.api.exception_handlers",
        "energy_trading.api.middleware",
        "energy_trading.api.routers.health",
        "energy_trading.api.routers.regulatory_intelligence",
        "energy_trading.shared.config.settings",
        "energy_trading.shared.observability.logging",
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


def test_create_app_imports_production_lifespan_builder_only() -> None:
    leaked = sorted(
        module
        for module in imported_modules(API_APP)
        if is_forbidden(module, FORBIDDEN_APP_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(API_APP) - ALLOWED_APP_IMPORTS
    assert extras == set()
    names = imported_names(API_APP)
    assert "build_production_lifespan" in names
    assert "build_regulatory_intelligence_lifespan" not in names
    assert "build_document_vector_index_lifespan" not in names
    assert "FastAPI" in names
    assert "health_router" in names
    assert "regulatory_intelligence_router" in names
    assert "query_regulatory_intelligence" not in names
    assert "get_regulatory_intelligence_query_execution_service" not in names
    assert "RegulatoryIntelligenceQueryRequest" not in names
    assert "RegulatoryIntelligenceQueryResponse" not in names
    assert "loaded_regulatory_intelligence_runtime" not in names
    assert "managed_regulatory_intelligence_runtime" not in names
    assert "loaded_document_vector_index_runtime" not in names
    assert "managed_document_vector_index_runtime" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    assert "load_document_vector_index_runtime_settings" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "openai" not in names
    assert "qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names


def test_create_app_signature_has_narrow_lifespan_seam() -> None:
    create_app = _create_app_function()
    assert tuple(arg.arg for arg in create_app.args.args) == ("settings",)
    assert tuple(arg.arg for arg in create_app.args.kwonlyargs) == ("lifespan",)
    assert ast.unparse(create_app.args.kw_defaults[0]) == "None"
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in create_app.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {
        "lifespan": "Callable[[FastAPI], AbstractAsyncContextManager[None]] | None"
    }
    leaked_types = sorted(
        name for name in annotation_type_names(API_APP) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_production_default_installs_returned_lifespan_into_fastapi() -> None:
    create_app = _create_app_function()
    constructed: list[str] = []
    runtime_calls: list[str] = []
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        constructed.append(name)
        if name in {
            "loaded_regulatory_intelligence_runtime",
            "managed_regulatory_intelligence_runtime",
            "loaded_document_vector_index_runtime",
            "managed_document_vector_index_runtime",
            "load_openai_settings",
            "load_qdrant_settings",
            "load_regulatory_intelligence_runtime_settings",
            "load_document_vector_index_runtime_settings",
            "create_openai_client",
            "create_qdrant_client",
            "build_regulatory_intelligence_lifespan",
            "build_document_vector_index_lifespan",
            "execute",
            "embed_query",
            "embed",
            "index",
            "search",
            "infer",
            "run",
        }:
            runtime_calls.append(name)
    assert runtime_calls == []
    assert "build_production_lifespan" in constructed
    assert constructed.count("build_production_lifespan") == 1
    assert "build_regulatory_intelligence_lifespan" not in constructed
    assert "build_document_vector_index_lifespan" not in constructed
    assert constructed.count("FastAPI") == 1
    fastapi_call = next(
        node
        for node in ast.walk(create_app)
        if isinstance(node, ast.Call) and _call_name(node) == "FastAPI"
    )
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in fastapi_call.keywords}
    assert "lifespan" in keywords
    assert keywords["lifespan"] == "resolved_lifespan"
    builder_call = next(
        node
        for node in ast.walk(create_app)
        if isinstance(node, ast.Call) and _call_name(node) == "build_production_lifespan"
    )
    assert builder_call.args == []
    assert builder_call.keywords == []
    async_with_nodes = [node for node in ast.walk(create_app) if isinstance(node, ast.AsyncWith)]
    assert async_with_nodes == []
    source = API_APP.read_text(encoding="utf-8")
    assert "app.state" not in source
    assert "regulatory_intelligence_query_execution_service" not in source
    assert "document_vector_index_execution_service" not in source
    assert ".execute(" not in source
    assert ".index(" not in source
    assert ".embed(" not in source
    assert ".search(" not in source
    assert "global " not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []


def test_create_app_includes_regulatory_router_once_with_api_prefix() -> None:
    modules = imported_modules(API_APP)
    assert "energy_trading.api.routers.health" in modules
    assert "energy_trading.api.routers.regulatory_intelligence" in modules
    assert "energy_trading.api.dependencies.regulatory_intelligence" not in modules
    assert "energy_trading.api.schemas.regulatory_intelligence" not in modules
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
    ]
    source = API_APP.read_text(encoding="utf-8")
    assert "/regulatory-intelligence/query" not in source
    assert "/regulatory-intelligence" not in source
    assert ".execute(" not in source
    assert "app.state" not in source
    assert "regulatory_intelligence_query_execution_service" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_regulatory_intelligence_runtime_settings" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "langgraph" not in source.lower()
    assert "build_regulatory_intelligence_query_execution" not in source
    assert "build_regulatory_intelligence_provider_runtime" not in source
    assert "build_regulatory_intelligence_configured_runtime" not in source
    assert "managed_regulatory_intelligence_runtime" not in source
    assert "loaded_regulatory_intelligence_runtime" not in source
    assert "loaded_document_vector_index_runtime" not in source
    assert "managed_document_vector_index_runtime" not in source
    assert "build_regulatory_intelligence_lifespan" not in source
    assert "build_document_vector_index_lifespan" not in source


def test_health_router_and_http_routes_remain_service_free() -> None:
    forbidden = (
        "openai",
        "qdrant_client",
        "energy_trading.api.composition",
        "energy_trading.api.composition.regulatory_intelligence_lifespan",
        "energy_trading.api.composition.regulatory_intelligence_loaded_runtime",
    )
    assert collect_import_violations(API_ROOT / "routers", forbidden) == []
    health_names = imported_names(HEALTH_ROUTER)
    assert "build_regulatory_intelligence_lifespan" not in health_names
    assert "loaded_regulatory_intelligence_runtime" not in health_names
    assert "RegulatoryIntelligenceQueryExecutionService" not in health_names
    assert "get_regulatory_intelligence_query_execution_service" not in health_names
    assert "get_regulatory_intelligence_query_execution_service" not in imported_names(API_APP)
    health_source = HEALTH_ROUTER.read_text(encoding="utf-8")
    assert "app.state" not in health_source
    assert "regulatory_intelligence_query_execution_service" not in health_source
    assert (
        collect_http_api_import_violations(
            API_ROOT,
            (
                "openai",
                "qdrant_client",
                "energy_trading.api.composition.regulatory_intelligence_loaded_runtime",
            ),
        )
        == []
    )


def test_provider_sdk_allowlist_remains_the_existing_two_modules() -> None:
    assert REGULATORY_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/regulatory_intelligence_runtime.py",
        "energy_trading/api/composition/regulatory_intelligence_configured_runtime.py",
    )
    relative = API_APP.relative_to(SRC_ROOT).as_posix()
    assert relative not in REGULATORY_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(API_APP)
    assert "qdrant_client" not in imported_modules(API_APP)
    assert "openai" not in imported_modules(LIFESPAN_MODULE)
    assert "qdrant_client" not in imported_modules(LIFESPAN_MODULE)


def test_application_domain_ml_and_graph_remain_unwired() -> None:
    forbidden = (
        "energy_trading.api.app",
        "energy_trading.api.composition.regulatory_intelligence_lifespan",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    names = imported_names(GRAPH_MODULE)
    assert "create_app" not in names
    assert "build_production_lifespan" not in names
    assert "build_regulatory_intelligence_lifespan" not in names
    assert "build_document_vector_index_lifespan" not in names
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api" not in source
    assert "build_production_lifespan" not in source
    assert "build_regulatory_intelligence_lifespan" not in source
    assert "build_document_vector_index_lifespan" not in source
    assert "create_app" not in imported_names(LIFESPAN_MODULE)
    assert "create_app" not in imported_names(LOADED_RUNTIME_MODULE)
    assert "regulatory_intelligence_query_execution_service" not in source
