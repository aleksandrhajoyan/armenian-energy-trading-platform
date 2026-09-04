# Testing Strategy

Tests protect the Anti-Corruption Layer, canonical contracts, dependency direction, and later ML quality.

Default rule: tests **must not** depend on live external APIs. Use `tests/fixtures/` and fakes/stubs behind ports.

## Current toolchain (Chunk 1)

All commands are run through uv so a separately activated virtualenv is not required:

| Tool | Role | Command |
| --- | --- | --- |
| pytest | Test runner | `uv run pytest` |
| pytest-asyncio | Async test support | enabled via `asyncio_mode = auto` |
| HTTPX | ASGI transport for API tests (no real TCP server) | used in `tests/unit/test_health.py` and `tests/unit/api/` |
| Ruff | Lint (pycodestyle, pyflakes, import order, bugbear, pyupgrade) and format | `uv run ruff check .` / `uv run ruff format --check .` |
| mypy | Strict typing of `src` | `uv run mypy src` |

Settings tests must not depend on a developer’s local `.env`. Construct `AppSettings` / `load_settings(env_file=None)` and call `clear_settings_cache()` between cases. Health and API tests inject settings through `create_app(settings=...)`.

Domain contract tests live in `tests/unit/domain/` and do not use FastAPI. They cover UTC timestamp normalization, frozen/extra-forbid behavior, MW/MWh constraints, Decimal money (including float rejection), generation/regulatory/bid/settlement/DLQ invariants, and JSON serialization.

Chunk 3 observability and error-boundary tests:

- Application error mapping (`tests/unit/api/test_error_mapping.py`): `InvalidRequestError`→400, `ResourceNotFoundError`→404, `ConflictError`→409, `DependencyUnavailableError`→503, plus unknown-route 404. Uses test-only routes, not production endpoints.
- Unmapped application errors fail closed: bare `ApplicationError` and an unregistered subclass both become sanitized HTTP 500 `internal_error`; original messages/codes are not exposed.
- Request validation sanitization: HTTP 422 `request_validation_error` envelope; correlation ID present; field details included; raw invalid `input` omitted.
- Unexpected exception sanitization: HTTP 500 `internal_error` with a generic public message; secret-looking runtime text, exception class, traceback, and module path are absent from the client body; internal structured logs retain the correlation ID and exception.
- Unexpected 500 request-completion observability: the same request emits one `http_request_completed` event with `status_code=500` and the same correlation ID as the sanitized 500 response, distinct from the internal exception log.
- Correlation propagation on `GET /api/v1/health`: valid `X-Correlation-ID` reused; missing ID generated; invalid ID replaced without rejecting the request.
- Correlation isolation: sequential requests keep independent IDs; concurrent async requests with distinct supplied IDs do not contaminate each other.
- Structured logger formatting (`tests/unit/observability/test_logging.py`): JSON records include UTC timestamp, level, logger, message, and correlation ID (or JSON `null` when unbound). Unknown extras are dropped.
- Idempotent logging setup: repeated `configure_logging` / `create_app` calls do not stack duplicate handlers and do not reconfigure pytest's root capture.
- Application-layer dependency enforcement (`tests/architecture/test_application_dependencies.py`): `energy_trading.application` must not import `energy_trading.api`, `infrastructure`, `ml`, FastAPI, or Starlette.

`tests/architecture/test_domain_dependencies.py` uses the standard library `ast` module to fail if `energy_trading.domain` imports `energy_trading.api`, `application`, `infrastructure`, `ml`, `shared`, or FastAPI. No extra architecture-testing dependency is used.

Infrastructure integration tests against PostgreSQL, Redis, or Qdrant are **not** run (those services are not implemented).

## Layout

| Directory | Intent |
| --- | --- |
| `tests/unit/` | Domain contracts/value objects, settings, health, application errors, API envelope, observability |
| `tests/integration/` | Real adapters against local files/containers when those exist |
| `tests/architecture/` | Import-graph / layering rules |
| `tests/fixtures/` | CSV/Excel/PDF snippets, malformed series, canonical JSON |

## Planned suites

### Domain unit tests

Implemented in Chunk 2 (`tests/unit/domain/`): value objects, UTC vs naive timestamps, unknown-field / frozen-model behavior, non-negative MW, positive bid quantity, NaN/Infinity rejection, currency format, Decimal money, generation available≤total, regulatory date/bound windows, settlement period and single-currency, DLQ non-empty diagnostics, Pydantic JSON serialization.

Later: MW vs MWh consistency when a verified interval exists; incomplete `RiskAssessment` completeness flags when that field is added.

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

`GET /api/v1/health` is covered with HTTPX ASGI transport. Error envelope, sanitized validation/500 responses, correlation header propagation, and correlation isolation (including a concurrent async case) are covered in Chunk 3. Routers must not contain business rules (behavior + architecture).

### ML validation / backtesting

Walk-forward or holdout on **versioned local datasets**. Metrics recorded in `EXPERIMENT_LOG.md`. Not a substitute for unit tests. No requirement to hit external weather/market APIs during CI.

### Architecture / dependency tests

Implemented for domain: fail if `src/energy_trading/domain/` imports `energy_trading.api`, `energy_trading.application`, `energy_trading.infrastructure`, `energy_trading.ml`, `energy_trading.shared`, or FastAPI.

Implemented for application (Chunk 3): fail if `src/energy_trading/application/` imports `energy_trading.api`, `energy_trading.infrastructure`, `energy_trading.ml`, FastAPI, or Starlette.

Still planned: fail if `ml` imports agents or orchestration; if agents import XGBoost, LightGBM, Prophet, or concrete model classes; if `api` contains domain formulas beyond mapping HTTP ↔ use cases.

## CI expectations (future)

- Unit + architecture tests on every change once a runner exists.
- Integration tests gated on optional services.
- No secret-bearing `.env` in CI; use `.env.example` values and fixtures.
