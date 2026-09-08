"""Chunk 74 managed Regulatory runtime stays an outer lifecycle layer."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
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
BUILDER_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_managed_runtime.py"
CONFIGURED_RUNTIME_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_configured_runtime.py"
PROVIDER_RUNTIME_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_runtime.py"
NEUTRAL_BUILDER_MODULE = COMPOSITION_ROOT / "regulatory_intelligence.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_PREFIXES = (
    "openai",
    "qdrant_client",
    "energy_trading.ml",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.shared.config.settings",
    "energy_trading.shared.config.database",
    "energy_trading.shared.config.redis",
    "energy_trading.infrastructure.embeddings",
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "fastapi",
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
        "AppSettings",
        "FastAPI",
        "APIRouter",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "QdrantDocumentVectorConfig",
        "RegulatoryIntelligenceAgent",
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
        "SettingsRegistry",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "collections.abc",
        "contextlib",
        "energy_trading.api.composition.regulatory_intelligence_configured_runtime",
        "energy_trading.application.orchestration.regulatory_intelligence_query_execution",
        "energy_trading.infrastructure.openai.client",
        "energy_trading.infrastructure.vector_store.qdrant.client",
        "energy_trading.shared.config.openai",
        "energy_trading.shared.config.qdrant",
        "energy_trading.shared.config.regulatory_intelligence",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "embed_query",
        "prepare",
        "search",
        "infer",
        "run",
        "execute",
        "getenv",
        "get_settings",
        "load_openai_settings",
        "load_qdrant_settings",
        "load_regulatory_intelligence_runtime_settings",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "create_collection",
        "include_router",
        "add_api_route",
        "build_regulatory_intelligence_query_execution",
        "build_regulatory_intelligence_provider_runtime",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "QdrantDocumentVectorConfig",
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


def _managed_function(path: Path) -> ast.AsyncFunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == (
            "managed_regulatory_intelligence_runtime"
        ):
            return node
    msg = "managed_regulatory_intelligence_runtime not found"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


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
    assert "OpenAISettings" in names
    assert "QdrantSettings" in names
    assert "RegulatoryIntelligenceRuntimeSettings" in names
    assert "create_openai_client" in names
    assert "create_qdrant_client" in names
    assert "build_regulatory_intelligence_configured_runtime" in names
    assert "RegulatoryIntelligenceQueryExecutionService" in names
    assert "AsyncExitStack" in names
    assert "asynccontextmanager" in names
    assert "openai" not in names
    assert "qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in names
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
    assert "QdrantDocumentVectorSearch" not in names
    assert "QdrantDocumentVectorConfig" not in names
    assert "build_regulatory_intelligence_provider_runtime" not in names
    assert "build_regulatory_intelligence_query_execution" not in names
    assert "RegulatoryIntelligenceAgent" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_async_context_manager() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["managed_regulatory_intelligence_runtime"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in public)
    assert _module_class_names(BUILDER_MODULE) == []
    managed = _managed_function(BUILDER_MODULE)
    assert len(managed.decorator_list) == 1
    decorator = managed.decorator_list[0]
    assert isinstance(decorator, ast.Name)
    assert decorator.id == "asynccontextmanager"
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "managed_regulatory_intelligence_runtime"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        "energy_trading/api/composition/regulatory_intelligence_managed_runtime.py"
    ]


def test_builder_signature_is_keyword_only_settings() -> None:
    builder = _managed_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "openai_settings",
        "qdrant_settings",
        "regulatory_settings",
    )
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {
        "openai_settings": "OpenAISettings",
        "qdrant_settings": "QdrantSettings",
        "regulatory_settings": "RegulatoryIntelligenceRuntimeSettings",
    }
    assert ast.unparse(builder.returns) == (
        "AsyncIterator[RegulatoryIntelligenceQueryExecutionService]"
    )


def test_builder_registers_cleanup_then_delegates_to_chunk_73() -> None:
    builder = _managed_function(BUILDER_MODULE)
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
        "AsyncExitStack",
        "create_openai_client",
        "push_async_callback",
        "create_qdrant_client",
        "push_async_callback",
        "build_regulatory_intelligence_configured_runtime",
    ]
    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 1
    async_with = statements[0]
    assert isinstance(async_with, ast.AsyncWith)
    assert len(async_with.items) == 1
    item = async_with.items[0]
    assert isinstance(item.context_expr, ast.Call)
    assert _call_name(item.context_expr) == "AsyncExitStack"
    assert item.optional_vars is not None
    assert isinstance(item.optional_vars, ast.Name)
    assert item.optional_vars.id == "stack"
    inner = list(async_with.body)
    assert len(inner) == 6
    first, second, third, fourth, fifth, sixth = inner
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "create_openai_client"
    assert ast.unparse(first.value.args[0]) == "openai_settings"
    assert isinstance(second, ast.Expr)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "push_async_callback"
    assert ast.unparse(second.value.args[0]) == "openai_client.close"
    assert isinstance(third, ast.Assign)
    assert isinstance(third.value, ast.Call)
    assert _call_name(third.value) == "create_qdrant_client"
    assert ast.unparse(third.value.args[0]) == "qdrant_settings"
    assert isinstance(fourth, ast.Expr)
    assert isinstance(fourth.value, ast.Call)
    assert _call_name(fourth.value) == "push_async_callback"
    assert ast.unparse(fourth.value.args[0]) == "qdrant_client.close"
    assert isinstance(fifth, ast.Assign)
    assert isinstance(fifth.value, ast.Call)
    assert _call_name(fifth.value) == "build_regulatory_intelligence_configured_runtime"
    fifth_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in fifth.value.keywords}
    assert fifth_keywords == {
        "openai_client": "openai_client",
        "qdrant_client": "qdrant_client",
        "settings": "regulatory_settings",
    }
    assert isinstance(sixth, ast.Expr)
    assert isinstance(sixth.value, ast.Yield)
    assert ast.unparse(sixth.value.value) == "service"
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "create_openai_client" in source
    assert "create_qdrant_client" in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_regulatory_intelligence_runtime_settings" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert ".env" not in source
    assert ".embed_query(" not in source
    assert ".search(" not in source
    assert ".infer(" not in source
    assert ".execute(" not in source
    assert ".run(" not in source
    assert "create_collection" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_application_and_domain_do_not_import_the_managed_runtime() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.regulatory_intelligence_managed_runtime",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "managed_regulatory_intelligence_runtime" not in names
        source = path.read_text(encoding="utf-8")
        assert "managed_regulatory_intelligence_runtime" not in source


def test_http_create_app_does_not_invoke_the_managed_runtime() -> None:
    forbidden_wiring = (
        "openai",
        "qdrant_client",
        "energy_trading.api.composition.regulatory_intelligence_managed_runtime",
        "energy_trading.infrastructure.openai",
        "energy_trading.infrastructure.vector_store.qdrant.client",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    names = imported_names(API_APP)
    assert "managed_regulatory_intelligence_runtime" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    assert "managed_regulatory_intelligence_runtime" not in app_source
    assert "managed_regulatory_intelligence_runtime" not in CONFIGURED_RUNTIME_MODULE.read_text(
        encoding="utf-8"
    )
    assert "managed_regulatory_intelligence_runtime" not in PROVIDER_RUNTIME_MODULE.read_text(
        encoding="utf-8"
    )
    assert "managed_regulatory_intelligence_runtime" not in NEUTRAL_BUILDER_MODULE.read_text(
        encoding="utf-8"
    )


def test_graph_remains_unwired_to_the_managed_runtime() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "managed_regulatory_intelligence_runtime" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "qdrant_client" not in modules
    assert "energy_trading.api.composition" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "managed_regulatory_intelligence_runtime" not in source
    assert "energy_trading.api" not in source
