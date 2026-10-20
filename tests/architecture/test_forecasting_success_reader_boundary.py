"""In-memory forecasting-success reader stays read-only, infrastructure-owned, and unwired."""

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
READER_MODULE = INFRA_ORCHESTRATION_ROOT / "forecasting_success_reader.py"
IN_MEMORY_CONTEXT_MODULE = INFRA_ORCHESTRATION_ROOT / "forecasting_context.py"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
CONTEXT_PORT_MODULE = ORCHESTRATION_ROOT / "forecasting_context.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
API_ROOT = PRODUCTION_ROOT / "api"
APP_MODULE = API_ROOT / "app.py"
READER_MODULE_NAME = "energy_trading.infrastructure.orchestration.forecasting_success_reader"
READER_CLASS = "InMemoryForecastingSuccessReader"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "__future__",
        "collections.abc",
        "energy_trading.application.errors",
        "energy_trading.application.orchestration.forecasting_success",
    }
)

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_success_read",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.infrastructure.orchestration.forecasting_context",
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
    "asyncio",
    "threading",
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
        "InMemoryForecastingWorkflowContext",
        "ForecastingWorkflowContextPort",
        "ForecastingSuccessReadPort",
        "WorkflowState",
        "Protocol",
        "ABC",
        "Generic",
        "Any",
        "Optional",
        "deepcopy",
        "global",
        "setdefault",
        "get",
        "pop",
        "update",
        "clear",
        "Lock",
        "open",
        "dumps",
        "loads",
        "retry",
        "fallback",
        "select_model",
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
        "record_success",
        "store_success",
        "put",
        "add",
        "update",
        "delete",
        "remove",
        "clear",
        "reset",
        "list_successes",
        "get",
        "load",
        "save",
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


def test_reader_module_belongs_to_infrastructure_orchestration() -> None:
    assert READER_MODULE.parent == INFRA_ORCHESTRATION_ROOT
    assert READER_MODULE.name == "forecasting_success_reader.py"
    assert READER_MODULE.exists()


def test_reader_module_exposes_exactly_one_public_class() -> None:
    tree = _tree(READER_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == [READER_CLASS]
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


def test_reader_is_structural_and_inherits_nothing() -> None:
    class_def = _class_def(READER_MODULE, READER_CLASS)
    assert class_def.bases == []
    assert class_def.keywords == []
    assert class_def.decorator_list == []
    assert list(class_def.type_params) == []
    assert not any(isinstance(node, ast.Assign | ast.AnnAssign) for node in class_def.body)


def test_constructor_takes_required_keyword_only_successes_mapping() -> None:
    class_def = _class_def(READER_MODULE, READER_CLASS)
    init_fn = _method(class_def, "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self",)
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert [arg.arg for arg in init_fn.args.kwonlyargs] == ["successes"]
    assert init_fn.args.kw_defaults == [None]
    annotation = init_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "Mapping[str, ForecastingSuccess]"
    assert init_fn.returns is not None
    assert ast.unparse(init_fn.returns) == "None"


def test_constructor_copies_the_snapshot_mapping_once() -> None:
    class_def = _class_def(READER_MODULE, READER_CLASS)
    init_fn = _method(class_def, "__init__")
    assert len(init_fn.body) == 1
    statement = init_fn.body[0]
    assert isinstance(statement, ast.AnnAssign)
    assert ast.unparse(statement.target) == "self._successes"
    assert statement.annotation is not None
    assert ast.unparse(statement.annotation) == "dict[str, ForecastingSuccess]"
    assert statement.value is not None
    assert ast.unparse(statement.value) == "dict(successes)"


def test_get_success_is_the_only_public_async_operation() -> None:
    class_def = _class_def(READER_MODULE, READER_CLASS)
    assert _public_methods(class_def) == ["get_success"]
    private_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("_")
    ]
    assert private_methods == ["__init__"]
    assert FORBIDDEN_PUBLIC_METHODS.isdisjoint(_public_methods(class_def))
    get_fn = _method(class_def, "get_success")
    assert isinstance(get_fn, ast.AsyncFunctionDef)
    assert get_fn.decorator_list == []
    assert tuple(arg.arg for arg in get_fn.args.args) == ("self",)
    assert get_fn.args.posonlyargs == []
    assert get_fn.args.defaults == []
    assert get_fn.args.vararg is None
    assert get_fn.args.kwarg is None
    assert [arg.arg for arg in get_fn.args.kwonlyargs] == ["workflow_id"]
    assert get_fn.args.kw_defaults == [None]
    annotation = get_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "str"
    assert get_fn.returns is not None
    assert ast.unparse(get_fn.returns) == "ForecastingSuccess"


def test_get_success_is_exact_lookup_that_fails_closed() -> None:
    class_def = _class_def(READER_MODULE, READER_CLASS)
    get_fn = _method(class_def, "get_success")
    body = [
        node
        for node in get_fn.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
    ]
    assert len(body) == 1
    try_node = body[0]
    assert isinstance(try_node, ast.Try)
    assert try_node.orelse == []
    assert try_node.finalbody == []
    assert len(try_node.body) == 1
    returned = try_node.body[0]
    assert isinstance(returned, ast.Return)
    assert returned.value is not None
    assert ast.unparse(returned.value) == "self._successes[workflow_id]"
    assert len(try_node.handlers) == 1
    handler = try_node.handlers[0]
    assert handler.type is not None
    assert ast.unparse(handler.type) == "KeyError"
    assert len(handler.body) == 1
    raised = handler.body[0]
    assert isinstance(raised, ast.Raise)
    assert raised.exc is not None
    assert ast.unparse(raised.exc) == "ResourceNotFoundError(_MSG_SUCCESS_NOT_FOUND)"
    assert raised.cause is not None
    assert ast.unparse(raised.cause) == "None"


def test_reader_imports_only_mapping_success_and_error_contracts() -> None:
    modules = imported_modules(READER_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(READER_MODULE) - modules == {
        "annotations",
        "Mapping",
        "ResourceNotFoundError",
        "ForecastingSuccess",
    }
    source = READER_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_reader_has_no_storage_retry_selection_or_context_coupling() -> None:
    names = annotation_type_names(READER_MODULE)
    assert names <= {"Mapping", "str", "ForecastingSuccess", "dict", "None"}
    identifiers = _identifier_names(READER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    code_tokens = " ".join(sorted(identifiers | imported_modules(READER_MODULE))).lower()
    for token in (
        "redis",
        "sqlalchemy",
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
        "persistence",
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


def test_forecasting_context_port_and_in_memory_context_keep_two_method_contract() -> None:
    port_def = _class_def(CONTEXT_PORT_MODULE, "ForecastingWorkflowContextPort")
    assert _public_methods(port_def) == ["resolve_plan", "record_success"]
    context_def = _class_def(IN_MEMORY_CONTEXT_MODULE, "InMemoryForecastingWorkflowContext")
    assert _public_methods(context_def) == ["resolve_plan", "record_success"]
    assert READER_MODULE_NAME not in imported_modules(IN_MEMORY_CONTEXT_MODULE)
    assert READER_CLASS not in IN_MEMORY_CONTEXT_MODULE.read_text(encoding="utf-8")


def test_graph_and_create_app_remain_unaware_of_the_reader() -> None:
    for path in (GRAPH_MODULE, APP_MODULE):
        assert READER_MODULE_NAME not in imported_modules(path)
        assert READER_CLASS not in imported_names(path)
        source = path.read_text(encoding="utf-8")
        assert READER_CLASS not in source
        assert "forecasting_success_reader" not in source


def test_no_api_or_application_module_imports_the_reader_yet() -> None:
    for root in (API_ROOT, APPLICATION_ROOT):
        for path in sorted(root.rglob("*.py")):
            assert READER_MODULE_NAME not in imported_modules(path), path
            assert READER_CLASS not in imported_names(path), path
            assert READER_CLASS not in path.read_text(encoding="utf-8"), path
