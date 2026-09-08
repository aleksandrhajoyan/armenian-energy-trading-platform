"""Chunk 81 Regulatory HTTP query route stays a thin API transport boundary."""

from __future__ import annotations

import ast
from pathlib import Path

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
ROUTER_MODULE = API_ROOT / "routers" / "regulatory_intelligence.py"
ACCESSOR_MODULE = API_ROOT / "dependencies" / "regulatory_intelligence.py"
SCHEMA_MODULE = API_ROOT / "schemas" / "regulatory_intelligence.py"
LIFESPAN_MODULE = API_ROOT / "composition" / "regulatory_intelligence_lifespan.py"
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
    "energy_trading.api.app",
    "energy_trading.api.composition",
    "energy_trading.api.composition.regulatory_intelligence_lifespan",
    "energy_trading.api.composition.regulatory_intelligence_loaded_runtime",
    "energy_trading.api.composition.regulatory_intelligence_managed_runtime",
    "energy_trading.api.composition.regulatory_intelligence_configured_runtime",
    "energy_trading.api.composition.regulatory_intelligence_runtime",
    "energy_trading.api.composition.regulatory_intelligence",
    "energy_trading.shared.config.settings",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.qdrant",
    "energy_trading.shared.config.regulatory_intelligence",
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
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
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
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "typing",
        "fastapi",
        "energy_trading.api.dependencies.regulatory_intelligence",
        "energy_trading.api.schemas.regulatory_intelligence",
        "energy_trading.application.orchestration.regulatory_intelligence_query_execution",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "embed_query",
        "prepare",
        "search",
        "infer",
        "run",
        "HTTPException",
        "include_router",
        "add_api_route",
        "load_openai_settings",
        "load_qdrant_settings",
        "load_regulatory_intelligence_runtime_settings",
        "create_openai_client",
        "create_qdrant_client",
        "loaded_regulatory_intelligence_runtime",
        "managed_regulatory_intelligence_runtime",
        "build_regulatory_intelligence_lifespan",
        "build_regulatory_intelligence_configured_runtime",
        "build_regulatory_intelligence_provider_runtime",
        "build_regulatory_intelligence_query_execution",
        "create_app",
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


def _handler() -> ast.AsyncFunctionDef:
    for node in _module_function_defs(ROUTER_MODULE):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "query_regulatory_intelligence":
            return node
    msg = "query_regulatory_intelligence not found"
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
    assert [node.name for node in public] == ["query_regulatory_intelligence"]
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
    assert "get_regulatory_intelligence_query_execution_service" in names
    assert "RegulatoryIntelligenceQueryRequest" in names
    assert "RegulatoryIntelligenceQueryResponse" in names
    assert "RegulatoryConstraintResponse" in names
    assert "RegulatoryIntelligenceQueryExecutionService" in names
    assert "HTTPException" not in names
    assert "create_app" not in names
    assert "loaded_regulatory_intelligence_runtime" not in names
    assert "build_regulatory_intelligence_lifespan" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_router_defines_post_query_route_with_depends_and_existing_dtos() -> None:
    assignment = _router_assignment()
    assert _call_name(assignment) == "APIRouter"
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in assignment.keywords}
    assert keywords["prefix"] == "'/regulatory-intelligence'"
    handler = _handler()
    assert tuple(arg.arg for arg in handler.args.args) == ("request", "service")
    assert ast.unparse(handler.args.args[0].annotation) == "RegulatoryIntelligenceQueryRequest"
    assert "Depends(get_regulatory_intelligence_query_execution_service)" in ast.unparse(
        handler.args.args[1].annotation
    )
    assert ast.unparse(handler.returns) == "RegulatoryIntelligenceQueryResponse"
    assert len(handler.decorator_list) == 1
    decorator = handler.decorator_list[0]
    assert isinstance(decorator, ast.Call)
    assert _call_name(decorator) == "post"
    assert [ast.unparse(arg) for arg in decorator.args] == ["'/query'"]
    decorator_keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in decorator.keywords}
    assert decorator_keywords["response_model"] == "RegulatoryIntelligenceQueryResponse"


def test_handler_executes_once_and_forwards_exact_request_fields() -> None:
    handler = _handler()
    except_handlers = [node for node in ast.walk(handler) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    execute_calls: list[ast.Call] = []
    runtime_calls: list[str] = []
    constructed: list[str] = []
    for node in ast.walk(handler):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        constructed.append(name)
        if name == "execute":
            execute_calls.append(node)
        if name in RUNTIME_CALL_NAMES:
            runtime_calls.append(name)
    assert runtime_calls == []
    assert len(execute_calls) == 1
    execute_call = execute_calls[0]
    assert execute_call.args == []
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in execute_call.keywords}
    assert keywords == {"query_text": "request.query_text", "limit": "request.limit"}
    assert "RegulatoryIntelligenceQueryResponse" in constructed
    assert "RegulatoryConstraintResponse" in constructed
    source = ROUTER_MODULE.read_text(encoding="utf-8")
    assert "try:" not in source
    assert "except " not in source
    assert "HTTPException" not in source
    assert "app.state" not in source
    assert ".strip(" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(ROUTER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    assert "confidence" not in source
    assert "citation" not in source
    assert "openai" not in source
    assert "qdrant" not in source
    assert "api_key" not in source


def test_provider_sdk_allowlist_remains_the_existing_two_modules() -> None:
    assert REGULATORY_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/regulatory_intelligence_runtime.py",
        "energy_trading/api/composition/regulatory_intelligence_configured_runtime.py",
    )
    relative = ROUTER_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in REGULATORY_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(ROUTER_MODULE)
    assert "qdrant_client" not in imported_modules(ROUTER_MODULE)
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


def test_application_domain_and_graph_do_not_import_the_router() -> None:
    forbidden = (
        "energy_trading.api.routers.regulatory_intelligence",
        "energy_trading.api.routers",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    names = imported_names(GRAPH_MODULE)
    assert "query_regulatory_intelligence" not in names
    assert "RegulatoryIntelligenceQueryRequest" not in names
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api" not in source
    assert "regulatory-intelligence" not in source


def test_accessor_schema_lifespan_and_health_remain_unwired_to_the_handler() -> None:
    names = imported_names(API_APP)
    assert "query_regulatory_intelligence" not in names
    assert "get_regulatory_intelligence_query_execution_service" not in names
    health_source = HEALTH_ROUTER.read_text(encoding="utf-8")
    assert "get_regulatory_intelligence_query_execution_service" not in health_source
    accessor_source = ACCESSOR_MODULE.read_text(encoding="utf-8")
    assert "query_regulatory_intelligence" not in accessor_source
    schema_source = SCHEMA_MODULE.read_text(encoding="utf-8")
    assert "query_regulatory_intelligence" not in schema_source
    lifespan_source = LIFESPAN_MODULE.read_text(encoding="utf-8")
    assert "query_regulatory_intelligence" not in lifespan_source
    assert "include_router" not in lifespan_source
