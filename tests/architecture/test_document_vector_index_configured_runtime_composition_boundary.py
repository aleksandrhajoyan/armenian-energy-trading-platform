"""Chunk 89 configured document vector index composition stays an outer adapter layer."""

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
BUILDER_MODULE = COMPOSITION_ROOT / "document_vector_index_configured_runtime.py"
PROVIDER_RUNTIME_MODULE = COMPOSITION_ROOT / "document_vector_index_runtime.py"
NEUTRAL_BUILDER_MODULE = COMPOSITION_ROOT / "document_vector_index_execution.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"
EXTRACTION_PORT = PRODUCTION_ROOT / "application" / "ports" / "document_extraction.py"
OPENAI_DOCUMENT_EMBEDDING = (
    PRODUCTION_ROOT / "infrastructure" / "embeddings" / "openai_document_embedding.py"
)
QDRANT_INDEX = PRODUCTION_ROOT / "infrastructure" / "vector_store" / "qdrant" / "document_vector.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.ml",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.qdrant",
    "energy_trading.shared.config.settings",
    "energy_trading.shared.config.database",
    "energy_trading.shared.config.redis",
    "energy_trading.shared.config.regulatory_intelligence",
    "energy_trading.infrastructure.openai",
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
        "OpenAISettings",
        "QdrantSettings",
        "AppSettings",
        "FastAPI",
        "APIRouter",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
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
        "RuntimeSettings",
        "IndexingRegistry",
        "IndexingFactory",
        "DocumentIndexingPipeline",
        "CompositionRegistry",
        "ServiceLocator",
        "DependencyGraph",
        "SettingsRegistry",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "openai",
        "qdrant_client",
        "energy_trading.api.composition.document_vector_index_runtime",
        "energy_trading.application.orchestration.document_vector_index_execution",
        "energy_trading.infrastructure.vector_store.qdrant.document_vector",
        "energy_trading.shared.config.document_vector_index",
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
        "load_openai_settings",
        "create_openai_client",
        "load_qdrant_settings",
        "create_qdrant_client",
        "load_document_vector_index_runtime_settings",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "close",
        "aclose",
        "create_collection",
        "upsert",
        "retrieve",
        "include_router",
        "add_api_route",
        "build_document_vector_index_execution",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
    }
)

REGULATORY_COMPOSITION_MODULES = (
    COMPOSITION_ROOT / "regulatory_intelligence.py",
    COMPOSITION_ROOT / "regulatory_intelligence_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_configured_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_managed_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_loaded_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py",
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
        if isinstance(node, ast.FunctionDef) and node.name == (
            "build_document_vector_index_configured_runtime"
        ):
            return node
    msg = "build_document_vector_index_configured_runtime not found"
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
    assert "AsyncOpenAI" in names
    assert "AsyncQdrantClient" in names
    assert "DocumentVectorIndexRuntimeSettings" in names
    assert "QdrantDocumentVectorConfig" in names
    assert "build_document_vector_index_provider_runtime" in names
    assert "DocumentVectorIndexExecutionService" in names
    assert "OpenAISettings" not in names
    assert "QdrantSettings" not in names
    assert "AppSettings" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_document_vector_index_runtime_settings" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "OpenAIDocumentEmbeddingAdapter" not in names
    assert "QdrantDocumentVectorIndex" not in names
    assert "build_document_vector_index_execution" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_synchronous_function() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["build_document_vector_index_configured_runtime"]
    assert all(isinstance(node, ast.FunctionDef) for node in public)
    assert _module_class_names(BUILDER_MODULE) == []
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "build_document_vector_index_configured_runtime"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        "energy_trading/api/composition/document_vector_index_configured_runtime.py"
    ]


def test_builder_signature_is_keyword_only_clients_and_settings() -> None:
    builder = _builder_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "openai_client",
        "qdrant_client",
        "settings",
    )
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {
        "openai_client": "AsyncOpenAI",
        "qdrant_client": "AsyncQdrantClient",
        "settings": "DocumentVectorIndexRuntimeSettings",
    }
    assert ast.unparse(builder.returns) == "DocumentVectorIndexExecutionService"


def test_builder_constructs_one_qdrant_config_and_delegates_to_chunk_87() -> None:
    builder = _builder_function(BUILDER_MODULE)
    control = [
        type(node).__name__
        for node in ast.walk(builder)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
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
        "QdrantDocumentVectorConfig",
        "build_document_vector_index_provider_runtime",
    ]
    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 2
    first, second = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "QdrantDocumentVectorConfig"
    first_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in first.value.keywords}
    assert first_keywords == {
        "collection_name": "settings.qdrant_collection_name",
        "vector_size": "settings.qdrant_vector_size",
    }
    assert isinstance(second, ast.Return)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "build_document_vector_index_provider_runtime"
    return_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in second.value.keywords}
    assert return_keywords == {
        "openai_client": "openai_client",
        "qdrant_client": "qdrant_client",
        "qdrant_config": "qdrant_config",
        "document_embedding_model": "settings.document_embedding_model",
    }
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    assert "await " not in source
    assert "async def" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_document_vector_index_runtime_settings" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert ".env" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert ".execute(" not in source
    assert ".prepare(" not in source
    assert "create_collection" not in source
    assert "close(" not in source
    assert "aclose(" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_application_and_domain_do_not_import_the_configured_builder() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.document_vector_index_configured_runtime",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "build_document_vector_index_configured_runtime" not in names
        source = path.read_text(encoding="utf-8")
        assert "build_document_vector_index_configured_runtime" not in source


def test_http_create_app_does_not_invoke_the_configured_builder() -> None:
    forbidden_wiring = (
        "openai",
        "qdrant_client",
        "energy_trading.api.composition.document_vector_index_configured_runtime",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    names = imported_names(API_APP)
    assert "build_document_vector_index_configured_runtime" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "DocumentVectorIndexRuntimeSettings" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    assert "build_document_vector_index_configured_runtime" not in app_source
    assert (
        "build_document_vector_index_configured_runtime"
        not in PROVIDER_RUNTIME_MODULE.read_text(encoding="utf-8")
    )
    assert "build_document_vector_index_configured_runtime" not in NEUTRAL_BUILDER_MODULE.read_text(
        encoding="utf-8"
    )


def test_graph_extraction_and_adapters_remain_unwired_to_the_configured_builder() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "build_document_vector_index_configured_runtime" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "qdrant_client" not in modules
    assert "energy_trading.api.composition" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "build_document_vector_index_configured_runtime" not in source
    assert "energy_trading.api" not in source
    for path in (OPENAI_DOCUMENT_EMBEDDING, QDRANT_INDEX, EXTRACTION_PORT):
        path_names = imported_names(path)
        assert "build_document_vector_index_configured_runtime" not in path_names
        path_modules = imported_modules(path)
        assert (
            "energy_trading.api.composition.document_vector_index_configured_runtime"
            not in path_modules
        )


def test_regulatory_composition_remains_unwired_to_the_configured_builder() -> None:
    for path in REGULATORY_COMPOSITION_MODULES:
        names = imported_names(path)
        assert "build_document_vector_index_configured_runtime" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.api.composition.document_vector_index_configured_runtime" not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "build_document_vector_index_configured_runtime" not in source
        assert "OpenAIDocumentEmbeddingAdapter" not in source
        assert "QdrantDocumentVectorIndex" not in names
