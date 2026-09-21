"""Forecasting failure-policy decision service stays application-owned."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
DECISION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_decision.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
INITIAL_POLICY_MODULE = ORCHESTRATION_ROOT / "forecasting_initial_failure_policy.py"
INITIAL_ATTEMPT_MODULE = ORCHESTRATION_ROOT / "forecasting_initial_attempt_number_source.py"
RESOLUTION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context_resolution.py"
PREPARATION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_context_preparation.py"
FAILURE_TRANSITION_MODULE = ORCHESTRATION_ROOT / "forecasting_failure_transition.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "forecasting_workflow.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "forecasting_executor.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
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
        "Exception",
        "BaseException",
        "WorkflowState",
        "WorkflowStatus",
        "InitialForecastingFailurePolicy",
        "InitialParallelIngestionFailurePolicy",
        "ParallelIngestionFailureDecisionService",
        "ForecastingAttemptNumberPort",
        "InitialForecastingAttemptNumberSource",
        "ForecastingFailureSelectionPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingFailureFact",
        "ForecastingAgentFailure",
        "ForecastingFailureContextResolutionService",
        "ForecastingFailureContextPreparationService",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "AgentPort",
        "AgentName",
        "AdapterDiagnostic",
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
        "Exception",
        "BaseException",
        "WorkflowState",
        "WorkflowStatus",
        "fail_after_forecasting",
        "advance_after_forecasting",
        "InitialForecastingFailurePolicy",
        "InitialParallelIngestionFailurePolicy",
        "ParallelIngestionFailureDecisionService",
        "ForecastingAttemptNumberPort",
        "InitialForecastingAttemptNumberSource",
        "ForecastingFailureSelectionPort",
        "StrictSingleForecastingFailureSelector",
        "ForecastingFailureFact",
        "ForecastingAgentFailure",
        "ForecastingFailureContextResolutionService",
        "ForecastingFailureContextPreparationService",
        "ParallelForecastingExecutionService",
        "ForecastingWorkflowStep",
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
        "wait",
        "phase",
        "error_code",
        "attempt_number",
        "agent_name",
    }
)

FORBIDDEN_IMPLEMENTATION_NAMES = frozenset(
    {
        "DefaultFailurePolicy",
        "RetryAllDependenciesPolicy",
        "ExponentialBackoffPolicy",
        "AgentFailurePolicy",
        "StaticFailurePolicy",
        "ConservativeFailurePolicy",
        "InitialForecastingFailurePolicy",
        "InitialParallelIngestionFailurePolicy",
        "ParallelIngestionFailureDecisionService",
    }
)

CONTEXT_FIELDS = frozenset({"phase", "error_code", "attempt_number", "agent_name"})

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.failure_policy",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "policy": "FailurePolicyPort",
}

UNWIRED_MODULES = (
    GRAPH_MODULE,
    WORKFLOW_MODULE,
    EXECUTOR_MODULE,
    PREPARATION_MODULE,
    RESOLUTION_MODULE,
    INITIAL_POLICY_MODULE,
    INITIAL_ATTEMPT_MODULE,
    STATE_MODULE,
    FAILURE_POLICY_MODULE,
    FAILURE_TRANSITION_MODULE,
)


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


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


def _public_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _init_arg_annotations(class_def: ast.ClassDef) -> dict[str, str]:
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    annotations: dict[str, str] = {}
    for arg in (*init_fn.args.args, *init_fn.args.kwonlyargs):
        if arg.arg == "self" or arg.annotation is None:
            continue
        annotations[arg.arg] = ast.unparse(arg.annotation)
    return annotations


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


def _decide_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide":
            return node
    msg = "async method 'decide' not found on ForecastingFailureDecisionService"
    raise AssertionError(msg)


def test_decision_service_module_belongs_to_application_orchestration() -> None:
    assert DECISION_MODULE.parent == ORCHESTRATION_ROOT
    assert DECISION_MODULE.exists()


def test_decision_service_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(DECISION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(DECISION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(DECISION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(DECISION_MODULE)
    assert "FailureAction" in names
    assert "FailurePolicyContext" in names
    assert "FailurePolicyPort" in names
    assert "WorkflowState" not in names
    assert "WorkflowStatus" not in names
    assert "InitialForecastingFailurePolicy" not in names
    assert "InitialParallelIngestionFailurePolicy" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "ForecastingAttemptNumberPort" not in names
    assert "InitialForecastingAttemptNumberSource" not in names
    assert "ForecastingFailureSelectionPort" not in names
    assert "StrictSingleForecastingFailureSelector" not in names
    assert "ForecastingFailureFact" not in names
    assert "ForecastingAgentFailure" not in names
    assert "ForecastingFailureContextResolutionService" not in names
    assert "ForecastingFailureContextPreparationService" not in names
    assert "ParallelForecastingExecutionService" not in names
    assert "ForecastingWorkflowStep" not in names
    assert "fail_after_forecasting" not in names


def test_decision_service_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(DECISION_MODULE) == []
    assert _module_class_names(DECISION_MODULE) == ["ForecastingFailureDecisionService"]
    class_def = _class_def(DECISION_MODULE, "ForecastingFailureDecisionService")
    assert _base_names(class_def) == set()
    assert class_def.type_params == []
    assert "Protocol" not in _base_names(class_def)
    assert "ABC" not in _base_names(class_def)
    assert not any(
        (isinstance(decorator, ast.Name) and decorator.id == "dataclass")
        or (isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass")
        for decorator in class_def.decorator_list
    )
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name == "ForecastingFailureDecisionService":
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/forecasting_failure_decision.py"
    ]
    for name in FORBIDDEN_IMPLEMENTATION_NAMES:
        assert name not in _identifier_names(DECISION_MODULE)


def test_constructor_injects_exactly_the_published_failure_policy_port() -> None:
    class_def = _class_def(DECISION_MODULE, "ForecastingFailureDecisionService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self", "policy")
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [
        ast.unparse(node.func) for node in ast.walk(init_fn) if isinstance(node, ast.Call)
    ]
    assert constructed == []


def test_decide_signature_is_async_context_to_action() -> None:
    class_def = _class_def(DECISION_MODULE, "ForecastingFailureDecisionService")
    decide_fn = _decide_method(class_def)
    assert tuple(arg.arg for arg in decide_fn.args.args) == ("self", "context")
    assert decide_fn.args.posonlyargs == []
    assert decide_fn.args.kwonlyargs == []
    assert decide_fn.args.vararg is None
    assert decide_fn.args.kwarg is None
    assert decide_fn.args.args[1].annotation is not None
    assert decide_fn.returns is not None
    assert ast.unparse(decide_fn.args.args[1].annotation) == "FailurePolicyContext"
    assert ast.unparse(decide_fn.returns) == "FailureAction"
    assert async_function_arg_names(DECISION_MODULE, "decide") == ("self", "context")
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["decide"]


def test_decide_delegates_once_without_branching_or_execution() -> None:
    class_def = _class_def(DECISION_MODULE, "ForecastingFailureDecisionService")
    decide_fn = _decide_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(decide_fn)
        if isinstance(
            node,
            (
                ast.If,
                ast.IfExp,
                ast.Match,
                ast.For,
                ast.While,
                ast.Try,
                ast.With,
                ast.ListComp,
                ast.SetComp,
                ast.DictComp,
                ast.GeneratorExp,
            ),
        )
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(decide_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    policy_calls = 0
    for node in ast.walk(decide_fn):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "decide":
            policy_calls += 1
            assert len(node.args) == 1
            assert node.keywords == []
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "context"
    assert policy_calls == 1
    returns = [node for node in ast.walk(decide_fn) if isinstance(node, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Await)
    assert isinstance(returns[0].value.value, ast.Call)
    constructed = [
        node.func.id
        for node in ast.walk(decide_fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert constructed == []
    accessed_fields = sorted(
        node.attr
        for node in ast.walk(decide_fn)
        if isinstance(node, ast.Attribute) and node.attr in CONTEXT_FIELDS
    )
    assert accessed_fields == []
    identifiers = _identifier_names(DECISION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(DECISION_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = DECISION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "fail_after_forecasting" not in source
    assert "InitialForecastingFailurePolicy" not in source
    assert "InitialParallelIngestionFailurePolicy" not in source
    assert "ParallelIngestionFailureDecisionService" not in source
    assert "tenacity" not in lowered
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered


def test_graph_workflow_and_preparation_remain_unwired_to_the_decision_service() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "ForecastingFailureDecisionService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.forecasting_failure_decision" not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ForecastingFailureDecisionService" not in source
        assert "forecasting_failure_decision" not in source


def test_workflow_state_shape_is_unchanged_by_the_decision_service() -> None:
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


def test_api_composition_does_not_import_or_construct_the_decision_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.forecasting_failure_decision",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "ForecastingFailureDecisionService" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "forecastingfailuredecisionservice" not in app_source
    assert "forecasting_failure_decision" not in app_source
