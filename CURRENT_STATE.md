# Current State

Living snapshot. Update at the end of every chunk. Do not list features that do not exist.

## Phase and chunk

- **Current phase:** Phase 1 — Anti-Corruption Layer
- **Completed chunks:** Chunk 0 — Documentation and repository skeleton; Chunk 1 — Python Project Bootstrap, Dependency Management, Typed Configuration, and Minimal Application Health Check; Chunk 2 — Canonical Domain Contracts and Value Objects; Chunk 3 — Error Contracts, Diagnostics, and Observability Foundation; Chunk 4 — Adapter Ports and Structured Ingestion Boundary; Chunk 5 — Semantic Schema Mapping and Field Resolution Engine; Chunk 6 — CSV Structured Ingestion Adapter; Chunk 7 — Excel Structured Ingestion Adapter
- **Next recommended chunk:** Time-series normalization (units, timezone, missing hours, duplicates)

## What this repository is

A reproducible Python 3.12 application skeleton with typed settings, a FastAPI factory, process health, canonical domain contracts, transport-neutral application errors, a standard API error envelope, correlation IDs, structured JSON logging, an application-facing structured ingestion boundary, a deterministic infrastructure-local schema field-resolution engine, a concrete Consumption CSV adapter, and a concrete Consumption Excel `.xlsx` adapter. It is **not** a running trading platform.

## What is not implemented

- REST/API adapters
- Other domain-specific structured adapters
- Legacy `.xls`
- Semantic/LLM mapping
- Unit conversion
- Source timezone inference
- Time-series cleaning
- DLQ persistence/runtime
- Unstructured document adapters
- Agents
- LangGraph
- Databases (PostgreSQL / TimescaleDB)
- Redis
- Qdrant
- Docker
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
- Shared Consumption field-profile and MW-safe fuzzy mapping policy
- Concrete `ConsumptionCsvAdapter` implementing `StructuredIngestionPort[ConsumptionRecord]`
- Stdlib CSV acquisition (`csv.reader`, UTF-8 including BOM) behind `asyncio.to_thread`
- Concrete `ConsumptionExcelAdapter` implementing `StructuredIngestionPort[ConsumptionRecord]`
- openpyxl `.xlsx` acquisition in read-only/data-only mode behind `asyncio.to_thread`
- Integration of Chunk 5 schema resolution with Consumption CSV and Excel headers
- Canonical `ConsumptionRecord` construction from MW-safe CSV and Excel rows
- Partial success plus canonical DLQ metadata (not persisted)
- ACL boundary architecture tests (no raw-source types on application ingestion ports)
- Schema-mapping architecture tests (no provider SDKs, file readers, or application/domain leakage)
- CSV adapter architecture tests (no pandas/Excel/HTTP/DB/LLM/ML imports)
- Excel adapter architecture tests (openpyxl allowed; no pandas/xlrd/HTTP/DB/LLM/ML imports)
- Domain and application architecture dependency tests
- Initial automated quality/test toolchain: pytest, pytest-asyncio, HTTPX, Ruff, mypy

## Pending work

Everything after Chunk 7 in `ROADMAP.md`. Highest priority: time-series normalization (units, timezone, missing hours, duplicates). Do not install LangGraph, databases, ML stacks, or Docker services until those chunks.

## Known issues

- Armenian DAM official products, gate times, bid envelope, currency, and settlement math are **unverified** and must not be hardcoded.
- Concrete external API providers are **not** selected.
- WSL2 RAM cap vs future Compose services is an operational risk (see `ARCHITECTURE.md`).

## Architectural constraints (in force)

- Clean Architecture: `domain` ← `application` ← `api` / composition root; `infrastructure` and `ml` implement application ports and use domain contracts
- Mandatory Anti-Corruption Layer
- Canonical Pydantic contracts (implemented)
- Application-facing structured ingestion receives canonical models only
- Raw external field names stay inside infrastructure schema mapping; they do not cross Chunk 4 application ports
- CSV and Excel values ingested as `value_mw` must already be MW; timestamps must already be timezone-aware
- UTC timestamps; MW vs MWh; Decimal money; explicit currency codes
- Application/domain exceptions contain no HTTP semantics; HTTP translation is API-only
- Unexpected exception details are never sent to clients
- Correlation IDs propagate through logs and error responses
- ML ≠ LLM for numerical forecasts; agents never import concrete ML implementations
- No secrets in git; `.env` must not be committed
- Avoid always-on heavy local services

## Current services

None.

## Current APIs

- `GET /api/v1/health` — process liveness only (`API_CONTRACTS.md`)
- Standard error envelope and `X-Correlation-ID` on API responses, including health and unknown routes

## Current agents

None implemented. Thirteen agents are specified in `AGENTS.md` only. They will consume the implemented canonical contracts through application ports; they must not parse raw source schemas.

## Current ML models

None. No experiments have been run (`EXPERIMENT_LOG.md`).
