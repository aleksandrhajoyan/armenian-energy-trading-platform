"""Chunk 191 forecasting failure runtime composition constructs published services only."""

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
BUILDER_MODULE = COMPOSITION_ROOT / "forecasting_failure_runtime.py"
BUILDER_NAME = "build_forecasting_failure_runtime_handler"
BUILDER_MODULE_NAME = "energy_trading.api.composition.forecasting_failure_runtime"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
GRAPH_MODULE = APPLICATION_ROOT / "orchestration" / "graph.py"
ML_ROOT = PRODUCTION_ROOT / "ml"
INFRASTRUCTURE_ROOT = PRODUCTION_ROOT / "infrastructure"

RESOLUTION = "ForecastingFailureContextResolutionService"
PREPARATION = "ForecastingFailureContextPreparationService"
DECISION = "ForecastingFailureDecisionService"
HANDLING = "ForecastingFailureHandlingService"
RUNTIME = "ForecastingFailureRuntimeHandlingService"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.domain",
    "energy_trading.application.agents",
    "energy_trading.application.ports",
    "energy_trading.application.orchestration.forecasting_strict_single_failure_selector",
    "energy_trading.application.orchestration.forecasting_initial_attempt_number_source",
    "energy_trading.application.orchestration.forecasting_initial_failure_policy",
    "energy_trading.application.orchestration.forecasting_failure_action",
    "energy_trading.application.orchestration.forecasting_failure_transition",
    "energy_trading.application.orchestration.forecasting_exception_group",
    "energy_trading.application.orchestration.forecasting_failure_classification",
    "energy_trading.application.orchestration.forecasting_executor",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.parallel_ingestion",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.api.dependencies",
    "energy_trading.api.composition.forecasting",
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
    "lightgbm",
    "xgboost",
    "prophet",
    "sklearn",
    "n8n",
    "importlib",
    "asyncio",
    "logging",
    "os",
    "sys",
    "typing",
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.failure_policy",
        "energy_trading.application.orchestration.forecasting_attempt_number",
        "energy_trading.application.orchestration.forecasting_failure_context_preparation",
        "energy_trading.application.orchestration.forecasting_failure_context_resolution",
        "energy_trading.application.orchestration.forecasting_failure_decision",
        "energy_trading.application.orchestration.forecasting_failure_handling",
        "energy_trading.application.orchestration.forecasting_failure_runtime_handling",
        "energy_trading.application.orchestration.forecasting_failure_selection",
    }
)

ALLOWED_IMPORTED_NAMES = frozenset(
    {
        "FailurePolicyPort",
        "ForecastingAttemptNumberPort",
        "ForecastingFailureSelectionPort",
        RESOLUTION,
        PREPARATION,
        DECISION,
        HANDLING,
        RUNTIME,
    }
)

ALLOWED_ANNOTATIONS = {
    "selector": "ForecastingFailureSelectionPort",
    "attempt_number_source": "ForecastingAttemptNumberPort",
    "policy": "FailurePolicyPort",
}

CONSTRUCTED_SERVICES = (RESOLUTION, PREPARATION, DECISION, HANDLING, RUNTIME)

CONCRETE_POLICY_NAMES = frozenset(
    {
        "StrictSingleForecastingFailureSelector",
        "InitialForecastingAttemptNumberSource",
        "InitialForecastingFailurePolicy",
        "StrictSingleParallelIngestionFailureSelector",
        "InitialParallelIngestionAttemptNumberSource",
        "InitialParallelIngestionFailurePolicy",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "select",
        "get_attempt_number",
        "resolve",
        "prepare",
        "decide",
        "handle",
        "execute",
        "run",
        "forecast",
        "FailureAction",
        "FailurePolicyContext",
        "RETRY",
        "FALLBACK",
        "FAIL",
        "WorkflowState",
        "WorkflowPhase",
        "ForecastingFailureFact",
        "ForecastingAgentFailure",
        "execute_forecasting_failure_action",
        "fail_after_forecasting",
        "extract_forecasting_agent_failures",
        "classify_forecasting_agent_failures",
        "build_forecasting_failure_policy_context",
        "ForecastingWorkflowStep",
        "ParallelForecastingExecutionService",
        "build_parallel_forecasting_execution_service",
        "build_forecasting_workflow_step",
        "build_forecasting_workflow_step_from_model_ports",
        "create_app",
        "build_workflow_graph",
        "StateGraph",
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
        "registry",
        "Registry",
        "factory",
        "Factory",
        "container",
        "Container",
        "locator",
        "get_service",
        "selected",
        "default",
        "champion",
        "best",
        "preferred",
        "winner",
        "priority",
        "rank",
        "severity",
        "retry",
        "fallback",
        "logger",
        "getLogger",
        "cache",
        "lru_cache",
        "create_task",
        "gather",
        "TaskGroup",
        "import_module",
        "__import__",
        "getattr",
        "setattr",
        "TYPE_CHECKING",
        "cast",
        *CONCRETE_POLICY_NAMES,
    }
)

FORBIDDEN_CODE_FRAGMENTS = (
    "energy_trading.ml",
    "infrastructure",
    "strict_single",
    "initial_",
    "lightgbm",
    "xgboost",
    "prophet",
    "langgraph",
    "langchain",
    "fastapi",
    "starlette",
    "openai",
    "anthropic",
    "qdrant",
    "redis",
    "sqlalchemy",
    "n8n",
    "importlib",
    "__import__",
    "type_checking",
    "os.environ",
    "getenv",
    "app.state",
    ".select(",
    ".get_attempt_number(",
    ".resolve(",
    ".prepare(",
    ".decide(",
    ".handle(",
    ".execute(",
    ".forecast(",
    ".run(",
    "await ",
    "async ",
    "try:",
    "except ",
    "raise ",
    "global ",
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _strip_docstrings(tree: ast.Module) -> ast.Module:
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return tree


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


def _positional_names(call: ast.Call) -> list[str]:
    assert call.keywords == []
    names: list[str] = []
    for arg in call.args:
        assert isinstance(arg, ast.Name)
        names.append(arg.id)
    return names


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.exists()
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert COMPOSITION_ROOT.parent == API_ROOT
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).with_suffix("").as_posix()
    assert relative.replace("/", ".") == BUILDER_MODULE_NAME


def test_builder_imports_only_policy_ports_and_published_failure_services() -> None:
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
    relative_imports = [
        node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.level != 0
    ]
    assert relative_imports == []
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
    assert definitions == ["energy_trading/api/composition/forecasting_failure_runtime.py"]


def test_builder_signature_has_three_required_keyword_only_ports() -> None:
    builder = _builder_function()
    assert builder.decorator_list == []
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == tuple(ALLOWED_ANNOTATIONS)
    assert builder.args.kw_defaults == [None, None, None]
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == ALLOWED_ANNOTATIONS
    assert builder.returns is not None
    assert ast.unparse(builder.returns) == RUNTIME


def test_builder_constructs_the_five_services_once_with_exact_forwarding() -> None:
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
                ast.Global,
                ast.Nonlocal,
            ),
        )
    ]
    assert control == []
    calls = [node for node in ast.walk(builder) if isinstance(node, ast.Call)]
    assert sorted(_call_name(node) or "" for node in calls) == sorted(CONSTRUCTED_SERVICES)
    assert all(isinstance(node.func, ast.Name) for node in calls)

    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 5
    *assignments, returned = statements
    bound: dict[str, str] = {}
    for assignment in assignments:
        assert isinstance(assignment, ast.Assign)
        assert len(assignment.targets) == 1
        assert isinstance(assignment.targets[0], ast.Name)
        assert isinstance(assignment.value, ast.Call)
        class_name = _call_name(assignment.value)
        assert class_name is not None
        bound[class_name] = assignment.targets[0].id
    assert [
        _call_name(a.value)
        for a in assignments
        if isinstance(a, ast.Assign) and isinstance(a.value, ast.Call)
    ] == [
        RESOLUTION,
        PREPARATION,
        DECISION,
        HANDLING,
    ]
    assert len(set(bound.values())) == 4
    assert set(bound.values()).isdisjoint(ALLOWED_ANNOTATIONS)

    arguments = {
        _call_name(a.value): _positional_names(a.value)
        for a in assignments
        if isinstance(a, ast.Assign) and isinstance(a.value, ast.Call)
    }
    assert arguments[RESOLUTION] == ["selector", "attempt_number_source"]
    assert arguments[PREPARATION] == [bound[RESOLUTION]]
    assert arguments[DECISION] == ["policy"]
    assert arguments[HANDLING] == [bound[DECISION]]

    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Call)
    assert _call_name(returned.value) == RUNTIME
    assert _positional_names(returned.value) == [bound[PREPARATION], bound[HANDLING]]


def test_builder_constructs_no_concrete_selector_attempt_source_or_policy() -> None:
    for node in ast.walk(_parse(BUILDER_MODULE)):
        if isinstance(node, ast.Call):
            assert _call_name(node) not in CONCRETE_POLICY_NAMES
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    for name in CONCRETE_POLICY_NAMES:
        assert name not in source, name


def test_builder_owns_no_execution_selection_or_runtime_policy() -> None:
    identifiers = _identifier_names(BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    assert annotation_type_names(BUILDER_MODULE) <= {
        "ForecastingFailureSelectionPort",
        "ForecastingAttemptNumberPort",
        "FailurePolicyPort",
        RUNTIME,
    }
    code_only = ast.unparse(_strip_docstrings(_parse(BUILDER_MODULE))).lower()
    for fragment in FORBIDDEN_CODE_FRAGMENTS:
        assert fragment not in code_only, fragment


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
    assert not call_names & set(CONSTRUCTED_SERVICES)
    assert "forecasting_failure_runtime" not in app_source.lower()


def test_other_api_modules_do_not_import_the_builder() -> None:
    for path in sorted(API_ROOT.rglob("*.py")):
        if path == BUILDER_MODULE:
            continue
        assert BUILDER_NAME not in imported_names(path)
        assert BUILDER_MODULE_NAME not in imported_modules(path)
        assert BUILDER_NAME not in path.read_text(encoding="utf-8")
    assert "forecasting_failure_runtime" not in COMPOSITION_INIT.read_text(encoding="utf-8")


def test_graph_remains_unwired_and_consumes_an_already_composed_failure_handler() -> None:
    names = imported_names(GRAPH_MODULE)
    modules = imported_modules(GRAPH_MODULE)
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert BUILDER_NAME not in names
    assert BUILDER_MODULE_NAME not in modules
    assert not any(module.startswith("energy_trading.api") for module in modules)
    assert BUILDER_NAME not in source
    assert RUNTIME in names
    tree = _parse(GRAPH_MODULE)
    build_graph = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_workflow_graph"
    )
    kwonly = {arg.arg: arg for arg in build_graph.args.kwonlyargs}
    handler_arg = kwonly["forecasting_failure_runtime_handler"]
    assert handler_arg.annotation is not None
    assert ast.unparse(handler_arg.annotation) == RUNTIME
    defaults = dict(zip(build_graph.args.kwonlyargs, build_graph.args.kw_defaults, strict=True))
    assert defaults[handler_arg] is None
    constructions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _call_name(node) in set(CONSTRUCTED_SERVICES)
    ]
    assert constructions == []
    for name in CONCRETE_POLICY_NAMES:
        assert name not in source, name
