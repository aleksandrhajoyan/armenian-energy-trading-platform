"""Chunk 79 Regulatory request accessor stays a read-only API dependency boundary."""

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
ACCESSOR_MODULE = API_ROOT / "dependencies" / "regulatory_intelligence.py"
ACCESSOR_PACKAGE_INIT = API_ROOT / "dependencies" / "__init__.py"
LIFESPAN_MODULE = API_ROOT / "composition" / "regulatory_intelligence_lifespan.py"
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
    "energy_trading.infrastructure",
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
        "Container",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "SettingsRegistry",
        "ServiceRegistry",
        "HTTPException",
        "APIRouter",
        "Depends",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "Container",
        "ServiceRegistry",
        "ProviderRegistry",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "SettingsRegistry",
        "SettingsAggregator",
        "HTTPException",
        "Depends",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "fastapi",
        "energy_trading.application.errors",
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
        "execute",
        "setattr",
        "delattr",
        "Depends",
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


def _accessor_function(path: Path) -> ast.FunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.FunctionDef) and node.name == (
            "get_regulatory_intelligence_query_execution_service"
        ):
            return node
    msg = "get_regulatory_intelligence_query_execution_service not found"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _state_attribute(node: ast.AST) -> ast.Attribute | None:
    if not isinstance(node, ast.Attribute):
        return None
    if node.attr != "regulatory_intelligence_query_execution_service":
        return None
    return node


def test_accessor_lives_in_api_dependencies_package() -> None:
    assert ACCESSOR_MODULE.parent == API_ROOT / "dependencies"
    assert ACCESSOR_MODULE.exists()
    assert ACCESSOR_MODULE.parent.parent == API_ROOT
    assert ACCESSOR_PACKAGE_INIT.exists()
    init_names = imported_names(ACCESSOR_PACKAGE_INIT)
    assert "get_regulatory_intelligence_query_execution_service" in init_names
    assert "Depends" not in init_names
    assert "HTTPException" not in init_names
    assert "openai" not in imported_modules(ACCESSOR_PACKAGE_INIT)
    assert "qdrant_client" not in imported_modules(ACCESSOR_PACKAGE_INIT)
    assert _module_function_defs(ACCESSOR_PACKAGE_INIT) == []
    assert _module_class_names(ACCESSOR_PACKAGE_INIT) == []


def test_accessor_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(ACCESSOR_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(ACCESSOR_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(ACCESSOR_MODULE)
    assert "Request" in names
    assert "RegulatoryIntelligenceQueryExecutionService" in names
    assert "DependencyUnavailableError" in names
    assert "Depends" not in names
    assert "HTTPException" not in names
    assert "APIRouter" not in names
    assert "create_app" not in names
    assert "loaded_regulatory_intelligence_runtime" not in names
    assert "build_regulatory_intelligence_lifespan" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_accessor_exposes_exactly_one_public_sync_function() -> None:
    public = _module_function_defs(ACCESSOR_MODULE)
    assert [node.name for node in public] == ["get_regulatory_intelligence_query_execution_service"]
    assert isinstance(public[0], ast.FunctionDef)
    assert not isinstance(public[0], ast.AsyncFunctionDef)
    assert _module_class_names(ACCESSOR_MODULE) == []
    production_accessors: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "get_regulatory_intelligence_query_execution_service"
            ):
                production_accessors.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_accessors == ["energy_trading/api/dependencies/regulatory_intelligence.py"]


def test_accessor_signature_reads_request_and_returns_the_service_type() -> None:
    accessor = _accessor_function(ACCESSOR_MODULE)
    assert accessor.args.posonlyargs == []
    assert tuple(arg.arg for arg in accessor.args.args) == ("request",)
    assert accessor.args.kwonlyargs == []
    assert accessor.args.vararg is None
    assert accessor.args.kwarg is None
    assert ast.unparse(accessor.args.args[0].annotation) == "Request"
    assert ast.unparse(accessor.returns) == "RegulatoryIntelligenceQueryExecutionService"


def test_accessor_reads_exact_state_attribute_without_mutation_or_execution() -> None:
    accessor = _accessor_function(ACCESSOR_MODULE)
    except_handlers = [node for node in ast.walk(accessor) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    runtime_calls: list[str] = []
    constructed: list[str] = []
    for node in ast.walk(accessor):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        constructed.append(name)
        if name in RUNTIME_CALL_NAMES:
            runtime_calls.append(name)
    assert runtime_calls == []
    assert "getattr" in constructed
    assert "isinstance" in constructed
    assert "DependencyUnavailableError" in constructed
    assigns = [node for node in ast.walk(accessor) if isinstance(node, ast.Assign)]
    for assignment in assigns:
        for target in assignment.targets:
            assert _state_attribute(target) is None
    deletes = [node for node in ast.walk(accessor) if isinstance(node, ast.Delete)]
    for deletion in deletes:
        for target in deletion.targets:
            assert _state_attribute(target) is None
    source = ACCESSOR_MODULE.read_text(encoding="utf-8")
    assert "regulatory_intelligence_query_execution_service" in source
    assert "request.app.state" in source
    assert "global " not in source
    assert "Depends(" not in source
    assert "@" not in source
    assert "HTTPException" not in source
    assert ".execute(" not in source
    assert ".run(" not in source
    assert ".embed_query(" not in source
    assert ".search(" not in source
    assert ".infer(" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(ACCESSOR_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_provider_sdk_allowlist_remains_the_existing_two_modules() -> None:
    assert REGULATORY_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/regulatory_intelligence_runtime.py",
        "energy_trading/api/composition/regulatory_intelligence_configured_runtime.py",
    )
    relative = ACCESSOR_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in REGULATORY_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(ACCESSOR_MODULE)
    assert "qdrant_client" not in imported_modules(ACCESSOR_MODULE)


def test_application_domain_and_graph_do_not_import_the_accessor() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.dependencies",
        "energy_trading.api.dependencies.regulatory_intelligence",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    names = imported_names(GRAPH_MODULE)
    assert "get_regulatory_intelligence_query_execution_service" not in names
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "get_regulatory_intelligence_query_execution_service" not in source
    assert "energy_trading.api" not in source


def test_app_health_and_routers_remain_unwired_to_the_accessor() -> None:
    for path in (API_APP, HEALTH_ROUTER, LIFESPAN_MODULE):
        names = imported_names(path)
        assert "get_regulatory_intelligence_query_execution_service" not in names
        source = path.read_text(encoding="utf-8")
        assert "get_regulatory_intelligence_query_execution_service" not in source
    for path in sorted((API_ROOT / "routers").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "get_regulatory_intelligence_query_execution_service" not in source
        assert "regulatory_intelligence_query_execution_service" not in source
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
    lifespan_source = LIFESPAN_MODULE.read_text(encoding="utf-8")
    assert "get_regulatory_intelligence_query_execution_service" not in lifespan_source
