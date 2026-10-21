"""Trading Strategy Agent stays a thin application↔bid-port delegate."""

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
AGENTS_ROOT = APPLICATION_ROOT / "agents"
AGENT_MODULE = AGENTS_ROOT / "trading_strategy.py"
AGENTS_INIT_MODULE = AGENTS_ROOT / "__init__.py"
AGENT_BASE_MODULE = AGENTS_ROOT / "base.py"
ORCHESTRATION_ROOT = APPLICATION_ROOT / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
AGENT_MODULE_NAME = "energy_trading.application.agents.trading_strategy"
BID_MODULE_NAME = "energy_trading.application.ports.trading_strategy_bid"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.orchestration",
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
    "asyncio",
    "logging",
    "decimal",
    "math",
    "statistics",
)

ALLOWED_AGENT_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.base",
        BID_MODULE_NAME,
        "energy_trading.domain.models.trading",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "AgentName",
        "TradingStrategyBidPort",
        "TradingStrategyBidRequest",
        "MarketBid",
    }
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
        "WorkflowState",
        "ForecastingSuccessReadPort",
        "ForecastingWorkflowContextPort",
        "PortfolioRiskAssessmentPort",
        "InMemoryForecastingSuccessReader",
        "InMemoryForecastingReadAfterWriteContext",
        "FailurePolicyPort",
        "BidSide",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "get_success",
        "resolve_plan",
        "record_success",
        "assess",
        "submit",
        "submit_bids",
        "clear",
        "settle",
        "model_validate",
        "model_construct",
        "model_copy",
        "BUY",
        "SELL",
        "quantity_mw",
        "limit_price",
        "amount_per_mwh",
        "currency",
        "value_at_risk",
        "risk_score",
        "expected_margin",
        "TaskGroup",
        "gather",
        "create_task",
        "sleep",
        "sum",
        "min",
        "max",
        "round",
        "sorted",
        "Decimal",
        "logger",
        "getLogger",
        "save",
        "store",
        "open",
        "cache",
        "lru_cache",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
        "StateGraph",
    }
)

CANONICAL_AGENT_MEMBERS = (
    ("REGULATORY_INTELLIGENCE", "Regulatory Intelligence Agent"),
    ("PRICING_AND_SALES", "Pricing & Sales Agent"),
    ("WEATHER_AND_RENEWABLE_FORECAST", "Weather & Renewable Forecast Agent"),
    ("HYDRO_RESOURCES", "Hydro Resources Agent"),
    ("GENERATION_AVAILABILITY", "Generation Availability Agent"),
    ("NEWS_INTELLIGENCE", "News Intelligence Agent"),
    ("MARKET_MONITORING", "Market Monitoring Agent"),
    ("CONSUMER_LOAD_FORECAST", "Consumer Load Forecast Agent"),
    ("DAM_PRICE_FORECAST", "DAM Price Forecast Agent"),
    ("PORTFOLIO_AND_RISK", "Portfolio & Risk Agent"),
    ("TRADING_STRATEGY", "Trading Strategy Agent"),
    ("BILLING_AND_SETTLEMENT", "Billing & Settlement Agent"),
    ("CHIEF_ORCHESTRATOR", "Chief Orchestrator Agent"),
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
    msg = f"method {name!r} not found in {class_def.name}"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


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


def test_trading_strategy_agent_lives_under_application_agents() -> None:
    assert AGENT_MODULE.parent == AGENTS_ROOT
    assert AGENT_MODULE.exists()


def test_module_defines_only_the_trading_strategy_agent_class() -> None:
    tree = _tree(AGENT_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == ["TradingStrategyAgent"]
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert module_functions == []
    assert [node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)] == []
    production_agents = sorted(
        path.relative_to(PRODUCTION_ROOT).as_posix()
        for path in PRODUCTION_ROOT.rglob("*.py")
        for node in _tree(path).body
        if isinstance(node, ast.ClassDef) and node.name == "TradingStrategyAgent"
    )
    assert production_agents == ["application/agents/trading_strategy.py"]


def test_agent_structurally_implements_agent_port_without_inheritance() -> None:
    class_def = _class_def(AGENT_MODULE, "TradingStrategyAgent")
    assert class_def.bases == []
    assert class_def.keywords == []
    assert list(class_def.type_params) == []
    assert class_def.decorator_list == []
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert defined == ["__init__", "name", "run"]


def test_constructor_keyword_only_injects_the_published_bid_port() -> None:
    init_fn = _method(_class_def(AGENT_MODULE, "TradingStrategyAgent"), "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    assert tuple(arg.arg for arg in init_fn.args.args) == ("self",)
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert len(init_fn.args.kwonlyargs) == 1
    assert init_fn.args.kw_defaults == [None]
    parameter = init_fn.args.kwonlyargs[0]
    annotation = parameter.annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "TradingStrategyBidPort"
    assert [node for node in ast.walk(init_fn) if isinstance(node, ast.Call)] == []
    _self_attribute_assigned_from(init_fn, parameter.arg)


def test_name_returns_existing_canonical_trading_strategy_identity() -> None:
    name_fn = _method(_class_def(AGENT_MODULE, "TradingStrategyAgent"), "name")
    assert isinstance(name_fn, ast.FunctionDef)
    assert [ast.unparse(item) for item in name_fn.decorator_list] == ["property"]
    assert name_fn.returns is not None
    assert ast.unparse(name_fn.returns) == "AgentName"
    assert len(name_fn.body) == 1
    statement = name_fn.body[0]
    assert isinstance(statement, ast.Return)
    assert statement.value is not None
    assert ast.unparse(statement.value) == "AgentName.TRADING_STRATEGY"


def test_run_is_async_and_narrowly_typed() -> None:
    run_fn = _method(_class_def(AGENT_MODULE, "TradingStrategyAgent"), "run")
    assert isinstance(run_fn, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "request")
    assert run_fn.args.posonlyargs == []
    assert run_fn.args.kwonlyargs == []
    assert run_fn.args.vararg is None
    assert run_fn.args.kwarg is None
    assert run_fn.args.defaults == []
    annotation = run_fn.args.args[1].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "TradingStrategyBidRequest"
    assert run_fn.returns is not None
    assert ast.unparse(run_fn.returns) == "tuple[MarketBid, ...]"
    assert run_fn.decorator_list == []


def test_run_awaits_propose_bids_exactly_once_and_returns_its_result_unchanged() -> None:
    class_def = _class_def(AGENT_MODULE, "TradingStrategyAgent")
    init_fn = _method(class_def, "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    port_attribute = _self_attribute_assigned_from(init_fn, init_fn.args.kwonlyargs[0].arg)
    run_fn = _method(class_def, "run")
    assert len(run_fn.body) == 1
    statement = run_fn.body[0]
    assert isinstance(statement, ast.Return)
    assert isinstance(statement.value, ast.Await)
    call = statement.value.value
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Attribute)
    assert call.func.attr == "propose_bids"
    assert ast.unparse(call.func.value) == f"self.{port_attribute}"
    assert call.args == []
    assert [(keyword.arg, ast.unparse(keyword.value)) for keyword in call.keywords] == [
        ("request", "request")
    ]
    awaits = [node for node in ast.walk(run_fn) if isinstance(node, ast.Await)]
    calls = [node for node in ast.walk(run_fn) if isinstance(node, ast.Call)]
    assert len(awaits) == 1
    assert calls == [call]


def test_agent_has_no_control_flow_error_handling_arithmetic_or_bid_construction() -> None:
    tree = _tree(AGENT_MODULE)
    control = [
        type(node).__name__
        for node in ast.walk(tree)
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
            | ast.Subscript
            | ast.Tuple
            | ast.List
            | ast.Dict,
        )
        # The return annotation ``tuple[MarketBid, ...]`` is the only subscript.
        and not (isinstance(node, ast.Subscript | ast.Tuple) and _in_annotation(tree, node))
    ]
    assert control == []
    constructed = sorted(
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (name := _call_name(node))
        in {"MarketBid", "TradingStrategyBidRequest", "RiskAssessment", "tuple", "list"}
    )
    assert constructed == []


def _in_annotation(tree: ast.Module, target: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            annotations = [node.returns] + [
                arg.annotation for arg in (*node.args.args, *node.args.kwonlyargs)
            ]
            for annotation in annotations:
                if annotation is not None and any(
                    child is target for child in ast.walk(annotation)
                ):
                    return True
    return False


def test_agent_imports_only_application_contracts_and_canonical_domain() -> None:
    modules = imported_modules(AGENT_MODULE)
    assert modules == ALLOWED_AGENT_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(AGENT_MODULE) - modules == ALLOWED_IMPORTED_NAMES
    source = AGENT_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_agent_excludes_payload_escape_hatches_and_hidden_behavior() -> None:
    names = annotation_type_names(AGENT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(AGENT_MODULE) | imported_names(AGENT_MODULE)
    assert sorted(identifiers & FORBIDDEN_TYPE_NAMES) == []
    assert sorted(identifiers & FORBIDDEN_IDENTIFIERS) == []


def test_agent_does_not_import_forecasting_reader_risk_engine_or_workflow_state() -> None:
    modules = imported_modules(AGENT_MODULE)
    for module in modules:
        assert not module.startswith("energy_trading.infrastructure"), module
        assert "forecasting_success_read" not in module, module
        assert "read_after_write" not in module, module
        assert "portfolio_risk" not in module, module
        assert not module.endswith(".state"), module


def test_agents_package_does_not_export_the_trading_strategy_agent() -> None:
    assert AGENT_MODULE_NAME not in imported_modules(AGENTS_INIT_MODULE)
    assert "TradingStrategyAgent" not in AGENTS_INIT_MODULE.read_text(encoding="utf-8")


def test_graph_and_workflow_state_remain_unaware_of_the_trading_strategy_agent() -> None:
    for path in (GRAPH_MODULE, STATE_MODULE):
        modules = imported_modules(path)
        assert AGENT_MODULE_NAME not in modules, path
        assert BID_MODULE_NAME not in modules, path
        assert "TradingStrategyAgent" not in path.read_text(encoding="utf-8"), path


def test_api_and_create_app_remain_unwired_to_the_trading_strategy_agent() -> None:
    assert API_APP.exists()
    for path in sorted(API_ROOT.rglob("*.py")):
        assert AGENT_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyAgent" not in path.read_text(encoding="utf-8"), path


def test_no_other_production_module_imports_the_trading_strategy_agent() -> None:
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path == AGENT_MODULE:
            continue
        assert AGENT_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyAgent" not in path.read_text(encoding="utf-8"), path


def test_shared_agent_name_agent_port_and_workflow_state_are_unchanged() -> None:
    enum_def = _class_def(AGENT_BASE_MODULE, "AgentName")
    members = tuple(
        (item.targets[0].id, item.value.value)
        for item in enum_def.body
        if isinstance(item, ast.Assign)
        and isinstance(item.targets[0], ast.Name)
        and isinstance(item.value, ast.Constant)
    )
    assert members == CANONICAL_AGENT_MEMBERS
    port_def = _class_def(AGENT_BASE_MODULE, "AgentPort")
    assert [ast.unparse(param) for param in port_def.type_params] == ["TRequest", "TResult"]
    port_methods = [
        node.name
        for node in port_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert port_methods == ["name", "run"]
    state_def = _class_def(STATE_MODULE, "WorkflowState")
    state_fields = tuple(
        item.target.id
        for item in state_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert state_fields == WORKFLOW_STATE_FIELDS
