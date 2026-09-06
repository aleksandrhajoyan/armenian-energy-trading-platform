"""Static inspection of the on-demand TimescaleDB Compose profile."""

from __future__ import annotations

from tests.architecture.import_inspection import SRC_ROOT

COMPOSE_FILE = SRC_ROOT.parent / "compose.yaml"
PINNED_IMAGE = "timescale/timescaledb:2.29.2-pg17"


def _compose_text() -> str:
    return COMPOSE_FILE.read_text(encoding="utf-8")


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


def test_compose_file_exists() -> None:
    assert COMPOSE_FILE.is_file()


def test_pinned_timescaledb_image_is_exact_release_tag() -> None:
    text = _compose_text()
    assert PINNED_IMAGE in text
    assert "latest" not in text
    assert "timescaledb-ha" not in text
    assert "bitnami" not in text.lower()


def test_timescaledb_service_is_postgres_profile_gated() -> None:
    text = _compose_text()
    names = _top_level_service_names(text)
    assert "timescaledb" in names
    timescaledb_block = _service_block(text, "timescaledb")
    assert "profiles:" in timescaledb_block
    assert "- postgres" in timescaledb_block
    assert "- redis" not in timescaledb_block
    assert "- qdrant" not in timescaledb_block


def test_database_port_is_loopback_bound() -> None:
    text = _compose_text()
    assert "127.0.0.1" in text
    assert "0.0.0.0" not in text
    assert "5432:5432" not in text
    assert "host_ip: 127.0.0.1" in text


def test_named_volume_is_used_without_bind_mount_data_dir() -> None:
    text = _compose_text()
    assert "timescale-data:" in text
    assert "/var/lib/postgresql/data" in text
    assert "./" not in text.split("volumes:", 1)[-1].split("timescale-data:", 1)[0]
    for forbidden in ("./pgdata", "./data", "./timescaledb-data", "type: bind"):
        assert forbidden not in text


def test_healthcheck_uses_pg_isready_without_password() -> None:
    timescaledb_block = _service_block(_compose_text(), "timescaledb")
    assert "healthcheck:" in timescaledb_block
    assert "pg_isready" in timescaledb_block
    assert "POSTGRES_PASSWORD" in timescaledb_block
    health_block = timescaledb_block.split("healthcheck:", 1)[1]
    assert "PASSWORD" not in health_block
    assert "ENERGY_DB_PASSWORD" not in health_block


def test_password_auth_required_and_not_hardcoded() -> None:
    text = _compose_text()
    assert "POSTGRES_HOST_AUTH_METHOD" not in text
    assert "trust" not in text.lower()
    assert "${ENERGY_DB_PASSWORD:?" in text
    assert "change-me" not in text


def test_compose_has_no_app_or_admin_services() -> None:
    text = _compose_text().lower()
    forbidden = (
        "fastapi",
        "uvicorn",
        "n8n",
        "pgadmin",
        "grafana",
        "prometheus",
        "jupyter",
    )
    for token in forbidden:
        assert token not in text
