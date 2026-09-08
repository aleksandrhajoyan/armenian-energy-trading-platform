"""Chunk 66 Regulatory Intelligence query execution stays application-owned."""

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
EXECUTION_MODULE = ORCHESTRATION_ROOT / "regulatory_intelligence_query_execution.py"
AGENT_MODULE = PRODUCTION_ROOT / "application" / "agents" / "regulatory_intelligence.py"
GRAPH_MODULE = ORCHESTRATION_ROOT / "graph.py"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.ml",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.ports.document_embedding",
    "energy_trading.application.ports.document_query_embedding",
    "energy_trading.application.ports.document_vector_index",
    "energy_trading.application.ports.document_vector_search",
    "energy_trading.application.ports.regulatory_constraint_inference",
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
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "DocumentEmbeddingPort",
        "DocumentChunkEmbedding",
        "DocumentQueryEmbedding",
        "DocumentQueryEmbeddingPort",
        "DocumentVectorSearchPort",
        "DocumentVectorIndexPort",
        "ExtractedDocumentChunk",
        "RegulatoryConstraintInferencePort",
        "QdrantClient",
        "Qdrant",
        "OpenAI",
        "Anthropic",
        "SentenceTransformer",
        "HttpUrl",
        "AnyUrl",
        "URL",
        "Request",
        "Response",
        "WorkflowState",
        "FailurePolicyPort",
        "CachePort",
        "AgentPort",
        "AgentRegistry",
        "AgentExecutor",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "dict",
        "Mapping",
        "ndarray",
        "embed_query",
        "search",
        "index",
        "upsert",
        "infer",
        "create_app",
        "build_workflow_graph",
        "DocumentQueryEmbeddingPort",
        "DocumentVectorSearchPort",
        "RegulatoryConstraintInferencePort",
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "AgentRegistry",
        "AgentExecutor",
        "RagPipeline",
        "provider",
        "model_name",
        "prompt",
        "collection_name",
        "score",
        "filter",
        "retry",
        "cache",
        "numpy",
        "asarray",
        "normalize",
        "clamp",
        "default_limit",
        "rewrite",
        "expand",
        "tokenize",
        "registry",
        "factory",
    }
)

GENERIC_FRAMEWORK_CLASS_NAMES = frozenset(
    {
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "GenericEmbeddingPort",
        "RagPipeline",
        "QueryPipeline",
        "GenericEmbeddingService",
        "AgentRegistry",
        "AgentExecutor",
        "GenericUseCase",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.regulatory_intelligence",
        "energy_trading.application.orchestration.document_vector_search_query_preparation",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "query_preparation_service": "DocumentVectorSearchQueryPreparationService",
    "regulatory_intelligence_agent": "RegulatoryIntelligenceAgent",
}

UNWIRED_MODULES = (
    GRAPH_MODULE,
    ORCHESTRATION_ROOT / "state.py",
    ORCHESTRATION_ROOT / "parallel_ingestion_workflow.py",
    ORCHESTRATION_ROOT / "parallel_ingestion_executor.py",
    ORCHESTRATION_ROOT / "parallel_ingestion_failure_runtime_handling.py",
    ORCHESTRATION_ROOT / "document_vector_search_query_preparation.py",
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


def _execute_method(class_def: ast.ClassDef) -> ast.AsyncFunctionDef:
    for node in class_def.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "execute":
            return node
    msg = "async method 'execute' not found on RegulatoryIntelligenceQueryExecutionService"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_execution_module_belongs_to_application_orchestration() -> None:
    assert EXECUTION_MODULE.parent == ORCHESTRATION_ROOT
    assert EXECUTION_MODULE.exists()


def test_execution_service_does_not_import_outer_layers_or_providers() -> None:
    leaked = sorted(
        module
        for module in imported_modules(EXECUTION_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(EXECUTION_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    leaked_names = sorted(
        name for name in imported_names(EXECUTION_MODULE) if name in FORBIDDEN_TYPE_NAMES
    )
    assert leaked_names == []
    names = imported_names(EXECUTION_MODULE)
    assert "DocumentVectorSearchQueryPreparationService" in names
    assert "RegulatoryIntelligenceAgent" in names
    assert "RegulatoryIntelligenceRequest" in names
    assert "RegulatoryIntelligenceResult" in names
    assert "DocumentQueryEmbeddingPort" not in names
    assert "DocumentVectorSearchPort" not in names
    assert "RegulatoryConstraintInferencePort" not in names


def test_execution_module_exposes_exactly_one_production_class() -> None:
    assert _public_function_defs(EXECUTION_MODULE) == []
    assert _module_class_names(EXECUTION_MODULE) == ["RegulatoryIntelligenceQueryExecutionService"]
    class_def = _class_def(EXECUTION_MODULE, "RegulatoryIntelligenceQueryExecutionService")
    assert _base_names(class_def) == set()
    production_classes: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.ClassDef)
                and node.name == "RegulatoryIntelligenceQueryExecutionService"
            ):
                production_classes.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_classes == [
        "energy_trading/application/orchestration/regulatory_intelligence_query_execution.py"
    ]
    leaked_implementations = sorted(
        name
        for name in _module_class_names(EXECUTION_MODULE)
        if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_implementations == []


def test_constructor_injects_exactly_preparation_service_and_agent() -> None:
    class_def = _class_def(EXECUTION_MODULE, "RegulatoryIntelligenceQueryExecutionService")
    init_fn = next(
        node
        for node in class_def.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert tuple(arg.arg for arg in init_fn.args.args) == (
        "self",
        "query_preparation_service",
        "regulatory_intelligence_agent",
    )
    assert init_fn.args.posonlyargs == []
    assert init_fn.args.kwonlyargs == []
    assert init_fn.args.vararg is None
    assert init_fn.args.kwarg is None
    assert _init_arg_annotations(class_def) == ALLOWED_INIT_ANNOTATIONS
    constructed = [_call_name(node) for node in ast.walk(init_fn) if isinstance(node, ast.Call)]
    assert "DocumentVectorSearchQueryPreparationService" not in constructed
    assert "RegulatoryIntelligenceAgent" not in constructed
    assert "OpenAI" not in constructed
    assert "QdrantClient" not in constructed


def test_execute_signature_is_async_keyword_only_query_text_and_limit() -> None:
    class_def = _class_def(EXECUTION_MODULE, "RegulatoryIntelligenceQueryExecutionService")
    execute_fn = _execute_method(class_def)
    assert tuple(arg.arg for arg in execute_fn.args.args) == ("self",)
    assert execute_fn.args.posonlyargs == []
    assert tuple(arg.arg for arg in execute_fn.args.kwonlyargs) == ("query_text", "limit")
    assert execute_fn.args.vararg is None
    assert execute_fn.args.kwarg is None
    assert ast.unparse(execute_fn.args.kwonlyargs[0].annotation) == "str"
    assert ast.unparse(execute_fn.args.kwonlyargs[1].annotation) == "int"
    assert ast.unparse(execute_fn.returns) == "RegulatoryIntelligenceResult"
    public_methods = [
        node.name
        for node in class_def.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]
    assert public_methods == ["execute"]


def test_execute_prepares_constructs_request_and_runs_without_direct_ports() -> None:
    class_def = _class_def(EXECUTION_MODULE, "RegulatoryIntelligenceQueryExecutionService")
    execute_fn = _execute_method(class_def)
    control = [
        type(node).__name__
        for node in ast.walk(execute_fn)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(execute_fn) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    prepare_calls = 0
    request_calls = 0
    run_calls = 0
    embed_calls = 0
    search_calls = 0
    infer_calls = 0
    for node in ast.walk(execute_fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == "prepare":
            prepare_calls += 1
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {"query_text": "query_text", "limit": "limit"}
        if name == "RegulatoryIntelligenceRequest":
            request_calls += 1
            keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in node.keywords}
            assert keywords == {"search_query": "prepared_query"}
        if name == "run":
            run_calls += 1
            assert len(node.args) == 1
            assert isinstance(node.args[0], ast.Name)
            assert node.args[0].id == "request"
        if name == "embed_query":
            embed_calls += 1
        if name == "search":
            search_calls += 1
        if name == "infer":
            infer_calls += 1
    assert prepare_calls == 1
    assert request_calls == 1
    assert run_calls == 1
    assert embed_calls == 0
    assert search_calls == 0
    assert infer_calls == 0
    statements = [node for node in execute_fn.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 3
    first, second, third = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Await)
    assert isinstance(first.value.value, ast.Call)
    assert _call_name(first.value.value) == "prepare"
    assert isinstance(second, ast.Assign)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "RegulatoryIntelligenceRequest"
    assert isinstance(third, ast.Return)
    assert isinstance(third.value, ast.Await)
    assert isinstance(third.value.value, ast.Call)
    assert _call_name(third.value.value) == "run"
    identifiers = _identifier_names(EXECUTION_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(EXECUTION_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    application_implementations: list[str] = []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if isinstance(node, ast.ClassDef) and node.name in GENERIC_FRAMEWORK_CLASS_NAMES:
                application_implementations.append(node.name)
    assert application_implementations == []
    source = EXECUTION_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "qdrant" not in lowered
    assert "openai" not in lowered
    assert "numpy" not in lowered
    assert "redis" not in lowered
    assert ".search(" not in source
    assert "embed_query" not in source
    assert ".infer(" not in source
    assert "try:" not in source
    assert "except " not in source
    assert "DocumentQueryEmbeddingPort" not in source
    assert "DocumentVectorSearchPort" not in source
    assert "RegulatoryConstraintInferencePort" not in source


def test_graph_and_lower_layers_remain_unwired_to_the_execution_service() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        assert "RegulatoryIntelligenceQueryExecutionService" not in names
        modules = imported_modules(path)
        assert (
            "energy_trading.application.orchestration.regulatory_intelligence_query_execution"
            not in modules
        )
        source = path.read_text(encoding="utf-8")
        assert "RegulatoryIntelligenceQueryExecutionService" not in source
        assert "regulatory_intelligence_query_execution" not in source
    agent_names = imported_names(AGENT_MODULE)
    assert "RegulatoryIntelligenceQueryExecutionService" not in agent_names
    agent_modules = imported_modules(AGENT_MODULE)
    assert (
        "energy_trading.application.orchestration.regulatory_intelligence_query_execution"
        not in agent_modules
    )


def test_api_composition_does_not_import_or_construct_the_execution_service() -> None:
    forbidden_wiring = (
        "energy_trading.application.orchestration",
        "energy_trading.application.orchestration.regulatory_intelligence_query_execution",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "RegulatoryIntelligenceQueryExecutionService" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    tree = ast.parse(app_source, filename=str(API_APP))
    create_app = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    call_names: set[str] = set()
    for node in ast.walk(create_app):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            call_names.add(func.id)
        elif isinstance(func, ast.Attribute):
            call_names.add(func.attr)
    assert "RegulatoryIntelligenceQueryExecutionService" not in call_names
    lowered = app_source.lower()
    assert "regulatoryintelligencequeryexecutionservice" not in lowered
    assert "regulatory_intelligence_query_execution" not in lowered


def test_no_production_langgraph_imports_outside_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
