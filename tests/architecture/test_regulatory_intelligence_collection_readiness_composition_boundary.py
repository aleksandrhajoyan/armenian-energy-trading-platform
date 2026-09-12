"""Chunk 112 configured Regulatory collection readiness stays a narrow composition seam."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    REGULATORY_INTELLIGENCE_COLLECTION_READINESS_COMPOSITION_RELATIVE,
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
COMPOSITION_INIT = COMPOSITION_ROOT / "__init__.py"
BUILDER_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_collection_readiness.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

UNWIRED_RUNTIME_MODULES = (
    API_APP,
    GRAPH_MODULE,
    COMPOSITION_ROOT / "production_lifespan.py",
    COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py",
    COMPOSITION_ROOT / "regulatory_intelligence_loaded_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_configured_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_lifespan.py",
    COMPOSITION_ROOT / "document_vector_index_loaded_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_managed_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_configured_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_execution.py",
    COMPOSITION_ROOT / "document_vector_index_collection_ensure.py",
    COMPOSITION_ROOT / "pdf_document_extraction_index.py",
    COMPOSITION_ROOT / "pdf_document_extraction_index_execute.py",
    COMPOSITION_ROOT / "pdf_document_extraction_index_loaded_runtime.py",
    API_ROOT / "routers" / "document_vector_index.py",
    API_ROOT / "routers" / "regulatory_intelligence.py",
)

FORBIDDEN_PREFIXES = (
    "energy_trading.ml",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.settings",
    "energy_trading.shared.config.database",
    "energy_trading.shared.config.redis",
    "energy_trading.shared.config.document_vector_index",
    "energy_trading.infrastructure.openai",
    "energy_trading.infrastructure.embeddings",
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.infrastructure.vector_store.qdrant.client",
    "energy_trading.infrastructure.vector_store.qdrant.collection_creation",
    "energy_trading.infrastructure.vector_store.qdrant.collection_ensure",
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
    "openai",
    "pypdf",
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
        "QdrantDocumentVectorSearch",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "DocumentVectorIndexRuntimeSettings",
        "Distance",
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
        "RuntimeManager",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "qdrant_client",
        "energy_trading.api.composition.qdrant_document_vector_distance",
        "energy_trading.infrastructure.vector_store.qdrant.collection_readiness",
        "energy_trading.infrastructure.vector_store.qdrant.document_vector",
        "energy_trading.shared.config.qdrant",
        "energy_trading.shared.config.regulatory_intelligence",
    }
)

FORBIDDEN_CALL_NAMES = frozenset(
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
        "load_regulatory_intelligence_runtime_settings",
        "load_qdrant_document_vector_distance_settings",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "close",
        "aclose",
        "create_collection",
        "get_collection",
        "collection_exists",
        "create_qdrant_document_collection",
        "ensure_qdrant_document_collection_ready",
        "recreate_collection",
        "delete_collection",
        "update_collection",
        "upsert",
        "retrieve",
        "query_points",
        "include_router",
        "add_api_route",
        "build_regulatory_intelligence_configured_runtime",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "QdrantDocumentVectorSearch",
        "PdfTextExtractionAdapter",
        "sleep",
        "wait_for",
    }
)

DISTANCE_MEMBER_FRAGMENTS = (
    "Distance.COSINE",
    "Distance.DOT",
    "Distance.EUCLID",
    "Distance.MANHATTAN",
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


def _builder_function(path: Path) -> ast.AsyncFunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == (
            "verify_configured_regulatory_intelligence_collection_ready"
        ):
            return node
    msg = "verify_configured_regulatory_intelligence_collection_ready not found"
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
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative == REGULATORY_INTELLIGENCE_COLLECTION_READINESS_COMPOSITION_RELATIVE


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
    assert "AsyncQdrantClient" in names
    assert "RegulatoryIntelligenceRuntimeSettings" in names
    assert "QdrantDocumentVectorDistanceSettings" in names
    assert "QdrantDocumentVectorConfig" in names
    assert "map_qdrant_document_vector_distance" in names
    assert "verify_qdrant_document_collection_ready" in names
    assert "OpenAISettings" not in names
    assert "QdrantSettings" not in names
    assert "AppSettings" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    assert "load_qdrant_document_vector_distance_settings" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "create_qdrant_document_collection" not in names
    assert "ensure_qdrant_document_collection_ready" not in names
    assert "Distance" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_async_function() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == [
        "verify_configured_regulatory_intelligence_collection_ready"
    ]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in public)
    assert _module_class_names(BUILDER_MODULE) == []
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "verify_configured_regulatory_intelligence_collection_ready"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        REGULATORY_INTELLIGENCE_COLLECTION_READINESS_COMPOSITION_RELATIVE
    ]


def test_builder_signature_is_keyword_only_client_and_settings() -> None:
    builder = _builder_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "client",
        "runtime_settings",
        "distance_settings",
    )
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert builder.args.defaults == []
    assert all(default is None for default in builder.args.kw_defaults)
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {
        "client": "AsyncQdrantClient",
        "runtime_settings": "RegulatoryIntelligenceRuntimeSettings",
        "distance_settings": "QdrantDocumentVectorDistanceSettings",
    }
    assert ast.unparse(builder.returns) == "None"


def test_builder_constructs_one_config_maps_once_and_awaits_verify_once() -> None:
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
    forbidden_calls: list[str] = []
    for node in ast.walk(builder):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        if name in FORBIDDEN_CALL_NAMES:
            forbidden_calls.append(name)
        constructed.append(name)
    assert forbidden_calls == []
    assert constructed == [
        "QdrantDocumentVectorConfig",
        "map_qdrant_document_vector_distance",
        "verify_qdrant_document_collection_ready",
    ]
    awaits = [node for node in ast.walk(builder) if isinstance(node, ast.Await)]
    assert len(awaits) == 1
    assert isinstance(awaits[0].value, ast.Call)
    assert _call_name(awaits[0].value) == "verify_qdrant_document_collection_ready"
    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 2
    first, second = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "QdrantDocumentVectorConfig"
    first_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in first.value.keywords}
    assert first_keywords == {
        "collection_name": "runtime_settings.qdrant_collection_name",
        "vector_size": "runtime_settings.qdrant_vector_size",
    }
    assert isinstance(second, ast.Assign)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "map_qdrant_document_vector_distance"
    mapper_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in second.value.keywords}
    assert mapper_keywords == {
        "distance": "distance_settings.document_vector_distance",
    }
    verify_call = awaits[0].value
    verify_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in verify_call.keywords}
    assert verify_keywords == {
        "client": "client",
        "config": "qdrant_config",
        "distance": "distance",
    }
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    assert "AsyncQdrantClient(" not in source
    assert "create_qdrant_client" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_regulatory_intelligence_runtime_settings" not in source
    assert "load_qdrant_document_vector_distance_settings" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert ".env" not in source
    assert "create_qdrant_document_collection" not in source
    assert "ensure_qdrant_document_collection_ready" not in source
    assert "collection_exists" not in source
    assert "get_collection" not in source
    assert "close(" not in source
    assert "aclose(" not in source
    for fragment in DISTANCE_MEMBER_FRAGMENTS:
        assert fragment not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_composition_init_exports_the_configured_verify() -> None:
    names = imported_names(COMPOSITION_INIT)
    assert "verify_configured_regulatory_intelligence_collection_ready" in names
    source = COMPOSITION_INIT.read_text(encoding="utf-8")
    assert "verify_configured_regulatory_intelligence_collection_ready" in source
    assert "map_qdrant_document_vector_distance" not in names
    assert "verify_qdrant_document_collection_ready" not in names
    assert "ensure_qdrant_document_collection_ready" not in names


def test_application_and_domain_do_not_import_the_configured_verify() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.regulatory_intelligence_collection_readiness",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "verify_configured_regulatory_intelligence_collection_ready" not in names
        source = path.read_text(encoding="utf-8")
        assert "verify_configured_regulatory_intelligence_collection_ready" not in source


def test_http_create_app_and_runtimes_remain_unwired() -> None:
    forbidden_wiring = (
        "qdrant_client",
        "energy_trading.api.composition.regulatory_intelligence_collection_readiness",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    names = imported_names(API_APP)
    assert "verify_configured_regulatory_intelligence_collection_ready" not in names
    assert "AsyncQdrantClient" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    assert "verify_configured_regulatory_intelligence_collection_ready" not in app_source
    for path in UNWIRED_RUNTIME_MODULES:
        path_names = imported_names(path)
        assert "verify_configured_regulatory_intelligence_collection_ready" not in path_names
        modules = imported_modules(path)
        assert (
            "energy_trading.api.composition.regulatory_intelligence_collection_readiness"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "verify_configured_regulatory_intelligence_collection_ready" not in source
