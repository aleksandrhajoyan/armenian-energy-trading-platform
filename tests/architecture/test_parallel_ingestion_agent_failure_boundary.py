"""Phase 2 agent-failure attribution stays application-owned and LangGraph-free."""

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
FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXCEPTION_GROUP_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_executor.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
DECISION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_decision.py"
CONTEXT_BUILDER_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_context.py"
ACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_action.py"
HANDLING_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_handling.py"
WORKFLOW_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_workflow.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
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
        "Protocol",
        "ABC",
        "ExceptionGroup",
        "BaseException",
        "traceback",
        "TracebackType",
        "WorkflowState",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "AdapterDiagnostic",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Mapping",
        "ExceptionGroup",
        "BaseException",
        "traceback",
        "WorkflowState",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "build_parallel_ingestion_failure_policy_context",
        "execute_parallel_ingestion_failure_action",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "fail_parallel_ingestion",
        "registry",
        "factory",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
        "cause",
        "original_exception",
        "exception",
        "payload",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.base",
    }
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


def test_attribution_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(FAILURE_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(FAILURE_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(FAILURE_MODULE)
    assert "AgentName" in names
    assert "WorkflowState" not in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_attribution_module_exposes_exactly_one_production_class() -> None:
    assert _module_class_names(FAILURE_MODULE) == ["ParallelIngestionAgentFailure"]
    class_def = _class_def(FAILURE_MODULE, "ParallelIngestionAgentFailure")
    assert _base_names(class_def) == {"Exception"}
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name == "ParallelIngestionAgentFailure":
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/parallel_ingestion_agent_failure.py"
    ]


def test_constructor_accepts_only_agent_name() -> None:
    class_def = _class_def(FAILURE_MODULE, "ParallelIngestionAgentFailure")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self", "agent_name")
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert ast.unparse(init_fn.args.args[1].annotation) == "AgentName"
    attribute_stores = [
        node.attr
        for node in ast.walk(init_fn)
        if isinstance(node, ast.Attribute)
        and isinstance(node.ctx, ast.Store)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    ]
    assert attribute_stores == ["agent_name"]


def test_module_has_no_dto_traceback_or_policy_surface() -> None:
    identifiers = _identifier_names(FAILURE_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(FAILURE_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = FAILURE_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "traceback" not in lowered
    assert "__cause__" not in source
    assert "ExceptionGroup" not in source
    assert "tenacity" not in lowered


def test_policy_graph_and_handling_remain_unwired_to_attribution() -> None:
    for path in (
        GRAPH_MODULE,
        WORKFLOW_MODULE,
        FAILURE_POLICY_MODULE,
        DECISION_MODULE,
        CONTEXT_BUILDER_MODULE,
        ACTION_MODULE,
        HANDLING_MODULE,
        STATE_MODULE,
    ):
        names = imported_names(path)
        assert "ParallelIngestionAgentFailure" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_agent_failure"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "ParallelIngestionAgentFailure" not in source
        assert "parallel_ingestion_agent_failure" not in source
    executor_names = imported_names(EXECUTOR_MODULE)
    assert "ParallelIngestionAgentFailure" in executor_names
    executor_modules = imported_modules(EXECUTOR_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_agent_failure"
        in executor_modules
    )
    extractor_names = imported_names(EXCEPTION_GROUP_MODULE)
    assert "ParallelIngestionAgentFailure" in extractor_names
    extractor_modules = imported_modules(EXCEPTION_GROUP_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_agent_failure"
        in extractor_modules
    )
    fact_names = imported_names(FACT_MODULE)
    assert "ParallelIngestionAgentFailure" in fact_names
    fact_modules = imported_modules(FACT_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_agent_failure" in fact_modules
    )


def test_api_composition_does_not_import_or_construct_attribution() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_agent_failure",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "ParallelIngestionAgentFailure" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelingestionagentfailure" not in app_source
    assert "parallel_ingestion_agent_failure" not in app_source
