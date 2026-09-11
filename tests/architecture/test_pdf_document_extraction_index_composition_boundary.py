"""Chunk 102 PDF extraction-to-index composition stays an outer builder."""

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
BUILDER_MODULE = COMPOSITION_ROOT / "pdf_document_extraction_index.py"
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
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.shared.config",
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
        "MutableMapping",
        "TypedDict",
        "LLMPort",
        "EmbeddingPort",
        "AIProviderPort",
        "ProviderRegistry",
        "Container",
        "OpenAISettings",
        "QdrantSettings",
        "AppSettings",
        "DocumentVectorIndexRuntimeSettings",
        "RegulatoryIntelligenceRuntimeSettings",
        "FastAPI",
        "APIRouter",
        "Request",
        "Response",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "QdrantDocumentVectorSearch",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "PdfReader",
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
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "AgentRegistry",
        "RagPipeline",
        "Container",
        "Registry",
        "factory",
        "registry",
        "container",
        "resolve",
        "get_service",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "clock",
        "ocr",
        "tesseract",
    }
)

GENERIC_FRAMEWORK_CLASS_NAMES = frozenset(
    {
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "GenericEmbeddingPort",
        "RagPipeline",
        "QueryPipeline",
        "GenericEmbeddingService",
        "AgentRegistry",
        "AgentExecutor",
        "GenericUseCase",
        "Container",
        "ServiceContainer",
        "DependencyContainer",
        "DIContainer",
        "Registry",
        "ServiceRegistry",
        "AgentFactory",
        "ServiceFactory",
        "ProviderFactory",
        "DocumentIndexingPipeline",
        "IndexingPipeline",
        "IndexingFactory",
        "IndexingRegistry",
        "DocumentPipeline",
        "ParserRegistry",
        "DocumentSourceRegistry",
        "CompositionRegistry",
        "ServiceLocator",
        "DependencyGraph",
        "LifecycleManager",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "pathlib",
        "energy_trading.application.orchestration.document_extraction_index_execution",
        "energy_trading.application.orchestration.document_vector_index_execution",
        "energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "path": "Path",
    "document_id": "str",
    "source_name": "str",
    "index_execution_service": "DocumentVectorIndexExecutionService",
}

RUNTIME_CALL_NAMES = frozenset(
    {
        "extract",
        "execute",
        "embed",
        "prepare",
        "index",
        "exists",
        "is_file",
        "open",
        "stat",
        "getenv",
        "get_settings",
        "include_router",
        "add_api_route",
        "create_openai_client",
        "create_qdrant_client",
        "load_openai_settings",
        "load_qdrant_settings",
        "load_document_vector_index_runtime_settings",
        "AsyncOpenAI",
        "PdfReader",
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
    COMPOSITION_ROOT / "document_vector_index_loaded_runtime.py",
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


def _builder_function(path: Path) -> ast.FunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.FunctionDef) and node.name == (
            "build_pdf_document_extraction_index_execution"
        ):
            return node
    msg = "build_pdf_document_extraction_index_execution not found"
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


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert BUILDER_MODULE.exists()
    assert COMPOSITION_ROOT.parent == API_ROOT


def test_builder_imports_only_approved_pdf_and_application_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BUILDER_MODULE)
    assert "Path" in names
    assert "DocumentExtractionIndexExecutionService" in names
    assert "DocumentVectorIndexExecutionService" in names
    assert "PdfTextExtractionAdapter" in names
    assert "FastAPI" not in names
    assert "APIRouter" not in names
    assert "OpenAISettings" not in names
    assert "load_openai_settings" not in names
    assert "create_openai_client" not in names
    assert "QdrantSettings" not in names
    assert "create_qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "PdfReader" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_synchronous_function() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["build_pdf_document_extraction_index_execution"]
    assert all(isinstance(node, ast.FunctionDef) for node in public)
    assert _module_class_names(BUILDER_MODULE) == []
    leaked_implementations = sorted(
        name
        for name in _module_class_names(BUILDER_MODULE)
        if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_implementations == []
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "build_pdf_document_extraction_index_execution"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        "energy_trading/api/composition/pdf_document_extraction_index.py"
    ]


def test_builder_signature_is_keyword_only_path_identities_and_index_service() -> None:
    builder = _builder_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "path",
        "document_id",
        "source_name",
        "index_execution_service",
    )
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == ALLOWED_INIT_ANNOTATIONS
    assert ast.unparse(builder.returns) == "DocumentExtractionIndexExecutionService"


def test_builder_constructs_pdf_adapter_and_application_service_without_runtime_calls() -> None:
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
        "PdfTextExtractionAdapter",
        "DocumentExtractionIndexExecutionService",
    ]
    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 2
    first, second = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "PdfTextExtractionAdapter"
    first_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in first.value.keywords}
    assert first_keywords == {
        "path": "path",
        "document_id": "document_id",
        "source_name": "source_name",
    }
    assert first.value.args == []
    assert isinstance(second, ast.Return)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "DocumentExtractionIndexExecutionService"
    assert [ast.unparse(arg) for arg in second.value.args] == [
        "document_extraction_port",
        "index_execution_service",
    ]
    assert second.value.keywords == []
    identifiers = _identifier_names(BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
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
    assert ".env" not in source
    assert "try:" not in source
    assert "except " not in source
    assert ".extract(" not in source
    assert ".execute(" not in source
    assert ".exists(" not in source
    assert ".open(" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert "create_openai_client" not in source
    assert "clock=" not in source
    assert "retry" not in lowered
    leaked_frameworks = sorted(
        name for name in identifiers if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_frameworks == []


def test_application_does_not_import_the_outer_builder() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.pdf_document_extraction_index",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "build_pdf_document_extraction_index_execution" not in names
        source = path.read_text(encoding="utf-8")
        assert "build_pdf_document_extraction_index_execution" not in source


def test_infrastructure_does_not_import_api_composition() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.pdf_document_extraction_index",
    )
    assert collect_import_violations(INFRASTRUCTURE_ROOT, forbidden) == []
    names = imported_names(PDF_ADAPTER)
    assert "build_pdf_document_extraction_index_execution" not in names
    modules = imported_modules(PDF_ADAPTER)
    assert "energy_trading.api.composition.pdf_document_extraction_index" not in modules


def test_http_create_app_does_not_invoke_the_builder() -> None:
    forbidden_wiring = (
        "energy_trading.api.composition.pdf_document_extraction_index",
        "energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction",
        "energy_trading.application.orchestration.document_extraction_index_execution",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "build_pdf_document_extraction_index_execution" not in names
        modules = imported_modules(path)
        assert "energy_trading.api.composition.pdf_document_extraction_index" not in modules
        source = path.read_text(encoding="utf-8")
        assert "build_pdf_document_extraction_index_execution" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    names = imported_names(API_APP)
    assert "build_pdf_document_extraction_index_execution" not in names
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
    assert "build_pdf_document_extraction_index_execution" not in call_names
    assert "PdfTextExtractionAdapter" not in call_names
    assert "DocumentExtractionIndexExecutionService" not in call_names
    assert "build_pdf_document_extraction_index_execution" not in app_source


def test_production_lifespan_router_runtime_and_graph_remain_unwired() -> None:
    unwired = (
        GRAPH_MODULE,
        PRODUCTION_LIFESPAN,
        DOCUMENT_INDEX_ROUTER,
        DOCUMENT_INDEX_LIFESPAN,
        *DOCUMENT_INDEX_RUNTIME_MODULES,
        *REGULATORY_COMPOSITION_MODULES,
    )
    for path in unwired:
        names = imported_names(path)
        assert "build_pdf_document_extraction_index_execution" not in names
        modules = imported_modules(path)
        assert "energy_trading.api.composition.pdf_document_extraction_index" not in modules
        source = path.read_text(encoding="utf-8")
        assert "build_pdf_document_extraction_index_execution" not in source
        assert "PdfTextExtractionAdapter" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api" not in graph_source
    lifespan_names = imported_names(PRODUCTION_LIFESPAN)
    assert "PdfTextExtractionAdapter" not in lifespan_names
    assert "DocumentExtractionIndexExecutionService" not in lifespan_names
    router_names = imported_names(DOCUMENT_INDEX_ROUTER)
    assert "PdfTextExtractionAdapter" not in router_names
    assert "DocumentExtractionIndexExecutionService" not in router_names
