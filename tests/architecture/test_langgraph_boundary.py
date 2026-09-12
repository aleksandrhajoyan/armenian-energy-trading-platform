"""LangGraph belongs only to the application orchestration graph module."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    collect_http_api_import_violations,
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
FAILURE_SELECTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_selection.py"
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_attempt_number.py"
FAILURE_CONTEXT_RESOLUTION_MODULE = (
    ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_resolution.py"
)
FAILURE_CONTEXT_PREPARATION_MODULE = (
    ORCHESTRATION_ROOT / "parallel_ingestion_failure_context_preparation.py"
)
STRICT_SINGLE_FAILURE_SELECTOR_MODULE = (
    ORCHESTRATION_ROOT / "parallel_ingestion_strict_single_failure_selector.py"
)
INITIAL_ATTEMPT_NUMBER_SOURCE_MODULE = (
    ORCHESTRATION_ROOT / "parallel_ingestion_initial_attempt_number_source.py"
)
INITIAL_FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_initial_failure_policy.py"
FAILURE_RUNTIME_HANDLING_MODULE = (
    ORCHESTRATION_ROOT / "parallel_ingestion_failure_runtime_handling.py"
)
REGULATORY_INTELLIGENCE_WORKFLOW_NODE_MODULE = (
    ORCHESTRATION_ROOT / "regulatory_intelligence_workflow_node.py"
)
FORECASTING_PLAN_MODULE = ORCHESTRATION_ROOT / "forecasting_plan.py"
FORECASTING_SUCCESS_MODULE = ORCHESTRATION_ROOT / "forecasting_success.py"
FORECASTING_EXECUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_execution.py"
FORECASTING_CONTEXT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
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
        "energy_trading.application.errors",
        "energy_trading.application.orchestration.parallel_ingestion_failure_runtime_handling",
        "energy_trading.application.orchestration.parallel_ingestion_transition",
        "energy_trading.application.orchestration.parallel_ingestion_workflow",
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_node",
        "energy_trading.application.orchestration.state",
        "END",
        "START",
        "StateGraph",
        "CompiledStateGraph",
        "InvalidRequestError",
        "ParallelIngestionFailureRuntimeHandlingService",
        "ParallelIngestionWorkflowStep",
        "RegulatoryIntelligenceWorkflowNodeAdapter",
        "WorkflowPhase",
        "WorkflowState",
        "WorkflowStatus",
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


def test_failure_selection_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_SELECTION_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_SELECTION_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_attempt_number_module_remains_langgraph_free() -> None:
    names = imported_names(ATTEMPT_NUMBER_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(ATTEMPT_NUMBER_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_context_resolution_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_CONTEXT_RESOLUTION_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_CONTEXT_RESOLUTION_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_context_preparation_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_CONTEXT_PREPARATION_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_CONTEXT_PREPARATION_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_strict_single_failure_selector_module_remains_langgraph_free() -> None:
    names = imported_names(STRICT_SINGLE_FAILURE_SELECTOR_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(STRICT_SINGLE_FAILURE_SELECTOR_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_initial_attempt_number_source_module_remains_langgraph_free() -> None:
    names = imported_names(INITIAL_ATTEMPT_NUMBER_SOURCE_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(INITIAL_ATTEMPT_NUMBER_SOURCE_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_initial_failure_policy_module_remains_langgraph_free() -> None:
    names = imported_names(INITIAL_FAILURE_POLICY_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(INITIAL_FAILURE_POLICY_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_failure_runtime_handling_module_remains_langgraph_free() -> None:
    names = imported_names(FAILURE_RUNTIME_HANDLING_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FAILURE_RUNTIME_HANDLING_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_forecasting_plan_module_remains_langgraph_free() -> None:
    names = imported_names(FORECASTING_PLAN_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FORECASTING_PLAN_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_forecasting_success_module_remains_langgraph_free() -> None:
    names = imported_names(FORECASTING_SUCCESS_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FORECASTING_SUCCESS_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_forecasting_execution_module_remains_langgraph_free() -> None:
    names = imported_names(FORECASTING_EXECUTION_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FORECASTING_EXECUTION_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_forecasting_context_module_remains_langgraph_free() -> None:
    names = imported_names(FORECASTING_CONTEXT_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(FORECASTING_CONTEXT_MODULE)
    assert not any(
        is_forbidden(module, ("langgraph", "langchain", "langchain_core")) for module in modules
    )


def test_regulatory_intelligence_workflow_node_module_remains_langgraph_free() -> None:
    names = imported_names(REGULATORY_INTELLIGENCE_WORKFLOW_NODE_MODULE)
    assert "langgraph" not in names
    assert "langchain" not in names
    assert "langchain_core" not in names
    modules = imported_modules(REGULATORY_INTELLIGENCE_WORKFLOW_NODE_MODULE)
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
    assert "WorkflowPhase" in names
    assert "WorkflowStatus" in names
    assert "ParallelIngestionWorkflowStep" in names
    assert "ParallelIngestionFailureRuntimeHandlingService" in names
    assert "advance_after_parallel_ingestion" in names
    assert "InvalidRequestError" in names
    assert "AgentPort" not in names
    assert "AgentName" not in names
    assert "ParallelIngestionPlan" not in names
    assert "ParallelIngestionSuccess" not in names
    assert "ParallelIngestionExecutionPort" not in names
    assert "ParallelIngestionWorkflowContextPort" not in names
    assert "ConcurrentParallelIngestionExecutor" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
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
    assert "ParallelIngestionFailureSelectionPort" not in names
    assert "ParallelIngestionAttemptNumberPort" not in names
    assert "ParallelIngestionFailureContextResolutionService" not in names
    assert "ParallelIngestionFailureContextPreparationService" not in names
    assert "StrictSingleParallelIngestionFailureSelector" not in names
    assert "InitialParallelIngestionAttemptNumberSource" not in names
    assert "InitialParallelIngestionFailurePolicy" not in names
    assert "WeatherAndRenewableForecastAgent" not in names
    assert "HydroResourcesAgent" not in names
    assert "GenerationAvailabilityAgent" not in names
    assert "NewsIntelligenceAgent" not in names
    assert "MarketMonitoringAgent" not in names
    assert "RegulatoryIntelligenceAgent" not in names
    assert "ConsumerLoadForecastAgent" not in names
    assert "DAMPriceForecastAgent" not in names
    assert "DAMPriceForecastModelPort" not in names
    assert "DAMPriceForecastModelRequest" not in names
    assert "ForecastingPlan" not in names
    assert "ForecastingSuccess" not in names
    assert "ForecastingExecutionPort" not in names
    assert "ForecastingWorkflowContextPort" not in names
    assert "RegulatoryIntelligenceQueryExecutionService" not in names
    assert "RegulatoryIntelligenceWorkflowStep" not in names
    assert "RegulatoryIntelligenceWorkflowRequest" not in names
    assert "RegulatoryIntelligenceWorkflowContextPort" not in names
    assert "RegulatoryIntelligenceWorkflowNodeAdapter" in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.parallel_ingestion_workflow" in modules
    assert "energy_trading.application.orchestration.parallel_ingestion_transition" in modules
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_runtime_handling"
        in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        not in modules
    )
    assert "energy_trading.application.orchestration.parallel_ingestion" not in modules
    assert "energy_trading.application.orchestration.forecasting_plan" not in modules
    assert "energy_trading.application.orchestration.forecasting_success" not in modules
    assert "energy_trading.application.orchestration.forecasting_execution" not in modules
    assert "energy_trading.application.orchestration.forecasting_context" not in modules
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
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_selection"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_attempt_number" not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context_resolution"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context_preparation"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_strict_single_failure_selector"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_initial_attempt_number_source"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_initial_failure_policy"
        not in modules
    )
    assert "energy_trading.application.agents.weather_and_renewable_forecast" not in modules
    assert "energy_trading.application.agents.hydro_resources" not in modules
    assert "energy_trading.application.agents.generation_availability" not in modules
    assert "energy_trading.application.agents.news_intelligence" not in modules
    assert "energy_trading.application.agents.market_monitoring" not in modules
    assert "energy_trading.application.agents.regulatory_intelligence" not in modules
    assert "energy_trading.application.agents.consumer_load_forecast" not in modules
    assert "energy_trading.application.agents.dam_price_forecast" not in modules
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_query_execution"
        not in modules
    )
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_step"
        not in modules
    )
    assert "energy_trading.application.orchestration.regulatory_intelligence_context" not in modules
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_node" in modules
    )


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
    assert "add_conditional_edges" in call_names
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


def test_graph_factory_requires_injected_step_and_runtime_failure_handler() -> None:
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
    ]
    regulatory_annotation = factory.args.kwonlyargs[0].annotation
    step_annotation = factory.args.kwonlyargs[1].annotation
    handler_annotation = factory.args.kwonlyargs[2].annotation
    assert regulatory_annotation is not None
    assert step_annotation is not None
    assert handler_annotation is not None
    assert ast.unparse(regulatory_annotation) == "RegulatoryIntelligenceWorkflowNodeAdapter"
    assert ast.unparse(step_annotation) == "ParallelIngestionWorkflowStep"
    assert ast.unparse(handler_annotation) == "ParallelIngestionFailureRuntimeHandlingService"
    assert factory.args.kw_defaults == [None, None, None]


def test_graph_topology_includes_transition_node_without_lower_deps() -> None:
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
    assert "parallel_ingestion_failure_transition" not in string_constants
    add_node_count = 0
    add_edge_count = 0
    add_conditional_edges_count = 0
    constructed: list[str] = []
    transition_calls = 0
    handler_calls = 0
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
        elif name == "add_conditional_edges":
            add_conditional_edges_count += 1
        elif name == "advance_after_parallel_ingestion":
            transition_calls += 1
        elif name == "handle":
            handler_calls += 1
        if name in {
            "ParallelIngestionWorkflowStep",
            "ParallelIngestionFailureRuntimeHandlingService",
            "ConcurrentParallelIngestionExecutor",
            "ParallelIngestionPlan",
            "ParallelIngestionSuccess",
            "WeatherAndRenewableForecastAgent",
            "HydroResourcesAgent",
            "GenerationAvailabilityAgent",
            "NewsIntelligenceAgent",
            "MarketMonitoringAgent",
            "RegulatoryIntelligenceAgent",
            "ConsumerLoadForecastAgent",
            "DAMPriceForecastAgent",
            "RegulatoryIntelligenceWorkflowStep",
            "RegulatoryIntelligenceQueryExecutionService",
            "RegulatoryIntelligenceWorkflowContextPort",
            "RegulatoryIntelligenceWorkflowNodeAdapter",
            "ForecastingWorkflowContextPort",
        }:
            constructed.append(name)
    assert add_node_count == 4
    assert add_edge_count == 3
    assert add_conditional_edges_count == 2
    assert transition_calls == 1
    assert handler_calls == 1
    assert constructed == []
    assert "FailurePolicyPort" not in source
    assert "FailureAction" not in source
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
    assert "ParallelIngestionFailureSelectionPort" not in source
    assert "parallel_ingestion_failure_selection" not in source
    assert "ParallelIngestionAttemptNumberPort" not in source
    assert "parallel_ingestion_attempt_number" not in source
    assert "ParallelIngestionFailureContextResolutionService" not in source
    assert "parallel_ingestion_failure_context_resolution" not in source
    assert "ParallelIngestionFailureContextPreparationService" not in source
    assert "parallel_ingestion_failure_context_preparation" not in source
    assert "StrictSingleParallelIngestionFailureSelector" not in source
    assert "parallel_ingestion_strict_single_failure_selector" not in source
    assert "InitialParallelIngestionAttemptNumberSource" not in source
    assert "parallel_ingestion_initial_attempt_number_source" not in source
    assert "InitialParallelIngestionFailurePolicy" not in source
    assert "parallel_ingestion_initial_failure_policy" not in source
    assert "RegulatoryIntelligenceWorkflowContextPort" not in source
    assert "regulatory_intelligence_context" not in source
    assert "ForecastingWorkflowContextPort" not in source
    assert "forecasting_context" not in source
    assert "RegulatoryIntelligenceWorkflowNodeAdapter" in source
    assert "regulatory_intelligence_workflow_node" in source
    assert "RegulatoryIntelligenceWorkflowStep" not in source
    assert "regulatory_intelligence_workflow_step" not in source
    assert "ParallelIngestionFailureRuntimeHandlingService" in source
    assert "parallel_ingestion_failure_runtime_handling" in source
    assert "add_conditional_edges" in source
    identifiers = _identifier_names(GRAPH_MODULE)
    assert "replace" not in identifiers
    assert "WorkflowPhase" in identifiers
    assert "WorkflowStatus" in identifiers
    assert ".exceptions" not in source
    assert "__cause__" not in source


def test_graph_catches_only_base_exception_group_at_phase2_step_boundary() -> None:
    tree = ast.parse(GRAPH_MODULE.read_text(encoding="utf-8"), filename=str(GRAPH_MODULE))
    handlers = [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]
    assert len(handlers) == 1
    handler = handlers[0]
    assert isinstance(handler.type, ast.Name)
    assert handler.type.id == "BaseExceptionGroup"
    caught_types = {ast.unparse(node.type) for node in handlers if node.type is not None}
    assert caught_types == {"BaseExceptionGroup"}
    assert "Exception" not in caught_types
    assert "BaseException" not in caught_types


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
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "build_workflow_graph" not in app_source
    assert "langgraph" not in app_source
    assert "workflow_entry" not in app_source
    assert "parallel_ingestion" not in app_source
    assert "parallelingestionworkflowstep" not in app_source
