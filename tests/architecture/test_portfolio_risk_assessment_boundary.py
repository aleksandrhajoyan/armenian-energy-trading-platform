"""Portfolio & Risk assessment boundary stays typed, application-only, and unwired."""

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
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
PORTS_ROOT = APPLICATION_ROOT / "ports"
ORCHESTRATION_ROOT = APPLICATION_ROOT / "orchestration"
ASSESSMENT_MODULE = PORTS_ROOT / "portfolio_risk_assessment.py"
PORTS_INIT_MODULE = PORTS_ROOT / "__init__.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
READ_MODULE = ORCHESTRATION_ROOT / "forecasting_success_read.py"
API_ROOT = PRODUCTION_ROOT / "api"
APP_MODULE = API_ROOT / "app.py"
AGENT_MODULE = APPLICATION_ROOT / "agents" / "portfolio_risk.py"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "portfolio_risk_execution.py"
ASSESSMENT_MODULE_NAME = "energy_trading.application.ports.portfolio_risk_assessment"

PUBLIC_TYPES = ("PortfolioRiskAssessmentRequest", "PortfolioRiskAssessmentPort")

REQUEST_FIELDS = (
    ("workflow_id", "str"),
    ("portfolio_id", "EntityId"),
    ("delivery_date", "date"),
    ("forecasting_success", "ForecastingSuccess"),
    ("generation_availability", "tuple[GenerationAvailabilityRecord, ...]"),
    ("hydro_resources", "tuple[HydroRecord, ...]"),
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
        "HydroRecord",
        "RegulatoryConstraint",
        "RiskAssessment",
        "EntityId",
    }
)

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.application.agents",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.orchestration.state",
    "energy_trading.application.orchestration.forecasting_success_read",
    "energy_trading.application.orchestration.forecasting_context",
    "energy_trading.application.orchestration.forecasting_workflow",
    "energy_trading.application.orchestration.forecasting_executor",
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
        "LoadForecastPoint",
        "PriceForecastPoint",
        "MarketBid",
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
        "RiskAssessment_empty",
        "model_validate",
        "model_construct",
        "get_success",
        "record_success",
        "resolve_plan",
        "sorted",
        "sort",
        "sum",
        "min",
        "max",
        "Decimal",
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


def test_assessment_module_belongs_to_application_ports() -> None:
    assert ASSESSMENT_MODULE.parent == PORTS_ROOT
    assert ASSESSMENT_MODULE.exists()


def test_assessment_module_defines_only_the_two_public_contract_types() -> None:
    tree = _tree(ASSESSMENT_MODULE)
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
    class_def = _class_def(ASSESSMENT_MODULE, "PortfolioRiskAssessmentRequest")
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


def test_port_is_nongeneric_protocol_with_one_keyword_only_async_assess() -> None:
    class_def = _class_def(ASSESSMENT_MODULE, "PortfolioRiskAssessmentPort")
    assert _base_names(class_def) == {"Protocol"}
    assert list(class_def.type_params) == []
    assert class_def.decorator_list == []
    assert _public_methods(class_def) == ["assess"]
    methods = [
        node for node in class_def.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert len(methods) == 1
    assess_fn = methods[0]
    assert isinstance(assess_fn, ast.AsyncFunctionDef)
    assert tuple(arg.arg for arg in assess_fn.args.args) == ("self",)
    assert assess_fn.args.posonlyargs == []
    assert assess_fn.args.defaults == []
    assert assess_fn.args.vararg is None
    assert assess_fn.args.kwarg is None
    assert [arg.arg for arg in assess_fn.args.kwonlyargs] == ["request"]
    assert assess_fn.args.kw_defaults == [None]
    annotation = assess_fn.args.kwonlyargs[0].annotation
    assert annotation is not None
    assert ast.unparse(annotation) == "PortfolioRiskAssessmentRequest"
    assert assess_fn.returns is not None
    assert ast.unparse(assess_fn.returns) == "RiskAssessment"
    assert assess_fn.decorator_list == []
    source = ASSESSMENT_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "runtime_checkable" not in source


def test_assess_body_has_no_implementation_or_constructed_assessment() -> None:
    class_def = _class_def(ASSESSMENT_MODULE, "PortfolioRiskAssessmentPort")
    assess_fn = next(node for node in class_def.body if isinstance(node, ast.AsyncFunctionDef))
    body = list(assess_fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    assert len(body) == 1
    assert isinstance(body[0], ast.Expr)
    assert isinstance(body[0].value, ast.Constant)
    assert body[0].value.value is Ellipsis
    for node in ast.walk(_tree(ASSESSMENT_MODULE)):
        assert not isinstance(node, ast.Await | ast.Return)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "RiskAssessment"


def test_assessment_module_reuses_canonical_contracts_and_imports_nothing_else() -> None:
    modules = imported_modules(ASSESSMENT_MODULE)
    assert modules == ALLOWED_MODULE_IMPORTS
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_PREFIXES))
    assert leaked == []
    assert imported_names(ASSESSMENT_MODULE) - ALLOWED_MODULE_IMPORTS == ALLOWED_IMPORTED_NAMES
    source = ASSESSMENT_MODULE.read_text(encoding="utf-8")
    assert "TYPE_CHECKING" not in source
    assert "importlib" not in source
    assert "__import__" not in source


def test_assessment_contract_excludes_payload_escape_hatches_and_calculation() -> None:
    names = annotation_type_names(ASSESSMENT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(ASSESSMENT_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    code_only = " ".join(sorted(identifiers | imported_modules(ASSESSMENT_MODULE))).lower()
    for token in (
        "langgraph",
        "fastapi",
        "starlette",
        "redis",
        "sqlalchemy",
        "qdrant",
        "openai",
        "n8n",
        "registry",
        "factory",
        "repository",
        "cache",
        "retry",
        "fallback",
        "exposure",
        "convert",
    ):
        assert token not in code_only, token


def test_ports_package_does_not_export_the_assessment_contract() -> None:
    assert ASSESSMENT_MODULE_NAME not in imported_modules(PORTS_INIT_MODULE)
    source = PORTS_INIT_MODULE.read_text(encoding="utf-8")
    assert "PortfolioRiskAssessment" not in source


def test_read_port_and_workflow_state_remain_unaware_of_the_assessment_port() -> None:
    for path in (READ_MODULE, STATE_MODULE):
        assert ASSESSMENT_MODULE_NAME not in imported_modules(path)
        assert "PortfolioRiskAssessment" not in path.read_text(encoding="utf-8")


def test_graph_remains_unwired_to_the_assessment_port() -> None:
    assert ASSESSMENT_MODULE_NAME not in imported_modules(GRAPH_MODULE)
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "PortfolioRiskAssessment" not in source
    assert "portfolio_risk_assessment" not in source


def test_create_app_and_api_remain_unwired_to_the_assessment_port() -> None:
    assert ASSESSMENT_MODULE_NAME not in imported_modules(APP_MODULE)
    assert collect_import_violations(API_ROOT, (ASSESSMENT_MODULE_NAME,)) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "PortfolioRiskAssessment" not in source, path
        assert "portfolio_risk_assessment" not in source, path


def test_only_portfolio_risk_agent_may_import_assessment_port() -> None:
    # Chunk 198: the exact Portfolio & Risk Agent module is the sole authorized consumer.
    assert ASSESSMENT_MODULE_NAME in imported_modules(AGENT_MODULE)
    assert {"PortfolioRiskAssessmentPort", "PortfolioRiskAssessmentRequest"} <= imported_names(
        AGENT_MODULE
    )
    # Chunk 199: the exact execution-service module may import only the request DTO.
    assert ASSESSMENT_MODULE_NAME in imported_modules(EXECUTION_MODULE)
    assert "PortfolioRiskAssessmentRequest" in imported_names(EXECUTION_MODULE)
    assert "PortfolioRiskAssessmentPort" not in imported_names(EXECUTION_MODULE)
    assert "PortfolioRiskAssessmentPort" not in EXECUTION_MODULE.read_text(encoding="utf-8")
    assert {"assess", "RiskAssessment_empty", "value_at_risk", "risk_score"}.isdisjoint(
        _identifier_names(EXECUTION_MODULE)
    )
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path in (ASSESSMENT_MODULE, AGENT_MODULE, EXECUTION_MODULE):
            continue
        assert ASSESSMENT_MODULE_NAME not in imported_modules(path), path
        assert "PortfolioRiskAssessment" not in path.read_text(encoding="utf-8"), path
