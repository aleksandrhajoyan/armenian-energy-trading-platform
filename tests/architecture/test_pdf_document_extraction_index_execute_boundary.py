"""Chunk 104 one-shot PDF extraction-to-index execution stays an outer seam."""

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
BUILDER_MODULE = COMPOSITION_ROOT / "pdf_document_extraction_index_execute.py"
LOADED_PDF_RUNTIME_MODULE = COMPOSITION_ROOT / "pdf_document_extraction_index_loaded_runtime.py"
PDF_COMPOSITION_MODULE = COMPOSITION_ROOT / "pdf_document_extraction_index.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"
DOCUMENT_INDEX_ROUTER = API_ROOT / "routers" / "document_vector_index.py"
REGULATORY_ROUTER = API_ROOT / "routers" / "regulatory_intelligence.py"
PRODUCTION_LIFESPAN = COMPOSITION_ROOT / "production_lifespan.py"
DOCUMENT_INDEX_LIFESPAN = COMPOSITION_ROOT / "document_vector_index_lifespan.py"
PDF_ADAPTER = (
    PRODUCTION_ROOT / "infrastructure" / "adapters" / "unstructured" / "pdf_text_extraction.py"
)

FORBIDDEN_PREFIXES = (
    "energy_trading.ml",
    "energy_trading.application.orchestration",
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
    "asyncio",
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
        "JobRunner",
        "TaskRegistry",
        "AppSettings",
        "FastAPI",
        "APIRouter",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAIDocumentEmbeddingAdapter",
        "QdrantDocumentVectorIndex",
        "PdfTextExtractionAdapter",
        "DocumentVectorIndexExecutionService",
        "DocumentExtractionIndexExecutionService",
        "DocumentEmbeddingPort",
        "DocumentVectorIndexPort",
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
        "JobRunner",
        "TaskRegistry",
        "CommandBus",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "dict",
        "Mapping",
        "embed",
        "prepare",
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
        "create_task",
        "gather",
        "ensure_future",
        "create_openai_client",
        "create_qdrant_client",
        "load_openai_settings",
        "load_qdrant_settings",
        "PdfTextExtractionAdapter",
        "DocumentVectorIndexExecutionService",
        "DocumentExtractionIndexExecutionService",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "ManagedRuntime",
        "JobRunner",
        "TaskRegistry",
        "CommandBus",
        "clock",
        "ocr",
        "tesseract",
        "n8n",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "pathlib",
        "energy_trading.api.composition.pdf_document_extraction_index_loaded_runtime",
        "energy_trading.application.ports.document_extraction",
    }
)

FORBIDDEN_CALL_NAMES = frozenset(
    {
        "embed",
        "prepare",
        "index",
        "extract",
        "exists",
        "is_file",
        "open",
        "stat",
        "getenv",
        "create_task",
        "gather",
        "ensure_future",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "create_openai_client",
        "create_qdrant_client",
        "load_openai_settings",
        "load_qdrant_settings",
        "PdfTextExtractionAdapter",
        "DocumentVectorIndexExecutionService",
        "DocumentExtractionIndexExecutionService",
        "build_pdf_document_extraction_index_execution",
        "loaded_document_vector_index_runtime",
        "build_document_vector_index_lifespan",
        "build_production_lifespan",
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


def _execute_function(path: Path) -> ast.AsyncFunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == (
            "execute_loaded_pdf_document_extraction_index"
        ):
            return node
    msg = "execute_loaded_pdf_document_extraction_index not found"
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


def test_execution_module_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert BUILDER_MODULE.exists()
    assert COMPOSITION_ROOT.parent == API_ROOT


def test_execution_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BUILDER_MODULE)
    assert "loaded_pdf_document_extraction_index_runtime" in names
    assert "DocumentExtractionResult" in names
    assert "Path" in names
    assert "PdfTextExtractionAdapter" not in names
    assert "DocumentExtractionIndexExecutionService" not in names
    assert "DocumentVectorIndexExecutionService" not in names
    assert "asynccontextmanager" not in names
    assert "FastAPI" not in names
    assert "create_openai_client" not in names
    assert "load_openai_settings" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_execution_exposes_exactly_one_public_async_function() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["execute_loaded_pdf_document_extraction_index"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in public)
    execute = _execute_function(BUILDER_MODULE)
    assert execute.decorator_list == []
    assert _module_class_names(BUILDER_MODULE) == []
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.AsyncFunctionDef)
                and node.name == "execute_loaded_pdf_document_extraction_index"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        "energy_trading/api/composition/pdf_document_extraction_index_execute.py"
    ]


def test_execution_signature_is_keyword_only_path_identities_and_env_file() -> None:
    execute = _execute_function(BUILDER_MODULE)
    assert execute.args.posonlyargs == []
    assert execute.args.args == []
    assert tuple(arg.arg for arg in execute.args.kwonlyargs) == (
        "path",
        "document_id",
        "source_name",
        "env_file",
    )
    assert execute.args.vararg is None
    assert execute.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in execute.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {
        "path": "Path",
        "document_id": "str",
        "source_name": "str",
        "env_file": "str | Path | None",
    }
    assert execute.args.kw_defaults[0] is None
    assert execute.args.kw_defaults[1] is None
    assert execute.args.kw_defaults[2] is None
    assert ast.unparse(execute.args.kw_defaults[3]) == "'.env'"
    assert ast.unparse(execute.returns) == "DocumentExtractionResult"


def test_execution_enters_loaded_runtime_once_and_awaits_execute_once() -> None:
    execute = _execute_function(BUILDER_MODULE)
    control = [
        type(node).__name__
        for node in ast.walk(execute)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(execute) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    constructed: list[str] = []
    forbidden_calls: list[str] = []
    for node in ast.walk(execute):
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
        "loaded_pdf_document_extraction_index_runtime",
        "execute",
    ]
    statements = [node for node in execute.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 2
    outer, returned = statements
    assert isinstance(outer, ast.AsyncWith)
    assert len(outer.items) == 1
    item = outer.items[0]
    assert isinstance(item.context_expr, ast.Call)
    assert _call_name(item.context_expr) == "loaded_pdf_document_extraction_index_runtime"
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in item.context_expr.keywords}
    assert keywords == {
        "path": "path",
        "document_id": "document_id",
        "source_name": "source_name",
        "env_file": "env_file",
    }
    assert item.optional_vars is not None
    assert isinstance(item.optional_vars, ast.Name)
    assert item.optional_vars.id == "service"
    inner = list(outer.body)
    assert len(inner) == 1
    assign = inner[0]
    assert isinstance(assign, ast.Assign)
    assert [ast.unparse(target) for target in assign.targets] == ["result"]
    assert isinstance(assign.value, ast.Await)
    assert isinstance(assign.value.value, ast.Call)
    execute_call = assign.value.value
    assert _call_name(execute_call) == "execute"
    assert isinstance(execute_call.func, ast.Attribute)
    assert isinstance(execute_call.func.value, ast.Name)
    assert execute_call.func.value.id == "service"
    assert execute_call.args == []
    assert execute_call.keywords == []
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Name)
    assert returned.value.id == "result"
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
    assert "n8n" not in lowered
    assert "try:" not in source
    assert "except " not in source
    assert ".extract(" not in source
    assert ".embed(" not in source
    assert ".index(" not in source
    assert "create_task" not in source
    assert "PdfTextExtractionAdapter" not in source
    assert "create_openai_client" not in source
    assert "load_openai_settings" not in source
    assert source.count(".execute(") == 1
    assert "retry" not in lowered


def test_application_does_not_import_the_execution_function() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.pdf_document_extraction_index_execute",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "execute_loaded_pdf_document_extraction_index" not in names
        source = path.read_text(encoding="utf-8")
        assert "execute_loaded_pdf_document_extraction_index" not in source


def test_infrastructure_does_not_import_api_composition() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.pdf_document_extraction_index_execute",
    )
    assert collect_import_violations(INFRASTRUCTURE_ROOT, forbidden) == []
    names = imported_names(PDF_ADAPTER)
    assert "execute_loaded_pdf_document_extraction_index" not in names


def test_http_create_app_does_not_invoke_the_execution_function() -> None:
    forbidden_wiring = (
        "energy_trading.api.composition.pdf_document_extraction_index_execute",
        "energy_trading.infrastructure.adapters.unstructured.pdf_text_extraction",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "execute_loaded_pdf_document_extraction_index" not in names
        source = path.read_text(encoding="utf-8")
        assert "execute_loaded_pdf_document_extraction_index" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    names = imported_names(API_APP)
    assert "execute_loaded_pdf_document_extraction_index" not in names
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
    assert "execute_loaded_pdf_document_extraction_index" not in call_names
    assert "execute_loaded_pdf_document_extraction_index" not in app_source


def test_production_lifespan_router_runtime_and_graph_remain_unwired() -> None:
    unwired = (
        GRAPH_MODULE,
        PRODUCTION_LIFESPAN,
        DOCUMENT_INDEX_ROUTER,
        REGULATORY_ROUTER,
        DOCUMENT_INDEX_LIFESPAN,
        PDF_COMPOSITION_MODULE,
        LOADED_PDF_RUNTIME_MODULE,
        *DOCUMENT_INDEX_RUNTIME_MODULES,
        *REGULATORY_COMPOSITION_MODULES,
    )
    for path in unwired:
        names = imported_names(path)
        assert "execute_loaded_pdf_document_extraction_index" not in names
        modules = imported_modules(path)
        assert "energy_trading.api.composition.pdf_document_extraction_index_execute" not in modules
        source = path.read_text(encoding="utf-8")
        assert "execute_loaded_pdf_document_extraction_index" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api" not in graph_source
