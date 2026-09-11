"""Chunk 91 loaded document vector index runtime stays a settings-loading outer layer."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
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
BUILDER_MODULE = COMPOSITION_ROOT / "document_vector_index_loaded_runtime.py"
MANAGED_RUNTIME_MODULE = COMPOSITION_ROOT / "document_vector_index_managed_runtime.py"
CONFIGURED_RUNTIME_MODULE = COMPOSITION_ROOT / "document_vector_index_configured_runtime.py"
PROVIDER_RUNTIME_MODULE = COMPOSITION_ROOT / "document_vector_index_runtime.py"
NEUTRAL_BUILDER_MODULE = COMPOSITION_ROOT / "document_vector_index_execution.py"
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
    "energy_trading.shared.config.regulatory_intelligence",
    "energy_trading.infrastructure.openai",
    "energy_trading.infrastructure.embeddings",
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.vector_store",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.api.composition.document_vector_index_configured_runtime",
    "energy_trading.api.composition.document_vector_index_runtime",
    "energy_trading.api.composition.document_vector_index_execution",
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
        "SettingsRegistry",
        "AppSettings",
        "FastAPI",
        "APIRouter",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "QdrantDocumentVectorConfig",
        "OpenAISettings",
        "QdrantSettings",
        "DocumentVectorIndexRuntimeSettings",
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
        "SettingsAggregator",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "collections.abc",
        "contextlib",
        "pathlib",
        "energy_trading.api.composition.document_vector_index_managed_runtime",
        "energy_trading.application.orchestration.document_vector_index_execution",
        "energy_trading.shared.config.document_vector_index",
        "energy_trading.shared.config.openai",
        "energy_trading.shared.config.qdrant",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "embed",
        "prepare",
        "index",
        "execute",
        "getenv",
        "get_settings",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "create_openai_client",
        "create_qdrant_client",
        "create_collection",
        "include_router",
        "add_api_route",
        "build_document_vector_index_execution",
        "build_document_vector_index_provider_runtime",
        "build_document_vector_index_configured_runtime",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "QdrantDocumentVectorConfig",
        "OpenAISettings",
        "QdrantSettings",
        "DocumentVectorIndexRuntimeSettings",
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


def _loaded_function(path: Path) -> ast.AsyncFunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == (
            "loaded_document_vector_index_runtime"
        ):
            return node
    msg = "loaded_document_vector_index_runtime not found"
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
    assert "load_openai_settings" in names
    assert "load_qdrant_settings" in names
    assert "load_document_vector_index_runtime_settings" in names
    assert "managed_document_vector_index_runtime" in names
    assert "DocumentVectorIndexExecutionService" in names
    assert "asynccontextmanager" in names
    assert "Path" in names
    assert "openai" not in names
    assert "qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "OpenAISettings" not in names
    assert "QdrantSettings" not in names
    assert "DocumentVectorIndexRuntimeSettings" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "OpenAIDocumentEmbeddingAdapter" not in names
    assert "QdrantDocumentVectorIndex" not in names
    assert "QdrantDocumentVectorConfig" not in names
    assert "build_document_vector_index_configured_runtime" not in names
    assert "build_document_vector_index_provider_runtime" not in names
    assert "build_document_vector_index_execution" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_async_context_manager() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["loaded_document_vector_index_runtime"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in public)
    assert _module_class_names(BUILDER_MODULE) == []
    loaded = _loaded_function(BUILDER_MODULE)
    assert len(loaded.decorator_list) == 1
    decorator = loaded.decorator_list[0]
    assert isinstance(decorator, ast.Name)
    assert decorator.id == "asynccontextmanager"
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "loaded_document_vector_index_runtime"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        "energy_trading/api/composition/document_vector_index_loaded_runtime.py"
    ]


def test_builder_signature_is_keyword_only_env_file() -> None:
    builder = _loaded_function(BUILDER_MODULE)
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
    assert ast.unparse(builder.returns) == ("AsyncIterator[DocumentVectorIndexExecutionService]")


def test_builder_loads_settings_then_delegates_to_chunk_90() -> None:
    builder = _loaded_function(BUILDER_MODULE)
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
        "load_openai_settings",
        "load_qdrant_settings",
        "load_document_vector_index_runtime_settings",
        "managed_document_vector_index_runtime",
    ]
    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 4
    first, second, third, fourth = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "load_openai_settings"
    assert {keyword.arg: ast.unparse(keyword.value) for keyword in first.value.keywords} == {
        "env_file": "env_file"
    }
    assert isinstance(second, ast.Assign)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "load_qdrant_settings"
    assert {keyword.arg: ast.unparse(keyword.value) for keyword in second.value.keywords} == {
        "env_file": "env_file"
    }
    assert isinstance(third, ast.Assign)
    assert isinstance(third.value, ast.Call)
    assert _call_name(third.value) == "load_document_vector_index_runtime_settings"
    assert {keyword.arg: ast.unparse(keyword.value) for keyword in third.value.keywords} == {
        "env_file": "env_file"
    }
    assert isinstance(fourth, ast.AsyncWith)
    assert len(fourth.items) == 1
    item = fourth.items[0]
    assert isinstance(item.context_expr, ast.Call)
    assert _call_name(item.context_expr) == "managed_document_vector_index_runtime"
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in item.context_expr.keywords}
    assert keywords == {
        "openai_settings": "openai_settings",
        "qdrant_settings": "qdrant_settings",
        "document_vector_index_settings": "document_vector_index_settings",
    }
    assert item.optional_vars is not None
    assert isinstance(item.optional_vars, ast.Name)
    assert item.optional_vars.id == "service"
    inner = list(fourth.body)
    assert len(inner) == 1
    assert isinstance(inner[0], ast.Expr)
    assert isinstance(inner[0].value, ast.Yield)
    assert ast.unparse(inner[0].value.value) == "service"
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    assert "OpenAISettings(" not in source
    assert "QdrantSettings(" not in source
    assert "DocumentVectorIndexRuntimeSettings(" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "dotenv" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert ".execute(" not in source
    assert ".prepare(" not in source
    assert "create_collection" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_provider_sdk_allowlist_remains_the_existing_document_index_modules() -> None:
    assert DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/document_vector_index_runtime.py",
        "energy_trading/api/composition/document_vector_index_configured_runtime.py",
    )
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(BUILDER_MODULE)
    assert "qdrant_client" not in imported_modules(BUILDER_MODULE)
    assert "openai" in imported_modules(PROVIDER_RUNTIME_MODULE)
    assert "openai" in imported_modules(CONFIGURED_RUNTIME_MODULE)
    assert "qdrant_client" in imported_modules(PROVIDER_RUNTIME_MODULE)
    assert "qdrant_client" in imported_modules(CONFIGURED_RUNTIME_MODULE)
    assert "openai" not in imported_modules(MANAGED_RUNTIME_MODULE)
    assert "qdrant_client" not in imported_modules(MANAGED_RUNTIME_MODULE)


def test_application_and_domain_do_not_import_the_loaded_runtime() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.document_vector_index_loaded_runtime",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "loaded_document_vector_index_runtime" not in names
        source = path.read_text(encoding="utf-8")
        assert "loaded_document_vector_index_runtime" not in source


def test_http_create_app_does_not_invoke_the_loaded_runtime() -> None:
    forbidden_wiring = (
        "openai",
        "qdrant_client",
        "energy_trading.api.composition.document_vector_index_loaded_runtime",
        "energy_trading.infrastructure.openai",
        "energy_trading.infrastructure.vector_store.qdrant.client",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    names = imported_names(API_APP)
    assert "loaded_document_vector_index_runtime" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_document_vector_index_runtime_settings" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    assert "loaded_document_vector_index_runtime" not in app_source
    assert "loaded_document_vector_index_runtime" not in MANAGED_RUNTIME_MODULE.read_text(
        encoding="utf-8"
    )
    assert "loaded_document_vector_index_runtime" not in CONFIGURED_RUNTIME_MODULE.read_text(
        encoding="utf-8"
    )
    assert "loaded_document_vector_index_runtime" not in PROVIDER_RUNTIME_MODULE.read_text(
        encoding="utf-8"
    )
    assert "loaded_document_vector_index_runtime" not in NEUTRAL_BUILDER_MODULE.read_text(
        encoding="utf-8"
    )


def test_graph_remains_unwired_to_the_loaded_runtime() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "loaded_document_vector_index_runtime" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "qdrant_client" not in modules
    assert "energy_trading.api.composition" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "loaded_document_vector_index_runtime" not in source
    assert "energy_trading.api" not in source
