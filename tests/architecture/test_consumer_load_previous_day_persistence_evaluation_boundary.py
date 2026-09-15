"""Previous-day persistence MAE evaluation stays a narrow ML metric."""

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
ML_ROOT = PRODUCTION_ROOT / "ml"
CONSUMER_LOAD_ML_ROOT = ML_ROOT / "consumer_load"
EVALUATION_MODULE = CONSUMER_LOAD_ML_ROOT / "previous_day_persistence_evaluation.py"
AGENTS_ROOT = PRODUCTION_ROOT / "application" / "agents"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration",
    "energy_trading.application.ports",
    "energy_trading.ml.common",
    "energy_trading.ml.dam",
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
    "openpyxl",
    "numpy",
    "sklearn",
    "lightgbm",
    "xgboost",
    "prophet",
    "torch",
    "tensorflow",
    "joblib",
    "onnx",
    "onnxruntime",
    "mlflow",
    "optuna",
    "n8n",
    "uuid",
    "random",
    "secrets",
    "pathlib",
    "socket",
    "os",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "Dict",
        "Mapping",
        "MutableMapping",
        "TypedDict",
        "DataFrame",
        "ndarray",
        "NDArray",
        "Booster",
        "LGBMRegressor",
        "XGBRegressor",
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "Backtester",
        "Evaluator",
        "Metric",
        "AgentFactory",
        "ServiceLocator",
        "ClockPort",
        "UuidFactory",
        "ForecastingExecutionPort",
        "ForecastingWorkflowStep",
        "ConsumerLoadForecastAgent",
        "ConsumerLoadForecastModelPort",
        "LoadForecastPoint",
        "WorkflowState",
        "MAE",
        "MSE",
        "RMSE",
        "MAPE",
        "ConsumptionRecord",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "ModelPort",
        "ForecastPort",
        "ForecastModelPort",
        "MLPort",
        "Backtester",
        "Evaluator",
        "MetricRegistry",
        "ModelRegistry",
        "AgentFactory",
        "ServiceLocator",
        "ClockPort",
        "UuidFactory",
        "uuid4",
        "datetime.now",
        "ForecastingExecutionPort",
        "ConsumerLoadForecastAgent",
        "ConsumerLoadForecastModelPort",
        "PreviousDayPersistenceConsumerLoadForecastModel",
        "build_previous_day_persistence_backtest_cases",
        "LoadForecastPoint",
        "ConsumptionRecord",
        "build_workflow_graph",
        "create_app",
        "mean_absolute_error",
        "mean_squared_error",
        "root_mean_squared_error",
        "mean_absolute_percentage_error",
        "mse",
        "rmse",
        "mape",
        "residual",
        "residuals",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.errors",
        "energy_trading.domain.value_objects.quantities",
        "energy_trading.ml.consumer_load.previous_day_persistence_backtest",
    }
)

ALLOWED_RESULT_FIELDS = (
    "case_count",
    "mae_mw",
)

ALLOWED_RESULT_ANNOTATIONS = {
    "case_count": "int",
    "mae_mw": "NonNegativeMW",
}

GENERIC_ML_CLASS_NAMES = frozenset(
    {
        "ModelPort",
        "ForecastModelPort",
        "MLPort",
        "ForecastPort",
        "Predictor",
        "PredictorPort",
        "InferencePort",
        "GenericModelPort",
        "TimeSeriesModelPort",
        "Backtester",
        "Evaluator",
        "Metric",
        "ModelRegistry",
    }
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


def _class_def(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
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


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _module_function_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _identifier_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
    return names


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


def _annassign_field_annotations(path: Path, class_name: str) -> dict[str, str]:
    class_def = _class_def(path, class_name)
    annotations: dict[str, str] = {}
    for item in class_def.body:
        if (
            isinstance(item, ast.AnnAssign)
            and isinstance(item.target, ast.Name)
            and item.annotation is not None
        ):
            annotations[item.target.id] = ast.unparse(item.annotation)
    return annotations


def _dataclass_keywords(class_def: ast.ClassDef) -> dict[str, object]:
    for decorator in class_def.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        if call is None:
            continue
        func = call.func
        name = func.id if isinstance(func, ast.Name) else None
        if name != "dataclass":
            continue
        return {
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in call.keywords
            if keyword.arg is not None
        }
    msg = f"dataclass decorator not found on {class_def.name}"
    raise AssertionError(msg)


def test_evaluation_module_lives_under_ml_consumer_load() -> None:
    assert EVALUATION_MODULE.is_relative_to(CONSUMER_LOAD_ML_ROOT)
    assert EVALUATION_MODULE.name == "previous_day_persistence_evaluation.py"
    assert _module_class_names(EVALUATION_MODULE) == ["PreviousDayPersistenceMAEResult"]
    assert _module_function_names(EVALUATION_MODULE) == ["evaluate_previous_day_persistence_mae"]
    common_root = ML_ROOT / "common"
    common_python = sorted(common_root.rglob("*.py")) if common_root.exists() else []
    assert common_python == []


def test_result_is_frozen_slotted_with_exactly_two_fields() -> None:
    class_def = _class_def(EVALUATION_MODULE, "PreviousDayPersistenceMAEResult")
    assert _base_names(class_def) == set()
    assert list(class_def.type_params) == []
    assert _dataclass_keywords(class_def) == {"frozen": True, "slots": True}
    assert _annassign_field_names(EVALUATION_MODULE, "PreviousDayPersistenceMAEResult") == (
        ALLOWED_RESULT_FIELDS
    )
    annotations = _annassign_field_annotations(
        EVALUATION_MODULE,
        "PreviousDayPersistenceMAEResult",
    )
    assert annotations == ALLOWED_RESULT_ANNOTATIONS
    leaked_types = sorted(name for name in annotations.values() if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_evaluator_is_keyword_only_sync_over_backtest_cases() -> None:
    tree = ast.parse(
        EVALUATION_MODULE.read_text(encoding="utf-8"),
        filename=str(EVALUATION_MODULE),
    )
    evaluator = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "evaluate_previous_day_persistence_mae"
    )
    assert not isinstance(evaluator, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in evaluator.args.args) == ()
    assert tuple(arg.arg for arg in evaluator.args.kwonlyargs) == ("cases",)
    assert evaluator.args.vararg is None
    assert evaluator.args.kwarg is None
    cases_arg = evaluator.args.kwonlyargs[0]
    assert cases_arg.annotation is not None
    assert evaluator.returns is not None
    assert ast.unparse(cases_arg.annotation) == "tuple[PreviousDayPersistenceBacktestCase, ...]"
    assert ast.unparse(evaluator.returns) == "PreviousDayPersistenceMAEResult"


def test_evaluation_depends_only_on_allowed_inward_contracts() -> None:
    leaked = sorted(
        module
        for module in imported_modules(EVALUATION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(EVALUATION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(EVALUATION_MODULE)
    assert "PreviousDayPersistenceBacktestCase" in names
    assert "InvalidRequestError" in names
    assert "NonNegativeMW" in names
    assert "LoadForecastPoint" not in names
    assert "ConsumptionRecord" not in names
    assert "ConsumerLoadForecastModelPort" not in names
    assert "ConsumerLoadForecastModelRequest" not in names
    assert "PreviousDayPersistenceConsumerLoadForecastModel" not in names
    assert "build_previous_day_persistence_backtest_cases" not in names
    leaked_types = sorted(
        name for name in annotation_type_names(EVALUATION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_types == []


def test_evaluation_does_not_generate_identity_or_use_io() -> None:
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert "datetime.now" not in source
    assert "uuid4" not in source
    assert "open(" not in source
    identifiers = _identifier_names(EVALUATION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    modules = imported_modules(EVALUATION_MODULE)
    assert "uuid" not in modules
    assert "random" not in modules
    assert "pathlib" not in modules
    assert "datetime" not in modules
    assert "socket" not in modules
    assert "os" not in modules


def test_evaluation_does_not_introduce_generic_ml_or_other_metrics() -> None:
    class_names = [name for path in ML_ROOT.rglob("*.py") for name in _module_class_names(path)]
    leaked_classes = sorted(name for name in class_names if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_classes == []
    identifiers = _identifier_names(EVALUATION_MODULE)
    leaked_ids = sorted(name for name in identifiers if name in GENERIC_ML_CLASS_NAMES)
    assert leaked_ids == []
    source = EVALUATION_MODULE.read_text(encoding="utf-8").lower()
    assert "registry" not in source
    assert "lightgbm" not in source
    assert "xgboost" not in source
    assert "sklearn" not in source
    assert "numpy" not in source
    assert "pandas" not in source
    assert "rmse" not in source
    assert "mape" not in source
    assert "residual" not in source
    assert "mean_squared" not in source
    assert "ml/common" not in source
    assert "energy_trading.ml.common" not in source


def test_application_agents_do_not_import_the_mae_evaluator() -> None:
    assert collect_import_violations(AGENTS_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(AGENTS_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "PreviousDayPersistenceMAEResult" not in names
        assert "evaluate_previous_day_persistence_mae" not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_evaluation" not in source


def test_orchestration_and_langgraph_do_not_import_the_mae_evaluator() -> None:
    assert collect_import_violations(ORCHESTRATION_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "PreviousDayPersistenceMAEResult" not in names
        assert "evaluate_previous_day_persistence_mae" not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_evaluation" not in source
    graph_modules = imported_modules(GRAPH_MODULE)
    assert not any(
        module == "energy_trading.ml" or module.startswith("energy_trading.ml.")
        for module in graph_modules
    )
    graph_names = imported_names(GRAPH_MODULE)
    assert "evaluate_previous_day_persistence_mae" not in graph_names
    assert "PreviousDayPersistenceMAEResult" not in graph_names


def test_api_composition_does_not_import_or_construct_the_mae_evaluator() -> None:
    assert collect_import_violations(API_ROOT, ("energy_trading.ml",)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "PreviousDayPersistenceMAEResult" not in names
        assert "evaluate_previous_day_persistence_mae" not in names
        source = path.read_text(encoding="utf-8")
        assert "previous_day_persistence_evaluation" not in source
    app_source = API_APP.read_text(encoding="utf-8")
    assert "PreviousDayPersistenceMAEResult" not in app_source
    assert "evaluate_previous_day_persistence_mae" not in app_source


def test_workflow_state_shape_is_unchanged() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "PreviousDayPersistenceMAEResult" not in names
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "previous_day_persistence_evaluation" not in source
    assert "mae_mw" not in source


def test_no_dam_imports_in_consumer_load_evaluation() -> None:
    names = imported_names(EVALUATION_MODULE)
    source = EVALUATION_MODULE.read_text(encoding="utf-8")
    assert "DAMPriceForecastModelPort" not in names
    assert "DAMPriceForecastAgent" not in names
    assert "MarketPriceRecord" not in names
    assert "PriceForecastPoint" not in names
    assert "dam_price" not in source.lower()
    assert "energy_trading.ml.dam" not in imported_modules(EVALUATION_MODULE)
