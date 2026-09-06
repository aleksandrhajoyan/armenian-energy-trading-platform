"""Static inspection of the on-demand n8n Compose profile and live-test boundary."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.architecture.import_inspection import (
    SRC_ROOT,
    collect_import_violations,
    imported_names,
)

COMPOSE_FILE = SRC_ROOT.parent / "compose.yaml"
PYPROJECT_FILE = SRC_ROOT.parent / "pyproject.toml"
API_ROOT = SRC_ROOT / "energy_trading" / "api"
API_APP = API_ROOT / "app.py"
DOMAIN_ROOT = SRC_ROOT / "energy_trading" / "domain"
APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"
ML_ROOT = SRC_ROOT / "energy_trading" / "ml"
INFRASTRUCTURE_ROOT = SRC_ROOT / "energy_trading" / "infrastructure"
SHARED_ROOT = SRC_ROOT / "energy_trading" / "shared"
REPO_ROOT = SRC_ROOT.parent

PINNED_IMAGE = "n8nio/n8n:2.37.10"
APPROVED_SERVICES = ["timescaledb", "redis", "qdrant", "n8n"]
FORBIDDEN_N8N_PACKAGES = (
    "n8n",
    "n8n_python",
    "n8n_client",
    "pyn8n",
    "n8n_sdk",
)
PRODUCTION_WORKFLOW_DIRS = ("n8n", "workflows")


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


def test_pinned_n8n_image_is_exact_patch_tag() -> None:
    n8n_block = _service_block(_compose_text(), "n8n")
    assert PINNED_IMAGE in n8n_block
    assert "n8nio/n8n:latest" not in n8n_block
    assert "n8nio/n8n:stable" not in n8n_block
    assert "n8nio/n8n:2\n" not in n8n_block
    assert "n8nio/n8n:2.37\n" not in n8n_block
    assert "n8nio/n8n:nightly" not in n8n_block
    assert "n8nio/n8n:beta" not in n8n_block


def test_n8n_service_is_n8n_profile_gated() -> None:
    n8n_block = _service_block(_compose_text(), "n8n")
    assert "profiles:" in n8n_block
    assert "- n8n" in n8n_block
    assert "- postgres" not in n8n_block
    assert "- redis" not in n8n_block
    assert "- qdrant" not in n8n_block


def test_approved_compose_services_are_timescaledb_redis_qdrant_and_n8n() -> None:
    names = _top_level_service_names(_compose_text())
    assert names == APPROVED_SERVICES


def test_n8n_host_port_defaults_to_5678_and_is_loopback_only() -> None:
    n8n_block = _service_block(_compose_text(), "n8n")
    assert "host_ip: 127.0.0.1" in n8n_block
    assert "0.0.0.0" not in n8n_block
    assert "5678:5678" not in n8n_block
    assert "target: 5678" in n8n_block
    assert "${N8N_HOST_PORT:-5678}" in n8n_block
    assert "${N8N_HOST_PORT:?" not in n8n_block
    assert "${N8N_PORT:-" not in n8n_block
    assert "${N8N_PORT:?" not in n8n_block
    assert n8n_block.count("target:") == 1


def test_container_n8n_port_remains_5678() -> None:
    n8n_block = _service_block(_compose_text(), "n8n")
    assert 'N8N_PORT: "5678"' in n8n_block
    assert "N8N_PORT: ${N8N_HOST_PORT" not in n8n_block
    assert "target: 5678" in n8n_block


def test_n8n_encryption_key_is_required_and_not_hardcoded() -> None:
    n8n_block = _service_block(_compose_text(), "n8n")
    assert "${N8N_ENCRYPTION_KEY:?" in n8n_block
    assert "${N8N_ENCRYPTION_KEY:-" not in n8n_block
    assert "change-me" not in n8n_block
    assert "N8N_ENCRYPTION_KEY=" not in n8n_block.replace("${N8N_ENCRYPTION_KEY:?", "")


def test_n8n_local_telemetry_and_templates_are_disabled() -> None:
    n8n_block = _service_block(_compose_text(), "n8n")
    assert 'N8N_DIAGNOSTICS_ENABLED: "false"' in n8n_block
    assert 'N8N_VERSION_NOTIFICATIONS_ENABLED: "false"' in n8n_block
    assert 'N8N_TEMPLATES_ENABLED: "false"' in n8n_block
    assert 'N8N_PERSONALIZATION_ENABLED: "false"' in n8n_block


def test_n8n_named_volume_is_used_without_bind_mount() -> None:
    text = _compose_text()
    n8n_block = _service_block(text, "n8n")
    assert "n8n-data:/home/node/.n8n" in n8n_block
    assert "timescale-data" not in n8n_block
    assert "qdrant-data" not in n8n_block
    assert "type: bind" not in n8n_block
    assert "./" not in n8n_block
    volumes_block = text.split("\nvolumes:", 1)[-1]
    assert "n8n-data:" in volumes_block


def test_n8n_is_independently_profile_gated() -> None:
    text = _compose_text()
    timescaledb_block = _service_block(text, "timescaledb")
    redis_block = _service_block(text, "redis")
    qdrant_block = _service_block(text, "qdrant")
    n8n_block = _service_block(text, "n8n")
    assert "depends_on" not in timescaledb_block
    assert "depends_on" not in redis_block
    assert "depends_on" not in qdrant_block
    assert "depends_on" not in n8n_block
    assert "- n8n" not in timescaledb_block
    assert "- n8n" not in redis_block
    assert "- n8n" not in qdrant_block
    assert "- postgres" not in n8n_block
    assert "- redis" not in n8n_block
    assert "- qdrant" not in n8n_block
    assert "timescaledb" not in n8n_block
    assert "qdrant" not in n8n_block


def test_production_python_does_not_import_n8n_sdk() -> None:
    for root in (
        DOMAIN_ROOT,
        APPLICATION_ROOT,
        API_ROOT,
        INFRASTRUCTURE_ROOT,
        SHARED_ROOT,
    ):
        assert collect_import_violations(root, FORBIDDEN_N8N_PACKAGES) == []
    if ML_ROOT.exists():
        assert collect_import_violations(ML_ROOT, FORBIDDEN_N8N_PACKAGES) == []
    pyproject = PYPROJECT_FILE.read_text(encoding="utf-8")
    assert "n8n" not in pyproject.split("[tool.pytest.ini_options]", 1)[0]


def test_create_app_does_not_wire_n8n() -> None:
    assert collect_import_violations(API_ROOT, FORBIDDEN_N8N_PACKAGES) == []
    for path in sorted(API_ROOT.rglob("*.py")):
        names = imported_names(path)
        assert "n8n" not in names
        assert "N8nSettings" not in names
        assert "load_n8n_settings" not in names
    call_names = _create_app_call_names(API_APP)
    assert "n8n" not in call_names
    lowered = API_APP.read_text(encoding="utf-8").lower()
    assert "n8n" not in lowered


def test_no_production_n8n_workflow_artifacts() -> None:
    for directory_name in PRODUCTION_WORKFLOW_DIRS:
        assert not (REPO_ROOT / directory_name).exists()
    src_n8n = SRC_ROOT / "energy_trading" / "n8n"
    assert not src_n8n.exists()
