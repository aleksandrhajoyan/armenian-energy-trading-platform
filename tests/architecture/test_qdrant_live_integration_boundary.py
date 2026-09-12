"""Static inspection of the on-demand Qdrant Compose profile and live-test boundary."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    DOCUMENT_VECTOR_INDEX_INFRA_CLIENT_COMPOSITION_RELATIVES,
    DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
    DOCUMENT_VECTOR_INDEX_QDRANT_SETTINGS_COMPOSITION_RELATIVES,
    REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
    REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
    REGULATORY_QDRANT_SETTINGS_COMPOSITION_RELATIVES,
    SRC_ROOT,
    collect_import_violations,
    imported_names,
    is_document_vector_index_loaded_runtime_module,
    is_document_vector_index_managed_runtime_module,
    is_document_vector_index_provider_composition_module,
    is_document_vector_index_provider_runtime_module,
    is_regulatory_loaded_runtime_module,
    is_regulatory_managed_runtime_module,
    is_regulatory_provider_composition_module,
    is_regulatory_provider_runtime_module,
)

COMPOSE_FILE = SRC_ROOT.parent / "compose.yaml"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"
DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"
APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"
ML_ROOT = SRC_ROOT / "energy_trading" / "ml"
QDRANT_ROOT = SRC_ROOT / "energy_trading" / "infrastructure" / "vector_store" / "qdrant"
LIVE_TEST = (
    SRC_ROOT.parent
    / "tests"
    / "integration"
    / "infrastructure"
    / "vector_store"
    / "qdrant"
    / "test_qdrant_live.py"
)
LIVE_CONFTEST = LIVE_TEST.parent / "conftest.py"

PINNED_IMAGE = "qdrant/qdrant:v1.19.1"
APPROVED_SERVICES = ["timescaledb", "redis", "qdrant", "n8n"]
FORBIDDEN_INNER_QDRANT = (
    "qdrant_client",
    "energy_trading.infrastructure.vector_store.qdrant",
)
PRODUCTION_COLLECTION_FORBIDDEN = (
    "recreate_collection",
    "delete_collection",
    "update_collection",
    "Distance.DOT",
    "Distance.COSINE",
    "Distance.EUCLID",
    "Distance.MANHATTAN",
)
PRODUCTION_VECTOR_PARAMS_ALLOWED = frozenset({"collection_readiness.py", "collection_creation.py"})
PRODUCTION_DISTANCE_TYPE_ALLOWED = frozenset(
    {"collection_readiness.py", "collection_creation.py", "collection_ensure.py"}
)
PRODUCTION_CREATE_COLLECTION_ALLOWED = frozenset({"collection_creation.py"})
PRODUCTION_GET_COLLECTION_ALLOWED = frozenset({"collection_readiness.py"})
PRODUCTION_COLLECTION_EXISTS_ALLOWED = frozenset({"collection_ensure.py"})


def _compose_text() -> str:
    return COMPOSE_FILE.read_text(encoding="utf-8")


def _top_level_service_names(text: str) -> list[str]:
    names: list[str] = []
    in_services = False
    for line in text.splitlines():
        if line.startswith("services:"):
            in_services = True
            continue
        if not in_services:
            continue
        if (
            line
            and not line.startswith(" ")
            and not line.startswith("\t")
            and not line.startswith("#")
        ):
            break
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            name = line.strip()[:-1]
            if name and not name.startswith("#"):
                names.append(name)
    return names


def _service_block(text: str, service_name: str) -> str:
    names = _top_level_service_names(text)
    if service_name not in names:
        msg = f"service {service_name!r} not found"
        raise AssertionError(msg)
    start = text.index(f"\n  {service_name}:")
    following = names[names.index(service_name) + 1 :]
    if following:
        end = text.index(f"\n  {following[0]}:")
        return text[start:end]
    volumes_at = text.find("\nvolumes:", start)
    if volumes_at == -1:
        return text[start:]
    return text[start:volumes_at]


def _create_app_call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
    return call_names


def test_compose_file_exists() -> None:
    assert COMPOSE_FILE.is_file()


def test_pinned_qdrant_image_is_exact_patch_tag() -> None:
    text = _compose_text()
    qdrant_block = _service_block(text, "qdrant")
    assert PINNED_IMAGE in qdrant_block
    assert "qdrant/qdrant:latest" not in text
    assert "qdrant/qdrant:v1\n" not in text
    assert "qdrant/qdrant:v1.19\n" not in text
    assert "qdrant/qdrant:dev" not in text
    assert "qdrant/qdrant:gpu" not in text.lower()
    assert "unprivileged" not in qdrant_block.lower()


def test_qdrant_service_is_qdrant_profile_gated() -> None:
    qdrant_block = _service_block(_compose_text(), "qdrant")
    assert "profiles:" in qdrant_block
    assert "- qdrant" in qdrant_block
    assert "- postgres" not in qdrant_block
    assert "- redis" not in qdrant_block
    assert "- n8n" not in qdrant_block


def test_approved_compose_services_are_timescaledb_redis_qdrant_and_n8n() -> None:
    names = _top_level_service_names(_compose_text())
    assert names == APPROVED_SERVICES


def test_qdrant_rest_port_defaults_to_6333_and_is_loopback_only() -> None:
    qdrant_block = _service_block(_compose_text(), "qdrant")
    assert "host_ip: 127.0.0.1" in qdrant_block
    assert "0.0.0.0" not in qdrant_block
    assert "6333:6333" not in qdrant_block
    assert "target: 6333" in qdrant_block
    assert "${QDRANT_PORT:-6333}" in qdrant_block
    assert "${QDRANT_PORT:?" not in qdrant_block
    assert "target: 6334" not in qdrant_block
    assert "target: 6335" not in qdrant_block
    assert "6334" not in qdrant_block
    assert "6335" not in qdrant_block


def test_qdrant_api_key_is_required_and_not_hardcoded() -> None:
    qdrant_block = _service_block(_compose_text(), "qdrant")
    assert "QDRANT__SERVICE__API_KEY" in qdrant_block
    assert "${QDRANT_API_KEY:?" in qdrant_block
    assert "${QDRANT_PORT:-6333}" in qdrant_block
    assert "${QDRANT_PORT:?" not in qdrant_block
    assert "QDRANT__SERVICE__READ_ONLY_API_KEY" not in qdrant_block
    assert "change-me" not in qdrant_block


def test_qdrant_telemetry_is_disabled() -> None:
    qdrant_block = _service_block(_compose_text(), "qdrant")
    assert "QDRANT__TELEMETRY_DISABLED" in qdrant_block
    assert '"true"' in qdrant_block


def test_qdrant_named_volume_is_used_without_bind_mount() -> None:
    text = _compose_text()
    qdrant_block = _service_block(text, "qdrant")
    assert "qdrant-data:/qdrant/storage" in qdrant_block
    assert "type: bind" not in qdrant_block
    assert "./" not in qdrant_block
    volumes_block = text.split("\nvolumes:", 1)[-1]
    assert "qdrant-data:" in volumes_block
    assert "snapshots" not in qdrant_block.lower()


def test_qdrant_is_independently_profile_gated() -> None:
    text = _compose_text()
    timescaledb_block = _service_block(text, "timescaledb")
    redis_block = _service_block(text, "redis")
    qdrant_block = _service_block(text, "qdrant")
    assert "depends_on" not in timescaledb_block
    assert "depends_on" not in redis_block
    assert "depends_on" not in qdrant_block
    assert "- qdrant" not in timescaledb_block
    assert "- qdrant" not in redis_block
    assert "- postgres" not in qdrant_block
    assert "- redis" not in qdrant_block
    assert "- n8n" not in timescaledb_block
    assert "- n8n" not in redis_block
    assert "- n8n" not in qdrant_block


def test_compose_has_no_api_or_admin_services() -> None:
    text = _compose_text().lower()
    forbidden = (
        "fastapi",
        "uvicorn",
        "pgadmin",
        "grafana",
        "prometheus",
        "jupyter",
        "sentinel",
        "kubernetes",
        "helm",
    )
    for token in forbidden:
        assert token not in text


def _attribute_call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def test_production_qdrant_modules_do_not_provision_collections() -> None:
    for path in sorted(QDRANT_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        for fragment in PRODUCTION_COLLECTION_FORBIDDEN:
            assert fragment not in source
        if path.name not in PRODUCTION_VECTOR_PARAMS_ALLOWED:
            assert "VectorParams" not in source
        if path.name not in PRODUCTION_DISTANCE_TYPE_ALLOWED:
            assert "Distance" not in imported_names(path)
        call_names = _attribute_call_names(path)
        stripped = source.replace("create_qdrant_document_collection", "")
        if path.name in PRODUCTION_CREATE_COLLECTION_ALLOWED:
            assert "create_collection" in call_names
            assert "recreate_collection" not in call_names
            assert "delete_collection" not in call_names
            assert "update_collection" not in call_names
        else:
            assert "create_collection" not in call_names
            assert "create_collection" not in stripped
        if path.name in PRODUCTION_GET_COLLECTION_ALLOWED:
            assert "get_collection" in call_names
        else:
            assert "get_collection" not in call_names
        if path.name in PRODUCTION_COLLECTION_EXISTS_ALLOWED:
            assert "collection_exists" in call_names
            assert "VectorParams" not in source
            assert "create_collection" not in call_names
            assert "get_collection" not in call_names
        else:
            assert "collection_exists" not in call_names


def test_live_tests_own_ephemeral_collection_and_dot_metric() -> None:
    conftest = LIVE_CONFTEST.read_text(encoding="utf-8")
    live = LIVE_TEST.read_text(encoding="utf-8")
    assert "create_collection" in conftest
    assert "delete_collection" in conftest
    assert "VectorParams" in conftest
    assert "Distance.DOT" in conftest
    assert "size=TEST_VECTOR_SIZE" in conftest or "size=3" in conftest
    assert "TEST_VECTOR_SIZE = 3" in conftest
    assert "ENERGY_RUN_QDRANT_INTEGRATION" in conftest
    assert "create_qdrant_client" in conftest
    assert "QdrantDocumentVectorIndex" in live
    assert "QdrantDocumentVectorSearch" in live
    assert "create_collection" not in live
    assert "Distance.DOT" not in live


def test_inner_layers_remain_qdrant_free() -> None:
    assert collect_import_violations(DOMAIN_ROOT, FORBIDDEN_INNER_QDRANT) == []
    assert collect_import_violations(APPLICATION_ROOT, FORBIDDEN_INNER_QDRANT) == []
    assert (
        collect_import_violations(
            API_ROOT,
            ("qdrant_client",),
            exclude_relative_prefixes=(
                *REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
                *DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
            ),
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            ("energy_trading.infrastructure.vector_store.qdrant",),
            exclude_relative_prefixes=(
                *REGULATORY_INFRA_CLIENT_COMPOSITION_RELATIVES,
                *DOCUMENT_VECTOR_INDEX_INFRA_CLIENT_COMPOSITION_RELATIVES,
            ),
        )
        == []
    )
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_INNER_QDRANT) == []


def test_create_app_still_does_not_wire_qdrant() -> None:
    assert (
        collect_import_violations(
            API_ROOT,
            ("qdrant_client",),
            exclude_relative_prefixes=(
                *REGULATORY_PROVIDER_COMPOSITION_RELATIVES,
                *DOCUMENT_VECTOR_INDEX_PROVIDER_COMPOSITION_RELATIVES,
            ),
        )
        == []
    )
    assert (
        collect_import_violations(
            API_ROOT,
            (
                "energy_trading.infrastructure.vector_store",
                "energy_trading.infrastructure.vector_store.qdrant",
                "energy_trading.shared.config.qdrant",
            ),
            exclude_relative_prefixes=(
                *REGULATORY_QDRANT_SETTINGS_COMPOSITION_RELATIVES,
                *DOCUMENT_VECTOR_INDEX_QDRANT_SETTINGS_COMPOSITION_RELATIVES,
            ),
        )
        == []
    )
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        if is_document_vector_index_provider_composition_module(path):
            assert "AsyncQdrantClient" in names
            assert "QdrantDocumentVectorConfig" in names
            if is_document_vector_index_provider_runtime_module(path):
                assert "QdrantDocumentVectorIndex" in names
            else:
                assert "QdrantDocumentVectorIndex" not in names
            assert "QdrantDocumentVectorSearch" not in names
            assert "create_qdrant_client" not in names
            continue
        if is_regulatory_provider_composition_module(path):
            assert "AsyncQdrantClient" in names
            assert "QdrantDocumentVectorConfig" in names
            assert "QdrantDocumentVectorIndex" not in names
            assert "create_qdrant_client" not in names
            if is_regulatory_provider_runtime_module(path):
                assert "QdrantDocumentVectorSearch" in names
            else:
                assert "QdrantDocumentVectorSearch" not in names
            continue
        if is_regulatory_managed_runtime_module(path):
            assert "AsyncQdrantClient" not in names
            assert "QdrantDocumentVectorConfig" not in names
            assert "QdrantDocumentVectorIndex" not in names
            assert "QdrantDocumentVectorSearch" not in names
            assert "create_qdrant_client" in names
            continue
        if is_document_vector_index_managed_runtime_module(path):
            assert "AsyncQdrantClient" not in names
            assert "QdrantDocumentVectorConfig" not in names
            assert "QdrantDocumentVectorIndex" not in names
            assert "QdrantDocumentVectorSearch" not in names
            assert "create_qdrant_client" in names
            continue
        if is_document_vector_index_loaded_runtime_module(path):
            assert "AsyncQdrantClient" not in names
            assert "QdrantDocumentVectorConfig" not in names
            assert "QdrantDocumentVectorIndex" not in names
            assert "QdrantDocumentVectorSearch" not in names
            assert "create_qdrant_client" not in names
            continue
        if is_regulatory_loaded_runtime_module(path):
            assert "AsyncQdrantClient" not in names
            assert "QdrantDocumentVectorConfig" not in names
            assert "QdrantDocumentVectorIndex" not in names
            assert "QdrantDocumentVectorSearch" not in names
            assert "create_qdrant_client" not in names
            continue
        assert "AsyncQdrantClient" not in names
        assert "QdrantDocumentVectorIndex" not in names
        assert "QdrantDocumentVectorSearch" not in names
        assert "QdrantDocumentVectorConfig" not in names
        assert "create_qdrant_client" not in names
    call_names = _create_app_call_names(API_APP)
    assert "create_qdrant_client" not in call_names
    assert "AsyncQdrantClient" not in call_names
    assert "QdrantDocumentVectorIndex" not in call_names
    assert "QdrantDocumentVectorSearch" not in call_names
    lowered = API_APP.read_text(encoding="utf-8").lower()
    assert "qdrant" not in lowered
