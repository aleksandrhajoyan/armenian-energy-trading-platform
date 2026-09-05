# Current State

Living snapshot. Update at the end of every chunk. Do not list features that do not exist.

## Phase and chunk

- **Current phase:** Phase 2 — Infrastructure
- **Completed chunks:** Chunk 0 — Documentation and repository skeleton; Chunk 1 — Python Project Bootstrap, Dependency Management, Typed Configuration, and Minimal Application Health Check; Chunk 2 — Canonical Domain Contracts and Value Objects; Chunk 3 — Error Contracts, Diagnostics, and Observability Foundation; Chunk 4 — Adapter Ports and Structured Ingestion Boundary; Chunk 5 — Semantic Schema Mapping and Field Resolution Engine; Chunk 6 — CSV Structured Ingestion Adapter; Chunk 7 — Excel Structured Ingestion Adapter; Chunk 8 — Deterministic Consumption Unit and Timezone Normalization; Chunk 9 — Duplicate Timestamp Policy and Interval Validation; Chunk 10 — Missing-Interval Detection and Gap Reporting; Chunk 11 — DLQ Persistence Boundary; Chunk 12 — Unstructured Document Extraction Boundary; Chunk 13 — Async PostgreSQL/TimescaleDB Persistence Foundation; Chunk 14 — Consumption PostgreSQL Persistence Slice; Chunk 15 — PostgreSQL/TimescaleDB Service Profile and Live Persistence Integration; Chunk 16 — Application Cache Port Boundary
- **Next recommended chunk:** Next Phase 2 slice to be selected after Chunk 16 publication; concrete Redis infrastructure remains pending.

## What this repository is

A reproducible Python 3.12 application skeleton with typed settings, a FastAPI factory, process health, canonical domain contracts, transport-neutral application errors, a standard API error envelope, correlation IDs, structured JSON logging, an application-facing structured ingestion boundary, a deterministic infrastructure-local schema field-resolution engine, a concrete Consumption CSV adapter, a concrete Consumption Excel `.xlsx` adapter, explicit Consumption MW/kW plus IANA timezone normalization, fail-closed Consumption duplicate detection, optional interval-grid alignment, per-consumer internal gap reporting, an unwired filesystem-backed DLQ metadata persistence adapter, an application-owned unstructured document extraction boundary with no concrete PDF/OCR adapter, an unwired async PostgreSQL/TimescaleDB persistence foundation, an unwired Consumption PostgreSQL repository, an on-demand Compose TimescaleDB profile with live migration/repository tests, and an application-owned vendor-neutral cache port with no concrete Redis implementation. It is **not** a running trading platform.

## What is not implemented

- REST/API adapters
- Other domain-specific structured adapters
- Legacy `.xls`
- Semantic/LLM mapping
- Unit normalization for domains/units beyond Consumption MW/kW
- Source timezone inference
- Leading/trailing delivery-window completeness
- Gap repair
- Interpolation / resampling
- Synthetic record generation
- Chronological sorting policy
- Cross-batch completeness
- Adapter-side cross-ingestion duplicate queries against PostgreSQL
- DLQ replay / listing / deletion
- Ingestion orchestration that enqueues `StructuredIngestionResult.dlq_records`
- Ingestion → `ConsumptionRepositoryPort` wiring
- Unstructured document adapters (PDF/OCR acquisition and parsing)
- Embedding / indexing / vector-store ports
- RAG / retrieval
- Agents
- LangGraph
- Running PostgreSQL / TimescaleDB service as an always-on process
- Canonical database tables other than Consumption observations
- Repositories other than Consumption
- API database wiring / readiness checks
- PostgreSQL DLQ
- Redis package, client, settings, Compose service, or running cache
- Qdrant
- FastAPI Docker image / remaining Compose services
- ML implementations
- External integrations
- OpenTelemetry / Sentry / Prometheus
- Authentication
- n8n

## Implemented artifacts

- Root living docs, `.cursorrules`, `.gitignore`, `.env.example`
- Python 3.12 project baseline (`.python-version`, `requires-python = ">=3.12,<3.13"`)
- uv dependency management with committed `uv.lock`
- Typed application settings (`AppSettings`)
- Typed PostgreSQL settings (`DatabaseSettings`) loaded separately from process health
- FastAPI application factory (`create_app`)
- `GET /api/v1/health` (process/application health only)
- Canonical Pydantic domain contracts (`energy_trading.domain.models`)
- Canonical UTC timestamp normalization (`UtcDateTime`)
- Typed MW / MWh constraints
- Decimal monetary and energy-price value objects (`MoneyAmount`, `EnergyPrice`)
- Regulatory, forecast, risk, trading, and settlement contracts
- Adapter diagnostics and DLQ metadata contract (`payload_reference` only)
- Transport-neutral application error hierarchy (`ApplicationError` and subclasses)
- Standardized API error envelope with centralized HTTP exception translation
- Sanitized validation errors (no raw `input`) and sanitized unexpected 500 handling
- Correlation ID middleware and `ContextVar` context
- Structured JSON logging and HTTP request completion logs
- Generic async structured-ingestion application port (`StructuredIngestionPort`)
- Immutable structured ingestion result (`StructuredIngestionResult`)
- Canonical diagnostics/DLQ metadata propagation on the ingestion envelope
- Application-owned DLQ sink port (`DeadLetterQueuePort`)
- Partial-success ingestion semantics (success, partial, complete normalization failure, valid empty source)
- Deterministic schema field resolution inside the infrastructure ACL (`DeterministicFieldResolver`)
- Unicode field-name normalization, exact alias matching, and stdlib fuzzy matching with confidence/ambiguity
- Schema-level missing-required-field and destination-collision reporting
- Shared Consumption field-profile and unit-safe fuzzy mapping policy (MW and kW profiles)
- Concrete `ConsumptionCsvAdapter` implementing `StructuredIngestionPort[ConsumptionRecord]`
- Stdlib CSV acquisition (`csv.reader`, UTF-8 including BOM) behind `asyncio.to_thread`
- Concrete `ConsumptionExcelAdapter` implementing `StructuredIngestionPort[ConsumptionRecord]`
- openpyxl `.xlsx` acquisition in read-only/data-only mode behind `asyncio.to_thread`
- Integration of Chunk 5 schema resolution with Consumption CSV and Excel headers
- Explicit Consumption MW/kW power normalization (`PowerUnit`) with deterministic kW→MW conversion
- Explicit IANA source-timezone normalization (`zoneinfo` + `tzdata`); aware timestamps keep their instant
- DST-ambiguous and nonexistent local clocks fail closed (no fold policy)
- Canonical `ConsumptionRecord` construction from CSV and Excel rows (canonical output remains MW + UTC)
- Fail-closed Consumption duplicate detection on `(consumer_id, canonical UTC timestamp)` **within one `ingest()` batch**
- Optional explicit interval-grid alignment (`IntervalGrid`); default is disabled
- Per-consumer internal gap detection on an explicit `IntervalGrid` cadence
- Compact contiguous gap reporting (`missing_count` plus first/last missing timestamps, infrastructure-only)
- CSV/XLSX sanitized gap diagnostics (`consumption_missing_interval_gap`) with no fabricated DLQ for missing source rows
- Partial success plus canonical DLQ metadata (adapters do not persist it)
- Filesystem-backed `FilesystemDeadLetterQueue` implementing `DeadLetterQueuePort` (canonical metadata JSON only; single-record idempotent enqueue by `record_id`)
- Application-owned unstructured document extraction port (`DocumentExtractionPort`)
- Immutable `ExtractedDocumentChunk` and `DocumentExtractionResult` application DTOs (normalized text only; no embeddings, paths, or raw bytes)
- SQLAlchemy 2 async engine/session factories (`create_postgres_engine`, `create_session_factory`) using psycopg 3
- Structured PostgreSQL URL construction (`postgresql+psycopg`) without logging credentials
- Alembic migration foundation (`alembic.ini`, `alembic/env.py`)
- Bootstrap migration: TimescaleDB extension + `energy_trading` schema
- Application-owned `ConsumptionRepositoryPort.save_many`
- SQLAlchemy Core table `energy_trading.consumption_observations` (canonical fields only)
- Alembic revision `0002_consumption`: table + Timescale hypertable on `timestamp` (no explicit chunk interval)
- Concrete async `PostgresConsumptionRepository` with `ON CONFLICT DO NOTHING`, persisted-row canonical verification, exact-retry idempotency, and same-identity conflict
- Persistence-level uniqueness across already stored Consumption identities (not adapter-side PostgreSQL queries)
- On-demand Compose `postgres` profile (`timescaledb` service, image `timescale/timescaledb:2.29.2-pg17`, loopback bind, named volume, `pg_isready`)
- Live Alembic upgrade to `0002_consumption` against the pinned TimescaleDB
- Live Consumption hypertable, repository, idempotency, conflict, atomicity, and concurrency tests (opt-in)
- ACL boundary architecture tests (no raw-source types on application ingestion ports)
- Schema-mapping architecture tests (no provider SDKs, file readers, or application/domain leakage)
- CSV adapter architecture tests (no pandas/Excel/HTTP/DB/LLM/ML imports)
- Excel adapter architecture tests (openpyxl allowed; no pandas/xlrd/HTTP/DB/LLM/ML imports)
- Structured normalization architecture tests (normalization package isolated from application/API/ML/file readers)
- Time-series validation architecture tests (no application/API/ML/file-reader leakage; ports have no interval-grid or gap-report surface)
- DLQ persistence architecture tests (application port has no filesystem/raw-payload surface; filesystem adapter has no CSV/Excel/HTTP/DB/LLM/ML imports)
- Document extraction architecture tests (application port has no Path/bytes/URL/OCR/PDF/Qdrant surface; `extract()` accepts only `self`)
- PostgreSQL persistence architecture tests (domain/application/API unwired; settings have no engine objects)
- Consumption repository architecture tests (port has no SQLAlchemy/session surface; repository is infrastructure-only)
- Compose TimescaleDB profile architecture tests
- Application-owned generic cache port (`CachePort[TValue]`: async get/set/delete, mandatory positive TTL)
- Cache-port architecture tests (no Redis types, dependency, Compose service, or API wiring)
- Domain and application architecture dependency tests
- Initial automated quality/test toolchain: pytest, pytest-asyncio, HTTPX, Ruff, mypy

## Pending work

Everything after Chunk 16 in `ROADMAP.md`. Highest priority remains pending concrete Redis infrastructure after Architect selection. Do not install LangGraph, Qdrant, ML stacks, or unrelated Docker services until those chunks.

## Known issues

- Armenian DAM official products, gate times, bid envelope, currency, and settlement math are **unverified** and must not be hardcoded.
- Concrete external API providers are **not** selected.
- WSL2 RAM cap vs future Compose services is an operational risk (see `ARCHITECTURE.md`).
- TimescaleDB is pinned to `timescale/timescaledb:2.29.2-pg17` for local development; it is on-demand, not always running.

## Architectural constraints (in force)

- Clean Architecture: `domain` ← `application` ← `api` / composition root; `infrastructure` and `ml` implement application ports and use domain contracts
- Mandatory Anti-Corruption Layer
- Canonical Pydantic contracts (implemented)
- Application-facing structured ingestion receives canonical models only
- Raw external field names stay inside infrastructure schema mapping; they do not cross Chunk 4 application ports
- Consumption CSV/Excel may convert explicitly configured kW to MW and localize naive timestamps with an explicit IANA zone; units and timezones are never inferred; canonical output remains MW + UTC
- Consumption duplicate groups fail closed inside one `ingest()` batch; interval cadence is validated only against an explicit adapter `IntervalGrid`
- Missing intervals are reported only inside an observed per-consumer span; they do not fabricate DLQ records or synthetic observations
- Filesystem DLQ persistence stores canonical `DLQRecord` metadata only, is not wired to adapters or `create_app()`, and does not replace PostgreSQL as the planned system of record
- Unstructured document extraction is an application port returning normalized text chunks; it is not a `RegulatoryConstraint` and has no concrete PDF/OCR adapter
- PostgreSQL/TimescaleDB persistence is an infrastructure factory plus the Consumption Core table/repository; Compose `postgres` profile is optional and on-demand; no global engine, no FastAPI wiring, no ingestion→repository wiring
- Consumption persistence identity is `(consumer_id, timestamp)`; exact retries are idempotent; differing values conflict; adapters still do not query PostgreSQL
- Cache is an application-owned `CachePort[TValue]` only; values are ephemeral and TTL-bound; no concrete Redis implementation, package, settings, service, or API/orchestration wiring
- UTC timestamps; MW vs MWh; Decimal money; explicit currency codes
- Application/domain exceptions contain no HTTP semantics; HTTP translation is API-only
- Unexpected exception details are never sent to clients
- Correlation IDs propagate through logs and error responses
- ML ≠ LLM for numerical forecasts; agents never import concrete ML implementations
- No secrets in git; `.env` must not be committed
- Avoid always-on heavy local services

## Current services

TimescaleDB is available on demand under the Compose `postgres` profile (`timescale/timescaledb:2.29.2-pg17`, loopback-only). It is not assumed to be running continuously. There is no running cache. Redis and Qdrant are not present.

## Current APIs

- `GET /api/v1/health` — process liveness only (`API_CONTRACTS.md`)
- Standard error envelope and `X-Correlation-ID` on API responses, including health and unknown routes

## Current agents

None implemented. Thirteen agents are specified in `AGENTS.md` only. They will consume the implemented canonical contracts through application ports; they must not parse raw source schemas.

## Current ML models

None. No experiments have been run (`EXPERIMENT_LOG.md`).
