"""Parallel-ingestion workflow-context Protocol stays typed and LangGraph-free."""

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
CONTEXT_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_context.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
PLAN_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion.py"
EXECUTOR_MODULE = ORCHESTRATION_ROOT / "parallel_ingestion_executor.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
FAILURE_POLICY_MODULE = ORCHESTRATION_ROOT / "failure_policy.py"
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
        "Exception",
        "BaseException",
        "ApplicationError",
        "Optional",
        "Session",
        "AsyncSession",
        "Engine",
        "Connection",
        "Redis",
        "RedisClient",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "WorkflowState",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "AgentPort",
        "ConcurrentParallelIngestionExecutor",
        "ParallelIngestionExecutionPort",
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
        "Optional",
        "redis_get",
        "db_load",
        "insert",
        "commit",
        "save_row",
        "Session",
        "AsyncSession",
        "Redis",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "TaskGroup",
        "gather",
    }
)

APPLICATION_IMPLEMENTATION_NAMES = frozenset(
    {
        "InMemoryParallelIngestionWorkflowContext",
        "RedisParallelIngestionWorkflowContext",
        "PostgresParallelIngestionWorkflowContext",
        "FilesystemParallelIngestionWorkflowContext",
        "ParallelIngestionWorkflowContext",
        "WorkflowContextStore",
        "ParallelIngestionContextRepository",
        "LangGraphParallelIngestionWorkflowContext",
    }
)

DURABLE_IMPLEMENTATION_NAMES = frozenset(
    {
        "RedisParallelIngestionWorkflowContext",
        "PostgresParallelIngestionWorkflowContext",
        "FilesystemParallelIngestionWorkflowContext",
        "WorkflowContextStore",
        "ParallelIngestionContextRepository",
        "LangGraphParallelIngestionWorkflowContext",
    }
)

APPLICATION_ROOT = PRODUCTION_ROOT / "application"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "typing",
        "energy_trading.application.orchestration.parallel_ingestion",
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


def _async_method(class_def: ast.ClassDef, method_name: str) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name:
            return node
    msg = f"async method {method_name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def test_context_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(CONTEXT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(CONTEXT_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(CONTEXT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []


def test_context_port_is_nongeneric_protocol_with_exact_async_operations() -> None:
    class_def = _class_def(CONTEXT_MODULE, "ParallelIngestionWorkflowContextPort")
    assert class_def.name == "ParallelIngestionWorkflowContextPort"
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert "Generic" not in bases
    assert list(class_def.type_params) == []
    source = CONTEXT_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    defined_nodes = [
        node for node in class_def.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert [node.name for node in defined_nodes] == ["resolve_plan", "record_success"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in defined_nodes)


def test_resolve_plan_annotations_match_workflow_state_and_plan() -> None:
    class_def = _class_def(CONTEXT_MODULE, "ParallelIngestionWorkflowContextPort")
    resolve_fn = _async_method(class_def, "resolve_plan")
    assert tuple(arg.arg for arg in resolve_fn.args.args) == ("self", "workflow_id")
    assert resolve_fn.args.vararg is None
    assert resolve_fn.args.kwarg is None
    assert resolve_fn.args.kwonlyargs == []
    assert async_function_arg_names(CONTEXT_MODULE, "resolve_plan") == ("self", "workflow_id")
    assert resolve_fn.args.args[1].annotation is not None
    assert resolve_fn.returns is not None
    workflow_id_type = _annassign_field_annotations(STATE_MODULE, "WorkflowState")["workflow_id"]
    assert ast.unparse(resolve_fn.args.args[1].annotation) == workflow_id_type
    assert ast.unparse(resolve_fn.returns) == "ParallelIngestionPlan"


def test_record_success_annotations_match_workflow_state_and_success() -> None:
    class_def = _class_def(CONTEXT_MODULE, "ParallelIngestionWorkflowContextPort")
    record_fn = _async_method(class_def, "record_success")
    assert tuple(arg.arg for arg in record_fn.args.args) == ("self", "workflow_id", "success")
    assert record_fn.args.vararg is None
    assert record_fn.args.kwarg is None
    assert record_fn.args.kwonlyargs == []
    assert async_function_arg_names(CONTEXT_MODULE, "record_success") == (
        "self",
        "workflow_id",
        "success",
    )
    assert record_fn.args.args[1].annotation is not None
    assert record_fn.args.args[2].annotation is not None
    assert record_fn.returns is not None
    workflow_id_type = _annassign_field_annotations(STATE_MODULE, "WorkflowState")["workflow_id"]
    assert ast.unparse(record_fn.args.args[1].annotation) == workflow_id_type
    assert ast.unparse(record_fn.args.args[2].annotation) == "ParallelIngestionSuccess"
    assert ast.unparse(record_fn.returns) == "None"


def test_context_public_contract_excludes_generic_storage_and_runtime_types() -> None:
    names = annotation_type_names(CONTEXT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(CONTEXT_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    source = CONTEXT_MODULE.read_text(encoding="utf-8")
    assert "langgraph" not in source.lower()
    assert "langchain" not in source.lower()
    assert "redis" not in source.lower()
    assert "sqlalchemy" not in source.lower()
    assert "psycopg" not in source.lower()


def test_application_context_module_has_no_concrete_implementation() -> None:
    assert _module_class_names(CONTEXT_MODULE) == ["ParallelIngestionWorkflowContextPort"]
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in APPLICATION_IMPLEMENTATION_NAMES:
                application_implementations.append(
                    f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}"
                )
            bases = _base_names(node)
            if "ParallelIngestionWorkflowContextPort" in bases and node.name != (
                "ParallelIngestionWorkflowContextPort"
            ):
                application_implementations.append(
                    f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}"
                )
    assert application_implementations == []
    durable_implementations: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in DURABLE_IMPLEMENTATION_NAMES:
                durable_implementations.append(
                    f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}"
                )
    assert durable_implementations == []


def test_workflow_state_shape_is_unchanged_by_the_context_port() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "ParallelIngestionWorkflowContextPort" not in names
    assert "ParallelIngestionPlan" not in names
    assert "ParallelIngestionSuccess" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.parallel_ingestion_context" not in modules
    assert "energy_trading.application.orchestration.parallel_ingestion" not in modules


def test_graph_executor_and_failure_policy_remain_unwired_to_the_context_port() -> None:
    for path in (GRAPH_MODULE, EXECUTOR_MODULE, FAILURE_POLICY_MODULE, PLAN_MODULE):
        names = imported_names(path)
        assert "ParallelIngestionWorkflowContextPort" not in names
        modules = imported_modules(path)
        assert "energy_trading.application.orchestration.parallel_ingestion_context" not in modules
        source = path.read_text(encoding="utf-8")
        assert "ParallelIngestionWorkflowContextPort" not in source
        assert "resolve_plan" not in source
        assert "record_success" not in source


def test_api_composition_does_not_import_or_construct_context_port() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.parallel_ingestion_context",
    )
    assert collect_import_violations(API_ROOT, forbidden_wiring) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "ParallelIngestionWorkflowContextPort" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "parallelingestionworkflowcontextport" not in app_source
    assert "parallel_ingestion_context" not in app_source
