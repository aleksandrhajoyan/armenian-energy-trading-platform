"""Risk & Bid proposal handoff stays an immutable, application-owned, unwired record."""

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
PORTS_ROOT = APPLICATION_ROOT / "ports"
HANDOFF_MODULE = ORCHESTRATION_ROOT / "risk_and_bid_proposal_handoff.py"
ORCHESTRATION_INIT_MODULE = ORCHESTRATION_ROOT / "__init__.py"
AGENTS_INIT_MODULE = AGENTS_ROOT / "__init__.py"
PORTS_INIT_MODULE = PORTS_ROOT / "__init__.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
AGENT_BASE_MODULE = AGENTS_ROOT / "base.py"
API_ROOT = PRODUCTION_ROOT / "api"
APP_MODULE = API_ROOT / "app.py"
HANDOFF_MODULE_NAME = "energy_trading.application.orchestration.risk_and_bid_proposal_handoff"

HANDOFF_FIELDS = (
    ("workflow_id", "str"),
    ("portfolio_id", "EntityId"),
    ("delivery_date", "date"),
    ("forecasting_success", "ForecastingSuccess"),
    ("risk_assessment", "RiskAssessment"),
    ("bid_proposals", "tuple[MarketBid, ...]"),
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "datetime",
        "energy_trading.application.orchestration.forecasting_success",
        "energy_trading.domain.models.trading",
        "energy_trading.domain.value_objects.quantities",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "dataclass",
        "date",
        "ForecastingSuccess",
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
    "energy_trading.application.ports",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_success_read",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.portfolio_risk_execution",
    "energy_trading.application.orchestration.trading_strategy_execution",
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
        "MarketClearingResult",
        "ClearingStatus",
        "SettlementResult",
        "BidSide",
        "GenerationAvailabilityRecord",
        "RegulatoryConstraint",
        "HydroRecord",
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
        "ClearingStatus",
        "model_validate",
        "model_construct",
        "model_copy",
        "copy",
        "deepcopy",
        "replace",
        "get_success",
        "record_success",
        "resolve_plan",
        "assess",
        "propose_bids",
        "run",
        "execute",
        "submit",
        "submit_bids",
        "clear",
        "settle",
        "approve",
        "authorize",
        "sorted",
        "sort",
        "set",
        "frozenset",
        "filter",
        "sum",
        "min",
        "max",
        "round",
        "len",
        "Decimal",
        "quantity_mw",
        "limit_price",
        "amount_per_mwh",
        "value_at_risk",
        "risk_score",
        "expected_margin",
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
        "lru_cache",
        "cache",
        "Repository",
        "ServiceLocator",
        "AgentRegistry",
        "AgentFactory",
        "StateGraph",
    }
)

FORBIDDEN_FIELD_TOKENS = (
    "approv",
    "authori",
    "eligib",
    "ready",
    "readiness",
    "status",
    "submission",
    "submitted",
    "accept",
    "exchange",
    "settle",
    "success_flag",
    "is_",
)

COORDINATOR_CLASS_NAMES = frozenset(
    {
        "PortfolioRiskAgent",
        "TradingStrategyAgent",
        "PortfolioRiskExecutionService",
        "TradingStrategyExecutionService",
        "ForecastingSuccess",
        "RiskAssessment",
        "MarketBid",
        "tuple",
        "list",
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


def _keyword_value(call: ast.Call, name: str) -> object:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None


def test_handoff_module_belongs_to_application_orchestration() -> None:
    assert HANDOFF_MODULE.exists()
    assert HANDOFF_MODULE.parent == ORCHESTRATION_ROOT
    definitions = sorted(
        path.relative_to(PRODUCTION_ROOT).as_posix()
        for path in PRODUCTION_ROOT.rglob("*.py")
        for node in _tree(path).body
        if isinstance(node, ast.ClassDef) and node.name == "RiskAndBidProposalHandoff"
    )
    assert definitions == ["application/orchestration/risk_and_bid_proposal_handoff.py"]


def test_handoff_module_defines_exactly_one_public_contract_type() -> None:
    tree = _tree(HANDOFF_MODULE)
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert class_names == ["RiskAndBidProposalHandoff"]
    module_functions = [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert all(name.startswith("_") for name in module_functions)
    assert [node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign)] == []


def test_handoff_is_frozen_slotted_keyword_only_dataclass_with_canonical_fields() -> None:
    class_def = _class_def(HANDOFF_MODULE, "RiskAndBidProposalHandoff")
    assert class_def.bases == []
    assert class_def.keywords == []
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
    assert fields == HANDOFF_FIELDS


def test_handoff_fields_have_no_defaults_and_class_has_no_public_methods() -> None:
    class_def = _class_def(HANDOFF_MODULE, "RiskAndBidProposalHandoff")
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign):
            assert item.value is None
        assert not isinstance(item, ast.Assign)
    methods = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert methods == ["__post_init__"]
    assert not any(isinstance(node, ast.AsyncFunctionDef) for node in ast.walk(class_def))


def test_handoff_has_no_invented_status_or_authorization_fields() -> None:
    class_def = _class_def(HANDOFF_MODULE, "RiskAndBidProposalHandoff")
    field_names = [
        item.target.id
        for item in class_def.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    ]
    for name in field_names:
        lowered = name.lower()
        for token in FORBIDDEN_FIELD_TOKENS:
            assert token not in lowered, (name, token)
    tree = _tree(HANDOFF_MODULE)
    nested_classes = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name != "RiskAndBidProposalHandoff"
    ]
    assert nested_classes == []


def test_handoff_module_imports_only_canonical_contracts() -> None:
    modules = imported_modules(HANDOFF_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(HANDOFF_MODULE) - ALLOWED_MODULE_IMPORTS == ALLOWED_IMPORTED_NAMES
    source = HANDOFF_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_handoff_module_has_no_calculation_execution_or_reconstruction() -> None:
    tree = _tree(HANDOFF_MODULE)
    for node in ast.walk(tree):
        assert not isinstance(
            node,
            ast.Await
            | ast.AsyncWith
            | ast.AsyncFor
            | ast.BinOp
            | ast.AugAssign
            | ast.Lambda
            | ast.ListComp
            | ast.SetComp
            | ast.DictComp
            | ast.Global
            | ast.Nonlocal
            | ast.Yield
            | ast.YieldFrom,
        )
        if isinstance(node, ast.Call):
            assert _call_name(node) not in COORDINATOR_CLASS_NAMES
        if isinstance(node, ast.Return):
            assert node.value is None


def test_handoff_module_excludes_escape_hatches_policy_and_runtime_tokens() -> None:
    names = annotation_type_names(HANDOFF_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(HANDOFF_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    code_only = " ".join(sorted(identifiers | imported_modules(HANDOFF_MODULE))).lower()
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
        "convert",
        "mwh",
        "fx",
        "approv",
        "authoriz",
        "eligib",
        "submit",
        "settle",
        "psrc",
        "armenia",
    ):
        assert token not in code_only, token


def test_handoff_module_does_not_name_agents_ports_or_execution_services() -> None:
    source = HANDOFF_MODULE.read_text(encoding="utf-8")
    for name in (
        "PortfolioRiskAgent",
        "TradingStrategyAgent",
        "PortfolioRiskAssessment",
        "TradingStrategyBid",
        "PortfolioRiskExecutionService",
        "TradingStrategyExecutionService",
        "ForecastingSuccessReadPort",
        "AgentPort",
    ):
        assert name not in source, name


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


def test_handoff_does_not_add_a_concrete_agent() -> None:
    agent_modules = sorted(
        path.name for path in AGENTS_ROOT.glob("*.py") if path.name not in {"__init__.py"}
    )
    assert "risk_and_bid_proposal_handoff.py" not in agent_modules
    assert len([name for name in agent_modules if name != "base.py"]) == 10


def test_packages_do_not_export_the_handoff() -> None:
    for path in (ORCHESTRATION_INIT_MODULE, AGENTS_INIT_MODULE, PORTS_INIT_MODULE):
        assert HANDOFF_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert "RiskAndBidProposalHandoff" not in source, path
        assert "risk_and_bid_proposal_handoff" not in source, path


def test_workflow_state_and_graph_remain_unaware_of_the_handoff() -> None:
    for path in (STATE_MODULE, GRAPH_MODULE):
        assert HANDOFF_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert "RiskAndBidProposalHandoff" not in source, path
        assert "risk_and_bid_proposal_handoff" not in source, path


def test_no_other_production_module_imports_or_constructs_the_handoff() -> None:
    assert APP_MODULE.exists()
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path == HANDOFF_MODULE:
            continue
        assert HANDOFF_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert "RiskAndBidProposalHandoff" not in source, path
        assert "risk_and_bid_proposal_handoff" not in source, path
