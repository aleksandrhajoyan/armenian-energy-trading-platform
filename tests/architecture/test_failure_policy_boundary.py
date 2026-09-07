"""Application failure-policy contract remains framework-neutral and execution-free."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
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
    "numpy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
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
        "Exception",
        "BaseException",
        "ApplicationError",
        "TracebackType",
        "WorkflowState",
    }
)

FORBIDDEN_CONTEXT_FIELDS = frozenset(
    {
        "max_attempts",
        "maximum_attempts",
        "retry_limit",
        "delay",
        "backoff",
        "jitter",
        "timeout",
        "exception",
        "exc",
        "error",
        "traceback",
        "message",
        "workflow_state",
        "state",
        "callback",
        "on_retry",
        "fallback_target",
        "fallback_agent",
        "node",
        "operation",
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
    }
)

ALLOWED_CONTEXT_FIELDS = (
    "phase",
    "error_code",
    "attempt_number",
    "agent_name",
)

ALLOWED_FAILURE_ACTION_MEMBERS = (
    "RETRY",
    "FALLBACK",
    "FAIL",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "enum",
        "typing",
        "energy_trading.application.agents.base",
        "energy_trading.application.orchestration.state",
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


def _annassign_field_annotations(path: Path, class_name: str) -> dict[str, str]:
    class_def = _class_def(path, class_name)
    annotations: dict[str, str] = {}
    for item in class_def.body:
        if (
            isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and item.annotation is not None
        ):
            annotations[item.target.id] = ast.unparse(item.annotation)
    return annotations


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


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


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def test_failure_policy_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(FAILURE_POLICY_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(FAILURE_POLICY_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(FAILURE_POLICY_MODULE)
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []
    assert "WorkflowPhase" in names
    assert "AgentName" in names
    assert "WorkflowState" not in names
    assert "langgraph" not in names
    assert "RetryPolicy" not in names
    assert "tenacity" not in names


def test_failure_action_enum_surface_is_exact() -> None:
    class_def = _class_def(FAILURE_POLICY_MODULE, "FailureAction")
    assert "StrEnum" in _base_names(class_def)
    members = [
        node.targets[0].id
        for node in class_def.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    ]
    assert tuple(members) == ALLOWED_FAILURE_ACTION_MEMBERS
    values = [
        node.value.value
        for node in class_def.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
    ]
    assert values == ["retry", "fallback", "fail"]


def test_failure_policy_context_has_exact_four_fields() -> None:
    class_def = _class_def(FAILURE_POLICY_MODULE, "FailurePolicyContext")
    assert list(class_def.type_params) == []
    assert _base_names(class_def) == set()
    fields = _annassign_field_names(FAILURE_POLICY_MODULE, "FailurePolicyContext")
    assert fields == ALLOWED_CONTEXT_FIELDS
    leaked = sorted(name for name in fields if name in FORBIDDEN_CONTEXT_FIELDS)
    assert leaked == []
    annotations = _annassign_field_annotations(FAILURE_POLICY_MODULE, "FailurePolicyContext")
    assert annotations == {
        "phase": "WorkflowPhase",
        "error_code": "str",
        "attempt_number": "int",
        "agent_name": "AgentName | None",
    }
    leaked_types = sorted(name for name in annotations.values() if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_failure_policy_context_excludes_exceptions_and_execution_fields() -> None:
    names = annotation_type_names(FAILURE_POLICY_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(FAILURE_POLICY_MODULE)
    assert "TypeVar" not in identifiers
    assert "Generic" not in identifiers
    assert "Any" not in identifiers
    assert "dict" not in identifiers
    assert "Mapping" not in identifiers
    assert "Exception" not in identifiers
    assert "ApplicationError" not in identifiers
    assert "WorkflowState" not in identifiers
    assert "Callable" not in identifiers
    assert "sleep" not in identifiers
    assert "backoff" not in identifiers
    source = FAILURE_POLICY_MODULE.read_text(encoding="utf-8")
    assert "tenacity" not in source.lower()


def test_failure_policy_port_is_nongeneric_protocol_with_async_decide() -> None:
    class_def = _class_def(FAILURE_POLICY_MODULE, "FailurePolicyPort")
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert list(class_def.type_params) == []
    source = FAILURE_POLICY_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["decide"]
    decide_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide"
    )
    assert tuple(arg.arg for arg in decide_fn.args.args) == ("self", "context")
    assert decide_fn.args.vararg is None
    assert decide_fn.args.kwarg is None
    assert decide_fn.args.kwonlyargs == []
    assert async_function_arg_names(FAILURE_POLICY_MODULE, "decide") == ("self", "context")
    assert decide_fn.args.args[1].annotation is not None
    assert decide_fn.returns is not None
    assert ast.unparse(decide_fn.args.args[1].annotation) == "FailurePolicyContext"
    assert ast.unparse(decide_fn.returns) == "FailureAction"


def test_failure_policy_module_has_no_concrete_implementation() -> None:
    classes = _module_class_names(FAILURE_POLICY_MODULE)
    assert classes == ["FailureAction", "FailurePolicyContext", "FailurePolicyPort"]
    production_policy_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in FORBIDDEN_IMPLEMENTATION_NAMES:
                production_policy_classes.append(node.name)
            bases = _base_names(node)
            if "FailurePolicyPort" in bases and node.name != "FailurePolicyPort":
                production_policy_classes.append(node.name)
    assert production_policy_classes == []


def test_graph_module_does_not_import_or_inject_failure_policy() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "FailurePolicyPort" not in names
    assert "FailurePolicyContext" not in names
    assert "FailureAction" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.application.orchestration.failure_policy" not in modules
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "FailurePolicyPort" not in graph_source
    assert "decide(" not in graph_source
    assert "fail_parallel_ingestion" not in graph_source
    policy_names = imported_names(FAILURE_POLICY_MODULE)
    assert "fail_parallel_ingestion" not in policy_names
    assert "advance_after_parallel_ingestion" not in policy_names
    policy_modules = imported_modules(FAILURE_POLICY_MODULE)
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_failure_transition"
        not in policy_modules
    )
    assert (
        "energy_trading.application.orchestration.parallel_ingestion_transition"
        not in policy_modules
    )


def test_api_composition_does_not_import_or_construct_failure_policy() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.failure_policy",
        "tenacity",
        "backoff",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "FailurePolicyPort" not in names
        assert "FailurePolicyContext" not in names
        assert "FailureAction" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "failurepolicy" not in app_source
    assert "failureaction" not in app_source
