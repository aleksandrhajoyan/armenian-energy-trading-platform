"""Chunk 80 Regulatory HTTP schemas stay API-owned transport contracts."""

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
REGULATORY_ROUTER = API_ROOT / "routers" / "regulatory_intelligence.py"
SCHEMA_MODULE = API_ROOT / "schemas" / "regulatory_intelligence.py"
SCHEMA_PACKAGE_INIT = API_ROOT / "schemas" / "__init__.py"
ACCESSOR_MODULE = API_ROOT / "dependencies" / "regulatory_intelligence.py"
LIFESPAN_MODULE = API_ROOT / "composition" / "regulatory_intelligence_lifespan.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_PREFIXES = (
    "openai",
    "qdrant_client",
    "fastapi",
    "starlette",
    "energy_trading.ml",
    "energy_trading.application",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.regulatory_intelligence_query_execution",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.api.dependencies.regulatory_intelligence",
    "energy_trading.api.composition",
    "energy_trading.api.composition.regulatory_intelligence_lifespan",
    "energy_trading.shared.config",
    "energy_trading.infrastructure",
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
        "dict",
        "Dict",
        "Mapping",
        "HTTPException",
        "APIRouter",
        "Depends",
        "Request",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
        "RegulatoryIntelligenceQueryExecutionService",
        "SchemaFactory",
        "GenericMapper",
        "ServiceRegistry",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "SchemaFactory",
        "GenericMapper",
        "ServiceRegistry",
        "HTTPException",
        "Depends",
        "APIRouter",
        "Request",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "datetime",
        "typing",
        "pydantic",
    }
)

RUNTIME_CALL_NAMES = frozenset(
    {
        "execute",
        "run",
        "embed_query",
        "prepare",
        "search",
        "infer",
        "Depends",
        "HTTPException",
        "include_router",
        "add_api_route",
        "get_regulatory_intelligence_query_execution_service",
        "build_regulatory_intelligence_lifespan",
        "loaded_regulatory_intelligence_runtime",
    }
)

PUBLIC_CLASS_NAMES = (
    "RegulatoryIntelligenceQueryRequest",
    "RegulatoryConstraintResponse",
    "RegulatoryIntelligenceQueryResponse",
)


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _module_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_schema_module_lives_in_api_schemas_package() -> None:
    assert SCHEMA_MODULE.parent == API_ROOT / "schemas"
    assert SCHEMA_MODULE.exists()
    assert SCHEMA_PACKAGE_INIT.exists()
    init_names = imported_names(SCHEMA_PACKAGE_INIT)
    assert "RegulatoryIntelligenceQueryRequest" in init_names
    assert "RegulatoryIntelligenceQueryResponse" in init_names
    assert "RegulatoryConstraintResponse" in init_names
    assert "Depends" not in init_names
    assert "APIRouter" not in init_names
    assert _module_function_defs(SCHEMA_PACKAGE_INIT) == []


def test_schema_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(SCHEMA_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(SCHEMA_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(SCHEMA_MODULE)
    assert "BaseModel" in names
    assert "ConfigDict" in names
    assert "Field" in names
    assert "Request" not in names
    assert "Depends" not in names
    assert "APIRouter" not in names
    assert "get_regulatory_intelligence_query_execution_service" not in names
    assert "build_regulatory_intelligence_lifespan" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_schema_exposes_only_the_three_transport_models() -> None:
    assert _module_class_names(SCHEMA_MODULE) == list(PUBLIC_CLASS_NAMES)
    assert _module_function_defs(SCHEMA_MODULE) == []
    tree = ast.parse(SCHEMA_MODULE.read_text(encoding="utf-8"), filename=str(SCHEMA_MODULE))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = [ast.unparse(base) for base in node.bases]
        assert "BaseModel" in base_names


def test_schema_has_no_routes_depends_or_execution() -> None:
    source = SCHEMA_MODULE.read_text(encoding="utf-8")
    assert "Depends(" not in source
    assert "@" not in source
    assert "APIRouter" not in source
    assert "HTTPException" not in source
    assert ".execute(" not in source
    assert ".run(" not in source
    runtime_calls: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in RUNTIME_CALL_NAMES:
            runtime_calls.append(name)
    assert runtime_calls == []
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(SCHEMA_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    assert "query_text" in source
    assert "limit" in source
    assert "constraints" in source
    assert "openai" not in source
    assert "qdrant" not in source
    assert "api_key" not in source


def test_provider_sdk_allowlist_remains_the_existing_two_modules() -> None:
    assert REGULATORY_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/regulatory_intelligence_runtime.py",
        "energy_trading/api/composition/regulatory_intelligence_configured_runtime.py",
    )
    relative = SCHEMA_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in REGULATORY_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(SCHEMA_MODULE)
    assert "qdrant_client" not in imported_modules(SCHEMA_MODULE)


def test_application_domain_and_graph_do_not_import_the_schema() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.schemas",
        "energy_trading.api.schemas.regulatory_intelligence",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    names = imported_names(GRAPH_MODULE)
    assert "RegulatoryIntelligenceQueryRequest" not in names
    assert "RegulatoryIntelligenceQueryResponse" not in names
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "energy_trading.api.schemas" not in source


def test_app_health_accessor_and_routers_remain_unwired_to_the_schema() -> None:
    for path in (API_APP, HEALTH_ROUTER, ACCESSOR_MODULE, LIFESPAN_MODULE):
        names = imported_names(path)
        assert "RegulatoryIntelligenceQueryRequest" not in names
        assert "RegulatoryIntelligenceQueryResponse" not in names
        source = path.read_text(encoding="utf-8")
        assert "RegulatoryIntelligenceQueryRequest" not in source
        assert "energy_trading.api.schemas" not in source
    for path in sorted((API_ROOT / "routers").rglob("*.py")):
        if path.resolve() == REGULATORY_ROUTER.resolve():
            continue
        source = path.read_text(encoding="utf-8")
        assert "RegulatoryIntelligenceQueryRequest" not in source
        assert "RegulatoryIntelligenceQueryResponse" not in source
        assert "energy_trading.api.schemas" not in source
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
