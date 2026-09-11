"""Chunk 103 loaded PDF extraction-to-index runtime stays an outer composition."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
COMPOSITION_ROOT = API_ROOT / "composition"
BUILDER_MODULE = COMPOSITION_ROOT / "pdf_document_extraction_index_loaded_runtime.py"
PDF_COMPOSITION_MODULE = COMPOSITION_ROOT / "pdf_document_extraction_index.py"
LOADED_DOCUMENT_INDEX_MODULE = COMPOSITION_ROOT / "document_vector_index_loaded_runtime.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"
DOCUMENT_INDEX_ROUTER = API_ROOT / "routers" / "document_vector_index.py"
PRODUCTION_LIFESPAN = COMPOSITION_ROOT / "production_lifespan.py"
DOCUMENT_INDEX_LIFESPAN = COMPOSITION_ROOT / "document_vector_index_lifespan.py"
PDF_ADAPTER = (
    PRODUCTION_ROOT / "infrastructure" / "adapters" / "unstructured" / "pdf_text_extraction.py"
)

FORBIDDEN_PREFIXES = (
    "energy_trading.ml",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.shared.config",
    "energy_trading.infrastructure",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "sentence_transformers",
    "transformers",
    "redis",
    "qdrant_client",
    "qdrant",
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
    "pypdf",
    "pytesseract",
    "easyocr",
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
        "PdfTextExtractionAdapter",
        "DocumentVectorIndexExecutionService",
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

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "dict",
        "Mapping",
        "embed",
        "prepare",
        "execute",
        "extract",
        "index",
        "exists",
        "is_file",
        "create_app",
        "build_workflow_graph",
        "include_router",
        "add_api_route",
        "getenv",
        "environ",
        "get_settings",
        "AppSettings",
        "OpenAISettings",
        "QdrantSettings",
        "create_openai_client",
        "create_qdrant_client",
        "load_openai_settings",
        "load_qdrant_settings",
        "load_document_vector_index_runtime_settings",
        "PdfTextExtractionAdapter",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "SettingsRegistry",
        "Container",
        "clock",
        "ocr",
        "tesseract",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "collections.abc",
        "contextlib",
        "pathlib",
        "energy_trading.api.composition.document_vector_index_loaded_runtime",
        "energy_trading.api.composition.pdf_document_extraction_index",
        "energy_trading.application.orchestration.document_extraction_index_execution",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "embed",
        "prepare",
        "index",
        "execute",
        "extract",
        "exists",
        "is_file",
        "open",
        "stat",
        "getenv",
        "get_settings",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "create_openai_client",
        "create_qdrant_client",
        "create_collection",
        "include_router",
        "add_api_route",
        "load_openai_settings",
        "load_qdrant_settings",
        "load_document_vector_index_runtime_settings",
        "PdfTextExtractionAdapter",
        "DocumentVectorIndexExecutionService",
        "DocumentExtractionIndexExecutionService",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "QdrantDocumentVectorConfig",
        "OpenAISettings",
        "QdrantSettings",
        "DocumentVectorIndexRuntimeSettings",
        "managed_document_vector_index_runtime",
        "build_document_vector_index_execution",
        "build_document_vector_index_provider_runtime",
        "build_document_vector_index_configured_runtime",
        "build_document_vector_index_lifespan",
        "build_production_lifespan",
        "build_regulatory_intelligence_lifespan",
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

DOCUMENT_INDEX_RUNTIME_MODULES = (
    COMPOSITION_ROOT / "document_vector_index_execution.py",
    COMPOSITION_ROOT / "document_vector_index_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_configured_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_managed_runtime.py",
    LOADED_DOCUMENT_INDEX_MODULE,
    DOCUMENT_INDEX_LIFESPAN,
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
            "loaded_pdf_document_extraction_index_runtime"
        ):
            return node
    msg = "loaded_pdf_document_extraction_index_runtime not found"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _identifier_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
            names.update(param.name for param in node.type_params)
    return names


def test_runtime_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert BUILDER_MODULE.exists()
    assert COMPOSITION_ROOT.parent == API_ROOT


def test_runtime_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BUILDER_MODULE)
    assert "loaded_document_vector_index_runtime" in names
    assert "build_pdf_document_extraction_index_execution" in names
    assert "DocumentExtractionIndexExecutionService" in names
    assert "asynccontextmanager" in names
    assert "Path" in names
    assert "PdfTextExtractionAdapter" not in names
    assert "DocumentVectorIndexExecutionService" not in names
    assert "openai" not in names
    assert "qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "OpenAISettings" not in names
    assert "QdrantSettings" not in names
    assert "DocumentVectorIndexRuntimeSettings" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_document_vector_index_runtime_settings" not in names
    assert "FastAPI" not in names
    assert "APIRouter" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_runtime_exposes_exactly_one_public_async_context_manager() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["loaded_pdf_document_extraction_index_runtime"]
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
                and node.name == "loaded_pdf_document_extraction_index_runtime"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        "energy_trading/api/composition/pdf_document_extraction_index_loaded_runtime.py"
    ]


def test_runtime_signature_is_keyword_only_path_identities_and_env_file() -> None:
    builder = _loaded_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "path",
        "document_id",
        "source_name",
        "env_file",
    )
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {
        "path": "Path",
        "document_id": "str",
        "source_name": "str",
        "env_file": "str | Path | None",
    }
    assert builder.args.kw_defaults[0] is None
    assert builder.args.kw_defaults[1] is None
    assert builder.args.kw_defaults[2] is None
    assert ast.unparse(builder.args.kw_defaults[3]) == "'.env'"
    assert ast.unparse(builder.returns) == (
        "AsyncIterator[DocumentExtractionIndexExecutionService]"
    )


def test_runtime_delegates_once_to_loaded_index_runtime_and_chunk_102() -> None:
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
        "loaded_document_vector_index_runtime",
        "build_pdf_document_extraction_index_execution",
    ]
    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 1
    outer = statements[0]
    assert isinstance(outer, ast.AsyncWith)
    assert len(outer.items) == 1
    item = outer.items[0]
    assert isinstance(item.context_expr, ast.Call)
    assert _call_name(item.context_expr) == "loaded_document_vector_index_runtime"
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in item.context_expr.keywords}
    assert keywords == {"env_file": "env_file"}
    assert item.optional_vars is not None
    assert isinstance(item.optional_vars, ast.Name)
    assert item.optional_vars.id == "index_execution_service"
    inner = list(outer.body)
    assert len(inner) == 2
    assign, yield_stmt = inner
    assert isinstance(assign, ast.Assign)
    assert [ast.unparse(target) for target in assign.targets] == ["service"]
    assert isinstance(assign.value, ast.Call)
    assert _call_name(assign.value) == "build_pdf_document_extraction_index_execution"
    builder_keywords = {
        keyword.arg: ast.unparse(keyword.value) for keyword in assign.value.keywords
    }
    assert builder_keywords == {
        "path": "path",
        "document_id": "document_id",
        "source_name": "source_name",
        "index_execution_service": "index_execution_service",
    }
    assert assign.value.args == []
    assert isinstance(yield_stmt, ast.Expr)
    assert isinstance(yield_stmt.value, ast.Yield)
    assert ast.unparse(yield_stmt.value.value) == "service"
    identifiers = _identifier_names(BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "qdrant" not in lowered
    assert "openai" not in lowered
    assert "fastapi" not in lowered
    assert "starlette" not in lowered
    assert "numpy" not in lowered
    assert "redis" not in lowered
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "try:" not in source
    assert "except " not in source
    assert ".extract(" not in source
    assert ".execute(" not in source
    assert ".exists(" not in source
    assert ".open(" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert "PdfTextExtractionAdapter" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "load_openai_settings" not in source
    assert "load_qdrant_settings" not in source
    assert "load_document_vector_index_runtime_settings" not in source
    assert "AsyncExitStack" not in source
    assert "retry" not in lowered


def test_application_does_not_import_the_loaded_runtime() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "loaded_pdf_document_extraction_index_runtime" not in names
        source = path.read_text(encoding="utf-8")
        assert "loaded_pdf_document_extraction_index_runtime" not in source


def test_infrastructure_does_not_import_api_composition() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime",
    )
    assert collect_import_violations(INFRASTRUCTURE_ROOT, forbidden) == []
    names = imported_names(PDF_ADAPTER)
    assert "loaded_pdf_document_extraction_index_runtime" not in names
    modules = imported_modules(PDF_ADAPTER)
    assert (
        "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime" not in modules
    )


def test_http_create_app_does_not_invoke_the_loaded_runtime() -> None:
    forbidden_wiring = (
        "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime",
        "energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction",
        "energy_trading.application.orchestration.document_extraction_index_execution",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "loaded_pdf_document_extraction_index_runtime" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "loaded_pdf_document_extraction_index_runtime" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    names = imported_names(API_APP)
    assert "loaded_pdf_document_extraction_index_runtime" not in names
    assert "PdfTextExtractionAdapter" not in names
    assert "DocumentExtractionIndexExecutionService" not in names
    tree = ast.parse(app_source, filename=str(API_APP))
    create_app = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names: set[str] = set()
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "loaded_pdf_document_extraction_index_runtime" not in call_names
    assert "build_pdf_document_extraction_index_execution" not in call_names
    assert "PdfTextExtractionAdapter" not in call_names
    assert "DocumentExtractionIndexExecutionService" not in call_names
    assert "loaded_pdf_document_extraction_index_runtime" not in app_source


def test_production_lifespan_router_runtime_and_graph_remain_unwired() -> None:
    unwired = (
        GRAPH_MODULE,
        PRODUCTION_LIFESPAN,
        DOCUMENT_INDEX_ROUTER,
        DOCUMENT_INDEX_LIFESPAN,
        PDF_COMPOSITION_MODULE,
        *DOCUMENT_INDEX_RUNTIME_MODULES,
        *REGULATORY_COMPOSITION_MODULES,
    )
    for path in unwired:
        names = imported_names(path)
        assert "loaded_pdf_document_extraction_index_runtime" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "loaded_pdf_document_extraction_index_runtime" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api" not in graph_source
    lifespan_names = imported_names(PRODUCTION_LIFESPAN)
    assert "loaded_pdf_document_extraction_index_runtime" not in lifespan_names
    assert "PdfTextExtractionAdapter" not in lifespan_names
    assert "DocumentExtractionIndexExecutionService" not in lifespan_names
    router_names = imported_names(DOCUMENT_INDEX_ROUTER)
    assert "loaded_pdf_document_extraction_index_runtime" not in router_names
    assert "PdfTextExtractionAdapter" not in router_names
    assert "DocumentExtractionIndexExecutionService" not in router_names
    assert "loaded_pdf_document_extraction_index_runtime" not in PDF_COMPOSITION_MODULE.read_text(
        encoding="utf-8"
    )
    assert "loaded_pdf_document_extraction_index_runtime" not in (
        LOADED_DOCUMENT_INDEX_MODULE.read_text(encoding="utf-8")
    )
