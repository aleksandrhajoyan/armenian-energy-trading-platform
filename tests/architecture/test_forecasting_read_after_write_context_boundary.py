"""In-memory read-after-write forecasting context stays delegating, local, and unwired."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
INFRA_ORCHESTRATION_ROOT = PRODUCTION_ROOT / "infrastructure" / "orchestration"
WRAPPER_MODULE = INFRA_ORCHESTRATION_ROOT / "forecasting_read_after_write_context.py"
IN_MEMORY_CONTEXT_MODULE = INFRA_ORCHESTRATION_ROOT / "forecasting_context.py"
READER_MODULE = INFRA_ORCHESTRATION_ROOT / "forecasting_success_reader.py"
INFRA_PACKAGE_INIT = INFRA_ORCHESTRATION_ROOT / "__init__.py"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
CONTEXT_PORT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
READ_PORT_MODULE = ORCHESTRATION_ROOT / "forecasting_success_read.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
API_ROOT = PRODUCTION_ROOT / "api"
APP_MODULE = API_ROOT / "app.py"
WRAPPER_MODULE_NAME = (
    "energy_trading.infrastructure.orchestration.forecasting_read_after_write_context"
)
WRAPPER_CLASS = "InMemoryForecastingReadAfterWriteContext"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "__future__",
        "asyncio",
        "energy_trading.application.errors",
        "energy_trading.application.orchestration.forecasting_plan",
        "energy_trading.application.orchestration.forecasting_success",
        "energy_trading.application.orchestration.state",
        "energy_trading.infrastructure.orchestration.forecasting_context",
    }
)

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_success_read",
    "energy_trading.application.orchestration.forecasting_execution",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.infrastructure.orchestration.forecasting_success_reader",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.infrastructure.vector_store",
    "fastapi",
    "starlette",
    "langgraph",
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
    "httpx",
    "requests",
    "aiohttp",
    "pickle",
    "json",
    "shelve",
    "sqlite3",
    "pathlib",
    "os",
    "copy",
    "threading",
    "multiprocessing",
    "concurrent.futures",
    "logging",
    "datetime",
    "time",
    "tenacity",
    "backoff",
    "abc",
    "typing",
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "InMemoryForecastingSuccessReader",
        "ForecastingWorkflowContextPort",
        "ForecastingSuccessReadPort",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "Protocol",
        "ABC",
        "Generic",
        "Any",
        "Optional",
        "deepcopy",
        "setdefault",
        "pop",
        "update",
        "clear",
        "TaskGroup",
        "gather",
        "create_task",
        "sleep",
        "wait_for",
        "to_thread",
        "open",
        "dumps",
        "loads",
        "retry",
        "fallback",
        "select_model",
        "forecast",
        "execute",
        "logger",
        "getLogger",
        "now",
        "utcnow",
    }
)

FORBIDDEN_PUBLIC_METHODS = frozenset(
    {
        "set_success",
        "save_success",
        "store_success",
        "list_successes",
        "put",
        "add",
        "update",
        "delete",
        "remove",
        "clear",
        "reset",
        "get",
        "load",
        "save",
        "execute",
        "run",
        "forecast",
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

ALLOWED_SELF_ATTRIBUTES = frozenset({"_context", "_successes", "_lock"})


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    msg = f"class {class_name!r} not found in {path}"
    raise AssertionError(msg)


def _method(class_def: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return node
    msg = f"method {name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def _public_methods(class_def: ast.ClassDef) -> list[str]:
    return [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    ]


def _body_without_docstring(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.stmt]:
    return [
        node
        for node in function.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
    ]


def _identifier_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
    return names


def _wrapper_class() -> ast.ClassDef:
    return _class_def(WRAPPER_MODULE, WRAPPER_CLASS)


def _single_async_with(function: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AsyncWith:
    body = _body_without_docstring(function)
    assert len(body) == 1
    statement = body[0]
    assert isinstance(statement, ast.AsyncWith)
    assert len(statement.items) == 1
    assert ast.unparse(statement.items[0].context_expr) == "self._lock"
    assert statement.items[0].optional_vars is None
    return statement


def test_wrapper_module_belongs_to_infrastructure_orchestration() -> None:
    assert WRAPPER_MODULE.parent == INFRA_ORCHESTRATION_ROOT
    assert WRAPPER_MODULE.name == "forecasting_read_after_write_context.py"
    assert WRAPPER_MODULE.exists()


def test_wrapper_module_exposes_exactly_one_public_class_and_no_global_store() -> None:
    tree = _tree(WRAPPER_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == [WRAPPER_CLASS]
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert module_functions == []
    module_assignments: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            module_assignments.extend(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            module_assignments.append(node.target.id)
    assert module_assignments == ["_MSG_SUCCESS_NOT_FOUND"]
    message_assign = next(node for node in tree.body if isinstance(node, ast.Assign))
    assert isinstance(message_assign.value, ast.Constant)
    assert isinstance(message_assign.value.value, str)
    assert not any(isinstance(node, ast.Global | ast.Nonlocal) for node in ast.walk(tree))


def test_wrapper_is_structural_and_has_no_class_level_state() -> None:
    class_def = _wrapper_class()
    assert class_def.bases == []
    assert class_def.keywords == []
    assert class_def.decorator_list == []
    assert list(class_def.type_params) == []
    assert not any(isinstance(node, ast.Assign | ast.AnnAssign) for node in class_def.body)


def test_constructor_requires_injected_concrete_in_memory_context() -> None:
    init_fn = _method(_wrapper_class(), "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self",)
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert [arg.arg for arg in init_fn.args.kwonlyargs] == ["context"]
    assert init_fn.args.kw_defaults == [None]
    annotation = init_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "InMemoryForecastingWorkflowContext"
    assert init_fn.returns is not None
    assert ast.unparse(init_fn.returns) == "None"


def test_constructor_owns_one_lock_and_one_empty_success_mapping() -> None:
    init_fn = _method(_wrapper_class(), "__init__")
    statements = [ast.unparse(node) for node in init_fn.body]
    assert statements == [
        "self._context = context",
        "self._successes: dict[str, ForecastingSuccess] = {}",
        "self._lock = asyncio.Lock()",
    ]


def test_exactly_three_public_async_operations_with_published_signatures() -> None:
    class_def = _wrapper_class()
    assert _public_methods(class_def) == ["resolve_plan", "record_success", "get_success"]
    assert FORBIDDEN_PUBLIC_METHODS.isdisjoint(_public_methods(class_def))
    private_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("_")
    ]
    assert private_methods == ["__init__"]
    expected = {
        "resolve_plan": ([("state", "WorkflowState")], "ForecastingPlan"),
        "record_success": (
            [("state", "WorkflowState"), ("success", "ForecastingSuccess")],
            "None",
        ),
        "get_success": ([("workflow_id", "str")], "ForecastingSuccess"),
    }
    for name, (parameters, returns) in expected.items():
        function = _method(class_def, name)
        assert isinstance(function, ast.AsyncFunctionDef), name
        assert function.decorator_list == []
        assert tuple(arg.arg for arg in function.args.args) == ("self",)
        assert function.args.posonlyargs == []
        assert function.args.defaults == []
        assert function.args.vararg is None
        assert function.args.kwarg is None
        actual = [
            (arg.arg, ast.unparse(arg.annotation) if arg.annotation is not None else "")
            for arg in function.args.kwonlyargs
        ]
        assert actual == parameters, name
        assert function.args.kw_defaults == [None] * len(parameters)
        assert function.returns is not None
        assert ast.unparse(function.returns) == returns, name


def test_resolve_plan_delegates_once_and_returns_unchanged() -> None:
    function = _method(_wrapper_class(), "resolve_plan")
    body = _body_without_docstring(function)
    assert [ast.unparse(node) for node in body] == [
        "return await self._context.resolve_plan(state=state)"
    ]


def test_record_success_publishes_first_object_only_after_delegate_under_lock() -> None:
    function = _method(_wrapper_class(), "record_success")
    statement = _single_async_with(function)
    assert len(statement.body) == 2
    delegate, publish = statement.body
    assert ast.unparse(delegate) == (
        "await self._context.record_success(state=state, success=success)"
    )
    assert isinstance(publish, ast.If)
    assert ast.unparse(publish.test) == "state.workflow_id not in self._successes"
    assert publish.orelse == []
    assert [ast.unparse(node) for node in publish.body] == [
        "self._successes[state.workflow_id] = success"
    ]
    assert not any(isinstance(node, ast.Try) for node in ast.walk(function))


def test_get_success_is_locked_exact_lookup_that_fails_closed() -> None:
    function = _method(_wrapper_class(), "get_success")
    statement = _single_async_with(function)
    assert len(statement.body) == 1
    try_node = statement.body[0]
    assert isinstance(try_node, ast.Try)
    assert try_node.orelse == []
    assert try_node.finalbody == []
    assert [ast.unparse(node) for node in try_node.body] == ["return self._successes[workflow_id]"]
    assert len(try_node.handlers) == 1
    handler = try_node.handlers[0]
    assert handler.type is not None
    assert ast.unparse(handler.type) == "KeyError"
    assert handler.name is None
    assert [ast.unparse(node) for node in handler.body] == [
        "raise ResourceNotFoundError(_MSG_SUCCESS_NOT_FOUND) from None"
    ]


def test_wrapper_accesses_only_public_delegate_operations_and_own_state() -> None:
    class_def = _wrapper_class()
    for node in ast.walk(class_def):
        if not isinstance(node, ast.Attribute):
            continue
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            assert node.attr in ALLOWED_SELF_ATTRIBUTES, node.attr
        if ast.unparse(node.value) == "self._context":
            assert node.attr in {"resolve_plan", "record_success"}, node.attr
        if ast.unparse(node.value) == "self._successes":
            msg = f"unexpected mapping method {node.attr!r}"
            raise AssertionError(msg)
    source = WRAPPER_MODULE.read_text(encoding="utf-8")
    assert "_context._" not in source
    assert "_plans" not in source
    assert "_write_lock" not in source
    assert "getattr" not in source
    assert "__dict__" not in source
    assert "vars(" not in source


def test_wrapper_imports_only_published_contracts_and_the_in_memory_context() -> None:
    modules = imported_modules(WRAPPER_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(WRAPPER_MODULE) - modules == {
        "annotations",
        "ResourceNotFoundError",
        "ForecastingPlan",
        "ForecastingSuccess",
        "WorkflowState",
        "InMemoryForecastingWorkflowContext",
    }
    source = WRAPPER_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source
    assert "ConflictError" not in source


def test_wrapper_has_no_storage_retry_selection_or_background_work() -> None:
    names = annotation_type_names(WRAPPER_MODULE)
    assert names <= {
        "InMemoryForecastingWorkflowContext",
        "WorkflowState",
        "ForecastingPlan",
        "ForecastingSuccess",
        "dict",
        "str",
        "None",
    }
    identifiers = _identifier_names(WRAPPER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    code_tokens = " ".join(sorted(identifiers | imported_modules(WRAPPER_MODULE))).lower()
    for token in (
        "redis",
        "sqlalchemy",
        "postgres",
        "qdrant",
        "fastapi",
        "langgraph",
        "openai",
        "registry",
        "factory",
        "repository",
        "cache",
        "ttl",
        "persist",
        "serialize",
        "retry",
        "fallback",
        "champion",
        "ols",
        "thread",
    ):
        assert token not in code_tokens


def test_workflow_state_keeps_seven_canonical_fields() -> None:
    class_def = _class_def(STATE_MODULE, "WorkflowState")
    fields = tuple(
        item.target.id
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert fields == WORKFLOW_STATE_FIELDS


def test_application_ports_keep_their_published_operations() -> None:
    context_port = _class_def(CONTEXT_PORT_MODULE, "ForecastingWorkflowContextPort")
    assert _public_methods(context_port) == ["resolve_plan", "record_success"]
    read_port = _class_def(READ_PORT_MODULE, "ForecastingSuccessReadPort")
    assert _public_methods(read_port) == ["get_success"]
    for path in (CONTEXT_PORT_MODULE, READ_PORT_MODULE):
        assert WRAPPER_MODULE_NAME not in imported_modules(path)
        assert WRAPPER_CLASS not in path.read_text(encoding="utf-8")


def test_existing_in_memory_context_and_snapshot_reader_remain_unchanged() -> None:
    context_def = _class_def(IN_MEMORY_CONTEXT_MODULE, "InMemoryForecastingWorkflowContext")
    assert _public_methods(context_def) == ["resolve_plan", "record_success"]
    reader_def = _class_def(READER_MODULE, "InMemoryForecastingSuccessReader")
    assert _public_methods(reader_def) == ["get_success"]
    for path in (IN_MEMORY_CONTEXT_MODULE, READER_MODULE, INFRA_PACKAGE_INIT):
        assert WRAPPER_MODULE_NAME not in imported_modules(path), path
        assert WRAPPER_CLASS not in path.read_text(encoding="utf-8"), path
        assert "forecasting_read_after_write_context" not in path.read_text(encoding="utf-8")


def test_graph_and_create_app_remain_unaware_of_the_wrapper() -> None:
    for path in (GRAPH_MODULE, APP_MODULE):
        assert WRAPPER_MODULE_NAME not in imported_modules(path)
        assert WRAPPER_CLASS not in imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert WRAPPER_CLASS not in source
        assert "forecasting_read_after_write_context" not in source


def test_no_api_or_application_module_imports_the_wrapper_yet() -> None:
    for root in (API_ROOT, APPLICATION_ROOT):
        for path in sorted(root.rglob("*.py")):
            assert WRAPPER_MODULE_NAME not in imported_modules(path), path
            assert WRAPPER_CLASS not in imported_names(path), path
            assert WRAPPER_CLASS not in path.read_text(encoding="utf-8"), path
