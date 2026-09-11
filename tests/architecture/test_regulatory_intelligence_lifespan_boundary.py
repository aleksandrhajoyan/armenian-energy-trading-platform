"""Chunk 78 FastAPI Regulatory lifespan exposes Chunk 75 on lifespan-scoped app.state."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    SRC_ROOT,
    annotation_type_names,
    collect_http_api_import_violations,
    collect_import_violations,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
REGULATORY_ROUTER = API_ROOT / "routers" / "regulatory_intelligence.py"
COMPOSITION_ROOT = API_ROOT / "composition"
BUILDER_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py"
LOADED_RUNTIME_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_loaded_runtime.py"
MANAGED_RUNTIME_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_managed_runtime.py"
CONFIGURED_RUNTIME_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_configured_runtime.py"
PROVIDER_RUNTIME_MODULE = COMPOSITION_ROOT / "regulatory_intelligence_runtime.py"
NEUTRAL_BUILDER_MODULE = COMPOSITION_ROOT / "regulatory_intelligence.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
APPLICATION_ROOT = PRODUCTION_ROOT / "application"
DOMAIN_ROOT = PRODUCTION_ROOT / "domain"
ML_ROOT = PRODUCTION_ROOT / "ml"

FORBIDDEN_PREFIXES = (
    "openai",
    "qdrant_client",
    "energy_trading.ml",
    "energy_trading.application",
    "energy_trading.application.orchestration.graph",
    "energy_trading.application.agents",
    "energy_trading.api.app",
    "energy_trading.api.routers",
    "energy_trading.shared.config.settings",
    "energy_trading.shared.config.database",
    "energy_trading.shared.config.redis",
    "energy_trading.shared.config.openai",
    "energy_trading.shared.config.qdrant",
    "energy_trading.shared.config.regulatory_intelligence",
    "energy_trading.infrastructure",
    "energy_trading.infrastructure.openai",
    "energy_trading.infrastructure.embeddings",
    "energy_trading.infrastructure.regulatory",
    "energy_trading.infrastructure.vector_store",
    "energy_trading.infrastructure.cache",
    "energy_trading.infrastructure.persistence",
    "energy_trading.api.composition.regulatory_intelligence_configured_runtime",
    "energy_trading.api.composition.regulatory_intelligence_managed_runtime",
    "energy_trading.api.composition.regulatory_intelligence_runtime",
    "energy_trading.api.composition.regulatory_intelligence",
    "starlette",
    "langgraph",
    "langchain",
    "langchain_core",
    "anthropic",
    "google.generativeai",
    "google.genai",
    "sentence_transformers",
    "transformers",
    "redis",
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
    "dotenv",
)

FORBIDDEN_TYPE_NAMES = frozenset(
    {
        "Any",
        "TypeVar",
        "Generic",
        "dict",
        "Dict",
        "Mapping",
        "LLMPort",
        "EmbeddingPort",
        "ProviderRegistry",
        "Container",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "SettingsRegistry",
        "AppSettings",
        "APIRouter",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "QdrantDocumentVectorConfig",
        "RegulatoryIntelligenceAgent",
        "RegulatoryIntelligenceQueryExecutionService",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
    }
)

GENERIC_FRAMEWORK_NAMES = frozenset(
    {
        "LLMPort",
        "EmbeddingPort",
        "ProviderRegistry",
        "ServiceRegistry",
        "AgentFactory",
        "Container",
        "LiteLLM",
        "RAGPort",
        "ManagedRuntime",
        "ResourceManager",
        "LifecycleManager",
        "SettingsRegistry",
        "SettingsAggregator",
    }
)

ALLOWED_MODULE_IMPORTS = frozenset(
    {
        "collections.abc",
        "contextlib",
        "pathlib",
        "fastapi",
        "energy_trading.api.composition.regulatory_intelligence_loaded_runtime",
    }
)

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
        "load_openai_settings",
        "load_qdrant_settings",
        "load_regulatory_intelligence_runtime_settings",
        "AsyncOpenAI",
        "AsyncQdrantClient",
        "create_openai_client",
        "create_qdrant_client",
        "create_collection",
        "include_router",
        "add_api_route",
        "setattr",
        "delattr",
        "build_regulatory_intelligence_query_execution",
        "build_regulatory_intelligence_provider_runtime",
        "build_regulatory_intelligence_configured_runtime",
        "managed_regulatory_intelligence_runtime",
        "OpenAIDocumentQueryEmbeddingAdapter",
        "OpenAIRegulatoryConstraintInferenceAdapter",
        "QdrantDocumentVectorSearch",
        "QdrantDocumentVectorConfig",
        "OpenAISettings",
        "QdrantSettings",
        "RegulatoryIntelligenceRuntimeSettings",
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
            "build_regulatory_intelligence_lifespan"
        ):
            return node
    msg = "build_regulatory_intelligence_lifespan not found"
    raise AssertionError(msg)


def _nested_lifespan(builder: ast.FunctionDef) -> ast.AsyncFunctionDef:
    nested = [node for node in builder.body if isinstance(node, ast.AsyncFunctionDef)]
    if len(nested) != 1 or nested[0].name != "lifespan":
        msg = "expected exactly one nested lifespan callback"
        raise AssertionError(msg)
    return nested[0]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def test_builder_lives_in_api_composition_package() -> None:
    assert BUILDER_MODULE.parent == COMPOSITION_ROOT
    assert BUILDER_MODULE.exists()
    assert COMPOSITION_ROOT.parent == API_ROOT


def test_builder_imports_only_approved_surfaces() -> None:
    leaked = sorted(
        module
        for module in imported_modules(BUILDER_MODULE)
        if is_forbidden(module, FORBIDDEN_PREFIXES)
    )
    assert leaked == []
    extras = imported_modules(BUILDER_MODULE) - ALLOWED_MODULE_IMPORTS
    assert extras == set()
    names = imported_names(BUILDER_MODULE)
    assert "FastAPI" in names
    assert "loaded_regulatory_intelligence_runtime" in names
    assert "asynccontextmanager" in names
    assert "Path" in names
    assert "load_openai_settings" not in names
    assert "load_qdrant_settings" not in names
    assert "load_regulatory_intelligence_runtime_settings" not in names
    assert "managed_regulatory_intelligence_runtime" not in names
    assert "build_regulatory_intelligence_configured_runtime" not in names
    assert "build_regulatory_intelligence_provider_runtime" not in names
    assert "build_regulatory_intelligence_query_execution" not in names
    assert "openai" not in names
    assert "qdrant_client" not in names
    assert "AsyncOpenAI" not in names
    assert "AsyncQdrantClient" not in names
    assert "OpenAISettings" not in names
    assert "QdrantSettings" not in names
    assert "RegulatoryIntelligenceRuntimeSettings" not in names
    assert "create_openai_client" not in names
    assert "create_qdrant_client" not in names
    assert "OpenAIDocumentQueryEmbeddingAdapter" not in names
    assert "OpenAIRegulatoryConstraintInferenceAdapter" not in names
    assert "QdrantDocumentVectorSearch" not in names
    assert "QdrantDocumentVectorConfig" not in names
    assert "RegulatoryIntelligenceAgent" not in names
    assert "RegulatoryIntelligenceQueryExecutionService" not in names
    leaked_names = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_names == []


def test_builder_exposes_exactly_one_public_sync_factory() -> None:
    public = _module_function_defs(BUILDER_MODULE)
    assert [node.name for node in public] == ["build_regulatory_intelligence_lifespan"]
    assert isinstance(public[0], ast.FunctionDef)
    assert not isinstance(public[0], ast.AsyncFunctionDef)
    assert _module_class_names(BUILDER_MODULE) == []
    production_builders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in parsed.body:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "build_regulatory_intelligence_lifespan"
            ):
                production_builders.append(path.relative_to(SRC_ROOT).as_posix())
    assert production_builders == [
        "energy_trading/api/composition/regulatory_intelligence_lifespan.py"
    ]


def test_builder_returns_fastapi_compatible_async_lifespan_callback() -> None:
    builder = _builder_function(BUILDER_MODULE)
    assert builder.args.posonlyargs == []
    assert builder.args.args == []
    assert tuple(arg.arg for arg in builder.args.kwonlyargs) == ("env_file",)
    assert builder.args.vararg is None
    assert builder.args.kwarg is None
    annotations = {
        arg.arg: ast.unparse(arg.annotation)
        for arg in builder.args.kwonlyargs
        if arg.annotation is not None
    }
    assert annotations == {"env_file": "str | Path | None"}
    assert ast.unparse(builder.args.kw_defaults[0]) == "'.env'"
    assert ast.unparse(builder.returns) == (
        "Callable[[FastAPI], AbstractAsyncContextManager[None]]"
    )
    lifespan = _nested_lifespan(builder)
    assert len(lifespan.decorator_list) == 1
    decorator = lifespan.decorator_list[0]
    assert isinstance(decorator, ast.Name)
    assert decorator.id == "asynccontextmanager"
    assert tuple(arg.arg for arg in lifespan.args.args) == ("app",)
    assert ast.unparse(lifespan.args.args[0].annotation) == "FastAPI"
    assert ast.unparse(lifespan.returns) == "AsyncIterator[None]"
    statements = [
        node
        for node in builder.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
    ]
    assert [type(node).__name__ for node in statements] == ["AsyncFunctionDef", "Return"]
    returned = statements[1]
    assert isinstance(returned, ast.Return)
    assert isinstance(returned.value, ast.Name)
    assert returned.value.id == "lifespan"


def test_builder_construction_does_not_load_settings_or_enter_runtime() -> None:
    builder = _builder_function(BUILDER_MODULE)
    outer_calls: list[str] = []
    for statement in builder.body:
        if isinstance(statement, ast.AsyncFunctionDef):
            continue
        for node in ast.walk(statement):
            if isinstance(node, ast.Call):
                name = _call_name(node)
                if name is not None:
                    outer_calls.append(name)
    assert outer_calls == []


def _state_attribute(node: ast.AST) -> ast.Attribute | None:
    if not isinstance(node, ast.Attribute):
        return None
    if node.attr != "regulatory_intelligence_query_execution_service":
        return None
    owner = node.value
    if not isinstance(owner, ast.Attribute) or owner.attr != "state":
        return None
    if not isinstance(owner.value, ast.Name) or owner.value.id != "app":
        return None
    return node


def test_lifespan_assigns_chunk_75_service_on_app_state_and_deletes_it_before_exit() -> None:
    builder = _builder_function(BUILDER_MODULE)
    lifespan = _nested_lifespan(builder)
    control = [
        type(node).__name__
        for node in ast.walk(builder)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try))
    ]
    assert control == ["Try"]
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
    assert constructed == ["loaded_regulatory_intelligence_runtime"]
    statements = [node for node in lifespan.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 1
    wrapper = statements[0]
    assert isinstance(wrapper, ast.AsyncWith)
    assert len(wrapper.items) == 1
    item = wrapper.items[0]
    assert isinstance(item.context_expr, ast.Call)
    assert _call_name(item.context_expr) == "loaded_regulatory_intelligence_runtime"
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in item.context_expr.keywords}
    assert keywords == {"env_file": "env_file"}
    assert isinstance(item.optional_vars, ast.Name)
    assert item.optional_vars.id == "service"
    inner = [node for node in wrapper.body if not isinstance(node, ast.Expr)]
    assert [type(node).__name__ for node in inner] == ["Assign", "Try"]
    assignment = inner[0]
    assert isinstance(assignment, ast.Assign)
    assert len(assignment.targets) == 1
    assigned = _state_attribute(assignment.targets[0])
    assert assigned is not None
    assert isinstance(assignment.value, ast.Name)
    assert assignment.value.id == "service"
    try_node = inner[1]
    assert isinstance(try_node, ast.Try)
    assert try_node.handlers == []
    assert try_node.orelse == []
    assert len(try_node.body) == 1
    assert isinstance(try_node.body[0], ast.Expr)
    assert isinstance(try_node.body[0].value, ast.Yield)
    assert try_node.body[0].value.value is None
    assert len(try_node.finalbody) == 1
    deletion = try_node.finalbody[0]
    assert isinstance(deletion, ast.Delete)
    assert len(deletion.targets) == 1
    deleted = _state_attribute(deletion.targets[0])
    assert deleted is not None
    source = BUILDER_MODULE.read_text(encoding="utf-8")
    assert "app.state.regulatory_intelligence_query_execution_service" in source
    assert "request.state" not in source
    assert "dependency_overrides" not in source
    assert "global " not in source
    assert "get_regulatory_intelligence" not in source
    assert "Depends(" not in source
    assert "OpenAISettings(" not in source
    assert "QdrantSettings(" not in source
    assert "RegulatoryIntelligenceRuntimeSettings(" not in source
    assert "AsyncOpenAI(" not in source
    assert "AsyncQdrantClient(" not in source
    assert "create_openai_client" not in source
    assert "create_qdrant_client" not in source
    assert "os.environ" not in source
    assert "getenv" not in source
    assert "dotenv" not in source
    assert ".embed_query(" not in source
    assert ".search(" not in source
    assert ".infer(" not in source
    assert ".execute(" not in source
    assert ".run(" not in source
    assert "create_collection" not in source
    identifiers = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    leaked_frameworks = sorted(name for name in identifiers if name in GENERIC_FRAMEWORK_NAMES)
    assert leaked_frameworks == []
    names = annotation_type_names(BUILDER_MODULE)
    leaked_types = sorted(name for name in names if name in FORBIDDEN_TYPE_NAMES)
    assert leaked_types == []


def test_state_mutation_is_confined_to_the_lifespan_module() -> None:
    attribute = "regulatory_intelligence_query_execution_service"
    accessor_module = API_ROOT / "dependencies" / "regulatory_intelligence.py"
    dependencies_root = (API_ROOT / "dependencies").resolve()
    writer = BUILDER_MODULE.resolve()
    document_index_writer = (COMPOSITION_ROOT / "document_vector_index_lifespan.py").resolve()
    offenders: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        resolved = path.resolve()
        if (
            resolved == writer
            or resolved.is_relative_to(dependencies_root)
            or resolved == REGULATORY_ROUTER.resolve()
        ):
            continue
        source = path.read_text(encoding="utf-8")
        if resolved == document_index_writer:
            if attribute in source:
                offenders.append(path.relative_to(SRC_ROOT).as_posix())
            continue
        if attribute in source or "app.state" in source:
            offenders.append(path.relative_to(SRC_ROOT).as_posix())
    assert offenders == []
    for path in sorted((API_ROOT / "dependencies").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == attribute:
                        msg = "dependencies package must not assign the published state attribute"
                        raise AssertionError(msg)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
                if node.target.attr == attribute:
                    msg = "dependencies package must not assign the published state attribute"
                    raise AssertionError(msg)
            if isinstance(node, ast.Delete):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == attribute:
                        msg = "dependencies package must not delete the published state attribute"
                        raise AssertionError(msg)
        if path.resolve() != accessor_module.resolve():
            source = path.read_text(encoding="utf-8")
            assert "app.state" not in source
    tree = ast.parse(accessor_module.read_text(encoding="utf-8"), filename=str(accessor_module))
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "setattr" not in call_names
    assert "delattr" not in call_names
    for path in sorted((API_ROOT / "routers").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "app.state" not in source
        if path.resolve() == REGULATORY_ROUTER.resolve():
            continue
        assert attribute not in source


def test_provider_sdk_allowlist_remains_the_existing_two_modules() -> None:
    assert REGULATORY_PROVIDER_COMPOSITION_RELATIVES == (
        "energy_trading/api/composition/regulatory_intelligence_runtime.py",
        "energy_trading/api/composition/regulatory_intelligence_configured_runtime.py",
    )
    relative = BUILDER_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative not in REGULATORY_PROVIDER_COMPOSITION_RELATIVES
    assert "openai" not in imported_modules(BUILDER_MODULE)
    assert "qdrant_client" not in imported_modules(BUILDER_MODULE)
    assert "openai" in imported_modules(PROVIDER_RUNTIME_MODULE)
    assert "openai" in imported_modules(CONFIGURED_RUNTIME_MODULE)
    assert "qdrant_client" in imported_modules(PROVIDER_RUNTIME_MODULE)
    assert "qdrant_client" in imported_modules(CONFIGURED_RUNTIME_MODULE)
    assert "openai" not in imported_modules(LOADED_RUNTIME_MODULE)
    assert "qdrant_client" not in imported_modules(LOADED_RUNTIME_MODULE)
    assert "openai" not in imported_modules(MANAGED_RUNTIME_MODULE)
    assert "qdrant_client" not in imported_modules(MANAGED_RUNTIME_MODULE)


def test_application_and_domain_do_not_import_the_lifespan_builder() -> None:
    forbidden = (
        "energy_trading.api",
        "energy_trading.api.composition",
        "energy_trading.api.composition.regulatory_intelligence_lifespan",
        "openai",
        "qdrant_client",
    )
    assert collect_import_violations(APPLICATION_ROOT, forbidden) == []
    assert collect_import_violations(DOMAIN_ROOT, forbidden) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, forbidden) == []
    for path in sorted(APPLICATION_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "build_regulatory_intelligence_lifespan" not in names
        source = path.read_text(encoding="utf-8")
        assert "build_regulatory_intelligence_lifespan" not in source


def test_http_routes_remain_unwired_to_chunk_75_and_provider_sdks() -> None:
    forbidden_wiring = (
        "openai",
        "qdrant_client",
        "energy_trading.api.composition.regulatory_intelligence_loaded_runtime",
        "energy_trading.infrastructure.openai",
        "energy_trading.infrastructure.vector_store.qdrant.client",
    )
    assert collect_http_api_import_violations(API_ROOT, forbidden_wiring) == []
    names = imported_names(API_APP)
    assert "loaded_regulatory_intelligence_runtime" not in names
    app_source = API_APP.read_text(encoding="utf-8")
    assert "loaded_regulatory_intelligence_runtime" not in app_source
    for path in (
        LOADED_RUNTIME_MODULE,
        MANAGED_RUNTIME_MODULE,
        CONFIGURED_RUNTIME_MODULE,
        PROVIDER_RUNTIME_MODULE,
        NEUTRAL_BUILDER_MODULE,
    ):
        source = path.read_text(encoding="utf-8")
        assert "build_regulatory_intelligence_lifespan" not in source
    for path in sorted((API_ROOT / "routers").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "build_regulatory_intelligence_lifespan" not in source
        assert "loaded_regulatory_intelligence_runtime" not in source
        if path.resolve() == REGULATORY_ROUTER.resolve():
            continue
        assert "regulatory_intelligence_query_execution_service" not in source


def test_graph_remains_unwired_to_the_lifespan_builder() -> None:
    names = imported_names(GRAPH_MODULE)
    assert "build_regulatory_intelligence_lifespan" not in names
    modules = imported_modules(GRAPH_MODULE)
    assert "openai" not in modules
    assert "qdrant_client" not in modules
    assert "energy_trading.api.composition" not in modules
    source = GRAPH_MODULE.read_text(encoding="utf-8")
    assert "build_regulatory_intelligence_lifespan" not in source
    assert "loaded_regulatory_intelligence_runtime" not in source
    assert "energy_trading.api" not in source
    assert "regulatory_intelligence_query_execution_service" not in source
