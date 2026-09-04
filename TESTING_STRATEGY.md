# Testing Strategy

Tests protect the Anti-Corruption Layer, canonical contracts, dependency direction, and later ML quality.

Default rule: tests **must not** depend on live external APIs. Use `tests/fixtures/` and fakes/stubs behind ports.

## Current toolchain (Chunk 1)

All commands are run through uv so a separately activated virtualenv is not required:

| Tool | Role | Command |
| --- | --- | --- |
| pytest | Test runner | `uv run pytest` |
| pytest-asyncio | Async test support | enabled via `asyncio_mode = auto` |
| HTTPX | ASGI transport for API tests (no real TCP server) | used in `tests/unit/test_health.py` |
| Ruff | Lint (pycodestyle, pyflakes, import order, bugbear, pyupgrade) and format | `uv run ruff check .` / `uv run ruff format --check .` |
| mypy | Strict typing of `src` | `uv run mypy src` |

Settings tests must not depend on a developer’s local `.env`. Construct `AppSettings` / `load_settings(env_file=None)` and call `clear_settings_cache()` between cases. Health tests inject settings through `create_app(settings=...)`.

Infrastructure integration tests against PostgreSQL, Redis, or Qdrant are **not** run (those services are not implemented).

## Layout

| Directory | Intent |
| --- | --- |
| `tests/unit/` | Domain, mapping, agent (with fakes), ML unit (small fixtures); currently settings and health |
| `tests/integration/` | Real adapters against local files/containers when those exist |
| `tests/architecture/` | Import-graph / layering rules |
| `tests/fixtures/` | CSV/Excel/PDF snippets, malformed series, canonical JSON |

## Planned suites

### Domain unit tests

Value objects, invariants (MW vs MWh consistency when interval is known), refuse naive datetimes, incomplete `RiskAssessment` flags.

### Adapter normalization tests

Happy-path CSV/Excel/API-shaped fixtures → canonical models. Armenian headers and renamed columns map through semantic mapping, not through domain if-else on vendor names.

### Malformed-data tests

Truncated files, wrong types, empty sheets, HTML when CSV was expected. Expect validation errors and **DLQ**, not process crash.

### Unit-conversion tests

kW→MW, kWh→MWh, °F→°C, knots→m/s. Unknown units fail closed (DLQ), not guessed.

### Timezone tests

Naive timestamps, wrong offsets, `Asia/Yerevan` DST boundaries (when market TZ is confirmed). Output must be timezone-aware canonical timestamps.

### Missing-hour tests

Gaps in hourly (or whatever interval is later verified) series: cleaning policy vs DLQ must be explicit and tested.

### Duplicate-timestamp tests

Duplicate interval keys: reject or deterministically coalesce per documented rule; never average silently without a test that names that rule.

### DLQ tests

Unrecoverable records produce `DLQRecord` with stage, source, correlation ID, and payload ref. Workflow continues for siblings. No silent swallow.

### Agent tests

Each agent tested with port fakes. Assert canonical in/out. Especially: Consumer Load Forecast Agent and DAM Price Forecast Agent call forecasting **ports**, **not** an LLM port and **not** concrete ML libraries, for numeric outputs.

### LangGraph routing tests

When a graph exists: contract → parallel ingestion join → forecast → risk → strategy → clearing → settlement. Retry/fallback/degraded flags. Nodes stay thin (no business formulas in node bodies — architecture assertion as feasible). Nodes depend on application abstractions only.

### Infrastructure integration tests

Opt-in (marker) tests for PostgreSQL/TimescaleDB, Redis, Qdrant against Compose **when** those services exist. Not run by default in Chunk 0–1. Still no live third-party market APIs.

### API tests

`GET /api/v1/health` is covered with HTTPX ASGI transport. Later: error envelope, correlation header, routers do not contain business rules (behavior + optionally architecture).

### ML validation / backtesting

Walk-forward or holdout on **versioned local datasets**. Metrics recorded in `EXPERIMENT_LOG.md`. Not a substitute for unit tests. No requirement to hit external weather/market APIs during CI.

### Architecture / dependency tests

Fail the build if `domain` or `application` imports `energy_trading.infrastructure` concrete modules; if `application` imports `energy_trading.ml` concrete implementations; if `ml` imports agents or orchestration; if agents import XGBoost, LightGBM, Prophet, or concrete model classes; if `api` contains domain formulas beyond mapping HTTP ↔ use cases (heuristic + import checks).

## CI expectations (future)

- Unit + architecture tests on every change once a runner exists.
- Integration tests gated on optional services.
- No secret-bearing `.env` in CI; use `.env.example` values and fixtures.
