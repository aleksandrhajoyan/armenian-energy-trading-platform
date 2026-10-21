"""Portfolio & Risk execution service stays a thin read→request→agent composition."""

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
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
ORCHESTRATION_ROOT = APPLICATION_ROOT / "orchestration"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "portfolio_risk_execution.py"
ORCHESTRATION_INIT_MODULE = ORCHESTRATION_ROOT / "__init__.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
AGENT_MODULE = APPLICATION_ROOT / "agents" / "portfolio_risk.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
EXECUTION_MODULE_NAME = "energy_trading.application.orchestration.portfolio_risk_execution"
# Chunk 201: the exact API composition builder authorized to construct the service.
PORTFOLIO_RISK_STACK_MODULE = API_ROOT / "composition" / "portfolio_risk_stack.py"
PORTFOLIO_RISK_STACK_RELATIVE = "energy_trading/api/composition/portfolio_risk_stack.py"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "datetime",
        "energy_trading.application.agents.base",
        "energy_trading.application.orchestration.forecasting_success_read",
        "energy_trading.application.ports.portfolio_risk_assessment",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.models.regulatory",
        "energy_trading.domain.models.trading",
        "energy_trading.domain.value_objects.quantities",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "date",
        "AgentPort",
        "ForecastingSuccessReadPort",
        "PortfolioRiskAssessmentRequest",
        "GenerationAvailabilityRecord",
        "HydroRecord",
        "RegulatoryConstraint",
        "RiskAssessment",
        "EntityId",
    }
)

EXECUTE_PARAMETERS = (
    ("workflow_id", "str"),
    ("portfolio_id", "EntityId"),
    ("delivery_date", "date"),
    ("generation_availability", "tuple[GenerationAvailabilityRecord, ...]"),
    ("hydro_resources", "tuple[HydroRecord, ...]"),
    ("regulatory_constraints", "tuple[RegulatoryConstraint, ...]"),
)

REQUEST_KEYWORDS = (
    ("workflow_id", "workflow_id"),
    ("portfolio_id", "portfolio_id"),
    ("delivery_date", "delivery_date"),
    ("forecasting_success", "forecasting_success"),
    ("generation_availability", "generation_availability"),
    ("hydro_resources", "hydro_resources"),
    ("regulatory_constraints", "regulatory_constraints"),
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents.portfolio_risk",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_executor",
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
    "numpy",
    "scipy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "n8n",
    "tenacity",
    "backoff",
    "asyncio",
    "logging",
    "pathlib",
    "os",
    "uuid",
    "time",
    "decimal",
    "math",
    "statistics",
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
        "Union",
        "list",
        "WorkflowState",
        "ForecastingWorkflowContextPort",
        "PortfolioRiskAssessmentPort",
        "PortfolioRiskAgent",
        "InMemoryForecastingReadAfterWriteContext",
        "InMemoryForecastingSuccessReader",
        "MarketBid",
        "StateGraph",
        "CompiledStateGraph",
        "Redis",
        "AsyncSession",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "assess",
        "model_validate",
        "model_construct",
        "model_copy",
        "replace",
        "record_success",
        "resolve_plan",
        "sorted",
        "sort",
        "sum",
        "min",
        "max",
        "abs",
        "round",
        "Decimal",
        "value_at_risk",
        "risk_score",
        "expected_margin",
        "TaskGroup",
        "gather",
        "create_task",
        "sleep",
        "save",
        "store",
        "open",
        "logger",
        "getLogger",
        "now",
        "utcnow",
        "uuid4",
        "Repository",
        "ServiceLocator",
        "AgentRegistry",
        "AgentFactory",
        "StateGraph",
    }
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
    msg = f"method {name!r} not found in {class_def.name}"
    raise AssertionError(msg)


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


def _self_attribute_assigned_from(init_fn: ast.FunctionDef, value_name: str) -> str:
    for node in ast.walk(init_fn):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Attribute)
            and isinstance(node.targets[0].value, ast.Name)
            and node.targets[0].value.id == "self"
            and isinstance(node.value, ast.Name)
            and node.value.id == value_name
        ):
            return node.targets[0].attr
    msg = f"no self attribute assigned from {value_name!r}"
    raise AssertionError(msg)


def _execute_body(class_def: ast.ClassDef) -> list[ast.stmt]:
    body = list(_method(class_def, "execute").body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    return body


def test_execution_module_belongs_to_application_orchestration() -> None:
    assert EXECUTION_MODULE.parent == ORCHESTRATION_ROOT
    assert EXECUTION_MODULE.exists()


def test_module_defines_only_the_execution_service_class() -> None:
    tree = _tree(EXECUTION_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == ["PortfolioRiskExecutionService"]
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert module_functions == []
    assignments = [node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)]
    assert assignments == []


def test_service_has_no_base_class_decorator_or_type_parameters() -> None:
    class_def = _class_def(EXECUTION_MODULE, "PortfolioRiskExecutionService")
    assert class_def.bases == []
    assert class_def.keywords == []
    assert class_def.decorator_list == []
    assert list(class_def.type_params) == []
    methods = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert methods == ["__init__", "execute"]


def test_constructor_keyword_only_injects_reader_and_generic_agent_port() -> None:
    init_fn = _method(_class_def(EXECUTION_MODULE, "PortfolioRiskExecutionService"), "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    assert [arg.arg for arg in init_fn.args.args] == ["self"]
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    parameters = [
        (arg.arg, ast.unparse(arg.annotation) if arg.annotation else None)
        for arg in init_fn.args.kwonlyargs
    ]
    assert parameters == [
        ("forecast_reader", "ForecastingSuccessReadPort"),
        ("risk_agent", "AgentPort[PortfolioRiskAssessmentRequest, RiskAssessment]"),
    ]
    assert init_fn.args.kw_defaults == [None, None]
    assert len(init_fn.body) == 2
    assert all(isinstance(statement, ast.Assign) for statement in init_fn.body)
    _self_attribute_assigned_from(init_fn, "forecast_reader")
    _self_attribute_assigned_from(init_fn, "risk_agent")
    assert not any(isinstance(node, ast.Call) for node in ast.walk(init_fn))


def test_execute_is_async_with_exact_keyword_only_inputs() -> None:
    execute_fn = _method(_class_def(EXECUTION_MODULE, "PortfolioRiskExecutionService"), "execute")
    assert isinstance(execute_fn, ast.AsyncFunctionDef)
    assert [arg.arg for arg in execute_fn.args.args] == ["self"]
    assert execute_fn.args.posonlyargs == []
    assert execute_fn.args.vararg is None
    assert execute_fn.args.kwarg is None
    parameters = tuple(
        (arg.arg, ast.unparse(arg.annotation) if arg.annotation else None)
        for arg in execute_fn.args.kwonlyargs
    )
    assert parameters == EXECUTE_PARAMETERS
    assert execute_fn.args.kw_defaults == [None] * len(EXECUTE_PARAMETERS)
    assert execute_fn.returns is not None
    assert ast.unparse(execute_fn.returns) == "RiskAssessment"
    assert execute_fn.decorator_list == []


def test_execute_reads_once_constructs_once_delegates_once_and_returns() -> None:
    class_def = _class_def(EXECUTION_MODULE, "PortfolioRiskExecutionService")
    init_fn = _method(class_def, "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    reader_attribute = _self_attribute_assigned_from(init_fn, "forecast_reader")
    agent_attribute = _self_attribute_assigned_from(init_fn, "risk_agent")
    body = _execute_body(class_def)
    assert len(body) == 3

    read, construct, delegate = body
    assert isinstance(read, ast.Assign)
    assert [ast.unparse(target) for target in read.targets] == ["forecasting_success"]
    assert isinstance(read.value, ast.Await)
    read_call = read.value.value
    assert isinstance(read_call, ast.Call)
    assert isinstance(read_call.func, ast.Attribute)
    assert read_call.func.attr == "get_success"
    assert ast.unparse(read_call.func.value) == f"self.{reader_attribute}"
    assert read_call.args == []
    assert [(kw.arg, ast.unparse(kw.value)) for kw in read_call.keywords] == [
        ("workflow_id", "workflow_id")
    ]

    assert isinstance(construct, ast.Assign)
    assert [ast.unparse(target) for target in construct.targets] == ["request"]
    request_call = construct.value
    assert isinstance(request_call, ast.Call)
    assert isinstance(request_call.func, ast.Name)
    assert request_call.func.id == "PortfolioRiskAssessmentRequest"
    assert request_call.args == []
    assert tuple((kw.arg, ast.unparse(kw.value)) for kw in request_call.keywords) == (
        REQUEST_KEYWORDS
    )

    assert isinstance(delegate, ast.Return)
    assert isinstance(delegate.value, ast.Await)
    run_call = delegate.value.value
    assert isinstance(run_call, ast.Call)
    assert isinstance(run_call.func, ast.Attribute)
    assert run_call.func.attr == "run"
    assert ast.unparse(run_call.func.value) == f"self.{agent_attribute}"
    assert [ast.unparse(arg) for arg in run_call.args] == ["request"]
    assert run_call.keywords == []

    execute_fn = _method(class_def, "execute")
    awaits = [node for node in ast.walk(execute_fn) if isinstance(node, ast.Await)]
    calls = [node for node in ast.walk(execute_fn) if isinstance(node, ast.Call)]
    assert len(awaits) == 2
    assert sorted(calls, key=lambda node: (node.lineno, node.col_offset)) == [
        read_call,
        request_call,
        run_call,
    ]


def _method_body_nodes() -> list[ast.AST]:
    class_def = _class_def(EXECUTION_MODULE, "PortfolioRiskExecutionService")
    nodes: list[ast.AST] = []
    for method in class_def.body:
        if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef):
            for statement in method.body:
                nodes.extend(ast.walk(statement))
    return nodes


def test_service_has_no_control_flow_error_handling_or_arithmetic() -> None:
    control = [
        type(node).__name__
        for node in ast.walk(_tree(EXECUTION_MODULE))
        if isinstance(
            node,
            ast.If
            | ast.IfExp
            | ast.Match
            | ast.For
            | ast.AsyncFor
            | ast.While
            | ast.Try
            | ast.TryStar
            | ast.With
            | ast.AsyncWith
            | ast.ExceptHandler
            | ast.Raise
            | ast.ListComp
            | ast.SetComp
            | ast.DictComp
            | ast.GeneratorExp
            | ast.Lambda
            | ast.BinOp
            | ast.UnaryOp
            | ast.AugAssign
            | ast.Compare
            | ast.BoolOp
            | ast.Starred,
        )
    ]
    assert control == []
    body_nodes = _method_body_nodes()
    assert not any(isinstance(node, ast.Subscript | ast.Tuple | ast.List) for node in body_nodes)
    constructed = [
        node.func.id
        for node in body_nodes
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"RiskAssessment", "ForecastingSuccess", "tuple", "list"}
    ]
    assert constructed == []


def test_service_imports_only_application_contracts_and_canonical_domain() -> None:
    modules = imported_modules(EXECUTION_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(EXECUTION_MODULE) - modules == ALLOWED_IMPORTED_NAMES
    source = EXECUTION_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_service_excludes_payload_escape_hatches_and_hidden_behavior() -> None:
    names = annotation_type_names(EXECUTION_MODULE)
    assert sorted(names & FORBIDDEN_TYPE_NAMES) == []
    identifiers = _identifier_names(EXECUTION_MODULE) | imported_names(EXECUTION_MODULE)
    assert sorted(identifiers & FORBIDDEN_TYPE_NAMES) == []
    assert sorted(identifiers & FORBIDDEN_IDENTIFIERS) == []
    code_only = " ".join(sorted(identifiers | imported_modules(EXECUTION_MODULE))).lower()
    for token in (
        "langgraph",
        "fastapi",
        "starlette",
        "redis",
        "sqlalchemy",
        "postgres",
        "qdrant",
        "openai",
        "n8n",
        "registry",
        "factory",
        "repository",
        "cache",
        "retry",
        "fallback",
        "exposure",
        "convert",
        "bid",
    ):
        assert token not in code_only, token


def test_orchestration_package_does_not_export_the_execution_service() -> None:
    assert EXECUTION_MODULE_NAME not in imported_modules(ORCHESTRATION_INIT_MODULE)
    source = ORCHESTRATION_INIT_MODULE.read_text(encoding="utf-8")
    assert "PortfolioRiskExecutionService" not in source


def test_workflow_state_remains_unchanged_and_unaware() -> None:
    fields = tuple(
        item.target.id
        for item in _class_def(STATE_MODULE, "WorkflowState").body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert fields == (
        "workflow_id",
        "portfolio_id",
        "delivery_date",
        "correlation_id",
        "phase",
        "status",
        "diagnostics",
    )
    assert EXECUTION_MODULE_NAME not in imported_modules(STATE_MODULE)
    assert "PortfolioRiskExecutionService" not in STATE_MODULE.read_text(encoding="utf-8")


def test_graph_remains_unwired_to_the_execution_service() -> None:
    assert EXECUTION_MODULE_NAME not in imported_modules(GRAPH_MODULE)
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "PortfolioRiskExecutionService" not in source
    assert "portfolio_risk_execution" not in source


def test_only_portfolio_risk_composition_builder_may_import_service_from_api() -> None:
    assert EXECUTION_MODULE_NAME not in imported_modules(API_APP)
    app_source = API_APP.read_text(encoding="utf-8")
    assert "PortfolioRiskExecutionService" not in app_source
    assert "portfolio_risk_stack" not in app_source
    # Chunk 201: the exact builder imports the canonical service and never executes it.
    assert EXECUTION_MODULE_NAME in imported_modules(PORTFOLIO_RISK_STACK_MODULE)
    assert "PortfolioRiskExecutionService" in imported_names(PORTFOLIO_RISK_STACK_MODULE)
    assert "execute" not in _identifier_names(PORTFOLIO_RISK_STACK_MODULE)
    assert (
        collect_import_violations(
            API_ROOT,
            (EXECUTION_MODULE_NAME,),
            exclude_relative_prefixes=(PORTFOLIO_RISK_STACK_RELATIVE,),
        )
        == []
    )
    for path in sorted(API_ROOT.rglob("*.py")):
        if path == PORTFOLIO_RISK_STACK_MODULE:
            continue
        source = path.read_text(encoding="utf-8")
        assert "PortfolioRiskExecutionService" not in source, path
        assert "portfolio_risk_execution" not in source, path


def test_concrete_portfolio_risk_agent_remains_unaware_of_the_service() -> None:
    assert EXECUTION_MODULE_NAME not in imported_modules(AGENT_MODULE)
    source = AGENT_MODULE.read_text(encoding="utf-8")
    assert "PortfolioRiskExecutionService" not in source
    assert "ForecastingSuccessReadPort" not in source
    class_def = _class_def(AGENT_MODULE, "PortfolioRiskAgent")
    methods = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert methods == ["__init__", "name", "run"]


def test_no_other_production_module_imports_the_execution_service() -> None:
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path in (EXECUTION_MODULE, PORTFOLIO_RISK_STACK_MODULE):
            continue
        assert EXECUTION_MODULE_NAME not in imported_modules(path), path
        assert "PortfolioRiskExecutionService" not in path.read_text(encoding="utf-8"), path
