"""Chunk 115 Regulatory workflow-context Protocol stays typed and unwired."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_context.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
STEP_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_workflow_step.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.api",
    "energy_trading.shared.config",
    "energy_trading.application.orchestration.graph",
    "fastapi",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "openai",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "sentence_transformers",
    "transformers",
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
        "Exception",
        "BaseException",
        "ApplicationError",
        "Optional",
        "Session",
        "AsyncSession",
        "Engine",
        "Connection",
        "Redis",
        "RedisClient",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "AgentPort",
        "AgentFactory",
        "AgentRegistry",
        "RegulatoryIntelligenceWorkflowStep",
        "RegulatoryIntelligenceQueryExecutionService",
        "RegulatoryIntelligenceAgent",
        "ParallelIngestionWorkflowContextPort",
        "WorkflowContextPort",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Mapping",
        "MutableMapping",
        "TypedDict",
        "Callable",
        "Exception",
        "Optional",
        "redis_get",
        "db_load",
        "insert",
        "commit",
        "save_row",
        "Session",
        "AsyncSession",
        "Redis",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "TaskGroup",
        "gather",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
        "WorkflowContextPort",
    }
)

APPLICATION_IMPLEMENTATION_NAMES = frozenset(
    {
        "InMemoryRegulatoryIntelligenceWorkflowContext",
        "RedisRegulatoryIntelligenceWorkflowContext",
        "PostgresRegulatoryIntelligenceWorkflowContext",
        "FilesystemRegulatoryIntelligenceWorkflowContext",
        "RegulatoryIntelligenceWorkflowContext",
        "WorkflowContextStore",
        "RegulatoryIntelligenceContextRepository",
        "LangGraphRegulatoryIntelligenceWorkflowContext",
        "WorkflowContextPort",
        "AgentFactory",
        "AgentRegistry",
        "ServiceLocator",
    }
)

DURABLE_IMPLEMENTATION_NAMES = frozenset(
    {
        "RedisRegulatoryIntelligenceWorkflowContext",
        "PostgresRegulatoryIntelligenceWorkflowContext",
        "FilesystemRegulatoryIntelligenceWorkflowContext",
        "WorkflowContextStore",
        "RegulatoryIntelligenceContextRepository",
        "LangGraphRegulatoryIntelligenceWorkflowContext",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "typing",
        "energy_trading.application.agents.regulatory_intelligence",
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_step",
        "energy_trading.application.orchestration.state",
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


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


def _base_names(class_def: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


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
            names.update(param.name for param in node.type_params)
    return names


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _async_method(class_def: ast.ClassDef, method_name: str) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name:
            return node
    msg = f"async method {method_name!r} not found on {class_def.name}"
    raise AssertionError(msg)


def test_context_module_belongs_to_application_orchestration() -> None:
    assert CONTEXT_MODULE.parent == ORCHESTRATION_ROOT
    assert CONTEXT_MODULE.exists()


def test_context_module_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(CONTEXT_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(CONTEXT_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(CONTEXT_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(CONTEXT_MODULE)
    assert "Protocol" in names
    assert "WorkflowState" in names
    assert "RegulatoryIntelligenceWorkflowRequest" in names
    assert "RegulatoryIntelligenceResult" in names
    assert "RegulatoryIntelligenceWorkflowStep" not in names
    assert "RegulatoryIntelligenceAgent" not in names
    assert "RegulatoryIntelligenceQueryExecutionService" not in names
    assert "ParallelIngestionWorkflowContextPort" not in names


def test_context_port_is_nongeneric_protocol_with_exact_async_operations() -> None:
    class_def = _class_def(CONTEXT_MODULE, "RegulatoryIntelligenceWorkflowContextPort")
    assert class_def.name == "RegulatoryIntelligenceWorkflowContextPort"
    bases = _base_names(class_def)
    assert "Protocol" in bases
    assert "ABC" not in bases
    assert "Generic" not in bases
    assert list(class_def.type_params) == []
    source = CONTEXT_MODULE.read_text(encoding="utf-8")
    assert "abstractmethod" not in source
    assert "runtime_checkable" not in source
    defined_nodes = [
        node for node in class_def.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert [node.name for node in defined_nodes] == ["resolve_request", "record_result"]
    assert all(isinstance(node, ast.AsyncFunctionDef) for node in defined_nodes)


def test_resolve_request_annotations_match_workflow_state_and_request() -> None:
    class_def = _class_def(CONTEXT_MODULE, "RegulatoryIntelligenceWorkflowContextPort")
    resolve_fn = _async_method(class_def, "resolve_request")
    assert tuple(arg.arg for arg in resolve_fn.args.args) == ("self",)
    assert resolve_fn.args.vararg is None
    assert resolve_fn.args.kwarg is None
    assert [arg.arg for arg in resolve_fn.args.kwonlyargs] == ["state"]
    assert resolve_fn.args.kw_defaults == [None]
    assert resolve_fn.args.kwonlyargs[0].annotation is not None
    assert resolve_fn.returns is not None
    assert ast.unparse(resolve_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(resolve_fn.returns) == "RegulatoryIntelligenceWorkflowRequest"


def test_record_result_annotations_match_workflow_state_and_result() -> None:
    class_def = _class_def(CONTEXT_MODULE, "RegulatoryIntelligenceWorkflowContextPort")
    record_fn = _async_method(class_def, "record_result")
    assert tuple(arg.arg for arg in record_fn.args.args) == ("self",)
    assert record_fn.args.vararg is None
    assert record_fn.args.kwarg is None
    assert [arg.arg for arg in record_fn.args.kwonlyargs] == ["state", "result"]
    assert record_fn.args.kw_defaults == [None, None]
    assert record_fn.args.kwonlyargs[0].annotation is not None
    assert record_fn.args.kwonlyargs[1].annotation is not None
    assert record_fn.returns is not None
    assert ast.unparse(record_fn.args.kwonlyargs[0].annotation) == "WorkflowState"
    assert ast.unparse(record_fn.args.kwonlyargs[1].annotation) == "RegulatoryIntelligenceResult"
    assert ast.unparse(record_fn.returns) == "None"


def test_context_public_contract_excludes_generic_storage_and_runtime_types() -> None:
    names = annotation_type_names(CONTEXT_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(CONTEXT_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    source = CONTEXT_MODULE.read_text(encoding="utf-8").lower()
    assert "langgraph" not in source
    assert "langchain" not in source
    assert "redis" not in source
    assert "sqlalchemy" not in source
    assert "psycopg" not in source
    assert "qdrant" not in source
    assert "openai" not in source
    assert "fastapi" not in source
    assert "factory" not in source
    assert "registry" not in source
    assert "service locator" not in source


def test_application_context_module_has_no_concrete_implementation() -> None:
    assert _module_class_names(CONTEXT_MODULE) == ["RegulatoryIntelligenceWorkflowContextPort"]
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in APPLICATION_IMPLEMENTATION_NAMES:
                application_implementations.append(
                    f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}"
                )
            bases = _base_names(node)
            if "RegulatoryIntelligenceWorkflowContextPort" in bases and node.name != (
                "RegulatoryIntelligenceWorkflowContextPort"
            ):
                application_implementations.append(
                    f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}"
                )
    assert application_implementations == []
    durable_implementations: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in DURABLE_IMPLEMENTATION_NAMES:
                durable_implementations.append(
                    f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}"
                )
    assert durable_implementations == []
    production_ports: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "RegulatoryIntelligenceWorkflowContextPort"
            ):
                production_ports.append(f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}")
    assert production_ports == [
        "energy_trading/application/orchestration/regulatory_intelligence_context.py:"
        "RegulatoryIntelligenceWorkflowContextPort"
    ]


def test_existing_request_and_result_are_reused_not_duplicated() -> None:
    context_names = imported_names(CONTEXT_MODULE)
    assert "RegulatoryIntelligenceWorkflowRequest" in context_names
    assert "RegulatoryIntelligenceResult" in context_names
    assert "RegulatoryIntelligenceWorkflowRequest" in _identifier_names(STEP_MODULE)
    production_requests: list[str] = []
    production_results: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name == "RegulatoryIntelligenceWorkflowRequest":
                production_requests.append(path.relative_to(SRC_ROOT).as_posix())
            if node.name == "RegulatoryIntelligenceResult":
                production_results.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_requests == [
        "energy_trading/application/orchestration/regulatory_intelligence_workflow_step.py"
    ]
    assert production_results == ["energy_trading/application/agents/regulatory_intelligence.py"]


def test_workflow_state_shape_is_unchanged_and_does_not_import_the_port() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "RegulatoryIntelligenceWorkflowContextPort" not in names
    assert "RegulatoryIntelligenceWorkflowRequest" not in names
    assert "RegulatoryIntelligenceResult" not in names
    modules = imported_modules(STATE_MODULE)
    assert "energy_trading.application.orchestration.regulatory_intelligence_context" not in modules
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_step"
        not in modules
    )
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "regulatory_request" not in source
    assert "regulatory_result" not in source
    assert "regulatory_intelligence_request" not in source
    assert "regulatory_intelligence_result" not in source


def test_graph_and_step_remain_unwired_to_the_context_port() -> None:
    for path in (GRAPH_MODULE, STEP_MODULE):
        names = imported_names(path)
        assert "RegulatoryIntelligenceWorkflowContextPort" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.regulatory_intelligence_context"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "RegulatoryIntelligenceWorkflowContextPort" not in source
        assert "regulatory_intelligence_context" not in source


def test_api_composition_does_not_import_or_construct_context_port() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.regulatory_intelligence_context",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "RegulatoryIntelligenceWorkflowContextPort" not in names
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "regulatoryintelligenceworkflowcontextport" not in app_source
    assert "regulatory_intelligence_context" not in app_source
