"""Chunk 93 production FastAPI lifespan composition remains the nesting seam."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
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
COMPOSITION_ROOT = API_ROOT / "composition"
BUILDER_MODULE = COMPOSITION_ROOT / "production_lifespan.py"
REGULATORY_LIFESPAN_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py"
DOCUMENT_INDEX_LIFESPAN_MODULE = COMPOSITION_ROOT / "document_vector_index_lifespan.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_PREFIXES = (
    "openai",
    "qdrant_client",
    "energy_trading.ml",
    "energy_trading.application",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.shared.config.settings",
    "energy_trading.shared.config.database",
    "energy_trading.shared.config.redis",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.qdrant",
    "energy_trading.shared.config.document_vector_index",
    "energy_trading.shared.config.regulatory_intelligence",
    "energy_trading.infrastructure",
    "energy_trading.infrastructure.openai",
    "energy_trading.infrastructure.embeddings",
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.vector_store",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.api.composition.document_vector_index_loaded_runtime",
    "energy_trading.api.composition.document_vector_index_configured_runtime",
    "energy_trading.api.composition.document_vector_index_managed_runtime",
    "energy_trading.api.composition.document_vector_index_collection_ensure",
    "energy_trading.api.composition.document_vector_index_runtime",
    "energy_trading.api.composition.document_vector_index_execution",
    "energy_trading.api.composition.regulatory_intelligence_loaded_runtime",
    "energy_trading.api.composition.regulatory_intelligence_configured_runtime",
    "energy_trading.api.composition.regulatory_intelligence_managed_runtime",
    "energy_trading.api.composition.regulatory_intelligence_runtime",
    "energy_trading.api.composition.regulatory_intelligence",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "sentence_transformers",
    "transformers",
    "redis",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "httpx",
    "requests",
    "aiohttp",
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
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "LLMPort",
        "EmbeddingPort",
        "ProviderRegistry",
        "Container",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "LifespanRegistry",
        "SettingsRegistry",
        "AppSettings",
        "APIRouter",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "QdrantDocumentVectorConfig",
        "DocumentVectorIndexExecutionService",
        "RegulatoryIntelligenceQueryExecutionService",
        "OpenAISettings",
        "QdrantSettings",
        "DocumentVectorIndexRuntimeSettings",
        "RegulatoryIntelligenceRuntimeSettings",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "LLMPort",
        "EmbeddingPort",
        "ProviderRegistry",
        "ServiceRegistry",
        "AgentFactory",
        "Container",
        "LiteLLM",
        "RAGPort",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "LifespanRegistry",
        "SettingsRegistry",
        "SettingsAggregator",
        "compose_lifespans",
        "compose_lifespan",
        "LifespanComposer",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "collections.abc",
        "contextlib",
        "pathlib",
        "fastapi",
        "energy_trading.api.composition.document_vector_index_lifespan",
        "energy_trading.api.composition.regulatory_intelligence_lifespan",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "embed",
        "embed_query",
        "prepare",
        "index",
        "search",
        "infer",
        "run",
        "execute",
        "getenv",
        "get_settings",
        "load_openai_settings",
        "load_qdrant_settings",
        "load_document_vector_index_runtime_settings",
        "load_qdrant_document_vector_distance_settings",
        "load_regulatory_intelligence_runtime_settings",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "create_openai_client",
        "create_qdrant_client",
        "create_collection",
        "include_router",
        "add_api_route",
        "setattr",
        "delattr",
        "compose_lifespans",
        "loaded_document_vector_index_runtime",
        "loaded_regulatory_intelligence_runtime",
        "managed_document_vector_index_runtime",
        "managed_regulatory_intelligence_runtime",
        "build_document_vector_index_execution",
        "build_document_vector_index_provider_runtime",
        "build_document_vector_index_configured_runtime",
        "build_regulatory_intelligence_query_execution",
        "build_regulatory_intelligence_provider_runtime",
        "build_regulatory_intelligence_configured_runtime",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "QdrantDocumentVectorConfig",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "OpenAISettings",
        "QdrantSettings",
        "DocumentVectorIndexRuntimeSettings",
        "RegulatoryIntelligenceRuntimeSettings",
        "ensure_configured_document_vector_index_collection_ready",
        "map_qdrant_document_vector_distance",
    }
)


def _module_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _builder_function(path: Path) -> ast.FunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.FunctionDef) and node.name == "build_production_lifespan":
            return node
    msg = "build_production_lifespan not found"
    raise AssertionError(msg)


def _nested_lifespan(builder: ast.FunctionDef) -> ast.AsyncFunctionDef:
    nested = [node for node in builder.body if isinstance(node, ast.AsyncFunctionDef)]
    if len(nested) != 1 or nested[0].name != "lifespan":
        msg = "expected exactly one nested lifespan callback"
        raise AssertionError(msg)
    return nested[0]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _create_app_function() -> ast.FunctionDef:
    tree = ast.parse(API_APP.read_text(encoding="utf-8"), filename=str(API_APP))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert BUILDER_MODULE.exists()
    assert COMPOSITION_ROOT.parent == API_ROOT


def test_builder_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BUILDER_MODULE)
    assert "FastAPI" in names
    assert "build_regulatory_intelligence_lifespan" in names
    assert "build_document_vector_index_lifespan" in names
    assert "asynccontextmanager" in names
    assert "Path" in names
    assert "loaded_regulatory_intelligence_runtime" not in names
    assert "loaded_document_vector_index_runtime" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    assert "load_document_vector_index_runtime_settings" not in names
    assert "load_qdrant_document_vector_distance_settings" not in names
    assert "ensure_configured_document_vector_index_collection_ready" not in names
    assert "map_qdrant_document_vector_distance" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "compose_lifespans" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_sync_factory() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["build_production_lifespan"]
    assert isinstance(public[0], ast.FunctionDef)
    assert not isinstance(public[0], ast.AsyncFunctionDef)
    assert _module_class_names(BUILDER_MODULE) == []
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.FunctionDef) and node.name == "build_production_lifespan":
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == ["energy_trading/api/composition/production_lifespan.py"]


def test_builder_returns_fastapi_compatible_async_lifespan_callback() -> None:
    builder = _builder_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == ("env_file",)
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {"env_file": "str | Path | None"}
    assert ast.unparse(builder.args.kw_defaults[0]) == "'.env'"
    assert ast.unparse(builder.returns) == (
        "Callable[[FastAPI], AbstractAsyncContextManager[None]]"
    )
    lifespan = _nested_lifespan(builder)
    assert len(lifespan.decorator_list) == 1
    decorator = lifespan.decorator_list[0]
    assert isinstance(decorator, ast.Name)
    assert decorator.id == "asynccontextmanager"
    assert tuple(arg.arg for arg in lifespan.args.args) == ("app",)
    assert ast.unparse(lifespan.args.args[0].annotation) == "FastAPI"
    assert ast.unparse(lifespan.returns) == "AsyncIterator[None]"
    statements = [
        node
        for node in builder.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
    ]
    assert [type(node).__name__ for node in statements] == [
        "Assign",
        "Assign",
        "AsyncFunctionDef",
        "Return",
    ]
    returned = statements[3]
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Name)
    assert returned.value.id == "lifespan"


def test_factory_calls_each_child_builder_once_and_forwards_env_file() -> None:
    builder = _builder_function(BUILDER_MODULE)
    outer_calls: list[ast.Call] = []
    for statement in builder.body:
        if isinstance(statement, ast.AsyncFunctionDef):
            continue
        for node in ast.walk(statement):
            if isinstance(node, ast.Call):
                outer_calls.append(node)
    assert [_call_name(node) for node in outer_calls] == [
        "build_regulatory_intelligence_lifespan",
        "build_document_vector_index_lifespan",
    ]
    assignments = [node for node in builder.body if isinstance(node, ast.Assign)]
    assert len(assignments) == 2
    first_target = assignments[0].targets[0]
    second_target = assignments[1].targets[0]
    assert isinstance(first_target, ast.Name)
    assert first_target.id == "regulatory_lifespan"
    assert isinstance(second_target, ast.Name)
    assert second_target.id == "document_vector_index_lifespan"
    for call in outer_calls:
        assert call.args == []
        keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords}
        assert keywords == {"env_file": "env_file"}


def test_nested_lifespan_nests_regulatory_outer_document_index_inner() -> None:
    builder = _builder_function(BUILDER_MODULE)
    lifespan = _nested_lifespan(builder)
    control = [
        type(node).__name__
        for node in ast.walk(builder)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(builder) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    constructed: list[str] = []
    runtime_calls: list[str] = []
    for node in ast.walk(builder):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        if name in RUNTIME_CALL_NAMES:
            runtime_calls.append(name)
        constructed.append(name)
    assert runtime_calls == []
    assert constructed == [
        "build_regulatory_intelligence_lifespan",
        "build_document_vector_index_lifespan",
        "regulatory_lifespan",
        "document_vector_index_lifespan",
    ]
    statements = [node for node in lifespan.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 1
    outer = statements[0]
    assert isinstance(outer, ast.AsyncWith)
    assert len(outer.items) == 1
    outer_item = outer.items[0]
    assert isinstance(outer_item.context_expr, ast.Call)
    assert _call_name(outer_item.context_expr) == "regulatory_lifespan"
    assert len(outer_item.context_expr.args) == 1
    assert isinstance(outer_item.context_expr.args[0], ast.Name)
    assert outer_item.context_expr.args[0].id == "app"
    assert outer_item.optional_vars is None
    inner_statements = [node for node in outer.body if not isinstance(node, ast.Expr)]
    assert len(inner_statements) == 1
    inner = inner_statements[0]
    assert isinstance(inner, ast.AsyncWith)
    assert len(inner.items) == 1
    inner_item = inner.items[0]
    assert isinstance(inner_item.context_expr, ast.Call)
    assert _call_name(inner_item.context_expr) == "document_vector_index_lifespan"
    assert len(inner_item.context_expr.args) == 1
    assert isinstance(inner_item.context_expr.args[0], ast.Name)
    assert inner_item.context_expr.args[0].id == "app"
    assert inner_item.context_expr.args[0].id == outer_item.context_expr.args[0].id
    assert inner_item.optional_vars is None
    yields = [node for node in inner.body if isinstance(node, ast.Expr)]
    assert len(yields) == 1
    assert isinstance(yields[0].value, ast.Yield)
    assert yields[0].value.value is None
    yield_nodes = [node for node in ast.walk(builder) if isinstance(node, ast.Yield)]
    assert len(yield_nodes) == 1


def test_composite_does_not_assign_state_or_invoke_providers() -> None:
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    assert "app.state" not in source
    assert "regulatory_intelligence_query_execution_service" not in source
    assert "document_vector_index_execution_service" not in source
    assert "request.state" not in source
    assert "dependency_overrides" not in source
    assert "global " not in source
    assert "OpenAISettings(" not in source
    assert "QdrantSettings(" not in source
    assert "DocumentVectorIndexRuntimeSettings(" not in source
    assert "RegulatoryIntelligenceRuntimeSettings(" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "dotenv" not in source
    assert ".embed(" not in source
    assert ".embed_query(" not in source
    assert ".index(" not in source
    assert ".execute(" not in source
    assert ".search(" not in source
    assert ".infer(" not in source
    assert ".prepare(" not in source
    assert "create_collection" not in source
    assert "compose_lifespans" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_provider_sdk_allowlist_remains_the_existing_modules() -> None:
    assert REGULATORY_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/regulatory_intelligence_runtime.py",
        "energy_trading/api/composition/regulatory_intelligence_configured_runtime.py",
    )
    assert DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/document_vector_index_runtime.py",
        "energy_trading/api/composition/document_vector_index_configured_runtime.py",
    )
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in REGULATORY_PROVIDER_COMPOSITION_RELATIVES
    assert relative not in DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(BUILDER_MODULE)
    assert "qdrant_client" not in imported_modules(BUILDER_MODULE)
    assert "openai" not in imported_modules(REGULATORY_LIFESPAN_MODULE)
    assert "qdrant_client" not in imported_modules(REGULATORY_LIFESPAN_MODULE)
    assert "openai" not in imported_modules(DOCUMENT_INDEX_LIFESPAN_MODULE)
    assert "qdrant_client" not in imported_modules(DOCUMENT_INDEX_LIFESPAN_MODULE)


def test_application_and_domain_do_not_import_the_production_lifespan() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.production_lifespan",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "build_production_lifespan" not in names
        source = path.read_text(encoding="utf-8")
        assert "build_production_lifespan" not in source


def test_create_app_installs_production_lifespan_without_child_factories() -> None:
    forbidden_wiring = (
        "openai",
        "qdrant_client",
        "energy_trading.api.composition.document_vector_index_lifespan",
        "energy_trading.api.composition.regulatory_intelligence_lifespan",
        "energy_trading.api.composition.document_vector_index_loaded_runtime",
        "energy_trading.infrastructure.openai",
        "energy_trading.infrastructure.vector_store.qdrant.client",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    names = imported_names(API_APP)
    assert "build_production_lifespan" in names
    assert "build_document_vector_index_lifespan" not in names
    assert "build_regulatory_intelligence_lifespan" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    assert "build_production_lifespan" in app_source
    assert "build_document_vector_index_lifespan" not in app_source
    assert "build_regulatory_intelligence_lifespan" not in app_source
    create_app = _create_app_function()
    constructed: list[str] = []
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is not None:
            constructed.append(name)
    assert constructed.count("build_production_lifespan") == 1
    assert "build_regulatory_intelligence_lifespan" not in constructed
    assert "build_document_vector_index_lifespan" not in constructed
    builder_call = next(
        node
        for node in ast.walk(create_app)
        if isinstance(node, ast.Call) and _call_name(node) == "build_production_lifespan"
    )
    assert builder_call.args == []
    assert builder_call.keywords == []
    async_with_nodes = [node for node in ast.walk(create_app) if isinstance(node, ast.AsyncWith)]
    assert async_with_nodes == []
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call) or _call_name(node) != "FastAPI":
            continue
        for keyword in node.keywords:
            if keyword.arg != "lifespan":
                continue
            assert ast.unparse(keyword.value) == "resolved_lifespan"
            assert "document_vector_index" not in ast.unparse(keyword.value)
            assert "regulatory_intelligence" not in ast.unparse(keyword.value)
    for path in sorted((API_ROOT / "routers").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "build_production_lifespan" not in source
        assert "build_document_vector_index_lifespan" not in source
        assert "build_regulatory_intelligence_lifespan" not in source


def test_graph_remains_unwired_to_the_production_lifespan() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "build_production_lifespan" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "qdrant_client" not in modules
    assert "energy_trading.api.composition" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "build_production_lifespan" not in source
    assert "energy_trading.api" not in source
