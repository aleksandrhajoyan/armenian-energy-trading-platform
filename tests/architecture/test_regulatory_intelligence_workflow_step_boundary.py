"""Chunk 114 Regulatory workflow step stays application-owned and unwired."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    http_transport_api_paths,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
ORCHESTRATION_ROOT = PRODUCTION_ROOT / "application" / "orchestration"
STEP_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_workflow_step.py"
EXECUTION_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_query_execution.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
STATE_MODULE = ORCHESTRATION_ROOT / "state.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
AGENT_BASE = PRODUCTION_ROOT / "application" / "agents" / "base.py"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
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
        "ndarray",
        "NDArray",
        "DataFrame",
        "Path",
        "bytes",
        "bytearray",
        "Protocol",
        "ABC",
        "WorkflowState",
        "WorkflowPhase",
        "WorkflowStatus",
        "FailurePolicyPort",
        "CachePort",
        "AgentPort",
        "AgentRegistry",
        "AgentExecutor",
        "AgentFactory",
        "WorkflowStepPort",
        "RegulatoryAgentPort",
        "ExecutionPort",
        "QdrantClient",
        "Qdrant",
        "OpenAI",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
        "QdrantDocumentVectorConfig",
        "QdrantDocumentVectorDistanceSettings",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "dict",
        "Mapping",
        "create_app",
        "build_workflow_graph",
        "create_openai_client",
        "create_qdrant_client",
        "loaded_regulatory_intelligence_runtime",
        "managed_regulatory_intelligence_runtime",
        "build_regulatory_intelligence_configured_runtime",
        "build_regulatory_intelligence_provider_runtime",
        "build_regulatory_intelligence_query_execution",
        "verify_configured_regulatory_intelligence_collection_ready",
        "AgentRegistry",
        "AgentExecutor",
        "AgentFactory",
        "WorkflowStepPort",
        "RegulatoryAgentPort",
        "ExecutionPort",
        "retry",
        "fallback",
        "sleep",
        "tenacity",
        "backoff",
    }
)

GENERIC_FRAMEWORK_CLASS_NAMES = frozenset(
    {
        "AgentRegistry",
        "AgentExecutor",
        "AgentFactory",
        "WorkflowStepPort",
        "RegulatoryAgentPort",
        "ExecutionPort",
        "CollectionManager",
        "ServiceLocator",
        "GenericUseCase",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "dataclasses",
        "energy_trading.application.agents.base",
        "energy_trading.application.agents.regulatory_intelligence",
        "energy_trading.application.orchestration.regulatory_intelligence_query_execution",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "query_execution_service": "RegulatoryIntelligenceQueryExecutionService",
}

UNWIRED_GRAPH_AND_RUNTIME = (
    GRAPH_MODULE,
    STATE_MODULE,
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


def _public_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


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
    msg = "async method 'run' not found on RegulatoryIntelligenceWorkflowStep"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_workflow_step_module_belongs_to_application_orchestration() -> None:
    assert STEP_MODULE.parent == ORCHESTRATION_ROOT
    assert STEP_MODULE.exists()


def test_workflow_step_does_not_import_outer_layers_or_providers() -> None:
    leaked = sorted(
        module
        for module in imported_modules(STEP_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(STEP_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(STEP_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(STEP_MODULE)
    assert "AgentName" in names
    assert "RegulatoryIntelligenceResult" in names
    assert "RegulatoryIntelligenceQueryExecutionService" in names
    assert "AgentPort" not in names
    assert "WorkflowState" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names


def test_workflow_module_exposes_exactly_request_and_step() -> None:
    assert _public_function_defs(STEP_MODULE) == []
    assert _module_class_names(STEP_MODULE) == [
        "RegulatoryIntelligenceWorkflowRequest",
        "RegulatoryIntelligenceWorkflowStep",
    ]
    request_def = _class_def(STEP_MODULE, "RegulatoryIntelligenceWorkflowRequest")
    step_def = _class_def(STEP_MODULE, "RegulatoryIntelligenceWorkflowStep")
    assert _base_names(step_def) == set()
    assert "Protocol" not in _base_names(request_def)
    assert "Protocol" not in _base_names(step_def)
    leaked_implementations = sorted(
        name for name in _module_class_names(STEP_MODULE) if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_implementations == []
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name in {
                "RegulatoryIntelligenceWorkflowRequest",
                "RegulatoryIntelligenceWorkflowStep",
            }:
                production_classes.append(f"{path.relative_to(SRC_ROOT).as_posix()}:{node.name}")
    assert production_classes == [
        "energy_trading/application/orchestration/regulatory_intelligence_workflow_step.py:"
        "RegulatoryIntelligenceWorkflowRequest",
        "energy_trading/application/orchestration/regulatory_intelligence_workflow_step.py:"
        "RegulatoryIntelligenceWorkflowStep",
    ]


def test_request_fields_are_exactly_query_text_and_limit() -> None:
    request_def = _class_def(STEP_MODULE, "RegulatoryIntelligenceWorkflowRequest")
    fields: list[tuple[str, str]] = []
    for item in request_def.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            assert item.annotation is not None
            fields.append((item.target.id, ast.unparse(item.annotation)))
            assert item.value is None
    assert fields == [("query_text", "str"), ("limit", "int")]
    defined = [
        node.name
        for node in request_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert defined == []


def test_constructor_injects_exactly_the_query_execution_service() -> None:
    class_def = _class_def(STEP_MODULE, "RegulatoryIntelligenceWorkflowStep")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "query_execution_service",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "RegulatoryIntelligenceQueryExecutionService" not in constructed
    assert "OpenAI" not in constructed
    assert "QdrantClient" not in constructed


def test_public_operations_are_name_and_run() -> None:
    class_def = _class_def(STEP_MODULE, "RegulatoryIntelligenceWorkflowStep")
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    public_properties = [
        node.name
        for node in class_def.body
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(decorator, ast.Name) and decorator.id == "property"
            for decorator in node.decorator_list
        )
    ]
    assert public_methods == ["name", "run"]
    assert public_properties == ["name"]
    run_fn = _run_method(class_def)
    assert tuple(arg.arg for arg in run_fn.args.args) == ("self", "request")
    assert run_fn.args.posonlyargs == []
    assert run_fn.args.kwonlyargs == []
    assert ast.unparse(run_fn.args.args[1].annotation) == "RegulatoryIntelligenceWorkflowRequest"
    assert ast.unparse(run_fn.returns) == "RegulatoryIntelligenceResult"


def test_run_awaits_existing_execute_exactly_once() -> None:
    class_def = _class_def(STEP_MODULE, "RegulatoryIntelligenceWorkflowStep")
    run_fn = _run_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(run_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(run_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    execute_calls = 0
    for node in ast.walk(run_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "execute":
            execute_calls += 1
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {
                "query_text": "request.query_text",
                "limit": "request.limit",
            }
    assert execute_calls == 1
    statements = [node for node in run_fn.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 1
    returned = statements[0]
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Await)
    assert isinstance(returned.value.value, ast.Call)
    assert _call_name(returned.value.value) == "execute"
    identifiers = _identifier_names(STEP_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(STEP_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = STEP_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "qdrant" not in lowered
    assert "openai" not in lowered
    assert "fastapi" not in lowered
    assert "try:" not in source
    assert "except " not in source
    assert "factory" not in lowered
    assert "registry" not in lowered
    assert "service locator" not in lowered


def test_existing_agent_port_is_reused_and_not_replaced() -> None:
    assert AGENT_BASE.exists()
    assert "AgentPort" in _identifier_names(AGENT_BASE)
    step_names = imported_names(STEP_MODULE)
    assert "AgentPort" not in step_names
    assert "RegulatoryAgentPort" not in step_names
    assert "WorkflowStepPort" not in step_names
    assert "ExecutionPort" not in step_names
    protocols = [
        node.name
        for node in ast.parse(STEP_MODULE.read_text(encoding="utf-8")).body
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "Protocol")
            or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
            for base in node.bases
        )
    ]
    assert protocols == []


def test_existing_regulatory_result_is_reused_not_duplicated() -> None:
    execution_names = imported_names(EXECUTION_MODULE)
    assert "RegulatoryIntelligenceResult" in execution_names
    step_names = imported_names(STEP_MODULE)
    assert "RegulatoryIntelligenceResult" in step_names
    production_results: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name == "RegulatoryIntelligenceResult":
                production_results.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_results == ["energy_trading/application/agents/regulatory_intelligence.py"]


def test_graph_and_runtime_remain_unwired_to_the_workflow_step() -> None:
    for path in UNWIRED_GRAPH_AND_RUNTIME:
        names = imported_names(path)
        assert "RegulatoryIntelligenceWorkflowStep" not in names
        assert "RegulatoryIntelligenceWorkflowRequest" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.regulatory_intelligence_workflow_step"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "RegulatoryIntelligenceWorkflowStep" not in source
        assert "regulatory_intelligence_workflow_step" not in source
    graph_source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "RegulatoryIntelligenceQueryExecutionService" not in graph_source
    assert "regulatory_intelligence_query_execution" not in graph_source
    tree = ast.parse(graph_source, filename=str(GRAPH_MODULE))
    constructed: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in {
            "RegulatoryIntelligenceWorkflowStep",
            "RegulatoryIntelligenceQueryExecutionService",
        }:
            constructed.append(name)
    assert constructed == []
    string_constants = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "workflow_entry" in string_constants
    assert "parallel_ingestion" in string_constants
    assert "regulatory_intelligence" not in string_constants
    assert "contract" not in string_constants


def test_application_and_domain_do_not_import_api_or_infrastructure_for_this_step() -> None:
    leaked_step = sorted(
        module
        for module in imported_modules(STEP_MODULE)
        if is_forbidden(
            module,
            (
                "energy_trading.api",
                "energy_trading.infrastructure",
                "energy_trading.ml",
                "openai",
                "qdrant_client",
                "fastapi",
                "langgraph",
            ),
        )
    )
    assert leaked_step == []
    assert (
        collect_import_violations(
            DOMAIN_ROOT,
            ("energy_trading.api", "energy_trading.infrastructure"),
        )
        == []
    )
    assert collect_import_violations(APPLICATION_ROOT, ("energy_trading.api",)) == []
    assert collect_import_violations(APPLICATION_ROOT, ("energy_trading.infrastructure",)) == []


def test_http_transport_api_does_not_import_the_workflow_step() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration.regulatory_intelligence_workflow_step",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "RegulatoryIntelligenceWorkflowStep" not in names
        assert "RegulatoryIntelligenceWorkflowRequest" not in names


def test_no_production_langgraph_imports_outside_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
