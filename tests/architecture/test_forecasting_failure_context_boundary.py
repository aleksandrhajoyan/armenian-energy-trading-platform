"""Forecasting failure-policy context builder stays application-owned."""

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
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
PHASE2_CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
ATTEMPT_NUMBER_MODULE = ORCHESTRATION_ROOT / "forecasting_attempt_number.py"
SELECTION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_selection.py"
SELECTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_strict_single_failure_selector.py"
FACT_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_fact.py"
CLASSIFICATION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_classification.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "forecasting_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "forecasting_exception_group.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_executor.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
FAILURE_TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_transition.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents.consumer_load_forecast",
    "energy_trading.application.agents.dam_price_forecast",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.forecasting_failure_fact",
    "energy_trading.application.orchestration.forecasting_failure_selection",
    "energy_trading.application.orchestration.forecasting_strict_single_failure_selector",
    "energy_trading.application.orchestration.forecasting_attempt_number",
    "energy_trading.application.orchestration.forecasting_agent_failure",
    "energy_trading.application.orchestration.forecasting_exception_group",
    "energy_trading.application.orchestration.forecasting_failure_classification",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_failure_transition",
    "energy_trading.application.orchestration.parallel_ingestion_failure_context",
    "energy_trading.application.orchestration.parallel_ingestion_agent_failure",
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
    "tenacity",
    "backoff",
    "traceback",
    "pathlib",
    "os",
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
        "Callable",
        "Optional",
        "ABC",
        "Exception",
        "BaseException",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "TracebackType",
        "WorkflowState",
        "FailureAction",
        "FailurePolicyPort",
        "ForecastingFailureFact",
        "ForecastingFailureSelectionPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingAttemptNumberPort",
        "ForecastingAgentFailure",
        "ForecastingPlan",
        "ForecastingSuccess",
        "ForecastingExecutionPort",
        "ForecastingWorkflowContextPort",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "ParallelIngestionAgentFailure",
        "ParallelIngestionFailureFact",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "AgentPort",
        "AdapterDiagnostic",
        "Path",
        "PurePath",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Mapping",
        "MutableMapping",
        "Callable",
        "ABC",
        "Exception",
        "BaseException",
        "ExceptionGroup",
        "BaseExceptionGroup",
        "traceback",
        "exc_info",
        "WorkflowState",
        "FailureAction",
        "FailurePolicyPort",
        "ForecastingFailureFact",
        "ForecastingFailureSelectionPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingAttemptNumberPort",
        "ForecastingAgentFailure",
        "extract_forecasting_agent_failures",
        "classify_forecasting_agent_failure",
        "classify_forecasting_agent_failures",
        "fail_after_forecasting",
        "advance_after_forecasting",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "build_parallel_ingestion_failure_policy_context",
        "execute_parallel_ingestion_failure_action",
        "ParallelIngestionAgentFailure",
        "ParallelIngestionFailureFact",
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "CONSUMER_LOAD_FORECAST",
        "DAM_PRICE_FORECAST",
        "registry",
        "factory",
        "StateMachine",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
        "increment",
        "reset",
        "select",
        "get_attempt_number",
        "Path",
        "open",
        "environ",
        "getenv",
        "__cause__",
        "__context__",
        "__traceback__",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.base",
        "energy_trading.application.orchestration.failure_policy",
        "energy_trading.application.orchestration.state",
    }
)

UNWIRED_MODULES = (
    GRAPH_MODULE,
    WORKFLOW_MODULE,
    EXECUTOR_MODULE,
    EXTRACTION_MODULE,
    CLASSIFICATION_MODULE,
    FACT_MODULE,
    AGENT_FAILURE_MODULE,
    FAILURE_POLICY_MODULE,
    FAILURE_TRANSITION_MODULE,
    SELECTION_MODULE,
    SELECTOR_MODULE,
    ATTEMPT_NUMBER_MODULE,
    PHASE2_CONTEXT_BUILDER_MODULE,
    STATE_MODULE,
)


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _public_function_defs(path: Path) -> list[ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]


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


def test_context_builder_module_belongs_to_application_orchestration() -> None:
    assert CONTEXT_BUILDER_MODULE.parent == ORCHESTRATION_ROOT
    assert CONTEXT_BUILDER_MODULE.exists()


def test_context_builder_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(CONTEXT_BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(CONTEXT_BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(CONTEXT_BUILDER_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(CONTEXT_BUILDER_MODULE)
    assert "FailurePolicyContext" in names
    assert "WorkflowPhase" in names
    assert "AgentName" in names
    assert "FailureAction" not in names
    assert "FailurePolicyPort" not in names
    assert "WorkflowState" not in names
    assert "ForecastingFailureFact" not in names
    assert "ForecastingFailureSelectionPort" not in names
    assert "StrictSingleForecastingFailureSelector" not in names
    assert "ForecastingAttemptNumberPort" not in names
    assert "Exception" not in names
    assert "BaseException" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names


def test_context_builder_module_exposes_exactly_one_public_function() -> None:
    public_functions = _public_function_defs(CONTEXT_BUILDER_MODULE)
    assert [node.name for node in public_functions] == ["build_forecasting_failure_policy_context"]
    assert _module_class_names(CONTEXT_BUILDER_MODULE) == []
    tree = ast.parse(
        CONTEXT_BUILDER_MODULE.read_text(encoding="utf-8"),
        filename=str(CONTEXT_BUILDER_MODULE),
    )
    async_functions = [node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert async_functions == []
    protocols = [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "Protocol")
            or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
            for base in node.bases
        )
    ]
    assert protocols == []


def test_builder_signature_is_keyword_only_published_fields() -> None:
    builder = _public_function_defs(CONTEXT_BUILDER_MODULE)[0]
    assert builder.args.args == []
    assert builder.args.posonlyargs == []
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "phase",
        "error_code",
        "attempt_number",
        "agent_name",
    )
    assert ast.unparse(builder.args.kwonlyargs[0].annotation) == "WorkflowPhase"
    assert ast.unparse(builder.args.kwonlyargs[1].annotation) == "str"
    assert ast.unparse(builder.args.kwonlyargs[2].annotation) == "int"
    assert ast.unparse(builder.args.kwonlyargs[3].annotation) == "AgentName | None"
    assert ast.unparse(builder.returns) == "FailurePolicyContext"
    defaults = builder.args.kw_defaults
    assert defaults[0] is None
    assert defaults[1] is None
    assert defaults[2] is None
    assert isinstance(defaults[3], ast.Constant)
    assert defaults[3].value is None


def test_builder_constructs_published_context_once_without_branching() -> None:
    builder = _public_function_defs(CONTEXT_BUILDER_MODULE)[0]
    control = [
        type(node).__name__
        for node in ast.walk(builder)
        if isinstance(
            node,
            (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With),
        )
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(builder) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    arithmetic = [
        type(node).__name__
        for stmt in builder.body
        for node in ast.walk(stmt)
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.AugAssign))
    ]
    assert arithmetic == []
    constructed = [
        node
        for node in ast.walk(builder)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FailurePolicyContext"
    ]
    assert len(constructed) == 1
    call = constructed[0]
    assert call.args == []
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords}
    assert keywords == {
        "phase": "phase",
        "error_code": "error_code",
        "attempt_number": "attempt_number",
        "agent_name": "agent_name",
    }
    identifiers = _identifier_names(CONTEXT_BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(CONTEXT_BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = CONTEXT_BUILDER_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "traceback" not in lowered
    assert "exceptiongroup" not in lowered
    assert "fail_after_forecasting" not in source
    assert "build_parallel_ingestion_failure_policy_context" not in source
    assert "ForecastingFailureFact" not in source
    assert "ForecastingAttemptNumberPort" not in source
    assert "ForecastingFailureSelectionPort" not in source
    assert "StrictSingleForecastingFailureSelector" not in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "os.environ" not in lowered
    assert "getenv" not in lowered


def test_failure_policy_contract_remains_unchanged_and_unwired_to_the_builder() -> None:
    names = imported_names(FAILURE_POLICY_MODULE)
    assert "build_forecasting_failure_policy_context" not in names
    modules = imported_modules(FAILURE_POLICY_MODULE)
    assert "energy_trading.application.orchestration.forecasting_failure_context" not in modules
    source = FAILURE_POLICY_MODULE.read_text(encoding="utf-8")
    assert "build_forecasting_failure_policy_context" not in source
    assert "forecasting_failure_context" not in source


def test_phase2_builder_is_not_reused_as_the_phase3_function() -> None:
    names = imported_names(CONTEXT_BUILDER_MODULE)
    assert "build_parallel_ingestion_failure_policy_context" not in names
    modules = imported_modules(CONTEXT_BUILDER_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_context" not in modules
    )
    phase2_names = imported_names(PHASE2_CONTEXT_BUILDER_MODULE)
    assert "build_forecasting_failure_policy_context" not in phase2_names
    phase2_modules = imported_modules(PHASE2_CONTEXT_BUILDER_MODULE)
    assert (
        "energy_trading.application.orchestration.forecasting_failure_context" not in phase2_modules
    )
    phase2_source = PHASE2_CONTEXT_BUILDER_MODULE.read_text(encoding="utf-8")
    assert "build_forecasting_failure_policy_context" not in phase2_source
    assert "forecasting_failure_context" not in phase2_source


def test_graph_workflow_and_failure_internals_remain_unwired_to_the_builder() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "build_forecasting_failure_policy_context" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.forecasting_failure_context" not in modules
        source = path.read_text(encoding="utf-8")
        assert "build_forecasting_failure_policy_context" not in source
        assert "forecasting_failure_context" not in source


def test_workflow_state_shape_is_unchanged_by_context_builder() -> None:
    tree = ast.parse(STATE_MODULE.read_text(encoding="utf-8"), filename=str(STATE_MODULE))
    fields: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "WorkflowState":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
    assert tuple(fields) == (
        "workflow_id",
        "portfolio_id",
        "delivery_date",
        "correlation_id",
        "phase",
        "status",
        "diagnostics",
    )


def test_api_composition_does_not_import_or_construct_the_builder() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.forecasting_failure_context",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "build_forecasting_failure_policy_context" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "build_forecasting_failure_policy_context" not in app_source
    assert "forecasting_failure_context" not in app_source
