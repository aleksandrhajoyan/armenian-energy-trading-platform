"""Chunk 109 Qdrant document-vector distance configuration stays explicit.

Chunk 110 is the authorized mapper-to-ensure composition. Chunk 111 authorizes
the existing document-index loaded runtime to load distance settings and the
existing managed runtime to receive those already-constructed settings.
Chunk 112 is the authorized mapper-to-verify composition for Regulatory
collection readiness and remains unwired from runtime. The mapper, create_app,
production/document-index/Regulatory lifespans, HTTP, and LangGraph remain
unwired from mapping.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    QDRANT_DOCUMENT_VECTOR_DISTANCE_MAPPER_RELATIVE,
    SRC_ROOT,
    annotation_type_names,
    imported_modules,
    imported_names,
    is_forbidden,
)

PRODUCTION_ROOT = SRC_ROOT / "energy_trading"
API_ROOT = PRODUCTION_ROOT / "api"
API_APP = API_ROOT / "app.py"
GRAPH_MODULE = PRODUCTION_ROOT / "application" / "orchestration" / "graph.py"
CONFIG_MODULE = PRODUCTION_ROOT / "shared" / "config" / "qdrant.py"
MAPPER_MODULE = API_ROOT / "composition" / "qdrant_document_vector_distance.py"
COMPOSITION_INIT = API_ROOT / "composition" / "__init__.py"
QDRANT_ROOT = PRODUCTION_ROOT / "infrastructure" / "vector_store" / "qdrant"
CREATION_MODULE = QDRANT_ROOT / "collection_creation.py"
READINESS_MODULE = QDRANT_ROOT / "collection_readiness.py"
ENSURE_MODULE = QDRANT_ROOT / "collection_ensure.py"

UNWIRED_MODULES = (
    API_APP,
    GRAPH_MODULE,
    COMPOSITION_INIT,
    API_ROOT / "composition" / "production_lifespan.py",
    API_ROOT / "composition" / "document_vector_index_lifespan.py",
    API_ROOT / "composition" / "document_vector_index_configured_runtime.py",
    API_ROOT / "composition" / "document_vector_index_runtime.py",
    API_ROOT / "composition" / "document_vector_index_execution.py",
    API_ROOT / "composition" / "regulatory_intelligence_lifespan.py",
    API_ROOT / "composition" / "regulatory_intelligence_loaded_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_managed_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_configured_runtime.py",
    API_ROOT / "composition" / "regulatory_intelligence_runtime.py",
    API_ROOT / "composition" / "pdf_document_extraction_index.py",
    API_ROOT / "composition" / "pdf_document_extraction_index_execute.py",
    API_ROOT / "composition" / "pdf_document_extraction_index_loaded_runtime.py",
    API_ROOT / "routers" / "document_vector_index.py",
    API_ROOT / "routers" / "regulatory_intelligence.py",
    CREATION_MODULE,
    READINESS_MODULE,
    ENSURE_MODULE,
)

FORBIDDEN_CONFIG_IMPORTS = (
    "qdrant_client",
    "energy_trading.infrastructure",
    "energy_trading.api",
    "energy_trading.application",
    "energy_trading.ml",
    "fastapi",
    "starlette",
    "langgraph",
    "openai",
)

FORBIDDEN_MAPPER_PREFIXES = (
    "energy_trading.infrastructure",
    "energy_trading.application",
    "energy_trading.ml",
    "fastapi",
    "starlette",
    "langgraph",
    "openai",
    "os",
    "sys",
    "dotenv",
    "pathlib",
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "create_qdrant_document_collection",
        "verify_qdrant_document_collection_ready",
        "ensure_qdrant_document_collection_ready",
        "create_qdrant_client",
        "AsyncQdrantClient",
        "QdrantSettings",
        "load_qdrant_settings",
        "load_qdrant_document_vector_distance_settings",
        "create_app",
        "getenv",
        "environ",
        "CollectionManager",
        "DistanceMapper",
        "ProviderRegistry",
        "ServiceRegistry",
        "MetricCatalog",
        "VectorStoreManager",
    }
)

GENERIC_TYPE_NAMES = frozenset(
    {
        "CollectionManager",
        "DistanceMapper",
        "ProviderRegistry",
        "ServiceRegistry",
        "MetricCatalog",
        "VectorStoreManager",
        "ManagedRuntime",
    }
)

DISTANCE_MEMBERS = frozenset({"COSINE", "DOT", "EUCLID", "MANHATTAN"})
DISTANCE_MEMBER_FRAGMENTS = (
    "Distance.COSINE",
    "Distance.DOT",
    "Distance.EUCLID",
    "Distance.MANHATTAN",
)
EXPECTED_MAPPING = {
    "COSINE": "COSINE",
    "DOT": "DOT",
    "EUCLID": "EUCLID",
    "MANHATTAN": "MANHATTAN",
}


def _module_functions(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _distance_member_attrs(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "Distance"
        ):
            names.add(node.attr)
    return names


def _mapping_table(tree: ast.AST) -> dict[str, str]:
    for node in ast.walk(tree):
        target: ast.AST | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            if any(
                isinstance(item, ast.Name) and item.id == "_QDRANT_DISTANCE_BY_CONFIG"
                for item in node.targets
            ):
                target = node.targets[0]
                value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "_QDRANT_DISTANCE_BY_CONFIG":
                target = node.target
                value = node.value
        if target is None or value is None:
            continue
        assert isinstance(value, ast.Dict)
        mapping: dict[str, str] = {}
        for key, mapped in zip(value.keys, value.values, strict=True):
            assert isinstance(key, ast.Attribute)
            assert isinstance(key.value, ast.Name)
            assert key.value.id == "QdrantDocumentVectorDistance"
            assert isinstance(mapped, ast.Attribute)
            assert isinstance(mapped.value, ast.Name)
            assert mapped.value.id == "Distance"
            mapping[key.attr] = mapped.attr
        return mapping
    msg = "mapping table _QDRANT_DISTANCE_BY_CONFIG not found"
    raise AssertionError(msg)


def test_shared_config_does_not_import_qdrant_sdk() -> None:
    modules = imported_modules(CONFIG_MODULE)
    names = imported_names(CONFIG_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_CONFIG_IMPORTS))
    assert leaked == []
    assert "qdrant_client" not in names
    assert "Distance" not in names
    assert "AsyncQdrantClient" not in names
    source = CONFIG_MODULE.read_text(encoding="utf-8")
    for fragment in DISTANCE_MEMBER_FRAGMENTS:
        assert fragment not in source
    assert "default=" not in source.split("document_vector_distance:", 1)[-1].split("\n", 1)[0]
    assert "QDRANT_DOCUMENT_VECTOR_DISTANCE" in source
    assert "cosine" in source
    assert "dot" in source
    assert "euclid" in source
    assert "manhattan" in source


def test_mapper_lives_in_api_composition_and_is_narrow() -> None:
    relative = MAPPER_MODULE.relative_to(SRC_ROOT).as_posix()
    assert relative == QDRANT_DOCUMENT_VECTOR_DISTANCE_MAPPER_RELATIVE
    modules = imported_modules(MAPPER_MODULE)
    names = imported_names(MAPPER_MODULE)
    leaked = sorted(module for module in modules if is_forbidden(module, FORBIDDEN_MAPPER_PREFIXES))
    assert leaked == []
    assert "qdrant_client.http.models" in modules
    assert "energy_trading.shared.config.qdrant" in modules
    assert "Distance" in names
    assert "QdrantDocumentVectorDistance" in names
    assert names.isdisjoint(FORBIDDEN_IDENTIFIERS)
    functions = _module_functions(MAPPER_MODULE)
    assert [node.name for node in functions] == ["map_qdrant_document_vector_distance"]
    mapper = functions[0]
    assert isinstance(mapper, ast.FunctionDef)
    assert [arg.arg for arg in mapper.args.args] == []
    assert [arg.arg for arg in mapper.args.kwonlyargs] == ["distance"]
    assert mapper.args.defaults == []
    assert all(default is None for default in mapper.args.kw_defaults)
    annotations = annotation_type_names(MAPPER_MODULE)
    assert "QdrantDocumentVectorDistance" in annotations
    assert "Distance" in annotations
    assert annotations.isdisjoint(GENERIC_TYPE_NAMES)
    tree = ast.parse(MAPPER_MODULE.read_text(encoding="utf-8"), filename=str(MAPPER_MODULE))
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)
    assert not any(
        isinstance(node, (ast.For, ast.While, ast.AsyncFor, ast.Await)) for node in ast.walk(tree)
    )


def test_mapper_table_is_explicit_and_total() -> None:
    tree = ast.parse(MAPPER_MODULE.read_text(encoding="utf-8"), filename=str(MAPPER_MODULE))
    assert _mapping_table(tree) == EXPECTED_MAPPING
    assert _distance_member_attrs(tree) == DISTANCE_MEMBERS
    source = MAPPER_MODULE.read_text(encoding="utf-8")
    assert "Unsupported document vector distance" in source
    assert "create_qdrant_document_collection" not in source
    assert "verify_qdrant_document_collection_ready" not in source
    assert "ensure_qdrant_document_collection_ready" not in source


def test_concrete_qdrant_distance_members_exist_only_in_the_mapper() -> None:
    leaked: list[str] = []
    for path in sorted(PRODUCTION_ROOT.rglob("*.py")):
        relative = path.relative_to(SRC_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        if relative == QDRANT_DOCUMENT_VECTOR_DISTANCE_MAPPER_RELATIVE:
            for fragment in DISTANCE_MEMBER_FRAGMENTS:
                assert fragment in source
            continue
        for fragment in DISTANCE_MEMBER_FRAGMENTS:
            if fragment in source:
                leaked.append(f"{relative} contains {fragment}")
    assert leaked == []


def test_collection_primitives_remain_unaware_of_configured_distance() -> None:
    for path in (CREATION_MODULE, READINESS_MODULE, ENSURE_MODULE):
        names = imported_names(path)
        modules = imported_modules(path)
        source = path.read_text(encoding="utf-8")
        assert "QdrantDocumentVectorDistance" not in names
        assert "map_qdrant_document_vector_distance" not in names
        assert "load_qdrant_document_vector_distance_settings" not in names
        assert "energy_trading.shared.config.qdrant" not in modules
        assert "energy_trading.api.composition.qdrant_document_vector_distance" not in modules
        assert "QDRANT_DOCUMENT_VECTOR_DISTANCE" not in source
        assert "map_qdrant_document_vector_distance" not in source


def test_configured_distance_and_mapper_remain_unwired_from_runtime() -> None:
    for path in UNWIRED_MODULES:
        names = imported_names(path)
        modules = imported_modules(path)
        source = path.read_text(encoding="utf-8")
        assert "QdrantDocumentVectorDistance" not in names
        assert "QdrantDocumentVectorDistanceSettings" not in names
        assert "map_qdrant_document_vector_distance" not in names
        assert "load_qdrant_document_vector_distance_settings" not in names
        assert "energy_trading.api.composition.qdrant_document_vector_distance" not in modules
        assert "map_qdrant_document_vector_distance" not in source
        assert "QDRANT_DOCUMENT_VECTOR_DISTANCE" not in source
