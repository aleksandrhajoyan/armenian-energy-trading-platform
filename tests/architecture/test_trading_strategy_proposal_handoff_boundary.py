"""Trading Strategy proposal handoff service stays a thin execute→handoff composition."""

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
AGENTS_ROOT = APPLICATION_ROOT / "agents"
SERVICE_MODULE = ORCHESTRATION_ROOT / "trading_strategy_proposal_handoff.py"
ORCHESTRATION_INIT_MODULE = ORCHESTRATION_ROOT / "__init__.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
AGENT_BASE_MODULE = AGENTS_ROOT / "base.py"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "trading_strategy_execution.py"
HANDOFF_MODULE = ORCHESTRATION_ROOT / "risk_and_bid_proposal_handoff.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
SERVICE_MODULE_NAME = "energy_trading.application.orchestration.trading_strategy_proposal_handoff"
SERVICE_CLASS_NAME = "TradingStrategyProposalHandoffService"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "datetime",
        "energy_trading.application.orchestration.forecasting_success",
        "energy_trading.application.orchestration.risk_and_bid_proposal_handoff",
        "energy_trading.application.orchestration.trading_strategy_execution",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.models.regulatory",
        "energy_trading.domain.models.trading",
        "energy_trading.domain.value_objects.quantities",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "date",
        "ForecastingSuccess",
        "RiskAndBidProposalHandoff",
        "TradingStrategyExecutionService",
        "GenerationAvailabilityRecord",
        "RegulatoryConstraint",
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

STRATEGY_KEYWORDS = tuple((name, name) for name, _ in EXECUTE_PARAMETERS)

HANDOFF_PASSTHROUGH_KEYWORDS = (
    ("workflow_id", "workflow_id"),
    ("portfolio_id", "portfolio_id"),
    ("delivery_date", "delivery_date"),
    ("forecasting_success", "forecasting_success"),
    ("risk_assessment", "risk_assessment"),
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
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
    "threading",
    "concurrent",
    "functools",
    "logging",
    "pathlib",
    "os",
    "json",
    "pickle",
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
        "bool",
        "Literal",
        "WorkflowState",
        "WorkflowStatus",
        "WorkflowPhase",
        "AgentPort",
        "AgentName",
        "ForecastingSuccessReadPort",
        "ForecastingWorkflowContextPort",
        "TradingStrategyBidPort",
        "TradingStrategyBidRequest",
        "TradingStrategyAgent",
        "PortfolioRiskAssessmentPort",
        "PortfolioRiskAssessmentRequest",
        "PortfolioRiskExecutionService",
        "PortfolioRiskAgent",
        "InMemoryForecastingReadAfterWriteContext",
        "InMemoryForecastingSuccessReader",
        "MarketClearingResult",
        "ClearingStatus",
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
        "run",
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
        "copy",
        "deepcopy",
        "replace",
        "record_success",
        "resolve_plan",
        "sorted",
        "sort",
        "set",
        "frozenset",
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
        "consumer_load_forecast",
        "dam_price_forecast",
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
        "lru_cache",
        "cache",
        "Repository",
        "ServiceLocator",
        "AgentRegistry",
        "AgentFactory",
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

HANDOFF_FIELDS = (
    ("workflow_id", "str"),
    ("portfolio_id", "EntityId"),
    ("delivery_date", "date"),
    ("forecasting_success", "ForecastingSuccess"),
    ("risk_assessment", "RiskAssessment"),
    ("bid_proposals", "tuple[MarketBid, ...]"),
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


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


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


def _service_class() -> ast.ClassDef:
    return _class_def(SERVICE_MODULE, SERVICE_CLASS_NAME)


def _execute_body(class_def: ast.ClassDef) -> list[ast.stmt]:
    body = list(_method(class_def, "execute").body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    return body


def test_service_module_belongs_to_application_orchestration() -> None:
    assert SERVICE_MODULE.exists()
    assert SERVICE_MODULE.parent == ORCHESTRATION_ROOT
    definitions = sorted(
        path.relative_to(PRODUCTION_ROOT).as_posix()
        for path in PRODUCTION_ROOT.rglob("*.py")
        for node in _tree(path).body
        if isinstance(node, ast.ClassDef) and node.name == SERVICE_CLASS_NAME
    )
    assert definitions == ["application/orchestration/trading_strategy_proposal_handoff.py"]


def test_module_defines_exactly_one_public_service_class() -> None:
    tree = _tree(SERVICE_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == [SERVICE_CLASS_NAME]
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert module_functions == []
    assert [node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)] == []


def test_service_has_no_base_class_decorator_or_type_parameters() -> None:
    class_def = _service_class()
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


def test_constructor_keyword_only_injects_one_trading_strategy_execution_service() -> None:
    init_fn = _method(_service_class(), "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    assert [arg.arg for arg in init_fn.args.args] == ["self"]
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    parameters = [
        (arg.arg, ast.unparse(arg.annotation) if arg.annotation else None)
        for arg in init_fn.args.kwonlyargs
    ]
    assert parameters == [("trading_strategy_service", "TradingStrategyExecutionService")]
    assert init_fn.args.kw_defaults == [None]
    assert len(init_fn.body) == 1
    assert isinstance(init_fn.body[0], ast.Assign)
    _self_attribute_assigned_from(init_fn, "trading_strategy_service")
    assert not any(isinstance(node, ast.Call) for node in ast.walk(init_fn))


def test_execute_is_async_with_exact_keyword_only_canonical_inputs() -> None:
    execute_fn = _method(_service_class(), "execute")
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
    assert ast.unparse(execute_fn.returns) == "RiskAndBidProposalHandoff"
    assert execute_fn.decorator_list == []


def test_execute_awaits_strategy_once_then_constructs_and_returns_one_handoff() -> None:
    class_def = _service_class()
    init_fn = _method(class_def, "__init__")
    assert isinstance(init_fn, ast.FunctionDef)
    service_attribute = _self_attribute_assigned_from(init_fn, "trading_strategy_service")
    body = _execute_body(class_def)
    assert len(body) == 2

    delegate, construct = body
    assert isinstance(delegate, ast.Assign)
    assert len(delegate.targets) == 1
    assert isinstance(delegate.targets[0], ast.Name)
    proposals_name = delegate.targets[0].id
    assert isinstance(delegate.value, ast.Await)
    strategy_call = delegate.value.value
    assert isinstance(strategy_call, ast.Call)
    assert isinstance(strategy_call.func, ast.Attribute)
    assert strategy_call.func.attr == "execute"
    assert ast.unparse(strategy_call.func.value) == f"self.{service_attribute}"
    assert strategy_call.args == []
    assert tuple((kw.arg, ast.unparse(kw.value)) for kw in strategy_call.keywords) == (
        STRATEGY_KEYWORDS
    )

    assert isinstance(construct, ast.Return)
    handoff_call = construct.value
    assert isinstance(handoff_call, ast.Call)
    assert isinstance(handoff_call.func, ast.Name)
    assert handoff_call.func.id == "RiskAndBidProposalHandoff"
    assert handoff_call.args == []
    assert tuple((kw.arg, ast.unparse(kw.value)) for kw in handoff_call.keywords) == (
        *HANDOFF_PASSTHROUGH_KEYWORDS,
        ("bid_proposals", proposals_name),
    )

    execute_fn = _method(class_def, "execute")
    awaits = [node for node in ast.walk(execute_fn) if isinstance(node, ast.Await)]
    calls = [node for node in ast.walk(execute_fn) if isinstance(node, ast.Call)]
    assert len(awaits) == 1
    assert sorted(calls, key=lambda node: (node.lineno, node.col_offset)) == [
        strategy_call,
        handoff_call,
    ]


def test_service_has_no_control_flow_error_handling_or_arithmetic() -> None:
    control = [
        type(node).__name__
        for node in ast.walk(_tree(SERVICE_MODULE))
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
            | ast.Starred
            | ast.Global
            | ast.Nonlocal
            | ast.Yield
            | ast.YieldFrom,
        )
    ]
    assert control == []
    class_def = _service_class()
    body_nodes = [
        node
        for method in class_def.body
        if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef)
        for statement in method.body
        for node in ast.walk(statement)
    ]
    assert not any(isinstance(node, ast.Subscript | ast.Tuple | ast.List) for node in body_nodes)
    constructed = sorted(
        name
        for node in body_nodes
        if isinstance(node, ast.Call)
        and (name := _call_name(node))
        in {
            "MarketBid",
            "RiskAssessment",
            "ForecastingSuccess",
            "GenerationAvailabilityRecord",
            "RegulatoryConstraint",
            "TradingStrategyBidRequest",
            "TradingStrategyAgent",
            "TradingStrategyExecutionService",
            "PortfolioRiskAgent",
            "PortfolioRiskExecutionService",
            "tuple",
            "list",
        }
    )
    assert constructed == []


def test_service_imports_only_application_contracts_and_canonical_domain() -> None:
    modules = imported_modules(SERVICE_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(SERVICE_MODULE) - modules == ALLOWED_IMPORTED_NAMES
    source = SERVICE_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_service_excludes_policy_runtime_and_escape_hatch_tokens() -> None:
    names = annotation_type_names(SERVICE_MODULE)
    assert sorted(names & FORBIDDEN_TYPE_NAMES) == []
    identifiers = _identifier_names(SERVICE_MODULE) | imported_names(SERVICE_MODULE)
    assert sorted(identifiers & FORBIDDEN_TYPE_NAMES) == []
    assert sorted(identifiers & FORBIDDEN_IDENTIFIERS) == []
    code_only = " ".join(sorted(identifiers | imported_modules(SERVICE_MODULE))).lower()
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
        "singleton",
        "cache",
        "retry",
        "fallback",
        "background",
        "threshold",
        "eligib",
        "approv",
        "authoriz",
        "submit",
        "settle",
        "exposure",
        "convert",
        "mwh",
        "fx",
        "portfolio_risk",
        "forecasting_success_read",
    ):
        assert token not in code_only, token


def test_published_handoff_and_execution_contracts_remain_unchanged() -> None:
    handoff_def = _class_def(HANDOFF_MODULE, "RiskAndBidProposalHandoff")
    fields = tuple(
        (item.target.id, ast.unparse(item.annotation))
        for item in handoff_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert fields == HANDOFF_FIELDS
    execute_fn = _method(_class_def(EXECUTION_MODULE, "TradingStrategyExecutionService"), "execute")
    assert isinstance(execute_fn, ast.AsyncFunctionDef)
    assert (
        tuple(
            (arg.arg, ast.unparse(arg.annotation) if arg.annotation else None)
            for arg in execute_fn.args.kwonlyargs
        )
        == EXECUTE_PARAMETERS
    )
    assert execute_fn.returns is not None
    assert ast.unparse(execute_fn.returns) == "tuple[MarketBid, ...]"
    for path in (HANDOFF_MODULE, EXECUTION_MODULE):
        assert SERVICE_MODULE_NAME not in imported_modules(path), path
        assert SERVICE_CLASS_NAME not in path.read_text(encoding="utf-8"), path


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
    state_fields = tuple(
        item.target.id
        for item in _class_def(STATE_MODULE, "WorkflowState").body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert state_fields == WORKFLOW_STATE_FIELDS


def test_service_does_not_add_a_concrete_agent() -> None:
    agent_modules = sorted(
        path.name for path in AGENTS_ROOT.glob("*.py") if path.name not in {"__init__.py"}
    )
    assert "trading_strategy_proposal_handoff.py" not in agent_modules
    assert len([name for name in agent_modules if name != "base.py"]) == 10


def test_orchestration_package_does_not_export_the_service() -> None:
    assert SERVICE_MODULE_NAME not in imported_modules(ORCHESTRATION_INIT_MODULE)
    source = ORCHESTRATION_INIT_MODULE.read_text(encoding="utf-8")
    assert SERVICE_CLASS_NAME not in source
    assert "trading_strategy_proposal_handoff" not in source


def test_workflow_state_and_graph_remain_unaware_of_the_service() -> None:
    for path in (STATE_MODULE, GRAPH_MODULE):
        assert SERVICE_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert SERVICE_CLASS_NAME not in source, path
        assert "trading_strategy_proposal_handoff" not in source, path


def test_no_production_runtime_wiring_imports_or_constructs_the_service() -> None:
    assert API_APP.exists()
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path == SERVICE_MODULE:
            continue
        assert SERVICE_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert SERVICE_CLASS_NAME not in source, path
        assert "trading_strategy_proposal_handoff" not in source, path
