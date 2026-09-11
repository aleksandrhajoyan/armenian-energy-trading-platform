"""Chunk 98 Document Vector Index HTTP route stays a thin API transport boundary."""

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
HEALTH_ROUTER = API_ROOT / "routers" / "health.py"
REGULATORY_ROUTER = API_ROOT / "routers" / "regulatory_intelligence.py"
ROUTER_MODULE = API_ROOT / "routers" / "document_vector_index.py"
ACCESSOR_MODULE = API_ROOT / "dependencies" / "document_vector_index.py"
SCHEMA_MODULE = API_ROOT / "schemas" / "document_vector_index.py"
LIFESPAN_MODULE = API_ROOT / "composition" / "document_vector_index_lifespan.py"
PRODUCTION_LIFESPAN_MODULE = API_ROOT / "composition" / "production_lifespan.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_PREFIXES = (
    "openai",
    "qdrant_client",
    "energy_trading.ml",
    "energy_trading.infrastructure",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.document_vector_index_entry_preparation",
    "energy_trading.application.ports.document_vector_index",
    "energy_trading.application.ports.document_embedding",
    "energy_trading.api.app",
    "energy_trading.api.composition",
    "energy_trading.api.composition.document_vector_index_lifespan",
    "energy_trading.api.composition.document_vector_index_loaded_runtime",
    "energy_trading.api.composition.document_vector_index_managed_runtime",
    "energy_trading.api.composition.document_vector_index_configured_runtime",
    "energy_trading.api.composition.document_vector_index_runtime",
    "energy_trading.api.composition.document_vector_index_execution",
    "energy_trading.shared.config.settings",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.qdrant",
    "energy_trading.shared.config.document_vector_index",
    "starlette",
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
    "os",
    "sys",
    "dotenv",
    "pathlib",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "HTTPException",
        "UploadFile",
        "File",
        "Path",
        "bytes",
        "BackgroundTasks",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAISettings",
        "QdrantSettings",
        "DocumentVectorIndexRuntimeSettings",
        "DocumentVectorIndexResponse",
        "SchemaFactory",
        "GenericMapper",
        "ServiceRegistry",
        "AgentFactory",
        "LifecycleManager",
        "ManagedRuntime",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "SchemaFactory",
        "GenericMapper",
        "ServiceRegistry",
        "ProviderRegistry",
        "AgentFactory",
        "LifecycleManager",
        "ManagedRuntime",
        "ResourceManager",
        "HTTPException",
        "UploadFile",
        "BackgroundTasks",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "typing",
        "fastapi",
        "energy_trading.api.dependencies.document_vector_index",
        "energy_trading.api.schemas.document_vector_index",
        "energy_trading.application.orchestration.document_vector_index_execution",
        "energy_trading.application.ports.document_extraction",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "embed",
        "prepare",
        "index",
        "search",
        "infer",
        "run",
        "HTTPException",
        "include_router",
        "add_api_route",
        "load_openai_settings",
        "load_qdrant_settings",
        "load_document_vector_index_runtime_settings",
        "create_openai_client",
        "create_qdrant_client",
        "loaded_document_vector_index_runtime",
        "managed_document_vector_index_runtime",
        "build_document_vector_index_lifespan",
        "build_document_vector_index_configured_runtime",
        "build_document_vector_index_provider_runtime",
        "build_document_vector_index_execution",
        "create_app",
        "model_dump",
    }
)

PROJECTED_FIELDS = (
    "document_id",
    "chunk_id",
    "text",
    "ordinal",
    "page_number",
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


def _handler() -> ast.AsyncFunctionDef:
    for node in _module_function_defs(ROUTER_MODULE):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "index_document_vectors":
            return node
    msg = "index_document_vectors not found"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _router_assignment() -> ast.Call:
    tree = ast.parse(ROUTER_MODULE.read_text(encoding="utf-8"), filename=str(ROUTER_MODULE))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "router" for target in node.targets
        ):
            continue
        assert isinstance(node.value, ast.Call)
        return node.value
    msg = "router = APIRouter(...) not found"
    raise AssertionError(msg)


def test_router_lives_in_api_routers_package() -> None:
    assert ROUTER_MODULE.parent == API_ROOT / "routers"
    assert ROUTER_MODULE.exists()
    assert ROUTER_MODULE.parent.parent == API_ROOT
    assert _module_class_names(ROUTER_MODULE) == []
    public = _module_function_defs(ROUTER_MODULE)
    assert [node.name for node in public] == ["index_document_vectors"]
    assert isinstance(public[0], ast.AsyncFunctionDef)


def test_router_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ROUTER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ROUTER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(ROUTER_MODULE)
    assert "APIRouter" in names
    assert "Depends" in names
    assert "get_document_vector_index_execution_service" in names
    assert "DocumentVectorIndexRequest" in names
    assert "DocumentVectorIndexExecutionService" in names
    assert "ExtractedDocumentChunk" in names
    assert "HTTPException" not in names
    assert "create_app" not in names
    assert "loaded_document_vector_index_runtime" not in names
    assert "build_document_vector_index_lifespan" not in names
    assert "DocumentVectorIndexResponse" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_router_defines_post_index_route_with_depends_and_204() -> None:
    assignment = _router_assignment()
    assert _call_name(assignment) == "APIRouter"
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in assignment.keywords}
    assert keywords["prefix"] == "'/document-vector-index'"
    handler = _handler()
    assert tuple(arg.arg for arg in handler.args.args) == ("request", "service")
    assert ast.unparse(handler.args.args[0].annotation) == "DocumentVectorIndexRequest"
    assert "Depends(get_document_vector_index_execution_service)" in ast.unparse(
        handler.args.args[1].annotation
    )
    assert ast.unparse(handler.returns) == "None"
    assert len(handler.decorator_list) == 1
    decorator = handler.decorator_list[0]
    assert isinstance(decorator, ast.Call)
    assert _call_name(decorator) == "post"
    assert [ast.unparse(arg) for arg in decorator.args] == ["'/index'"]
    decorator_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in decorator.keywords}
    assert decorator_keywords["status_code"] == "204"
    assert "response_model" not in decorator_keywords


def test_handler_projects_chunks_and_awaits_execute_once() -> None:
    handler = _handler()
    except_handlers = [node for node in ast.walk(handler) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    execute_calls: list[ast.Call] = []
    runtime_calls: list[str] = []
    constructed: list[str] = []
    awaited_execute = 0
    projected_keywords: dict[str, str] | None = None
    for node in ast.walk(handler):
        if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
            if _call_name(node.value) == "execute":
                awaited_execute += 1
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        constructed.append(name)
        if name == "execute":
            execute_calls.append(node)
        if name == "ExtractedDocumentChunk":
            projected_keywords = {
                keyword.arg: ast.unparse(keyword.value)
                for keyword in node.keywords
                if keyword.arg is not None
            }
        if name in RUNTIME_CALL_NAMES:
            runtime_calls.append(name)
    assert runtime_calls == []
    assert len(execute_calls) == 1
    assert awaited_execute == 1
    execute_call = execute_calls[0]
    assert execute_call.args == []
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in execute_call.keywords}
    assert keywords == {"chunks": "chunks"}
    assert constructed.count("ExtractedDocumentChunk") == 1
    assert projected_keywords == {
        "document_id": "chunk.document_id",
        "chunk_id": "chunk.chunk_id",
        "text": "chunk.text",
        "ordinal": "chunk.ordinal",
        "page_number": "chunk.page_number",
    }
    assert tuple(projected_keywords) == PROJECTED_FIELDS
    source = ROUTER_MODULE.read_text(encoding="utf-8")
    assert "try:" not in source
    assert "except " not in source
    assert "HTTPException" not in source
    assert "app.state" not in source
    assert "model_dump" not in source
    assert "UploadFile" not in source
    assert "multipart" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(ROUTER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    assert "openai" not in source
    assert "qdrant" not in source
    assert "api_key" not in source
    assert "DocumentVectorIndexResponse" not in source


def test_provider_sdk_allowlist_remains_the_existing_document_index_modules() -> None:
    assert DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/document_vector_index_runtime.py",
        "energy_trading/api/composition/document_vector_index_configured_runtime.py",
    )
    relative = ROUTER_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(ROUTER_MODULE)
    assert "qdrant_client" not in imported_modules(ROUTER_MODULE)
    assert (
        collect_http_api_import_violations(
            API_ROOT,
            (
                "openai",
                "qdrant_client",
                "energy_trading.api.composition.document_vector_index_loaded_runtime",
            ),
        )
        == []
    )


def test_application_domain_and_graph_do_not_import_the_router() -> None:
    forbidden = (
        "energy_trading.api.routers.document_vector_index",
        "energy_trading.api.routers",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    names = imported_names(GRAPH_MODULE)
    assert "index_document_vectors" not in names
    assert "DocumentVectorIndexRequest" not in names
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api" not in source
    assert "document-vector-index" not in source


def test_accessor_schema_lifespan_health_and_regulatory_remain_unwired_to_the_handler() -> None:
    names = imported_names(API_APP)
    assert "index_document_vectors" not in names
    assert "get_document_vector_index_execution_service" not in names
    assert "DocumentVectorIndexRequest" not in names
    source = API_APP.read_text(encoding="utf-8")
    assert "index_document_vectors" not in source
    assert "/document-vector-index" not in source
    health_source = HEALTH_ROUTER.read_text(encoding="utf-8")
    assert "get_document_vector_index_execution_service" not in health_source
    assert "index_document_vectors" not in health_source
    regulatory_source = REGULATORY_ROUTER.read_text(encoding="utf-8")
    assert "index_document_vectors" not in regulatory_source
    assert "get_document_vector_index_execution_service" not in regulatory_source
    accessor_source = ACCESSOR_MODULE.read_text(encoding="utf-8")
    assert "index_document_vectors" not in accessor_source
    schema_source = SCHEMA_MODULE.read_text(encoding="utf-8")
    assert "index_document_vectors" not in schema_source
    lifespan_source = LIFESPAN_MODULE.read_text(encoding="utf-8")
    assert "index_document_vectors" not in lifespan_source
    assert "include_router" not in lifespan_source
    production_source = PRODUCTION_LIFESPAN_MODULE.read_text(encoding="utf-8")
    assert "index_document_vectors" not in production_source
    assert "include_router" not in production_source
