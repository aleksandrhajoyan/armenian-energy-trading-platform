"""Chunk 188 forecasting execution composition root stays an outer, unwired builder."""

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
BUILDER_MODULE = COMPOSITION_ROOT / "forecasting_execution.py"
BUILDER_NAME = "build_parallel_forecasting_execution_service"
BUILDER_MODULE_NAME = "energy_trading.api.composition.forecasting_execution"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
GRAPH_MODULE = APPLICATION_ROOT / "orchestration" / "graph.py"
ML_ROOT = PRODUCTION_ROOT / "ml"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.domain",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_plan",
    "energy_trading.application.orchestration.forecasting_success",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.failure_policy",
    "energy_trading.application.ports.forecasting_context",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.shared.config",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
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
    "joblib",
    "pickle",
    "tenacity",
    "backoff",
    "importlib",
    "asyncio",
    "os",
    "sys",
    "typing",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.consumer_load_forecast",
        "energy_trading.application.agents.dam_price_forecast",
        "energy_trading.application.orchestration.forecasting_executor",
        "energy_trading.application.ports.consumer_load_forecast_model",
        "energy_trading.application.ports.dam_price_forecast_model",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "ConsumerLoadForecastAgent",
        "DAMPriceForecastAgent",
        "ParallelForecastingExecutionService",
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
    }
)

ALLOWED_ANNOTATIONS = {
    "consumer_load_model": "ConsumerLoadForecastModelPort",
    "dam_price_model": "DAMPriceForecastModelPort",
}

CONCRETE_MODEL_NAMES = frozenset(
    {
        "PreviousDayPersistenceConsumerLoadForecastModel",
        "Lag24h168hOLSConsumerLoadForecastModel",
        "PreviousDayPersistenceDAMPriceForecastModel",
        "Lag24h168hOLSDAMPriceForecastModel",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "forecast",
        "run",
        "execute",
        "create_task",
        "gather",
        "TaskGroup",
        "ForecastingPlan",
        "ForecastingSuccess",
        "WorkflowState",
        "ForecastingWorkflowStep",
        "ForecastingWorkflowContextPort",
        "FailurePolicyPort",
        "FailureAction",
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
        "AppSettings",
        "settings",
        "env_file",
        "model_name",
        "model_path",
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
        "champion",
        "best",
        "preferred",
        "winner",
        "mae",
        "score",
        "compare",
        "threshold",
        "retry",
        "fallback",
        "load",
        "save",
        "persist",
        "import_module",
        "__import__",
        "getattr",
        "setattr",
        "TYPE_CHECKING",
        "cast",
        *CONCRETE_MODEL_NAMES,
    }
)

FORBIDDEN_SOURCE_FRAGMENTS = (
    "energy_trading.ml",
    "infrastructure",
    "persistence",
    "ols",
    "lag_24h",
    "lightgbm",
    "xgboost",
    "prophet",
    "langgraph",
    "langchain",
    "fastapi",
    "starlette",
    "openai",
    "qdrant",
    "redis",
    "importlib",
    "__import__",
    "type_checking",
    "os.environ",
    "getenv",
    "app.state",
    ".forecast(",
    ".run(",
    ".execute(",
    "await ",
    "try:",
    "except ",
)

EXPECTED_CONSTRUCTION_ORDER = [
    "ConsumerLoadForecastAgent",
    "DAMPriceForecastAgent",
    "ParallelForecastingExecutionService",
]


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
    return names


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.exists()
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert COMPOSITION_ROOT.parent == API_ROOT
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).with_suffix("").as_posix()
    assert relative.replace("/", ".") == BUILDER_MODULE_NAME


def test_builder_imports_only_the_five_application_contracts() -> None:
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
    plain_imports = [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
    assert plain_imports == []
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
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == (
                BUILDER_NAME
            ):
                definitions.append(path.relative_to(SRC_ROOT).as_posix())
    assert definitions == ["energy_trading/api/composition/forecasting_execution.py"]


def test_builder_signature_has_two_required_keyword_only_model_ports() -> None:
    builder = _builder_function()
    assert builder.decorator_list == []
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == tuple(ALLOWED_ANNOTATIONS)
    assert builder.args.kw_defaults == [None, None]
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == ALLOWED_ANNOTATIONS
    assert builder.returns is not None
    assert ast.unparse(builder.returns) == "ParallelForecastingExecutionService"


def test_builder_performs_exactly_the_narrow_construction_chain() -> None:
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
                ast.Compare,
                ast.Subscript,
                ast.Dict,
            ),
        )
    ]
    assert control == []
    calls = [_call_name(node) for node in ast.walk(builder) if isinstance(node, ast.Call)]
    assert sorted(name or "" for name in calls) == sorted(EXPECTED_CONSTRUCTION_ORDER)
    for node in ast.walk(builder):
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Name)

    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 3
    consumer_assign, dam_assign, returned = statements

    assert isinstance(consumer_assign, ast.Assign)
    assert len(consumer_assign.targets) == 1
    assert isinstance(consumer_assign.targets[0], ast.Name)
    consumer_agent_name = consumer_assign.targets[0].id
    assert isinstance(consumer_assign.value, ast.Call)
    assert _call_name(consumer_assign.value) == "ConsumerLoadForecastAgent"
    assert [ast.unparse(arg) for arg in consumer_assign.value.args] == ["consumer_load_model"]
    assert consumer_assign.value.keywords == []

    assert isinstance(dam_assign, ast.Assign)
    assert len(dam_assign.targets) == 1
    assert isinstance(dam_assign.targets[0], ast.Name)
    dam_agent_name = dam_assign.targets[0].id
    assert isinstance(dam_assign.value, ast.Call)
    assert _call_name(dam_assign.value) == "DAMPriceForecastAgent"
    assert [ast.unparse(arg) for arg in dam_assign.value.args] == ["dam_price_model"]
    assert dam_assign.value.keywords == []

    assert consumer_agent_name != dam_agent_name
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Call)
    assert _call_name(returned.value) == "ParallelForecastingExecutionService"
    assert [ast.unparse(arg) for arg in returned.value.args] == [
        consumer_agent_name,
        dam_agent_name,
    ]
    assert returned.value.keywords == []


def test_builder_owns_no_execution_selection_or_runtime_policy() -> None:
    identifiers = _identifier_names(BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    annotation_names = annotation_type_names(BUILDER_MODULE)
    assert annotation_names <= {
        "ConsumerLoadForecastModelPort",
        "DAMPriceForecastModelPort",
        "ParallelForecastingExecutionService",
    }
    lowered = BUILDER_MODULE.read_text(encoding="utf-8").lower()
    code_only = ast.unparse(_parse(BUILDER_MODULE)).lower()
    for fragment in FORBIDDEN_SOURCE_FRAGMENTS:
        assert fragment not in code_only, fragment
    assert "energy_trading.ml" not in lowered
    assert "import_module" not in lowered


def test_application_does_not_import_api_composition() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        BUILDER_MODULE_NAME,
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        assert BUILDER_NAME not in imported_names(path)
        assert BUILDER_NAME not in path.read_text(encoding="utf-8")


def test_ml_and_infrastructure_do_not_import_the_builder() -> None:
    for root in (ML_ROOT, INFRASTRUCTURE_ROOT):
        assert collect_import_violations(root, ("energy_trading.api",)) == []
        for path in sorted(root.rglob("*.py")):
            assert BUILDER_NAME not in path.read_text(encoding="utf-8")


def test_http_surfaces_and_create_app_remain_unaware_of_the_builder() -> None:
    for path in http_transport_api_paths(API_ROOT):
        assert BUILDER_NAME not in imported_names(path)
        assert BUILDER_MODULE_NAME not in imported_modules(path)
        assert BUILDER_NAME not in path.read_text(encoding="utf-8")
    app_source = API_APP.read_text(encoding="utf-8")
    tree = ast.parse(app_source, filename=str(API_APP))
    create_app = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names = {
        name
        for node in ast.walk(create_app)
        if isinstance(node, ast.Call)
        for name in (_call_name(node),)
        if name is not None
    }
    assert BUILDER_NAME not in call_names
    assert "ParallelForecastingExecutionService" not in call_names
    assert "ConsumerLoadForecastAgent" not in call_names
    assert "DAMPriceForecastAgent" not in call_names
    lowered = app_source.lower()
    assert "forecasting_execution" not in lowered
    assert "parallelforecastingexecutionservice" not in lowered


def test_other_composition_modules_do_not_import_the_builder() -> None:
    for path in sorted(COMPOSITION_ROOT.glob("*.py")):
        if path == BUILDER_MODULE:
            continue
        assert BUILDER_NAME not in imported_names(path)
        assert BUILDER_MODULE_NAME not in imported_modules(path)
        assert BUILDER_NAME not in path.read_text(encoding="utf-8")
    assert "forecasting_execution" not in COMPOSITION_INIT.read_text(encoding="utf-8")


def test_only_the_builder_constructs_forecasting_objects_inside_api() -> None:
    constructed_by: list[str] = []
    for path in sorted(API_ROOT.rglob("*.py")):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Call) and _call_name(node) in EXPECTED_CONSTRUCTION_ORDER:
                constructed_by.append(path.relative_to(SRC_ROOT).as_posix())
    assert sorted(set(constructed_by)) == [
        "energy_trading/api/composition/forecasting_execution.py"
    ]


def test_graph_remains_unwired_and_consumes_the_composed_workflow_step() -> None:
    names = imported_names(GRAPH_MODULE)
    modules = imported_modules(GRAPH_MODULE)
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert BUILDER_NAME not in names
    assert BUILDER_MODULE_NAME not in modules
    assert not any(module.startswith("energy_trading.api") for module in modules)
    assert BUILDER_NAME not in source
    assert "ParallelForecastingExecutionService" not in names
    assert "ForecastingWorkflowStep" in names


def test_no_concrete_ml_model_is_selected_by_the_builder() -> None:
    names = imported_names(BUILDER_MODULE) | _identifier_names(BUILDER_MODULE)
    assert names & CONCRETE_MODEL_NAMES == set()
    for path in sorted(API_ROOT.rglob("*.py")):
        assert not any(module.startswith("energy_trading.ml") for module in imported_modules(path))
        assert imported_names(path) & CONCRETE_MODEL_NAMES == set()
