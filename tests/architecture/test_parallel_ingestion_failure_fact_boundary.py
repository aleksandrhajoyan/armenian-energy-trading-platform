"""Parallel-ingestion sanitized failure-fact classification stays application-owned."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
FACT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_failure_fact.py"
AGENT_FAILURE_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_agent_failure.py"
EXTRACTION_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_exception_group.py"
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
    "energy_trading.application.agents.weather_and_renewable_forecast",
    "energy_trading.application.agents.hydro_resources",
    "energy_trading.application.agents.generation_availability",
    "energy_trading.application.agents.news_intelligence",
    "energy_trading.application.agents.market_monitoring",
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
        "BaseExceptionGroup",
        "TracebackType",
        "WorkflowState",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "ParallelIngestionPlan",
        "ParallelIngestionSuccess",
        "ParallelIngestionExecutionPort",
        "ParallelIngestionWorkflowContextPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "WeatherAndRenewableForecastAgent",
        "HydroResourcesAgent",
        "GenerationAvailabilityAgent",
        "NewsIntelligenceAgent",
        "MarketMonitoringAgent",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
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
        "Protocol",
        "ABC",
        "traceback",
        "exc_info",
        "format_exc",
        "format_tb",
        "extract_tb",
        "print_exc",
        "WorkflowState",
        "FailurePolicyContext",
        "FailurePolicyPort",
        "FailureAction",
        "build_parallel_ingestion_failure_policy_context",
        "execute_parallel_ingestion_failure_action",
        "ParallelIngestionFailureDecisionService",
        "ParallelIngestionFailureHandlingService",
        "fail_parallel_ingestion",
        "advance_after_parallel_ingestion",
        "extract_parallel_ingestion_agent_failures",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionWorkflowStep",
        "registry",
        "factory",
        "visitor",
        "tenacity",
        "backoff",
        "asyncio",
        "TaskGroup",
        "sleep",
        "retry",
        "fallback",
        "attempt_number",
        "split",
        "subgroup",
        "derive",
        "__name__",
        "__context__",
        "__traceback__",
    }
)

FORBIDDEN_FACT_FIELDS = frozenset(
    {
        "exception",
        "cause",
        "message",
        "traceback",
        "attempt_number",
        "workflow_state",
        "diagnostics",
        "retryable",
        "severity",
        "timestamp",
        "provider",
        "vendor",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.agents.base",
        "energy_trading.application.errors",
        "energy_trading.application.orchestration.parallel_ingestion_agent_failure",
    }
)

UNWIRED_MODULES = (
    GRAPH_MODULE,
    WORKFLOW_MODULE,
    EXECUTOR_MODULE,
    EXTRACTION_MODULE,
    FAILURE_POLICY_MODULE,
    DECISION_MODULE,
    CONTEXT_BUILDER_MODULE,
    ACTION_MODULE,
    HANDLING_MODULE,
    STATE_MODULE,
    AGENT_FAILURE_MODULE,
)


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


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


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    return tuple(
        item.target.id
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )


def _annassign_field_annotations(path: Path, class_name: str) -> dict[str, str]:
    class_def = _class_def(path, class_name)
    annotations: dict[str, str] = {}
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            annotations[item.target.id] = ast.unparse(item.annotation)
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


def _call_names(function: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _dataclass_keywords(class_def: ast.ClassDef) -> dict[str, object]:
    for decorator in class_def.decorator_list:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            if decorator.func.id != "dataclass":
                continue
            return {
                keyword.arg: keyword.value.value
                for keyword in decorator.keywords
                if keyword.arg is not None and isinstance(keyword.value, ast.Constant)
            }
    return {}


def test_classification_module_belongs_to_application_orchestration() -> None:
    assert FACT_MODULE.parent == ORCHESTRATION_ROOT
    assert FACT_MODULE.exists()


def test_classification_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(FACT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(FACT_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(FACT_MODULE)
    assert "AgentName" in names
    assert "ApplicationError" in names
    assert "ParallelIngestionAgentFailure" in names
    assert "dataclass" in names
    assert "WorkflowState" not in names
    assert "FailurePolicyContext" not in names
    assert "FailurePolicyPort" not in names
    assert "FailureAction" not in names
    assert "ParallelIngestionFailureDecisionService" not in names
    assert "ParallelIngestionFailureHandlingService" not in names
    assert "build_parallel_ingestion_failure_policy_context" not in names
    assert "execute_parallel_ingestion_failure_action" not in names
    assert "extract_parallel_ingestion_agent_failures" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_classification_module_exposes_exactly_one_dto_and_one_function() -> None:
    public_functions = _public_function_defs(FACT_MODULE)
    assert [node.name for node in public_functions] == ["classify_parallel_ingestion_agent_failure"]
    assert _module_class_names(FACT_MODULE) == ["ParallelIngestionFailureFact"]
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name == "ParallelIngestionFailureFact":
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/parallel_ingestion_failure_fact.py"
    ]
    tree = ast.parse(FACT_MODULE.read_text(encoding="utf-8"), filename=str(FACT_MODULE))
    async_functions = [node.name for node in tree.body if isinstance(node, ast.AsyncFunctionDef)]
    assert async_functions == []
    protocols = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "Protocol")
            or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
            for base in node.bases
        )
    ]
    assert protocols == []


def test_failure_fact_is_frozen_with_exact_two_fields() -> None:
    class_def = _class_def(FACT_MODULE, "ParallelIngestionFailureFact")
    keywords = _dataclass_keywords(class_def)
    assert keywords.get("frozen") is True
    assert keywords.get("slots") is True
    fields = _annassign_field_names(FACT_MODULE, "ParallelIngestionFailureFact")
    assert fields == ("agent_name", "error_code")
    leaked = sorted(name for name in fields if name in FORBIDDEN_FACT_FIELDS)
    assert leaked == []
    annotations = _annassign_field_annotations(FACT_MODULE, "ParallelIngestionFailureFact")
    assert annotations == {
        "agent_name": "AgentName",
        "error_code": "str",
    }
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__post_init__"]


def test_classifier_signature_is_one_attributed_failure_to_fact() -> None:
    classifier = _public_function_defs(FACT_MODULE)[0]
    assert classifier.name == "classify_parallel_ingestion_agent_failure"
    assert tuple(arg.arg for arg in classifier.args.args) == ("failure",)
    assert classifier.args.posonlyargs == []
    assert classifier.args.kwonlyargs == []
    assert classifier.args.vararg is None
    assert classifier.args.kwarg is None
    assert ast.unparse(classifier.args.args[0].annotation) == "ParallelIngestionAgentFailure"
    assert ast.unparse(classifier.returns) == "ParallelIngestionFailureFact"


def test_classifier_reuses_application_error_code_without_text_or_class_names() -> None:
    classifier = _public_function_defs(FACT_MODULE)[0]
    call_names = _call_names(classifier)
    assert "isinstance" in call_names
    assert "ParallelIngestionFailureFact" in call_names
    assert "str" not in call_names
    assert "repr" not in call_names
    assert "type" not in call_names
    assert "format_exc" not in call_names
    isinstance_checks = [
        ast.unparse(node)
        for node in ast.walk(classifier)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "isinstance"
    ]
    assert "isinstance(cause, ApplicationError)" in isinstance_checks
    code_reads = [
        ast.unparse(node)
        for node in ast.walk(classifier)
        if isinstance(node, ast.Attribute) and node.attr == "code"
    ]
    assert "cause.code" in code_reads
    cause_reads = [
        ast.unparse(node)
        for node in ast.walk(classifier)
        if isinstance(node, ast.Attribute) and node.attr == "__cause__"
    ]
    assert "failure.__cause__" in cause_reads
    constructed = [
        node
        for node in ast.walk(classifier)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ParallelIngestionFailureFact"
    ]
    assert len(constructed) == 1
    call = constructed[0]
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in call.keywords}
    assert keywords == {
        "agent_name": "failure.agent_name",
        "error_code": "error_code",
    }
    identifiers = _identifier_names(FACT_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(FACT_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = FACT_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "traceback" not in lowered
    assert "__cause__" in source
    assert "__context__" not in source
    assert "__traceback__" not in source
    assert "__name__" not in source
    assert "str(" not in source
    assert "repr(" not in source
    assert "parallel_ingestion_unexpected_failure" in source
    assert "time.sleep" not in lowered
    assert "asyncio.sleep" not in lowered
    assert "FailurePolicyContext" not in source
    assert "extract_parallel_ingestion_agent_failures" not in source


def test_graph_policy_extractor_and_executor_remain_unwired_to_classification() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "classify_parallel_ingestion_agent_failure" not in names
        assert "ParallelIngestionFailureFact" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.parallel_ingestion_failure_fact"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "classify_parallel_ingestion_agent_failure" not in source
        assert "ParallelIngestionFailureFact" not in source
        assert "parallel_ingestion_failure_fact" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "add_conditional_edges" not in graph_source


def test_api_composition_does_not_import_or_construct_classification() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_failure_fact",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "classify_parallel_ingestion_agent_failure" not in names
        assert "ParallelIngestionFailureFact" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "classify_parallel_ingestion_agent_failure" not in app_source
    assert "parallelingestionfailurefact" not in app_source
    assert "parallel_ingestion_failure_fact" not in app_source
