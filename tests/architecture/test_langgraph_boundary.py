"""LangGraph belongs only to the application orchestration graph module."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
FAILURE_DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
FAILURE_CONTEXT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
FAILURE_ACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_action.py"
FAILURE_HANDLING_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_handling.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXCEPTION_GROUP_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
FAILURE_FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
FAILURE_CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_classification.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
AGENT_BASE = AGENTS_ROOT / "base.py"
PORTS_ROOT = PRODUCTION_ROOT / "application" / "ports"
USE_CASES_ROOT = PRODUCTION_ROOT / "application" / "use_cases"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_GRAPH_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
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

FORBIDDEN_GRAPH_NAMES = frozenset(
    {
        "MessagesState",
        "MessageGraph",
        "add_messages",
        "Command",
        "Send",
        "RetryPolicy",
        "MemorySaver",
        "InMemorySaver",
        "BaseStore",
        "BaseCache",
        "add_conditional_edges",
        "entrypoint",
        "task",
        "interrupt",
        "AgentPort",
        "AgentName",
        "Any",
    }
)

ALLOWED_GRAPH_IMPORTS = frozenset(
    {
        "langgraph.graph",
        "langgraph.graph.state",
        "energy_trading.application.orchestration.parallel_ingestion_transition",
        "energy_trading.application.orchestration.parallel_ingestion_workflow",
        "energy_trading.application.orchestration.state",
        "END",
        "START",
        "StateGraph",
        "CompiledStateGraph",
        "ParallelIngestionWorkflowStep",
        "WorkflowState",
        "advance_after_parallel_ingestion",
    }
)


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
    return names


def test_langgraph_imports_are_confined_to_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []


def test_state_module_remains_langgraph_free() -> None:
    names = imported_names(STATE_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(STATE_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_policy_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_POLICY_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    assert "RetryPolicy" not in names
    modules = imported_modules(FAILURE_POLICY_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_decision_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_DECISION_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_DECISION_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_context_builder_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_CONTEXT_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_CONTEXT_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_action_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_ACTION_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_ACTION_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_handling_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_HANDLING_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_HANDLING_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_agent_failure_module_remains_langgraph_free() -> None:
    names = imported_names(AGENT_FAILURE_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(AGENT_FAILURE_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_exception_group_extraction_module_remains_langgraph_free() -> None:
    names = imported_names(EXCEPTION_GROUP_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(EXCEPTION_GROUP_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_fact_classification_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_FACT_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_FACT_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_classification_composition_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_CLASSIFICATION_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_CLASSIFICATION_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_agent_base_remains_langgraph_free() -> None:
    assert (
        collect_import_violations(AGENTS_ROOT, ("langgraph", "langchain", "langchain_core")) == []
    )
    names = imported_names(AGENT_BASE)
    assert "langgraph" not in names
    assert "StateGraph" not in names


def test_other_layers_do_not_import_langgraph() -> None:
    forbidden = ("langgraph", "langchain", "langchain_core")
    for root in (
        PRODUCTION_ROOT / "domain",
        PRODUCTION_ROOT / "infrastructure",
        PRODUCTION_ROOT / "ml",
        API_ROOT,
        PORTS_ROOT,
        USE_CASES_ROOT,
    ):
        assert collect_import_violations(root, forbidden) == []


def test_graph_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(GRAPH_MODULE)
        if is_forbidden(module, FORBIDDEN_GRAPH_PREFIXES)
    )
    assert leaked == []
    extras = imported_names(GRAPH_MODULE) - ALLOWED_GRAPH_IMPORTS
    assert extras == set()


def test_graph_module_depends_on_workflow_state_phase2_step_and_transition() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "WorkflowState" in names
    assert "ParallelIngestionWorkflowStep" in names
    assert "advance_after_parallel_ingestion" in names
    assert "WorkflowPhase" not in names
    assert "WorkflowStatus" not in names
    assert "AgentPort" not in names
    assert "AgentName" not in names
    assert "ParallelIngestionPlan" not in names
    assert "ParallelIngestionSuccess" not in names
    assert "ParallelIngestionExecutionPort" not in names
    assert "ParallelIngestionWorkflowContextPort" not in names
    assert "ConcurrentParallelIngestionExecutor" not in names
    assert "FailurePolicyPort" not in names
    assert "fail_parallel_ingestion" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "ParallelIngestionFailureHandlingService" not in names
    assert "ParallelIngestionAgentFailure" not in names
    assert "extract_parallel_ingestion_agent_failures" not in names
    assert "classify_parallel_ingestion_agent_failure" not in names
    assert "classify_parallel_ingestion_agent_failures" not in names
    assert "ParallelIngestionFailureFact" not in names
    assert "WeatherAndRenewableForecastAgent" not in names
    assert "HydroResourcesAgent" not in names
    assert "GenerationAvailabilityAgent" not in names
    assert "NewsIntelligenceAgent" not in names
    assert "MarketMonitoringAgent" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.parallel_ingestion_workflow" in modules
    assert "energy_trading.application.orchestration.parallel_ingestion_transition" in modules
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        not in modules
    )
    assert "energy_trading.application.orchestration.parallel_ingestion" not in modules
    assert "energy_trading.application.orchestration.parallel_ingestion_context" not in modules
    assert "energy_trading.application.orchestration.parallel_ingestion_executor" not in modules
    assert "energy_trading.application.orchestration.failure_policy" not in modules
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_decision"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context" not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_action" not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_handling"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_agent_failure" not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_exception_group" not in modules
    )
    assert "energy_trading.application.orchestration.parallel_ingestion_failure_fact" not in modules
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_classification"
        not in modules
    )
    assert "energy_trading.application.agents.weather_and_renewable_forecast" not in modules
    assert "energy_trading.application.agents.hydro_resources" not in modules
    assert "energy_trading.application.agents.generation_availability" not in modules
    assert "energy_trading.application.agents.news_intelligence" not in modules
    assert "energy_trading.application.agents.market_monitoring" not in modules


def test_graph_module_excludes_forbidden_runtime_features() -> None:
    identifiers = _identifier_names(GRAPH_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_GRAPH_NAMES)
    assert leaked == []
    imported = imported_names(GRAPH_MODULE)
    leaked_imports = sorted(name for name in imported if name in FORBIDDEN_GRAPH_NAMES)
    assert leaked_imports == []
    tree = ast.parse(GRAPH_MODULE.read_text(encoding="utf-8"), filename=str(GRAPH_MODULE))
    call_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "add_conditional_edges" not in call_names
    assert "compile" in call_names
    compile_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "compile"
    ]
    assert len(compile_calls) == 1
    compile_call = compile_calls[0]
    assert compile_call.args == []
    assert compile_call.keywords == []


def test_graph_factory_requires_injected_parallel_ingestion_step() -> None:
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
    assert [arg.arg for arg in factory.args.kwonlyargs] == ["parallel_ingestion_step"]
    annotation = factory.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "ParallelIngestionWorkflowStep"
    assert factory.args.kw_defaults == [None]


def test_graph_topology_includes_transition_node_without_lower_deps() -> None:
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(GRAPH_MODULE))
    string_constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "workflow_entry" in string_constants
    assert "parallel_ingestion" in string_constants
    assert "parallel_ingestion_success_transition" in string_constants
    assert "parallel_ingestion_failure_transition" not in string_constants
    add_node_count = 0
    add_edge_count = 0
    constructed: list[str] = []
    transition_calls = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name: str | None = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name == "add_node":
            add_node_count += 1
        elif name == "add_edge":
            add_edge_count += 1
        elif name == "advance_after_parallel_ingestion":
            transition_calls += 1
        if name in {
            "ParallelIngestionWorkflowStep",
            "ConcurrentParallelIngestionExecutor",
            "ParallelIngestionPlan",
            "ParallelIngestionSuccess",
            "WeatherAndRenewableForecastAgent",
            "HydroResourcesAgent",
            "GenerationAvailabilityAgent",
            "NewsIntelligenceAgent",
            "MarketMonitoringAgent",
        }:
            constructed.append(name)
    assert add_node_count == 3
    assert add_edge_count == 4
    assert transition_calls == 1
    assert constructed == []
    assert "FailurePolicyPort" not in source
    assert "fail_parallel_ingestion" not in source
    assert "ParallelIngestionFailureDecisionService" not in source
    assert "build_parallel_ingestion_failure_policy_context" not in source
    assert "execute_parallel_ingestion_failure_action" not in source
    assert "ParallelIngestionFailureHandlingService" not in source
    assert "ParallelIngestionAgentFailure" not in source
    assert "extract_parallel_ingestion_agent_failures" not in source
    assert "parallel_ingestion_exception_group" not in source
    assert "classify_parallel_ingestion_agent_failure" not in source
    assert "classify_parallel_ingestion_agent_failures" not in source
    assert "ParallelIngestionFailureFact" not in source
    assert "parallel_ingestion_failure_fact" not in source
    assert "parallel_ingestion_failure_classification" not in source
    assert "add_conditional_edges" not in source
    identifiers = _identifier_names(GRAPH_MODULE)
    assert "replace" not in identifiers
    assert "WorkflowPhase" not in identifiers
    assert "WorkflowStatus" not in identifiers


def test_graph_module_has_no_type_ignore_or_private_langgraph_imports() -> None:
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(GRAPH_MODULE), type_comments=True)
    assert tree.type_ignores == []
    assert "Any" not in _identifier_names(GRAPH_MODULE)
    private_imports = sorted(module for module in imported_modules(GRAPH_MODULE) if "._" in module)
    assert private_imports == []


def test_api_composition_does_not_import_or_construct_graph() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.graph",
        "langgraph",
        "langchain",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "build_workflow_graph" not in app_source
    assert "langgraph" not in app_source
    assert "workflow_entry" not in app_source
    assert "parallel_ingestion" not in app_source
    assert "parallelingestionworkflowstep" not in app_source
