"""Chunk 116 Regulatory workflow-node adapter stays application-owned and unwired."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    async_function_arg_names,
    collect_http_api_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
NODE_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_workflow_node.py"
CONTEXT_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_context.py"
STEP_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_workflow_step.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"

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
        "Optional",
        "FailurePolicyPort",
        "FailurePolicyContext",
        "FailureAction",
        "StateGraph",
        "CompiledStateGraph",
        "Send",
        "RetryPolicy",
        "AgentPort",
        "AgentRegistry",
        "AgentFactory",
        "WorkflowContextPort",
        "WorkflowNodePort",
        "WorkflowStepPort",
        "ParallelIngestionWorkflowContextPort",
        "RegulatoryIntelligenceQueryExecutionService",
        "RegulatoryIntelligenceAgent",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
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
        "tenacity",
        "backoff",
        "sleep",
        "wait",
        "retry",
        "fallback",
        "Timeout",
        "asyncio",
        "TaskGroup",
        "replace",
        "WorkflowContextPort",
        "WorkflowNodePort",
        "WorkflowStepPort",
        "AgentRegistry",
        "AgentFactory",
        "ServiceLocator",
        "create_app",
        "build_workflow_graph",
    }
)

GENERIC_FRAMEWORK_CLASS_NAMES = frozenset(
    {
        "WorkflowContextPort",
        "WorkflowNodePort",
        "WorkflowStepPort",
        "AgentRegistry",
        "AgentFactory",
        "AgentExecutor",
        "ServiceLocator",
        "GenericUseCase",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.orchestration.regulatory_intelligence_context",
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_step",
        "energy_trading.application.orchestration.state",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "context": "RegulatoryIntelligenceWorkflowContextPort",
    "workflow_step": "RegulatoryIntelligenceWorkflowStep",
}

WORKFLOW_STATE_FIELDS = (
    "workflow_id",
    "portfolio_id",
    "delivery_date",
    "correlation_id",
    "phase",
    "status",
    "diagnostics",
)

UNWIRED_GRAPH_AND_RUNTIME = (
    GRAPH_MODULE,
    API_APP,
    API_ROOT / "composition" / "production_lifespan.py",
    API_ROOT / "composition" / "regulatory_intelligence_lifespan.py",
    API_ROOT / "composition" / "regulatory_intelligence_loaded_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_managed_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_configured_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_runtime.py",
    API_ROOT / "routers" / "regulatory_intelligence.py",
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


def _annassign_field_names(path: Path, class_name: str) -> tuple[str, ...]:
    class_def = _class_def(path, class_name)
    names: list[str] = []
    for item in class_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.append(item.target.id)
    return tuple(names)


def _init_arg_annotations(class_def: ast.ClassDef) -> dict[str, str]:
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    annotations: dict[str, str] = {}
    for arg in (*init_fn.args.args, *init_fn.args.kwonlyargs):
        if arg.arg == "self" or arg.annotation is None:
            continue
        annotations[arg.arg] = ast.unparse(arg.annotation)
    return annotations


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


def _run_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run":
            return node
    msg = "async method 'run' not found on RegulatoryIntelligenceWorkflowNodeAdapter"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _awaited_call(statement: ast.stmt) -> ast.Call | None:
    value: ast.expr | None = None
    if isinstance(statement, ast.Assign):
        value = statement.value
    elif isinstance(statement, ast.Expr):
        value = statement.value
    if isinstance(value, ast.Await) and isinstance(value.value, ast.Call):
        return value.value
    return None


def test_node_adapter_module_belongs_to_application_orchestration() -> None:
    assert NODE_MODULE.parent == ORCHESTRATION_ROOT
    assert NODE_MODULE.exists()


def test_node_adapter_does_not_import_outer_layers_or_vendors() -> None:
    leaked = sorted(
        module
        for module in imported_modules(NODE_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(NODE_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(NODE_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(NODE_MODULE)
    assert "RegulatoryIntelligenceWorkflowContextPort" in names
    assert "RegulatoryIntelligenceWorkflowStep" in names
    assert "WorkflowState" in names
    assert "langgraph" not in names
    assert "WorkflowContextPort" not in names
    assert "WorkflowNodePort" not in names
    assert "WorkflowStepPort" not in names
    assert "ParallelIngestionWorkflowContextPort" not in names
    assert "RegulatoryIntelligenceQueryExecutionService" not in names


def test_node_module_exposes_exactly_one_concrete_class() -> None:
    assert _module_class_names(NODE_MODULE) == ["RegulatoryIntelligenceWorkflowNodeAdapter"]
    class_def = _class_def(NODE_MODULE, "RegulatoryIntelligenceWorkflowNodeAdapter")
    assert _base_names(class_def) == set()
    assert list(class_def.type_params) == []
    leaked_implementations = sorted(
        name for name in _module_class_names(NODE_MODULE) if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_implementations == []
    production_adapters: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == (
                "RegulatoryIntelligenceWorkflowNodeAdapter"
            ):
                production_adapters.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_adapters == [
        "energy_trading/application/orchestration/regulatory_intelligence_workflow_node.py"
    ]


def test_constructor_injects_exactly_the_published_context_and_step() -> None:
    class_def = _class_def(NODE_MODULE, "RegulatoryIntelligenceWorkflowNodeAdapter")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "context",
        "workflow_step",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "RegulatoryIntelligenceWorkflowContextPort" not in constructed
    assert "RegulatoryIntelligenceWorkflowStep" not in constructed
    assert "WorkflowState" not in constructed


def test_public_operation_is_async_run_over_workflow_state() -> None:
    class_def = _class_def(NODE_MODULE, "RegulatoryIntelligenceWorkflowNodeAdapter")
    defined = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == ["__init__", "run"]
    run_fn = _run_method(class_def)
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "state")
    assert run_fn.args.vararg is None
    assert run_fn.args.kwarg is None
    assert run_fn.args.kwonlyargs == []
    assert async_function_arg_names(NODE_MODULE, "run") == ("self", "state")
    assert run_fn.args.args[1].annotation is not None
    assert run_fn.returns is not None
    assert ast.unparse(run_fn.args.args[1].annotation) == "WorkflowState"
    assert ast.unparse(run_fn.returns) == "WorkflowState"


def test_run_coordinates_resolve_step_and_record_without_reconstruction() -> None:
    class_def = _class_def(NODE_MODULE, "RegulatoryIntelligenceWorkflowNodeAdapter")
    run_fn = _run_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(run_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(run_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    awaited: list[tuple[str | None, dict[str, str], list[str]]] = []
    for statement in run_fn.body:
        call = _awaited_call(statement)
        if call is None:
            continue
        keywords = {
            keyword.arg: ast.unparse(keyword.value)
            for keyword in call.keywords
            if keyword.arg is not None
        }
        args = [ast.unparse(arg) for arg in call.args]
        awaited.append((_call_name(call), keywords, args))
    assert awaited == [
        ("resolve_request", {"state": "state"}, []),
        ("run", {}, ["request"]),
        ("record_result", {"state": "state", "result": "result"}, []),
    ]
    returns = [node for node in ast.walk(run_fn) if isinstance(node, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[-1].value, ast.Name)
    assert returns[-1].value.id == "state"
    constructed: list[str] = []
    for node in ast.walk(run_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in {
            "WorkflowState",
            "replace",
            "RegulatoryIntelligenceWorkflowRequest",
            "RegulatoryIntelligenceResult",
        }:
            constructed.append(name or "")
    assert constructed == []
    source = NODE_MODULE.read_text(encoding="utf-8")
    assert "try:" not in source
    assert "except " not in source


def test_node_adapter_public_contract_excludes_payload_and_runtime_types() -> None:
    names = annotation_type_names(NODE_MODULE)
    leaked = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked == []
    identifiers = _identifier_names(NODE_MODULE)
    leaked_identifiers = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked_identifiers == []
    source = NODE_MODULE.read_text(encoding="utf-8").lower()
    assert "langgraph" not in source
    assert "langchain" not in source
    assert "fastapi" not in source
    assert "openai" not in source
    assert "qdrant" not in source
    assert "redis" not in source
    assert "sqlalchemy" not in source
    assert "factory" not in source
    assert "registry" not in source
    assert "service locator" not in source


def test_workflow_state_shape_is_unchanged_and_does_not_import_the_adapter() -> None:
    fields = _annassign_field_names(STATE_MODULE, "WorkflowState")
    assert fields == WORKFLOW_STATE_FIELDS
    names = imported_names(STATE_MODULE)
    assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in names
    assert "RegulatoryIntelligenceWorkflowContextPort" not in names
    assert "RegulatoryIntelligenceWorkflowStep" not in names
    modules = imported_modules(STATE_MODULE)
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_node"
        not in modules
    )
    source = STATE_MODULE.read_text(encoding="utf-8")
    assert "regulatory_request" not in source
    assert "regulatory_result" not in source
    assert "regulatory_intelligence_request" not in source
    assert "regulatory_intelligence_result" not in source


def test_graph_remains_unwired_from_regulatory_node_adapter() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in names
    assert "RegulatoryIntelligenceWorkflowContextPort" not in names
    assert "RegulatoryIntelligenceWorkflowStep" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_node"
        not in modules
    )
    assert "energy_trading.application.orchestration.regulatory_intelligence_context" not in modules
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_step"
        not in modules
    )
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in source
    assert "regulatory_intelligence_workflow_node" not in source
    assert "RegulatoryIntelligenceWorkflowContextPort" not in source
    assert "regulatory_intelligence_context" not in source
    assert "RegulatoryIntelligenceWorkflowStep" not in source
    assert "regulatory_intelligence_workflow_step" not in source
    tree = ast.parse(source, filename=str(GRAPH_MODULE))
    string_constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "workflow_entry" in string_constants
    assert "parallel_ingestion" in string_constants
    assert "regulatory_intelligence" not in string_constants
    add_node_count = 0
    add_edge_count = 0
    add_conditional_edges_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "add_node":
            add_node_count += 1
        elif name == "add_edge":
            add_edge_count += 1
        elif name == "add_conditional_edges":
            add_conditional_edges_count += 1
    assert add_node_count == 3
    assert add_edge_count == 3
    assert add_conditional_edges_count == 1


def test_context_and_step_modules_do_not_import_the_node_adapter() -> None:
    for path in (CONTEXT_MODULE, STEP_MODULE):
        names = imported_names(path)
        assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.regulatory_intelligence_workflow_node"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in source
        assert "regulatory_intelligence_workflow_node" not in source


def test_api_runtime_and_http_remain_unaware_of_the_node_adapter() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_node",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in (*UNWIRED_GRAPH_AND_RUNTIME, *http_transport_api_paths(API_ROOT)):
        names = imported_names(path)
        assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.regulatory_intelligence_workflow_node"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "RegulatoryIntelligenceWorkflowNodeAdapter" not in source
        assert "regulatory_intelligence_workflow_node" not in source
    app_source = API_APP.read_text(encoding="utf-8").lower()
    assert "regulatoryintelligenceworkflownodeadapter" not in app_source
