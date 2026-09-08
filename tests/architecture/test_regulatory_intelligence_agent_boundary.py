"""Regulatory Intelligence agent and inference port stay application-owned."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
AGENT_MODULE = PRODUCTION_ROOT / "application" / "agents" / "regulatory_intelligence.py"
PORT_MODULE = PRODUCTION_ROOT / "application" / "ports" / "regulatory_constraint_inference.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
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
        "bytes",
        "bytearray",
        "Path",
        "DataFrame",
        "Workbook",
        "Request",
        "Response",
        "RetryPolicy",
        "FailurePolicyPort",
        "LLMPort",
        "ChatCompletion",
        "QdrantClient",
        "QdrantDocumentVectorSearch",
        "AsyncQdrantClient",
        "PromptTemplate",
        "WeatherAndRenewableForecastAgent",
        "HydroResourcesAgent",
        "GenerationAvailabilityAgent",
        "NewsIntelligenceAgent",
        "MarketMonitoringAgent",
    }
)

ALLOWED_AGENT_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.agents.base",
        "energy_trading.application.ports.document_vector_search",
        "energy_trading.application.ports.regulatory_constraint_inference",
        "energy_trading.domain.models.regulatory",
    }
)

ALLOWED_PORT_IMPORTS = frozenset(
    {
        "typing",
        "energy_trading.application.ports.document_extraction",
        "energy_trading.domain.models.regulatory",
    }
)

DAM_RULE_IDENTIFIERS = frozenset(
    {
        "AMD",
        "HOURLY",
        "INTERVAL",
        "GATE_CLOSURE",
        "LOT_SIZE",
        "PRICE_CAP",
        "PRICE_FLOOR",
        "NOMINATION",
        "BALANCING",
        "PENALTY",
    }
)


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _assigned_identifiers(path: Path) -> set[str]:
    identifiers: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    identifiers.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            identifiers.add(node.target.id)
    return identifiers


def test_regulatory_modules_do_not_import_outer_layers_or_vendors() -> None:
    for path in (AGENT_MODULE, PORT_MODULE):
        leaked = sorted(
            module for module in imported_modules(path) if is_forbidden(module, FORBIDDEN_PREFIXES)
        )
        assert leaked == []
        leaked_names = sorted(name for name in imported_names(path) if name in FORBIDDEN_TYPE_NAMES)
        assert leaked_names == []
    extras_agent = imported_modules(AGENT_MODULE) - ALLOWED_AGENT_IMPORTS
    assert extras_agent == set()
    extras_port = imported_modules(PORT_MODULE) - ALLOWED_PORT_IMPORTS
    assert extras_port == set()


def test_inference_port_is_nongeneric_protocol_with_async_infer() -> None:
    class_def = _class_def(PORT_MODULE, "RegulatoryConstraintInferencePort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert list(class_def.type_params) == []
    source = PORT_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["infer"]
    infer_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "infer"
    )
    assert tuple(arg.arg for arg in infer_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in infer_fn.args.kwonlyargs) == ("chunks",)
    assert infer_fn.args.vararg is None
    assert infer_fn.args.kwarg is None
    assert infer_fn.returns is not None
    assert ast.unparse(infer_fn.returns) == "tuple[RegulatoryConstraint, ...]"
    names = annotation_type_names(PORT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "ExtractedDocumentChunk" in names
    assert "RegulatoryConstraint" in names
    assert "LLMPort" not in names


def test_inference_port_module_has_no_concrete_implementation() -> None:
    assert _module_class_names(PORT_MODULE) == ["RegulatoryConstraintInferencePort"]
    call_names = _call_names(PORT_MODULE)
    assert "RegulatoryConstraint" not in call_names
    assert "OpenAI" not in call_names
    assert "Anthropic" not in call_names
    assert "QdrantDocumentVectorSearch" not in call_names


def test_agent_public_surface_is_name_and_run() -> None:
    class_def = _class_def(AGENT_MODULE, "RegulatoryIntelligenceAgent")
    assert _base_names(class_def) == set()
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__init__", "name", "run"]
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self",)
    assert tuple(arg.arg for arg in init_fn.args.kwonlyargs) == ("search", "inference")
    name_fn = next(
        node for node in class_def.body if isinstance(node, ast.FunctionDef) and node.name == "name"
    )
    assert any(
        isinstance(item, ast.Name) and item.id == "property" for item in name_fn.decorator_list
    )
    run_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run"
    )
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "request")
    assert run_fn.args.vararg is None
    assert run_fn.args.kwarg is None
    assert ast.unparse(run_fn.args.args[1].annotation) == "RegulatoryIntelligenceRequest"
    assert ast.unparse(run_fn.returns) == "RegulatoryIntelligenceResult"
    names = annotation_type_names(AGENT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    assert "Any" not in imported_names(AGENT_MODULE)
    assert "dict" not in imported_names(AGENT_MODULE)
    assert "AgentRegistry" not in imported_names(AGENT_MODULE)
    assert "AgentFactory" not in imported_names(AGENT_MODULE)
    assert "FailurePolicyPort" not in imported_names(AGENT_MODULE)
    assert "LLMPort" not in imported_names(AGENT_MODULE)
    assert "QdrantDocumentVectorSearch" not in imported_names(AGENT_MODULE)
    assert "WeatherAndRenewableForecastAgent" not in imported_names(AGENT_MODULE)
    assert "HydroResourcesAgent" not in imported_names(AGENT_MODULE)
    assert "GenerationAvailabilityAgent" not in imported_names(AGENT_MODULE)
    assert "NewsIntelligenceAgent" not in imported_names(AGENT_MODULE)
    assert "MarketMonitoringAgent" not in imported_names(AGENT_MODULE)


def test_agent_does_not_construct_constraints_or_search_implementations() -> None:
    call_names = _call_names(AGENT_MODULE)
    assert "RegulatoryConstraint" not in call_names
    assert "QdrantDocumentVectorSearch" not in call_names
    assert "QdrantClient" not in call_names
    assert "AsyncQdrantClient" not in call_names
    assert "OpenAI" not in call_names
    assert "Anthropic" not in call_names
    assert "ChatCompletion" not in call_names
    assert "PromptTemplate" not in call_names
    assert "DocumentVectorSearchQuery" not in call_names
    agent_class = _class_def(AGENT_MODULE, "RegulatoryIntelligenceAgent")
    agent_calls: set[str] = set()
    for node in ast.walk(agent_class):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            agent_calls.add(func.id)
        elif isinstance(func, ast.Attribute):
            agent_calls.add(func.attr)
    assert "RegulatoryConstraint" not in agent_calls
    assert "RegulatoryIntelligenceResult" in agent_calls


def test_request_and_result_have_exact_fields() -> None:
    assert _annassign_field_names(AGENT_MODULE, "RegulatoryIntelligenceRequest") == (
        "search_query",
    )
    assert _annassign_field_names(AGENT_MODULE, "RegulatoryIntelligenceResult") == ("constraints",)


def test_regulatory_modules_have_no_dam_business_rule_constants() -> None:
    for path in (AGENT_MODULE, PORT_MODULE):
        leaked = sorted(
            name for name in _assigned_identifiers(path) if name in DAM_RULE_IDENTIFIERS
        )
        assert leaked == []
        names = imported_names(path)
        assert "timedelta" not in names


def test_graph_module_does_not_import_or_invoke_regulatory_agent() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "RegulatoryIntelligenceAgent" not in names
    assert "RegulatoryIntelligenceRequest" not in names
    assert "RegulatoryIntelligenceResult" not in names
    assert "RegulatoryConstraintInferencePort" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.agents.regulatory_intelligence" not in modules
    assert "energy_trading.application.ports.regulatory_constraint_inference" not in modules
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "RegulatoryIntelligenceAgent" not in graph_source
    assert "RegulatoryConstraintInferencePort" not in graph_source


def test_api_composition_does_not_import_or_construct_regulatory_agent() -> None:
    forbidden_wiring = (
        "energy_trading.application.agents.regulatory_intelligence",
        "energy_trading.application.ports.regulatory_constraint_inference",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "RegulatoryIntelligenceAgent" not in names
        assert "RegulatoryConstraintInferencePort" not in names
        assert "RegulatoryIntelligenceRequest" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "regulatoryintelligenceagent" not in app_source
    assert "regulatoryconstraintinferenceport" not in app_source


def test_no_production_langgraph_imports_outside_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
