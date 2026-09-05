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

Settings tests must not depend on a developer’s local `.env`. Construct `AppSettings` / `load_settings(env_file=None)` and `DatabaseSettings` / `load_database_settings(env_file=None)` and call `clear_settings_cache()` between cases. Health and API tests inject settings through `create_app(settings=...)`. Database settings tests also clear `ENERGY_DB_*` environment variables.

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

`tests/architecture/test_domain_dependencies.py` uses the standard library `ast` module to fail if `energy_trading.domain` imports `energy_trading.api`, `application`, `infrastructure`, `ml`, `shared`, FastAPI, SQLAlchemy, psycopg, or Alembic. No extra architecture-testing dependency is used.

Infrastructure integration tests against a running PostgreSQL process are **not** run by default. They require the Compose `postgres` profile and `ENERGY_RUN_POSTGRES_INTEGRATION=1`. Chunk 13 added offline PostgreSQL foundation tests that require no database service. Chunk 14 added offline Consumption table, migration, and repository tests that also require no database service. Redis and Qdrant still have no live tests.

## Layout

| Directory | Intent |
| --- | --- |
| `tests/unit/` | Domain contracts/value objects, settings, health, application errors, API envelope, observability, structured-ingestion ports, document-extraction ports, infrastructure adapters, filesystem DLQ persistence, PostgreSQL engine/Alembic foundation |
| `tests/integration/` | Opt-in live PostgreSQL/TimescaleDB tests (`postgres_integration`); other containers later |
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

Chunk 10 covers internal missing intervals on an explicit `IntervalGrid` only. Gaps are compact ranges, not expanded timestamp lists. Leading/trailing delivery-window completeness remains a later coverage-window policy.

### Duplicate-timestamp tests

Chunk 9 covers Consumption duplicate interval keys: every member of a `(consumer_id, canonical UTC timestamp)` group is rejected. There is no silent first/last/average winner. Tests name that fail-closed rule.

### DLQ tests

Unrecoverable records produce `DLQRecord` with stage, source, correlation ID, and payload ref. Workflow continues for siblings. No silent swallow.

Chunk 4 covers the application sink Protocol with an in-memory fake (`enqueue(DLQRecord)`). Chunk 11 covers the interim filesystem metadata implementation (`tests/unit/infrastructure/persistence/test_dlq.py`): one JSON artifact per canonical record; directory creation; round-trip into `DLQRecord`; canonical keys only; diagnostic and optional `correlation_id` survival; identical retry idempotency without a second file; same-ID/different-metadata `ConflictError` without overwrite; hashed filenames that cannot escape the configured root; sanitized `DependencyUnavailableError` for create/write/corrupt-file failures; and async `enqueue()` offload via `asyncio.to_thread`. Tests use `tmp_path` only. PostgreSQL integration tests and DLQ replay/list/delete tests remain later chunks.

### Agent tests

Each agent tested with port fakes. Assert canonical in/out. Especially: Consumer Load Forecast Agent and DAM Price Forecast Agent call forecasting **ports**, **not** an LLM port and **not** concrete ML libraries, for numeric outputs.

### LangGraph routing tests

When a graph exists: contract → parallel ingestion join → forecast → risk → strategy → clearing → settlement. Retry/fallback/degraded flags. Nodes stay thin (no business formulas in node bodies — architecture assertion as feasible). Nodes depend on application abstractions only.

### Infrastructure integration tests

Opt-in (marker) tests for PostgreSQL/TimescaleDB, Redis, Qdrant against Compose **when** those services exist. Not run by default. Real migration execution against TimescaleDB remains deferred until a runnable service/Compose profile exists. Still no live third-party market APIs.

### API tests

`GET /api/v1/health` is covered with HTTPX ASGI transport. Error envelope, sanitized validation/500 responses, correlation header propagation, and correlation isolation (including a concurrent async case) are covered in Chunk 3. Routers must not contain business rules (behavior + architecture).

### ML validation / backtesting

Walk-forward or holdout on **versioned local datasets**. Metrics recorded in `EXPERIMENT_LOG.md`. Not a substitute for unit tests. No requirement to hit external weather/market APIs during CI.

### Architecture / dependency tests

Implemented for domain: fail if `src/energy_trading/domain/` imports `energy_trading.api`, `energy_trading.application`, `energy_trading.infrastructure`, `energy_trading.ml`, `energy_trading.shared`, FastAPI, SQLAlchemy, psycopg, or Alembic.

Implemented for application (Chunk 3, extended in Chunk 13): fail if `src/energy_trading/application/` imports `energy_trading.api`, `energy_trading.infrastructure`, `energy_trading.ml`, FastAPI, Starlette, SQLAlchemy, psycopg, or Alembic.

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

Chunk 9 Consumption duplicate/interval validation tests:

- Primitive tests (`tests/unit/infrastructure/adapters/structured/time_series/`): `IntervalGrid` accepts positive 1-hour and 15-minute intervals; rejects zero/negative intervals and naive anchors; normalizes aware non-UTC anchors to UTC; remains frozen and equality-stable. Different timestamps for one consumer and the same timestamp for different consumers are valid. No grid means no cadence restriction. Exact and conflicting duplicates fail every group member. Canonically equivalent offsets collide. Nonadjacent and 3+ member groups are detected. Valid output keeps source order. Hourly on-grid timestamps succeed; 00:30 fails; pre-anchor timestamps use integer-microsecond modulo; `00:00` + `02:00` is not a missing-gap failure; out-of-order aligned timestamps stay unsorted; a duplicate that is also off-grid is classified as a duplicate only.
- CSV adapter additions: default ingest detects duplicates without an interval grid; conflicting MW values fail closed; different consumers at one instant survive; offset-equivalent aware strings collide; nonadjacent duplicates are removed; an explicit 1-hour UTC grid accepts aligned rows; 00:30 is isolated; a 2-hour gap is allowed; source order of `02:00, 00:00, 01:00` is preserved; kW and explicit timezone paths still work with structural validation; unique consumer/timestamp/value sentinels are absent from diagnostics and DLQ metadata.
- Excel adapter additions: duplicate canonical and typed-naive (explicit timezone) rows fail closed; conflicting duplicates fail; different consumers remain valid; offset-equivalent aware strings collide; explicit hourly grid accepts aligned typed rows; off-grid typed and aware timestamps are isolated; a 2-hour gap is allowed; out-of-order aligned rows keep source order; kW conversion and explicit timezone localization still work; naive timestamps without a configured zone still fail before interval classification; privacy sentinels stay out of outward metadata. Existing Chunk 7/8 cases remain the Excel regression suite.
- Architecture test (`tests/architecture/test_time_series_validation_boundary.py`): the time-series package must not import application/API/ML, pandas/openpyxl, HTTP clients, databases, or LLM/graph libraries. Application ports still expose no `IntervalGrid`, `timedelta` cadence config, duplicate policy, source positions, or `ConsumptionGap`.

Chunk 10 Consumption missing-interval / gap reporting tests:

- Primitive tests (`tests/unit/infrastructure/adapters/structured/time_series/test_gaps.py`): no grid means no gaps; consecutive hours have no gap; `00:00`+`02:00` is one missing interval; `00:00`+`05:00` is one compact gap of 4; two separated gaps stay two objects; 15-minute `00:00`+`00:45` has count 2; multiple consumers keep independent gaps; a complete sibling does not suppress another consumer's gap; a single record and an empty candidate tuple produce no gap; out-of-order candidates still detect the chronological gap while valid output stays in source order; `02:00`+`03:00` infers no leading/trailing coverage; pre-anchor `-03:00`/`-01:00` detects `-02:00`; equivalent offsets use canonical UTC only; a 10-day hourly span is one compact 239-count gap; gap objects are frozen and equality-stable; singular/plural diagnostic messages contain only the count.
- Structural interaction: duplicate rejection of `01:00` between valid `00:00` and `02:00` yields duplicate issues plus one canonical gap; an off-grid `00:30` between `00:00` and `02:00` yields an interval-misaligned issue plus a missing `01:00` gap; duplicate-over-interval precedence still holds and a lone survivor has no gap.
- CSV adapter additions: explicit hourly grid reports a gap diagnostic without DLQ; the same source without a grid reports no gap; a 4-interval span emits one diagnostic; multiple gaps emit multiple diagnostics; different consumers stay independent; duplicate-induced and off-grid-induced gaps keep row DLQ plus a separate gap diagnostic with no extra gap DLQ; out-of-order source order is preserved; kW/timezone paths still work; unique consumer/timestamp/value/anchor sentinels are absent from outward metadata; no synthetic `01:00` record appears.
- Excel adapter additions: corresponding typed/aware hourly gap, no-grid, compact multi-slot, per-consumer, duplicate-induced, off-grid-induced, out-of-order, timezone, kW, no-fake-DLQ, privacy, and no-synthetic-row cases. Existing Chunk 7–9 Excel tests remain the regression suite.
- Architecture test (`tests/architecture/test_time_series_gap_boundary.py`): gap types and coverage windows do not appear on application ingestion ports; the time-series package still has no application/API/ML/file-reader imports.

Chunk 11 filesystem DLQ persistence tests:

- Unit tests (`tests/unit/infrastructure/persistence/test_dlq.py`): `tmp_path` only; no database or broker. Enqueue creates one canonical JSON file; the persistence directory is created when absent; stored JSON round-trips to `DLQRecord`; persisted keys are canonical DLQ/diagnostic fields only; diagnostics and optional `correlation_id` survive; identical retry is idempotent and does not add a second file; same `record_id` with different metadata raises `ConflictError` without overwrite; an opaque/filename-unsafe `record_id` is stored under a SHA-256 filename inside the configured root; create/write/corrupt-file failures become sanitized `DependencyUnavailableError` with no root path, OS text, raw JSON, or secret sentinel; async `enqueue()` offloads blocking work through `asyncio.to_thread`.
- Architecture test (`tests/architecture/test_dlq_persistence_boundary.py`): application `DeadLetterQueuePort` still accepts one canonical `DLQRecord` and exposes no `Path`/raw-payload/database/HTTP/`Any` surface; `FilesystemDeadLetterQueue` may depend on application errors and domain contracts but must not import FastAPI, pandas/openpyxl, HTTP clients, databases, brokers, LangChain/LangGraph/OpenAI, ML libraries, or Consumption CSV/Excel adapters.
- These tests do not cover PostgreSQL DLQ storage, replay, listing, deletion, or payload-reference resolution.

Chunk 12 unstructured document extraction boundary tests:

- Unit tests (`tests/unit/application/ports/test_document_extraction.py`): valid frozen `ExtractedDocumentChunk`; identifier/text whitespace normalization; empty `document_id`/`chunk_id`/text rejected; negative ordinal rejected; `page_number` 0/negative rejected and `None` allowed; valid frozen `DocumentExtractionResult`; collection fields must be tuples; wrong chunk/diagnostic/DLQ types rejected; result/chunk `document_id` mismatch rejected; duplicate `chunk_id` rejected; empty chunks, partial success, and complete extraction failure remain representable; a test-only fake structurally satisfies async `DocumentExtractionPort.extract()` with no raw-document argument.
- Architecture test (`tests/architecture/test_document_extraction_boundary.py`): application extraction module imports none of infrastructure/API/ML, pathlib, pandas/openpyxl, PDF/OCR libraries, HTTP clients, databases, Redis, Qdrant, LangChain/LangGraph/OpenAI, or ML libraries. `extract()` accepts only `self`. DTOs have only normalized provenance fields and no embedding/vector/path/URL/raw-payload/metadata bag.
- Real PDF/OCR fixture and integration tests remain deferred until a concrete infrastructure adapter exists.

Chunk 13 async PostgreSQL/TimescaleDB persistence foundation tests:

- Database settings tests (`tests/unit/test_database_settings.py`): valid `DatabaseSettings`; default and explicit ports; invalid ports rejected; empty host/database/username rejected; positive pool size; zero/negative pool size rejected; non-negative max overflow; negative overflow rejected; positive timeout; zero/negative timeout rejected; sentinel password masked in `repr`/`str`; local `.env` does not contaminate explicit construction (`env_file=None` plus cleared `ENERGY_DB_*` vars). No database process.
- Engine/session factory tests (`tests/unit/infrastructure/persistence/postgres/test_engine.py`): `postgresql+psycopg` URL; host/port/database/user semantics; password retained internally and hidden in safe URL rendering; `AsyncEngine` returned without connecting; `pool_pre_ping` enabled; async session factory with `expire_on_commit=False`; no module-global engine. Engines are disposed in tests.
- Alembic offline/static tests (`tests/unit/infrastructure/persistence/postgres/test_alembic.py`): Alembic config loads; bootstrap revision `0001_bootstrap` remains the root and still creates no canonical business tables; TimescaleDB extension and `energy_trading` schema intent; bootstrap downgrade does not drop the TimescaleDB extension; no hardcoded credentials. Head is the later Consumption revision (see Chunk 14).
- Architecture tests (`tests/architecture/test_postgres_persistence_boundary.py`): domain/application/API do not import SQLAlchemy/psycopg/Alembic or postgres factories; `DatabaseSettings` does not import infrastructure/runtime DB libraries; postgres package does not import FastAPI/agents/ML/ingestion adapters/Redis/Qdrant; `create_app()` does not instantiate an engine.

Chunk 14 Consumption PostgreSQL persistence tests:

- Application port tests (`tests/unit/application/ports/test_consumption_repository.py`): a test-only fake structurally satisfies async `ConsumptionRepositoryPort.save_many`; exact signature; tuple of `ConsumptionRecord`; empty tuple is valid; port annotations expose no SQLAlchemy/session/database/raw-source types; fake can represent success and `ConflictError`.
- Core table metadata tests (`tests/unit/infrastructure/persistence/postgres/test_tables.py`): schema `energy_trading`; table `consumption_observations`; exact canonical columns; timezone-aware non-null timestamp; `DOUBLE PRECISION` MW; composite PK `(consumer_id, timestamp)`; non-negative/finite CHECK; no synthetic ID or provenance columns; no ORM class.
- Repository tests (`tests/unit/infrastructure/persistence/postgres/test_consumption_repository.py`): session-factory doubles only; no live PostgreSQL. Empty input opens no session; one/many records use one transaction; in-call exact duplicates coalesce; in-call differing identity conflicts before DB work; compiled insert uses `ON CONFLICT DO NOTHING` without `DO UPDATE`; exact persisted retry succeeds; differing stored MW is `ConflictError` with rollback; mixed new+conflict rolls back; persisted rows rebuild as `ConsumptionRecord`; corrupt storage fails closed; DBAPI and pool-timeout failures become sanitized `DependencyUnavailableError`; sentinel exception text is not exposed; repository does not create an engine and does not per-row commit.
- Alembic static tests (`tests/unit/infrastructure/persistence/postgres/test_alembic.py`): head is `0002_consumption`; down-revision is `0001_bootstrap`; Consumption hypertable on `timestamp` with compatible `create_hypertable` and no chunk interval; downgrade drops only the Consumption table without `CASCADE`/`DROP EXTENSION`/`DROP SCHEMA`; no credentials.
- Architecture tests (`tests/architecture/test_consumption_repository_boundary.py`): application port has no SQLAlchemy/session/raw-source surface; repository may use SQLAlchemy plus application errors and canonical Consumption; API remains unwired; filesystem DLQ is not PostgreSQL-backed; no generic `Repository`/`UnitOfWork`; no other canonical observation tables.

Chunk 15 PostgreSQL/TimescaleDB service profile and live persistence tests:

- Compose static tests (`tests/architecture/test_postgres_compose_profile.py`): `compose.yaml` exists; image is exactly `timescale/timescaledb:2.29.2-pg17`; no `latest`; service `timescaledb` is gated on profile `postgres`; port is loopback-bound; named volume `timescale-data` with no bind-mounted data directory; healthcheck uses `pg_isready` without a password; password interpolation required; no `POSTGRES_HOST_AUTH_METHOD=trust`; no FastAPI/Redis/Qdrant/n8n services; exactly one Compose service.
- Marker: `postgres_integration`. Opt-in: `ENERGY_RUN_POSTGRES_INTEGRATION=1`. Live modules skip cleanly when the flag is absent. Default `uv run pytest` does not require Docker.
- Live suite path: `tests/integration/persistence/postgres/`. No testcontainers, Docker SDK, or new Python dependencies. On Windows, Alembic and live tests use `WindowsSelectorEventLoopPolicy` because psycopg async cannot use ProactorEventLoop.
- Live migration tests: PostgreSQL server major version 17; TimescaleDB extension `2.29.2`; Alembic current `0002_consumption`; TimescaleDB extension and `energy_trading` schema exist; `consumption_observations` is a hypertable partitioned by `timestamp`; composite PK `(consumer_id, timestamp)`; non-negative/finite MW CHECK; controlled downgrade to `0001_bootstrap` then restore to head without dropping schema or extension.
- Live repository tests: real `save_many`; UTC instant round-trip from a non-UTC aware input; exact retry remains one row; differing same-identity value is `ConflictError` and preserves the original; mixed new+conflict batch rolls back the new row; concurrent exact retries both succeed with one physical row; concurrent conflicting writers yield one success, one `ConflictError`, one physical row; direct SQL negative MW is rejected by the database constraint.
- **Default pytest remains independent of services.** The integration suite requires an explicitly started local `postgres` profile. No live third-party APIs.

Still planned: fail if `ml` imports agents or orchestration; if agents import XGBoost, LightGBM, Prophet, or concrete model classes; if `api` contains domain formulas beyond mapping HTTP ↔ use cases.

## CI expectations (future)

- Unit + architecture tests on every change once a runner exists.
- Integration tests gated on optional services.
- No secret-bearing `.env` in CI; use `.env.example` values and fixtures.
