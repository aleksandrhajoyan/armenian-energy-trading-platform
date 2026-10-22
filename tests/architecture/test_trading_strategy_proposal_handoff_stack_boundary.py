"""Chunk 209 Trading Strategy proposal handoff composition stays an outer, unwired builder."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
COMPOSITION_ROOT = API_ROOT / "composition"
COMPOSITION_INIT = COMPOSITION_ROOT / "__init__.py"
BUILDER_MODULE = COMPOSITION_ROOT / "trading_strategy_proposal_handoff_stack.py"
BUILDER_NAME = "build_trading_strategy_proposal_handoff_service"
BUILDER_MODULE_NAME = "energy_trading.api.composition.trading_strategy_proposal_handoff_stack"
NESTED_BUILDER_NAME = "build_trading_strategy_execution_service"
NESTED_BUILDER_MODULE_NAME = "energy_trading.api.composition.trading_strategy_stack"
SERVICE_CLASS_NAME = "TradingStrategyProposalHandoffService"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
GRAPH_MODULE = APPLICATION_ROOT / "orchestration" / "graph.py"
STATE_MODULE = APPLICATION_ROOT / "orchestration" / "state.py"
AGENT_BASE_MODULE = APPLICATION_ROOT / "agents" / "base.py"
AGENTS_INIT = APPLICATION_ROOT / "agents" / "__init__.py"
ORCHESTRATION_INIT = APPLICATION_ROOT / "orchestration" / "__init__.py"
PORTS_INIT = APPLICATION_ROOT / "ports" / "__init__.py"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        NESTED_BUILDER_MODULE_NAME,
        "energy_trading.application.orchestration.trading_strategy_proposal_handoff",
        "energy_trading.application.ports.trading_strategy_bid",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        NESTED_BUILDER_NAME,
        SERVICE_CLASS_NAME,
        "TradingStrategyBidPort",
    }
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.domain",
    "energy_trading.application.errors",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.trading_strategy_execution",
    "energy_trading.application.orchestration.risk_and_bid_proposal_handoff",
    "energy_trading.application.orchestration.forecasting_success",
    "energy_trading.application.orchestration.portfolio_risk_execution",
    "energy_trading.application.ports.portfolio_risk_assessment",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.api.composition.portfolio_risk_stack",
    "energy_trading.shared.config",
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
    "n8n",
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "decimal",
    "math",
    "statistics",
    "functools",
    "tenacity",
    "backoff",
    "logging",
    "importlib",
    "asyncio",
    "os",
    "sys",
    "typing",
    "datetime",
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "propose_bids",
        "run",
        "execute",
        "create_task",
        "gather",
        "TaskGroup",
        "TradingStrategyAgent",
        "TradingStrategyExecutionService",
        "TradingStrategyBidRequest",
        "RiskAndBidProposalHandoff",
        "MarketBid",
        "BidSide",
        "BUY",
        "SELL",
        "RiskAssessment",
        "ForecastingSuccess",
        "ForecastingSuccessReadPort",
        "PortfolioRiskAssessmentPort",
        "PortfolioRiskAgent",
        "PortfolioRiskExecutionService",
        "GenerationAvailabilityRecord",
        "RegulatoryConstraint",
        "WorkflowState",
        "AgentName",
        "AgentPort",
        "get_success",
        "assess",
        "submit",
        "submit_bids",
        "clear",
        "settle",
        "approve",
        "authorize",
        "eligible",
        "eligibility",
        "create_app",
        "build_workflow_graph",
        "include_router",
        "add_api_route",
        "app",
        "state",
        "lifespan",
        "getenv",
        "environ",
        "get_settings",
        "settings",
        "env_file",
        "registry",
        "Registry",
        "factory",
        "Factory",
        "container",
        "Container",
        "locator",
        "resolve",
        "get_service",
        "select",
        "selected",
        "default",
        "policy",
        "threshold",
        "quantity_mw",
        "limit_price",
        "amount_per_mwh",
        "value_at_risk",
        "risk_score",
        "expected_margin",
        "exposure",
        "convert",
        "Decimal",
        "sum",
        "min",
        "max",
        "round",
        "sorted",
        "retry",
        "fallback",
        "cache",
        "lru_cache",
        "logger",
        "getLogger",
        "load",
        "save",
        "store",
        "persist",
        "open",
        "import_module",
        "__import__",
        "getattr",
        "setattr",
        "global",
        "TYPE_CHECKING",
        "cast",
    }
)

FORBIDDEN_CODE_FRAGMENTS = (
    "energy_trading.ml",
    "infrastructure",
    "inmemory",
    "langgraph",
    "fastapi",
    "starlette",
    "openai",
    "qdrant",
    "redis",
    "sqlalchemy",
    "importlib",
    "__import__",
    "type_checking",
    "os.environ",
    "getenv",
    "app.state",
    "gateway",
    ".propose_bids(",
    ".run(",
    ".execute(",
    "await ",
    "try:",
    "except ",
    "raise ",
)

AGENT_NAME_MEMBER_COUNT = 13
CONCRETE_AGENT_MODULE_COUNT = 10

WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _public_module_functions(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in _parse(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _builder_function() -> ast.FunctionDef:
    for node in _public_module_functions(BUILDER_MODULE):
        if isinstance(node, ast.FunctionDef) and node.name == BUILDER_NAME:
            return node
    msg = f"{BUILDER_NAME} not found"
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
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name)
        elif isinstance(node, ast.Global | ast.Nonlocal):
            names.add("global")
    return names


def _keywords(call: ast.Call) -> dict[str, str]:
    assert call.args == []
    assert all(keyword.arg is not None for keyword in call.keywords)
    return {str(keyword.arg): ast.unparse(keyword.value) for keyword in call.keywords}


def _body_without_docstring(function: ast.FunctionDef) -> list[ast.stmt]:
    body = list(function.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return body


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.exists()
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert COMPOSITION_ROOT.parent == API_ROOT
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).with_suffix("").as_posix()
    assert relative.replace("/", ".") == BUILDER_MODULE_NAME


def test_builder_imports_only_the_three_published_symbols() -> None:
    modules = imported_modules(BUILDER_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert modules == ALLOWED_MODULE_IMPORTS
    assert imported_names(BUILDER_MODULE) == ALLOWED_IMPORTED_NAMES | ALLOWED_MODULE_IMPORTS
    tree = _parse(BUILDER_MODULE)
    sources = {
        alias.name: node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert sources == {
        NESTED_BUILDER_NAME: NESTED_BUILDER_MODULE_NAME,
        SERVICE_CLASS_NAME: (
            "energy_trading.application.orchestration.trading_strategy_proposal_handoff"
        ),
        "TradingStrategyBidPort": "energy_trading.application.ports.trading_strategy_bid",
    }
    aliases = [
        alias.asname
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom | ast.Import)
        for alias in node.names
        if alias.asname is not None
    ]
    assert aliases == []
    assert [node for node in ast.walk(tree) if isinstance(node, ast.Import)] == []
    nested_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom) and node not in tree.body
    ]
    assert nested_imports == []
    assert all(node.level == 0 for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))


def test_builder_exposes_exactly_one_public_synchronous_function() -> None:
    public = _public_module_functions(BUILDER_MODULE)
    assert [node.name for node in public] == [BUILDER_NAME]
    assert all(isinstance(node, ast.FunctionDef) for node in public)
    tree = _parse(BUILDER_MODULE)
    assert [node for node in tree.body if isinstance(node, ast.ClassDef)] == []
    private_functions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("_")
    ]
    assert private_functions == []
    module_assignments = [
        node for node in tree.body if isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign)
    ]
    assert module_assignments == []
    async_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef | ast.Await | ast.AsyncWith | ast.AsyncFor)
    ]
    assert async_nodes == []
    definitions = sorted(
        path.relative_to(SRC_ROOT).as_posix()
        for path in PRODUCTION_ROOT.rglob("*.py")
        for node in _parse(path).body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == BUILDER_NAME
    )
    assert definitions == [
        "energy_trading/api/composition/trading_strategy_proposal_handoff_stack.py"
    ]


def test_builder_signature_has_one_required_keyword_only_bid_port() -> None:
    builder = _builder_function()
    assert builder.decorator_list == []
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert [arg.arg for arg in builder.args.kwonlyargs] == ["bid_port"]
    assert builder.args.kw_defaults == [None]
    annotation = builder.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "TradingStrategyBidPort"
    assert builder.returns is not None
    assert ast.unparse(builder.returns) == SERVICE_CLASS_NAME


def test_builder_calls_nested_builder_once_then_constructs_and_returns_one_service() -> None:
    builder = _builder_function()
    control = [
        type(node).__name__
        for node in ast.walk(builder)
        if isinstance(
            node,
            (
                ast.If,
                ast.IfExp,
                ast.Match,
                ast.For,
                ast.While,
                ast.Try,
                ast.With,
                ast.ExceptHandler,
                ast.Raise,
                ast.Lambda,
                ast.comprehension,
                ast.BoolOp,
                ast.BinOp,
                ast.UnaryOp,
                ast.Compare,
                ast.Subscript,
                ast.Dict,
                ast.List,
                ast.Tuple,
            ),
        )
    ]
    assert control == []
    calls = [node for node in ast.walk(builder) if isinstance(node, ast.Call)]
    assert all(isinstance(node.func, ast.Name) for node in calls)
    assert sorted(_call_name(node) or "" for node in calls) == sorted(
        [NESTED_BUILDER_NAME, SERVICE_CLASS_NAME]
    )

    statements = _body_without_docstring(builder)
    assert len(statements) == 2
    nested_assign, returned = statements

    assert isinstance(nested_assign, ast.Assign)
    assert len(nested_assign.targets) == 1
    assert isinstance(nested_assign.targets[0], ast.Name)
    nested_service_name = nested_assign.targets[0].id
    assert isinstance(nested_assign.value, ast.Call)
    assert _call_name(nested_assign.value) == NESTED_BUILDER_NAME
    assert _keywords(nested_assign.value) == {"bid_port": "bid_port"}

    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Call)
    assert _call_name(returned.value) == SERVICE_CLASS_NAME
    assert _keywords(returned.value) == {"trading_strategy_service": nested_service_name}


def test_builder_does_not_construct_agent_execution_service_or_runtime_dtos() -> None:
    identifiers = _identifier_names(BUILDER_MODULE)
    assert {
        "TradingStrategyAgent",
        "TradingStrategyExecutionService",
        "TradingStrategyBidRequest",
        "RiskAndBidProposalHandoff",
        "MarketBid",
        "RiskAssessment",
        "ForecastingSuccess",
    }.isdisjoint(identifiers)
    assert {"run", "execute", "propose_bids"}.isdisjoint(identifiers)
    calls = [node for node in ast.walk(_parse(BUILDER_MODULE)) if isinstance(node, ast.Call)]
    assert sorted(_call_name(node) or "" for node in calls) == sorted(
        [NESTED_BUILDER_NAME, SERVICE_CLASS_NAME]
    )


def test_builder_owns_no_bid_risk_eligibility_io_or_runtime_policy() -> None:
    identifiers = _identifier_names(BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    assert annotation_type_names(BUILDER_MODULE) <= {
        "TradingStrategyBidPort",
        SERVICE_CLASS_NAME,
    }
    code_only = ast.unparse(_parse(BUILDER_MODULE)).lower()
    for fragment in FORBIDDEN_CODE_FRAGMENTS:
        assert fragment not in code_only, fragment


def test_builder_selects_no_concrete_bid_port_implementation() -> None:
    assert not any(
        module.startswith(("energy_trading.infrastructure", "energy_trading.ml"))
        for module in imported_modules(BUILDER_MODULE)
    )
    for path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")) + sorted(ML_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "TradingStrategyBidPort" not in source, path
        assert "propose_bids" not in source, path


def test_packages_do_not_export_the_builder() -> None:
    source = COMPOSITION_INIT.read_text(encoding="utf-8")
    assert BUILDER_MODULE_NAME not in imported_modules(COMPOSITION_INIT)
    assert "trading_strategy_proposal_handoff_stack" not in source
    assert BUILDER_NAME not in source
    for path in (AGENTS_INIT, ORCHESTRATION_INIT, PORTS_INIT):
        source = path.read_text(encoding="utf-8")
        assert "TradingStrategy" not in source, path
        assert "trading_strategy" not in source, path


def test_no_other_production_module_imports_or_calls_the_builder() -> None:
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path == BUILDER_MODULE:
            continue
        assert BUILDER_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert BUILDER_NAME not in source, path
        assert "trading_strategy_proposal_handoff_stack" not in source, path
    for root in (APPLICATION_ROOT, DOMAIN_ROOT, ML_ROOT, INFRASTRUCTURE_ROOT):
        assert collect_import_violations(root, ("energy_trading.api",)) == []


def test_create_app_http_surfaces_and_graph_remain_unwired_to_the_builder() -> None:
    for path in http_transport_api_paths(API_ROOT):
        assert BUILDER_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert BUILDER_NAME not in source, path
        assert SERVICE_CLASS_NAME not in source, path
    app_tree = _parse(API_APP)
    create_app = next(
        node
        for node in ast.walk(app_tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names = {
        name
        for node in ast.walk(create_app)
        if isinstance(node, ast.Call)
        for name in (_call_name(node),)
        if name is not None
    }
    assert call_names.isdisjoint({BUILDER_NAME, NESTED_BUILDER_NAME, SERVICE_CLASS_NAME})
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "trading_strategy" not in app_source
    assert "tradingstrategy" not in app_source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert not any(
        module.startswith("energy_trading.api") for module in imported_modules(GRAPH_MODULE)
    )
    assert BUILDER_NAME not in graph_source
    assert "TradingStrategy" not in graph_source
    assert "trading_strategy" not in graph_source


def test_agent_identities_concrete_agents_and_workflow_state_are_unchanged() -> None:
    agent_name = next(
        node
        for node in _parse(AGENT_BASE_MODULE).body
        if isinstance(node, ast.ClassDef) and node.name == "AgentName"
    )
    members = [item for item in agent_name.body if isinstance(item, ast.Assign | ast.AnnAssign)]
    assert len(members) == AGENT_NAME_MEMBER_COUNT
    agent_port = next(
        node
        for node in _parse(AGENT_BASE_MODULE).body
        if isinstance(node, ast.ClassDef) and node.name == "AgentPort"
    )
    assert [ast.unparse(param) for param in agent_port.type_params] == ["TRequest", "TResult"]
    concrete_agents = sorted(
        path.name
        for path in (APPLICATION_ROOT / "agents").glob("*.py")
        if path.name not in {"__init__.py", "base.py"}
    )
    assert len(concrete_agents) == CONCRETE_AGENT_MODULE_COUNT
    workflow_state = next(
        node
        for node in _parse(STATE_MODULE).body
        if isinstance(node, ast.ClassDef) and node.name == "WorkflowState"
    )
    fields = tuple(
        item.target.id
        for item in workflow_state.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    )
    assert fields == WORKFLOW_STATE_FIELDS
    for path in (AGENT_BASE_MODULE, STATE_MODULE, *sorted(DOMAIN_ROOT.rglob("*.py"))):
        source = path.read_text(encoding="utf-8")
        assert "trading_strategy_proposal_handoff_stack" not in source, path
        assert BUILDER_NAME not in source, path
