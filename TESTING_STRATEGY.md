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

Chunk 4 structured-ingestion boundary tests:

- Structural Protocol implementation with a test-only `FakeConsumptionAdapter` (`tests/unit/application/`): the fake does not inherit an infrastructure base class; `async ingest()` returns `StructuredIngestionResult[ConsumptionRecord]`.
- Canonical success, partial success, complete normalization failure, and valid empty source. Partial success keeps the canonical record and isolates the failure as `DLQRecord.payload_reference`.
- Immutable batch collections: `StructuredIngestionResult` is a frozen dataclass; `records`, `diagnostics`, and `dlq_records` are tuples.
- No raw payload is embedded in the result envelope.
- Test-only in-memory `DeadLetterQueuePort` fake accepts canonical `DLQRecord` without Redis or other infrastructure.
- ACL/port architecture tests (`tests/architecture/test_structured_ingestion_boundary.py`): AST inspection of the ingestion-port modules for forbidden raw-source imports and annotations (`pandas`, `openpyxl`, `csv`, `requests`, `httpx`, `aiohttp`, BeautifulSoup, `bytes`, `bytearray`, `dict`, `Mapping`, `Any`, `DataFrame`). Application ports must not import `energy_trading.infrastructure`, `energy_trading.api`, `energy_trading.ml`, FastAPI, or Starlette.

`tests/architecture/test_domain_dependencies.py` uses the standard library `ast` module to fail if `energy_trading.domain` imports `energy_trading.api`, `application`, `infrastructure`, `ml`, `shared`, or FastAPI. No extra architecture-testing dependency is used.

Infrastructure integration tests against PostgreSQL, Redis, or Qdrant are **not** run (those services are not implemented).

## Layout

| Directory | Intent |
| --- | --- |
| `tests/unit/` | Domain contracts/value objects, settings, health, application errors, API envelope, observability, structured-ingestion ports |
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

Chunk 8 covers Consumption MW identity and explicit kW→MW (`1000 kW = 1 MW`, `12500 kW = 12.5 MW`) in `tests/unit/infrastructure/adapters/structured/normalization/`. Boolean measurements are rejected. Energy units (MWh/kWh) are not power and are not converted. Header/config mismatches fail closed. Later domains may add kWh→MWh, °F→°C, knots→m/s; unknown units still fail closed (DLQ), not guessed.

### Timezone tests

Chunk 8 covers explicit IANA localization (`zoneinfo` + `tzdata`) with `Europe/Berlin` DST fixtures: aware instants keep UTC; naive values fail without a configured zone; naive values with an explicit zone localize; ambiguous and nonexistent local clocks fail closed. No timezone is inferred, including no default `Asia/Yerevan`. Output remains timezone-aware canonical UTC.

### Missing-hour tests

Gaps in hourly (or whatever interval is later verified) series: cleaning policy vs DLQ must be explicit and tested.

### Duplicate-timestamp tests

Duplicate interval keys: reject or deterministically coalesce per documented rule; never average silently without a test that names that rule.

### DLQ tests

Unrecoverable records produce `DLQRecord` with stage, source, correlation ID, and payload ref. Workflow continues for siblings. No silent swallow.

Chunk 4 covers the application sink Protocol with an in-memory fake (`enqueue(DLQRecord)`). Persistence/runtime tests remain for a later chunk.

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

Implemented for the structured ingestion ACL boundary (Chunk 4): fail if application ingestion ports import raw-source libraries or annotate `ingest`/`enqueue` with `bytes`, `dict`, `Mapping`, `Any`, `DataFrame`, or similar escape hatches. Application ports may import canonical domain contracts. Infrastructure may later import application ports.

Chunk 6 Consumption CSV adapter tests (`tests/unit/infrastructure/adapters/structured/csv/`):

- tmp_path fixtures only; no live services. Stdlib CSV files, including UTF-8 Armenian identifiers and a test-only Armenian header alias.
- Exact canonical headers and the MW-safe `Consumption_MW` alias produce `ConsumptionRecord` values in source order with UTC timestamps and no DLQ.
- `Consumpton_MW` is accepted as fuzzy MW mapping with a warning whose `field_name` is canonical `value_mw`; the raw typo does not appear in outward diagnostics.
- Default profile rejects unit-ambiguous or energy-like headers (`Consumption_kW`, `Consumption_MWh`, `Consumption_MW_h`, and similar) as canonical MW (schema fail-closed unless `PowerUnit.KW` is explicit).
- Naive timestamps, negative/nonnumeric/NaN/Inf MW, and row-width mismatches isolate the bad row (diagnostic + DLQ) and keep siblings.
- Bare numeric timestamp strings (for example `1710000000`) fail closed and are not treated as Unix timestamps.
- Partial success, complete row-normalization failure, empty file, and header-only success.
- Fatal schema for missing required fields, header collisions, and forced ambiguity; unresolved extra columns warn and continue.
- Missing/unreadable files raise sanitized `DependencyUnavailableError` without the filesystem path. Malformed CSV and invalid UTF-8 are normalization failures with source-level DLQ metadata, not dependency errors.
- A unique raw bad cell value must not appear in diagnostics, DLQ metadata (except opaque source/row references), or serialized result fields.
- Architecture test (`tests/architecture/test_csv_adapter_boundary.py`): CSV adapter must not import pandas/Polars/openpyxl, HTTP clients, FastAPI, databases, LangChain/LangGraph/OpenAI, or ML libraries. Application ports still have no CSV/path/raw-row surface.

Chunk 7 Consumption Excel adapter tests (`tests/unit/infrastructure/adapters/structured/excel/`):

- Temporary `.xlsx` workbooks generated in `tmp_path`; no external Excel files and no live services.
- Exact canonical headers and the MW-safe `Consumption_MW` alias produce `ConsumptionRecord` values in worksheet order with UTC timestamps and no DLQ.
- `Consumpton_MW` is accepted as fuzzy MW mapping with a warning whose `field_name` is canonical `value_mw`; the raw typo does not appear in outward diagnostics.
- Default profile rejects unit-ambiguous or energy-like headers (`Consumption_kW`, `Consumption_MWh`, `Consumption_MW_h`, and similar) as canonical MW (schema fail-closed unless `PowerUnit.KW` is explicit).
- Timezone-aware ISO timestamp strings normalize to UTC. Excel typed naive datetime cells fail the row without timezone inference; sibling valid rows survive.
- Numeric timestamp cells (integers/floats such as Unix-like or Excel-serial numbers) and boolean `value_mw` cells fail closed and are not coerced; sibling valid rows survive.
- Negative/nonnumeric/NaN/Inf MW and missing required cells isolate the bad row (diagnostic + DLQ) and keep siblings.
- Partial success, empty worksheet, and header-only success.
- Fatal schema for missing required fields, header collisions, and forced ambiguity; unresolved extra columns warn and continue.
- Explicit `sheet_name` selects that worksheet. A missing configured worksheet is a sanitized source/schema failure with DLQ metadata, not a silent active-sheet fallback and not a leaked worksheet name.
- Missing/unreadable files raise sanitized `DependencyUnavailableError` without the filesystem path. Corrupt `.xlsx` bytes are normalization failures with source-level DLQ metadata, not dependency errors.
- A unique raw bad cell value must not appear in diagnostics, DLQ metadata (except opaque source/row references), or serialized result fields.
- Shared Consumption mapping tests (`tests/unit/infrastructure/adapters/structured/test_consumption_mapping.py`) prove CSV and Excel reuse the same MW-safety policy; existing CSV adapter tests remain the CSV regression suite.
- Architecture test (`tests/architecture/test_excel_adapter_boundary.py`): Excel adapter may import openpyxl and the shared mapping helper, but must not import pandas/Polars/xlrd, HTTP clients, FastAPI, databases, LangChain/LangGraph/OpenAI, or ML libraries. Application ports still have no Workbook/Worksheet/Cell/path surface.

Chunk 8 Consumption unit/timezone normalization tests:

- Primitive tests (`tests/unit/infrastructure/adapters/structured/normalization/`): MW identity; `1000 kW → 1 MW` and `12500 kW → 12.5 MW`; numeric strings; boolean rejection; deterministic repeated conversion; no energy-unit enum. Aware datetime/ISO strings keep the same UTC instant; naive values fail without a zone; naive datetime/text with explicit IANA localize correctly; bare numeric and date-only timestamps fail; invalid IANA names fail at configuration; Europe/Berlin ambiguous (`2026-10-25 02:30`) and nonexistent (`2026-03-29 02:30`) local clocks fail closed.
- CSV adapter additions: default constructor remains MW + no timezone (Chunk 6 regression). Explicit `PowerUnit.KW` converts `Consumption_kW` `12500 → 12.5 MW`. Default adapter still rejects `Consumption_kW`. `PowerUnit.KW` with an explicit MW header fails. Fuzzy `Consumpton_kW` with `PowerUnit.KW` is accepted with a warning and converted. Naive timestamps succeed only with explicit `source_timezone`. Aware `+04:00` is not overwritten by a configured fallback zone. DST-ambiguous/nonexistent rows fail in isolation; later valid rows survive. Unique raw timestamps/values/headers/zone names must not appear in diagnostics or DLQ metadata.
- Excel adapter additions: explicit kW numeric conversion; default kW rejection; MW/kW header-config mismatch; typed naive datetime + explicit IANA succeeds; typed naive datetime without timezone still fails; aware timestamp strings remain authoritative; numeric Excel timestamps still rejected; boolean MW/kW cells still rejected; ambiguous and nonexistent local datetimes fail; partial success and raw-source privacy are preserved. Existing Chunk 7 cases remain the Excel regression suite.
- Shared mapping tests cover KW-profile exact/fuzzy aliases and reject conflicting MW or energy-like headers.
- Architecture test (`tests/architecture/test_structured_normalization_boundary.py`): the normalization package must not import application/API/ML, pandas/openpyxl, HTTP clients, databases, or LLM/graph libraries. Application ports still expose no `PowerUnit`, `ZoneInfo`, timezone string, or normalization config.

Still planned: fail if `ml` imports agents or orchestration; if agents import XGBoost, LightGBM, Prophet, or concrete model classes; if `api` contains domain formulas beyond mapping HTTP ↔ use cases.

## CI expectations (future)

- Unit + architecture tests on every change once a runner exists.
- Integration tests gated on optional services.
- No secret-bearing `.env` in CI; use `.env.example` values and fixtures.
