"""Application layer must not depend on API, infrastructure, ML, or HTTP frameworks."""

from .import_inspection import SRC_ROOT, collect_import_violations

APPLICATION_ROOT = SRC_ROOT / "energy_trading" / "application"

FORBIDDEN_PREFIXES = (
    "energy_trading.api",
    "energy_trading.infrastructure",
    "energy_trading.ml",
    "fastapi",
    "starlette",
)


def test_application_does_not_import_api_infrastructure_ml_or_http_frameworks() -> None:
    violations = collect_import_violations(APPLICATION_ROOT, FORBIDDEN_PREFIXES)
    assert violations == []
