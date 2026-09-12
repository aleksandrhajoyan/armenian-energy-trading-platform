"""Chunk 111 document-index runtime owns collection readiness on the managed client."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    imported_modules,
    imported_names,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
COMPOSITION_ROOT = API_ROOT / "composition"
MANAGED_MODULE = COMPOSITION_ROOT / "document_vector_index_managed_runtime.py"
LOADED_MODULE = COMPOSITION_ROOT / "document_vector_index_loaded_runtime.py"
LIFESPAN_MODULE = COMPOSITION_ROOT / "document_vector_index_lifespan.py"
PRODUCTION_LIFESPAN_MODULE = COMPOSITION_ROOT / "production_lifespan.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"

ENSURE_NAME = "ensure_configured_document_vector_index_collection_ready"
DISTANCE_LOADER_NAME = "load_qdrant_document_vector_distance_settings"
DISTANCE_SETTINGS_NAME = "QdrantDocumentVectorDistanceSettings"
CONFIGURED_BUILDER_NAME = "build_document_vector_index_configured_runtime"

DIRECT_PRIMITIVE_NAMES = (
    "map_qdrant_document_vector_distance",
    "ensure_qdrant_document_collection_ready",
    "create_qdrant_document_collection",
    "verify_qdrant_document_collection_ready",
)

SECONDARY_ENSURE_OWNERS = (
    API_APP,
    GRAPH_MODULE,
    LIFESPAN_MODULE,
    PRODUCTION_LIFESPAN_MODULE,
    LOADED_MODULE,
    COMPOSITION_ROOT / "document_vector_index_configured_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_runtime.py",
    COMPOSITION_ROOT / "document_vector_index_execution.py",
    COMPOSITION_ROOT / "regulatory_intelligence_lifespan.py",
    COMPOSITION_ROOT / "regulatory_intelligence_loaded_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_managed_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_configured_runtime.py",
    COMPOSITION_ROOT / "regulatory_intelligence_runtime.py",
    API_ROOT / "routers" / "document_vector_index.py",
    API_ROOT / "routers" / "regulatory_intelligence.py",
)


def _module_function_defs(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _managed_function() -> ast.AsyncFunctionDef:
    for node in _module_function_defs(MANAGED_MODULE):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == (
            "managed_document_vector_index_runtime"
        ):
            return node
    msg = "managed_document_vector_index_runtime not found"
    raise AssertionError(msg)


def _loaded_function() -> ast.AsyncFunctionDef:
    for node in _module_function_defs(LOADED_MODULE):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == (
            "loaded_document_vector_index_runtime"
        ):
            return node
    msg = "loaded_document_vector_index_runtime not found"
    raise AssertionError(msg)


def test_managed_runtime_imports_distance_settings_and_chunk_110_ensure() -> None:
    names = imported_names(MANAGED_MODULE)
    modules = imported_modules(MANAGED_MODULE)
    assert DISTANCE_SETTINGS_NAME in names
    assert ENSURE_NAME in names
    assert "energy_trading.api.composition.document_vector_index_collection_ensure" in modules
    assert DISTANCE_LOADER_NAME not in names
    assert "QdrantDocumentVectorConfig" not in names
    assert "qdrant_client" not in names
    assert "AsyncQdrantClient" not in names
    for primitive in DIRECT_PRIMITIVE_NAMES:
        assert primitive not in names


def test_managed_runtime_awaits_chunk_110_ensure_once_before_configured_builder() -> None:
    managed = _managed_function()
    control = [
        type(node).__name__
        for node in ast.walk(managed)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match, ast.For, ast.While, ast.Try))
    ]
    assert control == []
    except_handlers = [node for node in ast.walk(managed) if isinstance(node, ast.ExceptHandler)]
    assert except_handlers == []
    ensure_calls: list[ast.Call] = []
    configured_calls: list[ast.Call] = []
    for node in ast.walk(managed):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name == ENSURE_NAME:
            ensure_calls.append(node)
        if name == CONFIGURED_BUILDER_NAME:
            configured_calls.append(node)
    assert len(ensure_calls) == 1
    assert len(configured_calls) == 1
    awaited = [
        node
        for node in ast.walk(managed)
        if isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and _call_name(node.value) == ENSURE_NAME
    ]
    assert len(awaited) == 1
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in ensure_calls[0].keywords}
    assert keywords == {
        "client": "qdrant_client",
        "runtime_settings": "document_vector_index_settings",
        "distance_settings": "distance_settings",
    }
    statements = [node for node in managed.body if not isinstance(node, ast.Expr)]
    assert len(statements) == 1
    async_with = statements[0]
    assert isinstance(async_with, ast.AsyncWith)
    inner = list(async_with.body)
    call_sequence: list[str] = []
    for node in inner:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            name = _call_name(node.value)
            if name is not None:
                call_sequence.append(name)
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Await):
            assert isinstance(node.value.value, ast.Call)
            name = _call_name(node.value.value)
            if name is not None:
                call_sequence.append(name)
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Yield):
            call_sequence.append("yield")
    assert call_sequence == [
        "create_openai_client",
        "create_qdrant_client",
        ENSURE_NAME,
        CONFIGURED_BUILDER_NAME,
        "yield",
    ]
    source = MANAGED_MODULE.read_text(encoding="utf-8")
    assert "sleep(" not in source
    assert "tenacity" not in source
    assert "backoff" not in source
    for primitive in DIRECT_PRIMITIVE_NAMES:
        assert primitive not in source


def test_loaded_runtime_loads_distance_settings_and_does_not_call_ensure() -> None:
    names = imported_names(LOADED_MODULE)
    modules = imported_modules(LOADED_MODULE)
    assert DISTANCE_LOADER_NAME in names
    assert ENSURE_NAME not in names
    assert DISTANCE_SETTINGS_NAME not in names
    assert "qdrant_client" not in modules
    assert "AsyncQdrantClient" not in names
    assert "create_qdrant_client" not in names
    assert "create_openai_client" not in names
    assert "energy_trading.api.composition.document_vector_index_collection_ensure" not in modules
    for primitive in DIRECT_PRIMITIVE_NAMES:
        assert primitive not in names
    loaded = _loaded_function()
    loader_calls: list[ast.Call] = []
    for node in ast.walk(loaded):
        if isinstance(node, ast.Call) and _call_name(node) == DISTANCE_LOADER_NAME:
            loader_calls.append(node)
    assert len(loader_calls) == 1
    assert {keyword.arg: ast.unparse(keyword.value) for keyword in loader_calls[0].keywords} == {
        "env_file": "env_file"
    }
    statements = [node for node in loaded.body if not isinstance(node, ast.Expr)]
    async_with = statements[-1]
    assert isinstance(async_with, ast.AsyncWith)
    item = async_with.items[0]
    assert isinstance(item.context_expr, ast.Call)
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in item.context_expr.keywords}
    assert keywords["distance_settings"] == "distance_settings"
    source = LOADED_MODULE.read_text(encoding="utf-8")
    assert ENSURE_NAME not in source
    assert "create_qdrant_client" not in source
    assert "create_openai_client" not in source


def test_create_app_and_child_lifespans_do_not_own_collection_ensure() -> None:
    app_names = imported_names(API_APP)
    app_modules = imported_modules(API_APP)
    assert "qdrant_client" not in app_modules
    assert DISTANCE_SETTINGS_NAME not in app_names
    assert DISTANCE_LOADER_NAME not in app_names
    assert ENSURE_NAME not in app_names
    app_source = API_APP.read_text(encoding="utf-8")
    assert ENSURE_NAME not in app_source
    assert DISTANCE_LOADER_NAME not in app_source
    ensure_mentions: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        mentioned = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == ENSURE_NAME:
                mentioned = True
                break
            if isinstance(node, ast.alias) and (
                node.name == ENSURE_NAME or node.asname == ENSURE_NAME
            ):
                mentioned = True
                break
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == ENSURE_NAME
            ):
                mentioned = True
                break
        if mentioned:
            ensure_mentions.append(path.relative_to(SRC_ROOT).as_posix())
    assert ensure_mentions == [
        "energy_trading/api/composition/__init__.py",
        "energy_trading/api/composition/document_vector_index_collection_ensure.py",
        "energy_trading/api/composition/document_vector_index_managed_runtime.py",
    ]
    for path in SECONDARY_ENSURE_OWNERS:
        names = imported_names(path)
        modules = imported_modules(path)
        source = path.read_text(encoding="utf-8")
        assert ENSURE_NAME not in names
        assert (
            "energy_trading.api.composition.document_vector_index_collection_ensure" not in modules
        )
        assert ENSURE_NAME not in source
