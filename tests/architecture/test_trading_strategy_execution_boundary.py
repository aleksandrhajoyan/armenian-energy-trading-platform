"""Trading Strategy execution service stays a thin request→agent composition."""

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
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
ORCHESTRATION_ROOT = APPLICATION_ROOT / "orchestration"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "trading_strategy_execution.py"
ORCHESTRATION_INIT_MODULE = ORCHESTRATION_ROOT / "__init__.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
AGENT_BASE_MODULE = APPLICATION_ROOT / "agents" / "base.py"
AGENT_MODULE = APPLICATION_ROOT / "agents" / "trading_strategy.py"
BID_MODULE = APPLICATION_ROOT / "ports" / "trading_strategy_bid.py"
PORTFOLIO_RISK_EXECUTION_MODULE = ORCHESTRATION_ROOT / "portfolio_risk_execution.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
EXECUTION_MODULE_NAME = "energy_trading.application.orchestration.trading_strategy_execution"
# Chunk 206: the exact API composition builder authorized to construct the service.
TRADING_STRATEGY_STACK_MODULE = API_ROOT / "composition" / "trading_strategy_stack.py"
# Chunk 208: the exact application service authorized to import and invoke the service.
PROPOSAL_HANDOFF_MODULE = ORCHESTRATION_ROOT / "trading_strategy_proposal_handoff.py"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "datetime",
        "energy_trading.application.agents.base",
        "energy_trading.application.orchestration.forecasting_success",
        "energy_trading.application.ports.trading_strategy_bid",
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
        "ForecastingSuccess",
        "TradingStrategyBidRequest",
        "GenerationAvailabilityRecord",
        "RegulatoryConstraint",
        "MarketBid",
        "RiskAssessment",
        "EntityId",
    }
)

EXECUTE_PARAMETERS = (
    ("workflow_id", "str"),
    ("portfolio_id", "EntityId"),
    ("delivery_date", "date"),
    ("risk_assessment", "RiskAssessment"),
    ("forecasting_success", "ForecastingSuccess"),
    ("generation_availability", "tuple[GenerationAvailabilityRecord, ...]"),
    ("regulatory_constraints", "tuple[RegulatoryConstraint, ...]"),
)

REQUEST_KEYWORDS = tuple((name, name) for name, _ in EXECUTE_PARAMETERS)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents.trading_strategy",
    "energy_trading.application.agents.portfolio_risk",
    "energy_trading.application.ports.portfolio_risk_assessment",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_success_read",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.portfolio_risk_execution",
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
        "ForecastingSuccessReadPort",
        "ForecastingWorkflowContextPort",
        "TradingStrategyBidPort",
        "TradingStrategyAgent",
        "PortfolioRiskAssessmentPort",
        "PortfolioRiskAssessmentRequest",
        "PortfolioRiskExecutionService",
        "PortfolioRiskAgent",
        "InMemoryForecastingReadAfterWriteContext",
        "InMemoryForecastingSuccessReader",
        "MarketClearingResult",
        "SettlementResult",
        "BidSide",
        "StateGraph",
        "CompiledStateGraph",
        "Redis",
        "AsyncSession",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "propose_bids",
        "get_success",
        "assess",
        "submit",
        "submit_bids",
        "clear",
        "settle",
        "approve",
        "authorize",
        "model_validate",
        "model_construct",
        "model_copy",
        "replace",
        "record_success",
        "resolve_plan",
        "sorted",
        "sort",
        "filter",
        "sum",
        "min",
        "max",
        "abs",
        "round",
        "len",
        "Decimal",
        "BUY",
        "SELL",
        "side",
        "quantity_mw",
        "limit_price",
        "amount_per_mwh",
        "value_at_risk",
        "risk_score",
        "expected_margin",
        "available_capacity_mw",
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


def _method_body_nodes() -> list[ast.AST]:
    class_def = _class_def(EXECUTION_MODULE, "TradingStrategyExecutionService")
    nodes: list[ast.AST] = []
    for method in class_def.body:
        if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef):
            for statement in method.body:
                nodes.extend(ast.walk(statement))
    return nodes


def test_execution_module_belongs_to_application_orchestration() -> None:
    assert EXECUTION_MODULE.parent == ORCHESTRATION_ROOT
    assert EXECUTION_MODULE.exists()


def test_module_defines_only_the_execution_service_class() -> None:
    tree = _tree(EXECUTION_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == ["TradingStrategyExecutionService"]
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert module_functions == []
    assignments = [node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)]
    assert assignments == []


def test_service_has_no_base_class_decorator_or_type_parameters() -> None:
    class_def = _class_def(EXECUTION_MODULE, "TradingStrategyExecutionService")
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


def test_constructor_keyword_only_injects_one_generic_agent_port() -> None:
    init_fn = _method(_class_def(EXECUTION_MODULE, "TradingStrategyExecutionService"), "__init__")
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
        ("bid_agent", "AgentPort[TradingStrategyBidRequest, tuple[MarketBid, ...]]"),
    ]
    assert init_fn.args.kw_defaults == [None]
    assert len(init_fn.body) == 1
    assert isinstance(init_fn.body[0], ast.Assign)
    _self_attribute_assigned_from(init_fn, "bid_agent")
    assert not any(isinstance(node, ast.Call) for node in ast.walk(init_fn))


def test_execute_is_async_with_exact_keyword_only_inputs() -> None:
    execute_fn = _method(_class_def(EXECUTION_MODULE, "TradingStrategyExecutionService"), "execute")
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
    assert ast.unparse(execute_fn.returns) == "tuple[MarketBid, ...]"
    assert execute_fn.decorator_list == []


def test_execute_constructs_once_delegates_once_and_returns() -> None:
    class_def = _class_def(EXECUTION_MODULE, "TradingStrategyExecutionService")
    init_fn = _method(class_def, "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    agent_attribute = _self_attribute_assigned_from(init_fn, "bid_agent")
    body = _execute_body(class_def)
    assert len(body) == 2

    construct, delegate = body
    assert isinstance(construct, ast.Assign)
    assert [ast.unparse(target) for target in construct.targets] == ["request"]
    request_call = construct.value
    assert isinstance(request_call, ast.Call)
    assert isinstance(request_call.func, ast.Name)
    assert request_call.func.id == "TradingStrategyBidRequest"
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
    assert len(awaits) == 1
    assert sorted(calls, key=lambda node: (node.lineno, node.col_offset)) == [
        request_call,
        run_call,
    ]


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
        and node.func.id
        in {
            "MarketBid",
            "RiskAssessment",
            "ForecastingSuccess",
            "GenerationAvailabilityRecord",
            "RegulatoryConstraint",
            "TradingStrategyAgent",
            "tuple",
            "list",
        }
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
        "anthropic",
        "llm",
        "n8n",
        "gateway",
        "registry",
        "factory",
        "repository",
        "cache",
        "retry",
        "fallback",
        "threshold",
        "eligib",
        "approv",
        "exposure",
        "convert",
        "mwh",
        "fx",
    ):
        assert token not in code_only, token


def test_orchestration_package_does_not_export_the_execution_service() -> None:
    assert EXECUTION_MODULE_NAME not in imported_modules(ORCHESTRATION_INIT_MODULE)
    source = ORCHESTRATION_INIT_MODULE.read_text(encoding="utf-8")
    assert "TradingStrategyExecutionService" not in source


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
    assert "TradingStrategyExecutionService" not in STATE_MODULE.read_text(encoding="utf-8")


def test_agent_name_and_generic_agent_port_remain_unchanged() -> None:
    enum_def = _class_def(AGENT_BASE_MODULE, "AgentName")
    members = [
        item.targets[0].id
        for item in enum_def.body
        if isinstance(item, ast.Assign) and isinstance(item.targets[0], ast.Name)
    ]
    assert len(members) == 13
    assert "TRADING_STRATEGY" in members
    port_def = _class_def(AGENT_BASE_MODULE, "AgentPort")
    assert [ast.unparse(param) for param in port_def.type_params] == ["TRequest", "TResult"]
    port_methods = [
        node.name
        for node in port_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert port_methods == ["name", "run"]


def test_graph_remains_unwired_to_the_execution_service() -> None:
    assert EXECUTION_MODULE_NAME not in imported_modules(GRAPH_MODULE)
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "TradingStrategyExecutionService" not in source
    assert "trading_strategy_execution" not in source


def test_api_and_create_app_remain_unwired_to_the_execution_service() -> None:
    assert API_APP.exists()
    for path in sorted(API_ROOT.rglob("*.py")):
        if path == TRADING_STRATEGY_STACK_MODULE:
            continue
        assert EXECUTION_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert "TradingStrategyExecutionService" not in source, path
        assert "trading_strategy_execution" not in source, path


def test_only_the_trading_strategy_stack_constructs_the_service_inside_api() -> None:
    # Chunk 206: the exact builder imports and constructs the service; it never executes it.
    assert EXECUTION_MODULE_NAME in imported_modules(TRADING_STRATEGY_STACK_MODULE)
    assert "TradingStrategyExecutionService" in imported_names(TRADING_STRATEGY_STACK_MODULE)
    constructed_by: list[str] = []
    for path in sorted(API_ROOT.rglob("*.py")):
        for node in ast.walk(_tree(path)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "TradingStrategyExecutionService"
            ):
                constructed_by.append(path.relative_to(PRODUCTION_ROOT).as_posix())
    assert constructed_by == ["api/composition/trading_strategy_stack.py"]
    assert "execute" not in _identifier_names(TRADING_STRATEGY_STACK_MODULE)


def test_agent_bid_port_and_portfolio_risk_execution_remain_unaware_of_the_service() -> None:
    for path in (AGENT_MODULE, BID_MODULE, PORTFOLIO_RISK_EXECUTION_MODULE):
        assert EXECUTION_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyExecutionService" not in path.read_text(encoding="utf-8"), path
    class_def = _class_def(AGENT_MODULE, "TradingStrategyAgent")
    methods = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert methods == ["__init__", "name", "run"]


def test_only_the_proposal_handoff_service_invokes_the_service_inside_application() -> None:
    # Chunk 208: the exact handoff service imports and awaits ``execute`` once; it
    # never constructs the service, the concrete agent, or invokes the bid port.
    assert EXECUTION_MODULE_NAME in imported_modules(PROPOSAL_HANDOFF_MODULE)
    assert "TradingStrategyExecutionService" in imported_names(PROPOSAL_HANDOFF_MODULE)
    tree = _tree(PROPOSAL_HANDOFF_MODULE)
    awaited_executes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "execute"
        and isinstance(node.value.func.value, ast.Attribute)
        and isinstance(node.value.func.value.value, ast.Name)
        and node.value.func.value.value.id == "self"
    ]
    assert len(awaited_executes) == 1
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "TradingStrategyExecutionService" not in called_names
    assert "TradingStrategyAgent" not in called_names
    identifiers = _identifier_names(PROPOSAL_HANDOFF_MODULE)
    assert "propose_bids" not in identifiers
    assert "TradingStrategyAgent" not in identifiers
    assert "TradingStrategyBidPort" not in identifiers
    application_users = sorted(
        path.relative_to(PRODUCTION_ROOT).as_posix()
        for path in APPLICATION_ROOT.rglob("*.py")
        if path != EXECUTION_MODULE and EXECUTION_MODULE_NAME in imported_modules(path)
    )
    assert application_users == ["application/orchestration/trading_strategy_proposal_handoff.py"]


def test_no_other_production_module_imports_the_execution_service() -> None:
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path in (EXECUTION_MODULE, TRADING_STRATEGY_STACK_MODULE, PROPOSAL_HANDOFF_MODULE):
            continue
        assert EXECUTION_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyExecutionService" not in path.read_text(encoding="utf-8"), path
