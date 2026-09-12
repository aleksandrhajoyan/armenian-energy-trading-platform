"""Chunk 117 Regulatory LangGraph wiring stays a terminal contract-phase slice."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
NODE_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_workflow_node.py"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_context.py"
STEP_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_workflow_step.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_GRAPH_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.shared.config",
    "energy_trading.application.agents",
    "fastapi",
    "starlette",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "redis",
    "qdrant_client",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "alembic",
    "httpx",
    "requests",
    "aiohttp",
    "pandas",
    "openpyxl",
    "numpy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "n8n",
)

FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "RegulatoryIntelligenceWorkflowContextPort",
        "RegulatoryIntelligenceWorkflowStep",
        "RegulatoryIntelligenceWorkflowRequest",
        "RegulatoryIntelligenceQueryExecutionService",
        "RegulatoryIntelligenceAgent",
        "PricingAndSalesAgent",
        "advance_after_regulatory_intelligence",
        "advance_after_contract",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
        "create_app",
    }
)

WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)

UNWIRED_API_AND_RUNTIME = (
    API_APP,
    API_ROOT / "composition" / "production_lifespan.py",
    API_ROOT / "composition" / "regulatory_intelligence_lifespan.py",
    API_ROOT / "composition" / "regulatory_intelligence_loaded_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_managed_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_configured_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_runtime.py",
    API_ROOT / "routers" / "regulatory_intelligence.py",
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


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_graph_imports_published_node_adapter_only() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "RegulatoryIntelligenceWorkflowNodeAdapter" in names
    leaked = sorted(name for name in names if name in FORBIDDEN_IMPORT_NAMES)
    assert leaked == []
    modules = imported_modules(GRAPH_MODULE)
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_node" in modules
    )
    assert "energy_trading.application.orchestration.regulatory_intelligence_context" not in modules
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_step"
        not in modules
    )
    leaked_modules = sorted(
        module for module in modules if is_forbidden(module, FORBIDDEN_GRAPH_PREFIXES)
    )
    assert leaked_modules == []


def test_factory_requires_four_injected_dependencies_without_defaults() -> None:
    tree = ast.parse(GRAPH_MODULE.read_text(encoding="utf-8"), filename=str(GRAPH_MODULE))
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_workflow_graph"
    )
    assert factory.args.args == []
    assert factory.args.vararg is None
    assert factory.args.kwarg is None
    assert factory.args.posonlyargs == []
    assert [arg.arg for arg in factory.args.kwonlyargs] == [
        "regulatory_intelligence_node",
        "parallel_ingestion_step",
        "parallel_ingestion_failure_runtime_handler",
        "forecasting_step",
    ]
    annotations = [ast.unparse(arg.annotation) for arg in factory.args.kwonlyargs]
    assert annotations == [
        "RegulatoryIntelligenceWorkflowNodeAdapter",
        "ParallelIngestionWorkflowStep",
        "ParallelIngestionFailureRuntimeHandlingService",
        "ForecastingWorkflowStep",
    ]
    assert factory.args.kw_defaults == [None, None, None, None]


def test_graph_does_not_construct_the_node_adapter() -> None:
    tree = ast.parse(GRAPH_MODULE.read_text(encoding="utf-8"), filename=str(GRAPH_MODULE))
    constructed: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in {
            "RegulatoryIntelligenceWorkflowNodeAdapter",
            "RegulatoryIntelligenceWorkflowContextPort",
            "RegulatoryIntelligenceWorkflowStep",
            "RegulatoryIntelligenceQueryExecutionService",
            "RegulatoryIntelligenceAgent",
            "PricingAndSalesAgent",
        }:
            constructed.append(name or "")
    assert constructed == []


def test_regulatory_node_delegates_once_to_adapter_run_without_try_except() -> None:
    tree = ast.parse(GRAPH_MODULE.read_text(encoding="utf-8"), filename=str(GRAPH_MODULE))
    class_def = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "_RegulatoryIntelligenceNode"
    )
    call_method = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "__call__"
    )
    except_handlers = [
        node for node in ast.walk(call_method) if isinstance(node, ast.ExceptHandler)
    ]
    assert except_handlers == []
    control = [
        type(node).__name__
        for node in ast.walk(call_method)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    run_calls = [
        node
        for node in ast.walk(call_method)
        if isinstance(node, ast.Call) and _call_name(node) == "run"
    ]
    assert len(run_calls) == 1
    run_call = run_calls[0]
    assert [ast.unparse(arg) for arg in run_call.args] == ["state"]
    statements = [node for node in call_method.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 1
    returned = statements[0]
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Await)
    assert isinstance(returned.value.value, ast.Call)
    assert _call_name(returned.value.value) == "run"


def test_entry_routing_recognizes_contract_ingestion_and_forecasting_running() -> None:
    tree = ast.parse(GRAPH_MODULE.read_text(encoding="utf-8"), filename=str(GRAPH_MODULE))
    router = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_route_after_workflow_entry"
    )
    source = ast.unparse(router)
    assert "WorkflowPhase.CONTRACT" in source
    assert "WorkflowStatus.RUNNING" in source
    assert "WorkflowPhase.INGESTION" in source
    assert "WorkflowPhase.FORECASTING" in source
    assert "InvalidRequestError" in source
    assert "advance_after_parallel_ingestion" not in source
    assert "advance_after_forecasting" not in source
    assert "PricingAndSales" not in source
    raises = [node for node in ast.walk(router) if isinstance(node, ast.Raise)]
    assert len(raises) == 1


def test_topology_keeps_terminal_regulatory_slice_with_forecasting_branch() -> None:
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(GRAPH_MODULE))
    string_constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "workflow_entry" in string_constants
    assert "regulatory_intelligence" in string_constants
    assert "parallel_ingestion" in string_constants
    assert "parallel_ingestion_success_transition" in string_constants
    assert "forecasting" in string_constants
    add_node_count = 0
    add_edge_count = 0
    add_conditional_edges_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "add_node":
            add_node_count += 1
        elif name == "add_edge":
            add_edge_count += 1
        elif name == "add_conditional_edges":
            add_conditional_edges_count += 1
    assert add_node_count == 5
    assert add_edge_count == 4
    assert add_conditional_edges_count == 2
    assert "advance_after_regulatory" not in source
    assert "advance_after_contract" not in source
    assert "advance_after_forecasting" not in source
    assert "CONTRACT → INGESTION" not in source
    assert "PricingAndSales" not in source
    assert "PricingAndSalesAgent" not in source


def test_no_contract_to_ingestion_transition_function_exists() -> None:
    identifiers: set[str] = set()
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                identifiers.add(node.name)
    assert "advance_after_regulatory_intelligence" not in identifiers
    assert "advance_after_contract" not in identifiers
    assert "PricingAndSalesAgent" not in identifiers


def test_workflow_state_remains_seven_fields() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "regulatory_request" not in source
    assert "regulatory_result" not in source
    assert "regulatory_intelligence_request" not in source
    assert "regulatory_intelligence_result" not in source


def test_node_adapter_remains_langgraph_free() -> None:
    modules = imported_modules(NODE_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )
    names = imported_names(NODE_MODULE)
    assert "langgraph" not in names
    source = NODE_MODULE.read_text(encoding="utf-8").lower()
    assert "langgraph" not in source


def test_context_and_step_remain_unaware_of_graph_wiring() -> None:
    for path in (CONTEXT_MODULE, STEP_MODULE):
        names = imported_names(path)
        assert "build_workflow_graph" not in names
        assert "StateGraph" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.graph" not in modules
        assert not any(is_forbidden(module, ("langgraph",)) for module in modules)


def test_api_composition_remains_unaware_of_graph_and_regulatory_wiring() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.graph",
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_node",
        "langgraph",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in (*UNWIRED_API_AND_RUNTIME, *http_transport_api_paths(API_ROOT)):
        names = imported_names(path)
        assert "build_workflow_graph" not in names
        assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.graph" not in modules
        assert (
            "energy_trading.application.orchestration.regulatory_intelligence_workflow_node"
            not in modules
        )
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "build_workflow_graph" not in app_source
    assert "regulatoryintelligenceworkflownodeadapter" not in app_source
    assert "langgraph" not in app_source


def test_production_langgraph_imports_remain_confined_to_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
