"""Chunk 67 Regulatory Intelligence composition root stays an outer builder."""

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
BUILDER_MODULE = COMPOSITION_ROOT / "regulatory_intelligence.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "energy_trading.application.orchestration.graph",
    "energy_trading.api.app",
    "energy_trading.api.routers",
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
    "os",
    "sys",
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
        "AppSettings",
        "FastAPI",
        "APIRouter",
        "Container",
        "ServiceContainer",
        "DependencyContainer",
        "DIContainer",
        "Registry",
        "ServiceRegistry",
        "AgentFactory",
        "ServiceFactory",
        "ProviderFactory",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "Any",
        "dict",
        "Mapping",
        "ndarray",
        "embed_query",
        "prepare",
        "execute",
        "run",
        "infer",
        "create_app",
        "build_workflow_graph",
        "include_router",
        "add_api_route",
        "getenv",
        "environ",
        "get_settings",
        "AppSettings",
        "EmbeddingPort",
        "LLMPort",
        "AIProviderPort",
        "AgentRegistry",
        "AgentExecutor",
        "RagPipeline",
        "Container",
        "Registry",
        "provider",
        "model_name",
        "prompt",
        "collection_name",
        "score",
        "retry",
        "cache",
        "numpy",
        "asarray",
        "normalize",
        "clamp",
        "rewrite",
        "expand",
        "tokenize",
        "registry",
        "factory",
        "container",
        "resolve",
        "get_service",
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
        "Container",
        "ServiceContainer",
        "DependencyContainer",
        "DIContainer",
        "Registry",
        "ServiceRegistry",
        "AgentFactory",
        "ServiceFactory",
        "ProviderFactory",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "energy_trading.application.agents.regulatory_intelligence",
        "energy_trading.application.orchestration.document_vector_search_query_preparation",
        "energy_trading.application.orchestration.regulatory_intelligence_query_execution",
        "energy_trading.application.ports.document_query_embedding",
        "energy_trading.application.ports.document_vector_search",
        "energy_trading.application.ports.regulatory_constraint_inference",
    }
)

ALLOWED_INIT_ANNOTATIONS = {
    "document_query_embedding_port": "DocumentQueryEmbeddingPort",
    "document_vector_search_port": "DocumentVectorSearchPort",
    "regulatory_constraint_inference_port": "RegulatoryConstraintInferencePort",
}

RUNTIME_CALL_NAMES = frozenset(
    {
        "embed_query",
        "prepare",
        "search",
        "infer",
        "run",
        "execute",
        "getenv",
        "get_settings",
        "include_router",
        "add_api_route",
    }
)


def _module_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _module_class_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def _builder_function(path: Path) -> ast.FunctionDef:
    for node in _module_function_defs(path):
        if isinstance(node, ast.FunctionDef) and node.name == (
            "build_regulatory_intelligence_query_execution"
        ):
            return node
    msg = "build_regulatory_intelligence_query_execution not found"
    raise AssertionError(msg)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


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


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert BUILDER_MODULE.exists()
    assert COMPOSITION_ROOT.parent == API_ROOT


def test_builder_depends_inward_on_application_only() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BUILDER_MODULE)
    assert "DocumentQueryEmbeddingPort" in names
    assert "DocumentVectorSearchPort" in names
    assert "RegulatoryConstraintInferencePort" in names
    assert "DocumentVectorSearchQueryPreparationService" in names
    assert "RegulatoryIntelligenceAgent" in names
    assert "RegulatoryIntelligenceQueryExecutionService" in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_synchronous_function() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["build_regulatory_intelligence_query_execution"]
    assert all(isinstance(node, ast.FunctionDef) for node in public)
    assert _module_class_names(BUILDER_MODULE) == []
    leaked_implementations = sorted(
        name
        for name in _module_class_names(BUILDER_MODULE)
        if name in GENERIC_FRAMEWORK_CLASS_NAMES
    )
    assert leaked_implementations == []
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "build_regulatory_intelligence_query_execution"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == ["energy_trading/api/composition/regulatory_intelligence.py"]


def test_builder_signature_has_exactly_three_keyword_only_application_ports() -> None:
    builder = _builder_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == (
        "document_query_embedding_port",
        "document_vector_search_port",
        "regulatory_constraint_inference_port",
    )
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == ALLOWED_INIT_ANNOTATIONS
    assert ast.unparse(builder.returns) == "RegulatoryIntelligenceQueryExecutionService"


def test_builder_constructs_three_application_objects_without_runtime_calls() -> None:
    builder = _builder_function(BUILDER_MODULE)
    control = [
        type(node).__name__
        for node in ast.walk(builder)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try, ast.With))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(builder) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    constructed: list[str] = []
    runtime_calls: list[str] = []
    for node in ast.walk(builder):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None:
            continue
        if name in RUNTIME_CALL_NAMES:
            runtime_calls.append(name)
        constructed.append(name)
    assert runtime_calls == []
    assert constructed == [
        "DocumentVectorSearchQueryPreparationService",
        "RegulatoryIntelligenceAgent",
        "RegulatoryIntelligenceQueryExecutionService",
    ]
    statements = [node for node in builder.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 3
    first, second, third = statements
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert _call_name(first.value) == "DocumentVectorSearchQueryPreparationService"
    assert len(first.value.args) == 1
    assert isinstance(first.value.args[0], ast.Name)
    assert first.value.args[0].id == "document_query_embedding_port"
    assert isinstance(second, ast.Assign)
    assert isinstance(second.value, ast.Call)
    assert _call_name(second.value) == "RegulatoryIntelligenceAgent"
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in second.value.keywords}
    assert keywords == {
        "search": "document_vector_search_port",
        "inference": "regulatory_constraint_inference_port",
    }
    assert isinstance(third, ast.Return)
    assert isinstance(third.value, ast.Call)
    assert _call_name(third.value) == "RegulatoryIntelligenceQueryExecutionService"
    assert [ast.unparse(arg) for arg in third.value.args] == [
        "query_preparation_service",
        "regulatory_intelligence_agent",
    ]
    identifiers = _identifier_names(BUILDER_MODULE)
    leaked = sorted(name for name in identifiers if name in FORBIDDEN_IDENTIFIERS)
    assert leaked == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    lowered = source.lower()
    assert "langgraph" not in lowered
    assert "langchain" not in lowered
    assert "qdrant" not in lowered
    assert "openai" not in lowered
    assert "fastapi" not in lowered
    assert "numpy" not in lowered
    assert "redis" not in lowered
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "try:" not in source
    assert "except " not in source
    assert ".embed_query(" not in source
    assert ".prepare(" not in source
    assert ".search(" not in source
    assert ".infer(" not in source
    assert ".run(" not in source
    assert ".execute(" not in source


def test_application_does_not_import_the_outer_builder() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.regulatory_intelligence",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "build_regulatory_intelligence_query_execution" not in names
        source = path.read_text(encoding="utf-8")
        assert "build_regulatory_intelligence_query_execution" not in source


def test_http_create_app_does_not_invoke_the_builder() -> None:
    for path in http_transport_api_paths(API_ROOT):
        names = imported_names(path)
        assert "build_regulatory_intelligence_query_execution" not in names
        modules = imported_modules(path)
        assert "energy_trading.api.composition" not in modules
        assert "energy_trading.api.composition.regulatory_intelligence" not in modules
        source = path.read_text(encoding="utf-8")
        assert "build_regulatory_intelligence_query_execution" not in source
        if path.resolve() == API_APP.resolve():
            assert "energy_trading.api.composition.production_lifespan" in modules
            assert "energy_trading.api.composition.regulatory_intelligence_lifespan" not in modules
            continue
        assert "api.composition" not in source
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
    assert "build_regulatory_intelligence_query_execution" not in call_names
    assert "RegulatoryIntelligenceQueryExecutionService" not in call_names
    lowered = app_source.lower()
    assert "build_regulatory_intelligence_query_execution" not in lowered
    assert "regulatoryintelligencequeryexecutionservice" not in lowered


def test_graph_remains_unwired_to_the_builder() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "build_regulatory_intelligence_query_execution" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "energy_trading.api.composition" not in modules
    assert "energy_trading.api.composition.regulatory_intelligence" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "build_regulatory_intelligence_query_execution" not in source
    assert "energy_trading.api" not in source


def test_no_production_langgraph_imports_outside_graph_module() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        if path.resolve() == GRAPH_MODULE.resolve():
            continue
        for module in sorted(imported_modules(path)):
            if is_forbidden(module, ("langgraph",)):
                leaked.append(f"{path.relative_to(SRC_ROOT)} imports {module}")
    assert leaked == []
