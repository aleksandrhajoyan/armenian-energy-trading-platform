"""Trading Strategy bid proposal boundary stays typed, application-only, and unwired."""

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
PORTS_ROOT = APPLICATION_ROOT / "ports"
ORCHESTRATION_ROOT = APPLICATION_ROOT / "orchestration"
AGENTS_ROOT = APPLICATION_ROOT / "agents"
BID_MODULE = PORTS_ROOT / "trading_strategy_bid.py"
PORTS_INIT_MODULE = PORTS_ROOT / "__init__.py"
AGENTS_INIT_MODULE = AGENTS_ROOT / "__init__.py"
ORCHESTRATION_INIT_MODULE = ORCHESTRATION_ROOT / "__init__.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
READ_MODULE = ORCHESTRATION_ROOT / "forecasting_success_read.py"
PORTFOLIO_RISK_ASSESSMENT_MODULE = PORTS_ROOT / "portfolio_risk_assessment.py"
PORTFOLIO_RISK_AGENT_MODULE = AGENTS_ROOT / "portfolio_risk.py"
PORTFOLIO_RISK_EXECUTION_MODULE = ORCHESTRATION_ROOT / "portfolio_risk_execution.py"
API_ROOT = PRODUCTION_ROOT / "api"
APP_MODULE = API_ROOT / "app.py"
BID_MODULE_NAME = "energy_trading.application.ports.trading_strategy_bid"
# Chunk 203: the exact application agent authorized to consume the bid port.
TRADING_STRATEGY_AGENT_MODULE = AGENTS_ROOT / "trading_strategy.py"
# Chunk 204: the exact execution service authorized to import only the request type.
TRADING_STRATEGY_EXECUTION_MODULE = ORCHESTRATION_ROOT / "trading_strategy_execution.py"

PUBLIC_TYPES = ("TradingStrategyBidRequest", "TradingStrategyBidPort")

REQUEST_FIELDS = (
    ("workflow_id", "str"),
    ("portfolio_id", "EntityId"),
    ("delivery_date", "date"),
    ("risk_assessment", "RiskAssessment"),
    ("forecasting_success", "ForecastingSuccess"),
    ("generation_availability", "tuple[GenerationAvailabilityRecord, ...]"),
    ("regulatory_constraints", "tuple[RegulatoryConstraint, ...]"),
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "typing",
        "energy_trading.application.orchestration.forecasting_success",
        "energy_trading.domain.models.observations",
        "energy_trading.domain.models.regulatory",
        "energy_trading.domain.models.trading",
        "energy_trading.domain.value_objects.quantities",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "dataclass",
        "date",
        "Protocol",
        "ForecastingSuccess",
        "GenerationAvailabilityRecord",
        "RegulatoryConstraint",
        "MarketBid",
        "RiskAssessment",
        "EntityId",
    }
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
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
        "PortfolioRiskAssessmentPort",
        "PortfolioRiskAssessmentRequest",
        "HydroRecord",
        "LoadForecastPoint",
        "PriceForecastPoint",
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
        "Any",
        "TypeVar",
        "Generic",
        "Mapping",
        "BidSide",
        "BUY",
        "SELL",
        "model_validate",
        "model_construct",
        "model_copy",
        "get_success",
        "record_success",
        "resolve_plan",
        "assess",
        "submit",
        "submit_bids",
        "clear",
        "settle",
        "sorted",
        "sort",
        "sum",
        "min",
        "max",
        "round",
        "Decimal",
        "quantity_mw",
        "limit_price",
        "amount_per_mwh",
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
        "Repository",
        "ServiceLocator",
        "AgentRegistry",
        "AgentFactory",
        "StateGraph",
        "TradingStrategyAgent",
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


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


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


def _public_methods(class_def: ast.ClassDef) -> list[str]:
    return [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    ]


def _keyword_value(call: ast.Call, name: str) -> object:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None


def test_bid_module_belongs_to_application_ports() -> None:
    assert BID_MODULE.parent == PORTS_ROOT
    assert BID_MODULE.exists()


def test_bid_module_defines_only_the_two_public_contract_types() -> None:
    tree = _tree(BID_MODULE)
    class_names = tuple(node.name for node in tree.body if isinstance(node, ast.ClassDef))
    assert class_names == PUBLIC_TYPES
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert all(name.startswith("_") for name in module_functions)
    module_assignments = [
        node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)
    ]
    assert module_assignments == []


def test_request_is_frozen_slotted_keyword_only_dataclass_with_typed_fields() -> None:
    class_def = _class_def(BID_MODULE, "TradingStrategyBidRequest")
    assert class_def.bases == []
    assert len(class_def.decorator_list) == 1
    decorator = class_def.decorator_list[0]
    assert isinstance(decorator, ast.Call)
    assert isinstance(decorator.func, ast.Name)
    assert decorator.func.id == "dataclass"
    assert _keyword_value(decorator, "frozen") is True
    assert _keyword_value(decorator, "slots") is True
    assert _keyword_value(decorator, "kw_only") is True
    fields = tuple(
        (item.target.id, ast.unparse(item.annotation))
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert fields == REQUEST_FIELDS
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign):
            assert item.value is None
    assert _public_methods(class_def) == []


def test_port_is_nongeneric_protocol_with_one_keyword_only_async_propose_bids() -> None:
    class_def = _class_def(BID_MODULE, "TradingStrategyBidPort")
    assert _base_names(class_def) == {"Protocol"}
    assert list(class_def.type_params) == []
    assert class_def.decorator_list == []
    assert _public_methods(class_def) == ["propose_bids"]
    methods = [
        node for node in class_def.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert len(methods) == 1
    propose_fn = methods[0]
    assert isinstance(propose_fn, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in propose_fn.args.args) == ("self",)
    assert propose_fn.args.posonlyargs == []
    assert propose_fn.args.defaults == []
    assert propose_fn.args.vararg is None
    assert propose_fn.args.kwarg is None
    assert [arg.arg for arg in propose_fn.args.kwonlyargs] == ["request"]
    assert propose_fn.args.kw_defaults == [None]
    annotation = propose_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "TradingStrategyBidRequest"
    assert propose_fn.returns is not None
    assert ast.unparse(propose_fn.returns) == "tuple[MarketBid, ...]"
    assert propose_fn.decorator_list == []
    source = BID_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "runtime_checkable" not in source


def test_propose_bids_body_has_no_implementation_or_constructed_bid() -> None:
    class_def = _class_def(BID_MODULE, "TradingStrategyBidPort")
    propose_fn = next(node for node in class_def.body if isinstance(node, ast.AsyncFunctionDef))
    body = list(propose_fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    assert len(body) == 1
    assert isinstance(body[0], ast.Expr)
    assert isinstance(body[0].value, ast.Constant)
    assert body[0].value.value is Ellipsis
    for node in ast.walk(_tree(BID_MODULE)):
        assert not isinstance(node, ast.Await | ast.Return | ast.BinOp | ast.AugAssign)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {
                "MarketBid",
                "RiskAssessment",
                "ForecastingSuccess",
                "GenerationAvailabilityRecord",
                "RegulatoryConstraint",
                "tuple",
                "list",
            }


def test_bid_module_reuses_canonical_contracts_and_imports_nothing_else() -> None:
    modules = imported_modules(BID_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(BID_MODULE) - ALLOWED_MODULE_IMPORTS == ALLOWED_IMPORTED_NAMES
    source = BID_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_bid_contract_excludes_payload_escape_hatches_and_calculation() -> None:
    names = annotation_type_names(BID_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(BID_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    code_only = " ".join(sorted(identifiers | imported_modules(BID_MODULE))).lower()
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
        "convert",
        "mwh",
        "fx",
    ):
        assert token not in code_only, token


def test_only_the_trading_strategy_agent_consumes_the_bid_port_in_agents() -> None:
    # Chunk 203: the exact agent module imports the published port and request.
    assert BID_MODULE_NAME in imported_modules(TRADING_STRATEGY_AGENT_MODULE)
    agent_names = imported_names(TRADING_STRATEGY_AGENT_MODULE)
    assert "TradingStrategyBidPort" in agent_names
    assert "TradingStrategyBidRequest" in agent_names
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        if path == TRADING_STRATEGY_AGENT_MODULE:
            continue
        assert BID_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyBid" not in path.read_text(encoding="utf-8"), path
        assert "TradingStrategyAgent" not in _identifier_names(path), path


def test_packages_do_not_export_the_bid_contract() -> None:
    for path in (PORTS_INIT_MODULE, AGENTS_INIT_MODULE, ORCHESTRATION_INIT_MODULE):
        assert BID_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyBid" not in path.read_text(encoding="utf-8"), path


def test_workflow_state_graph_and_read_port_remain_unaware_of_the_bid_port() -> None:
    for path in (STATE_MODULE, GRAPH_MODULE, READ_MODULE):
        assert BID_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert "TradingStrategyBid" not in source, path
        assert "trading_strategy_bid" not in source, path


def test_portfolio_risk_stack_remains_unwired_to_the_bid_port() -> None:
    for path in (
        PORTFOLIO_RISK_ASSESSMENT_MODULE,
        PORTFOLIO_RISK_AGENT_MODULE,
        PORTFOLIO_RISK_EXECUTION_MODULE,
    ):
        assert BID_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyBid" not in path.read_text(encoding="utf-8"), path


def test_api_and_create_app_remain_unwired_to_the_bid_port() -> None:
    assert APP_MODULE.exists()
    for path in sorted(API_ROOT.rglob("*.py")):
        assert BID_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert "TradingStrategyBid" not in source, path
        assert "trading_strategy_bid" not in source, path


def test_execution_service_imports_only_the_bid_request_and_never_the_port() -> None:
    # Chunk 204: the exact service assembles the request; the agent owns the port.
    assert BID_MODULE_NAME in imported_modules(TRADING_STRATEGY_EXECUTION_MODULE)
    service_names = imported_names(TRADING_STRATEGY_EXECUTION_MODULE)
    assert "TradingStrategyBidRequest" in service_names
    assert "TradingStrategyBidPort" not in service_names
    identifiers = _identifier_names(TRADING_STRATEGY_EXECUTION_MODULE)
    assert "TradingStrategyBidPort" not in identifiers
    assert "propose_bids" not in identifiers
    assert "MarketBid" not in {
        node.func.id
        for node in ast.walk(_tree(TRADING_STRATEGY_EXECUTION_MODULE))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_no_other_production_module_imports_the_bid_port() -> None:
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path in (BID_MODULE, TRADING_STRATEGY_AGENT_MODULE, TRADING_STRATEGY_EXECUTION_MODULE):
            continue
        assert BID_MODULE_NAME not in imported_modules(path), path
        assert "TradingStrategyBid" not in path.read_text(encoding="utf-8"), path
