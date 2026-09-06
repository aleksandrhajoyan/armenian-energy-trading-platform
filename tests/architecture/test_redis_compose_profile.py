"""Static inspection of the on-demand Redis Compose profile."""

from __future__ import annotations

from tests.architecture.import_inspection import SRC_ROOT

COMPOSE_FILE = SRC_ROOT.parent / "compose.yaml"
PINNED_IMAGE = "redis:8.2.9-alpine"
APPROVED_SERVICES = ["timescaledb", "redis"]


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


def test_compose_file_exists() -> None:
    assert COMPOSE_FILE.is_file()


def test_pinned_redis_image_is_exact_patch_tag() -> None:
    text = _compose_text()
    redis_block = _service_block(text, "redis")
    assert PINNED_IMAGE in redis_block
    assert "redis:latest" not in text
    assert "redis:8\n" not in text
    assert "redis:8-alpine" not in text
    assert "redis:8.2\n" not in text
    assert "redis:8.2-alpine" not in text
    assert "bitnami" not in text.lower()
    assert "redis-stack" not in text.lower()
    assert "redis-enterprise" not in text.lower()


def test_redis_service_is_redis_profile_gated() -> None:
    redis_block = _service_block(_compose_text(), "redis")
    assert "profiles:" in redis_block
    assert "- redis" in redis_block
    assert "- postgres" not in redis_block


def test_approved_compose_services_are_exactly_timescaledb_and_redis() -> None:
    names = _top_level_service_names(_compose_text())
    assert names == APPROVED_SERVICES


def test_redis_port_is_loopback_bound_with_interpolated_host_port() -> None:
    redis_block = _service_block(_compose_text(), "redis")
    assert "host_ip: 127.0.0.1" in redis_block
    assert "0.0.0.0" not in redis_block
    assert "6379:6379" not in redis_block
    assert "target: 6379" in redis_block
    assert "${REDIS_PORT:?" in redis_block


def test_redis_password_is_required_and_not_hardcoded() -> None:
    redis_block = _service_block(_compose_text(), "redis")
    assert "${REDIS_PASSWORD:?" in redis_block
    assert "requirepass" in redis_block
    assert "change-me" not in redis_block
    assert "REDIS_PASSWORD=" not in redis_block.replace("${REDIS_PASSWORD:?", "")


def test_healthcheck_uses_authenticated_redis_cli() -> None:
    redis_block = _service_block(_compose_text(), "redis")
    assert "healthcheck:" in redis_block
    health_block = redis_block.split("healthcheck:", 1)[1]
    assert "redis-cli" in health_block
    assert "PONG" in health_block
    assert "REDISCLI_AUTH" in redis_block
    assert "-a" not in health_block
    assert "REDIS_PASSWORD" not in health_block
    assert "${REDIS_PASSWORD" not in health_block


def test_redis_persistence_and_volume_are_disabled() -> None:
    redis_block = _service_block(_compose_text(), "redis")
    assert '--save ""' in redis_block
    assert "--appendonly no" in redis_block
    assert "volumes:" not in redis_block
    assert "/data" not in redis_block
    assert "type: bind" not in redis_block


def test_redis_and_timescaledb_are_independently_profile_gated() -> None:
    text = _compose_text()
    timescaledb_block = _service_block(text, "timescaledb")
    redis_block = _service_block(text, "redis")
    assert "depends_on" not in timescaledb_block
    assert "depends_on" not in redis_block
    assert "- postgres" in timescaledb_block
    assert "- redis" in redis_block
    assert "- redis" not in timescaledb_block
    assert "- postgres" not in redis_block


def test_compose_has_no_api_qdrant_cluster_or_admin_services() -> None:
    text = _compose_text().lower()
    forbidden = (
        "fastapi",
        "uvicorn",
        "qdrant",
        "n8n",
        "pgadmin",
        "grafana",
        "prometheus",
        "jupyter",
        "sentinel",
        "cluster",
        "redis-stack",
    )
    for token in forbidden:
        assert token not in text
