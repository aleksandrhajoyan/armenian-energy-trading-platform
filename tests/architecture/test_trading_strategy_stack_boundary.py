"""Chunk 206 Trading Strategy execution composition root stays an outer, unwired builder."""

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
BUILDER_MODULE = COMPOSITION_ROOT / "trading_strategy_stack.py"
BUILDER_NAME = "build_trading_strategy_execution_service"
BUILDER_MODULE_NAME = "energy_trading.api.composition.trading_strategy_stack"
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

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.domain",
    "energy_trading.application.errors",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_success",
    "energy_trading.application.orchestration.forecasting_success_read",
    "energy_trading.application.orchestration.portfolio_risk_execution",
    "energy_trading.application.ports.portfolio_risk_assessment",
    "energy_trading.application.agents.portfolio_risk",
    "energy_trading.application.agents.base",
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

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.trading_strategy",
        "energy_trading.application.orchestration.trading_strategy_execution",
        "energy_trading.application.ports.trading_strategy_bid",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "TradingStrategyAgent",
        "TradingStrategyExecutionService",
        "TradingStrategyBidPort",
    }
)

ALLOWED_ANNOTATIONS = {"bid_port": "TradingStrategyBidPort"}

EXPECTED_CONSTRUCTIONS = ["TradingStrategyAgent", "TradingStrategyExecutionService"]

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "propose_bids",
        "run",
        "execute",
        "create_task",
        "gather",
        "TaskGroup",
        "TradingStrategyBidRequest",
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


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.exists()
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert COMPOSITION_ROOT.parent == API_ROOT
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).with_suffix("").as_posix()
    assert relative.replace("/", ".") == BUILDER_MODULE_NAME


def test_builder_imports_only_the_three_published_application_types() -> None:
    modules = imported_modules(BUILDER_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert modules == ALLOWED_MODULE_IMPORTS
    assert imported_names(BUILDER_MODULE) == ALLOWED_IMPORTED_NAMES | ALLOWED_MODULE_IMPORTS
    tree = _parse(BUILDER_MODULE)
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
    definitions: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        for node in _parse(path).body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and (
                node.name == BUILDER_NAME
            ):
                definitions.append(path.relative_to(SRC_ROOT).as_posix())
    assert definitions == ["energy_trading/api/composition/trading_strategy_stack.py"]


def test_builder_signature_has_one_required_keyword_only_bid_port() -> None:
    builder = _builder_function()
    assert builder.decorator_list == []
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == tuple(ALLOWED_ANNOTATIONS)
    assert builder.args.kw_defaults == [None]
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == ALLOWED_ANNOTATIONS
    assert builder.returns is not None
    assert ast.unparse(builder.returns) == "TradingStrategyExecutionService"


def test_builder_constructs_agent_then_service_and_forwards_identities() -> None:
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
                ast.Constant,
            ),
        )
        and not (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and builder.body
            and isinstance(builder.body[0], ast.Expr)
            and builder.body[0].value is node
        )
    ]
    assert control == []
    calls = [_call_name(node) for node in ast.walk(builder) if isinstance(node, ast.Call)]
    assert sorted(name or "" for name in calls) == sorted(EXPECTED_CONSTRUCTIONS)
    for node in ast.walk(builder):
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Name)

    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 2
    agent_assign, returned = statements

    assert isinstance(agent_assign, ast.Assign)
    assert len(agent_assign.targets) == 1
    assert isinstance(agent_assign.targets[0], ast.Name)
    agent_name = agent_assign.targets[0].id
    assert isinstance(agent_assign.value, ast.Call)
    assert _call_name(agent_assign.value) == "TradingStrategyAgent"
    assert _keywords(agent_assign.value) == {"bid_port": "bid_port"}

    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Call)
    assert _call_name(returned.value) == "TradingStrategyExecutionService"
    assert _keywords(returned.value) == {"bid_agent": agent_name}


def test_builder_constructs_no_request_and_invokes_no_runtime_method() -> None:
    identifiers = _identifier_names(BUILDER_MODULE)
    assert {"TradingStrategyBidRequest", "propose_bids", "run", "execute"}.isdisjoint(identifiers)
    calls = [node for node in ast.walk(_parse(BUILDER_MODULE)) if isinstance(node, ast.Call)]
    assert all(isinstance(node.func, ast.Name) for node in calls)
    assert sorted(_call_name(node) or "" for node in calls) == sorted(EXPECTED_CONSTRUCTIONS)


def test_builder_owns_no_bid_generation_approval_risk_or_runtime_policy() -> None:
    identifiers = _identifier_names(BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    assert annotation_type_names(BUILDER_MODULE) <= {
        "TradingStrategyBidPort",
        "TradingStrategyExecutionService",
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
        assert "TradingStrategyBidPort" not in path.read_text(encoding="utf-8"), path
        assert "propose_bids" not in path.read_text(encoding="utf-8"), path


def test_composition_package_does_not_export_the_builder() -> None:
    source = COMPOSITION_INIT.read_text(encoding="utf-8")
    assert BUILDER_MODULE_NAME not in imported_modules(COMPOSITION_INIT)
    assert "trading_strategy_stack" not in source
    assert BUILDER_NAME not in source


def test_application_packages_do_not_export_trading_strategy_objects() -> None:
    for path in (AGENTS_INIT, ORCHESTRATION_INIT, PORTS_INIT):
        source = path.read_text(encoding="utf-8")
        assert "TradingStrategy" not in source, path
        assert "trading_strategy" not in source, path


def test_application_domain_ml_and_infrastructure_do_not_import_the_builder() -> None:
    for root in (APPLICATION_ROOT, DOMAIN_ROOT, ML_ROOT, INFRASTRUCTURE_ROOT):
        assert collect_import_violations(root, ("energy_trading.api",)) == []
        for path in sorted(root.rglob("*.py")):
            assert BUILDER_NAME not in path.read_text(encoding="utf-8"), path


def test_create_app_and_http_surfaces_remain_unwired_to_the_builder() -> None:
    for path in http_transport_api_paths(API_ROOT):
        assert BUILDER_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert BUILDER_NAME not in source, path
        assert "trading_strategy_stack" not in source, path
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
    assert call_names.isdisjoint({BUILDER_NAME, *EXPECTED_CONSTRUCTIONS})
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "trading_strategy" not in app_source
    assert "tradingstrategy" not in app_source


def test_other_composition_modules_do_not_import_or_construct_trading_strategy() -> None:
    for path in sorted(COMPOSITION_ROOT.glob("*.py")):
        if path == BUILDER_MODULE:
            continue
        assert BUILDER_MODULE_NAME not in imported_modules(path), path
        source = path.read_text(encoding="utf-8")
        assert BUILDER_NAME not in source, path
        assert "TradingStrategy" not in source, path
        assert "trading_strategy" not in source, path
    constructed_by: list[str] = []
    for path in sorted(API_ROOT.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Call) and _call_name(node) in EXPECTED_CONSTRUCTIONS:
                constructed_by.append(path.relative_to(SRC_ROOT).as_posix())
    assert sorted(set(constructed_by)) == [
        "energy_trading/api/composition/trading_strategy_stack.py"
    ]


def test_graph_remains_unwired_to_trading_strategy() -> None:
    modules = imported_modules(GRAPH_MODULE)
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert not any(module.startswith("energy_trading.api") for module in modules)
    assert BUILDER_NAME not in source
    assert "TradingStrategy" not in source
    assert "trading_strategy" not in source


def test_agent_identities_and_workflow_state_are_unchanged() -> None:
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
    for path in (AGENT_BASE_MODULE, STATE_MODULE):
        assert "trading_strategy_stack" not in path.read_text(encoding="utf-8")
    for path in sorted(DOMAIN_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "trading_strategy_stack" not in source, path
        assert BUILDER_NAME not in source, path
