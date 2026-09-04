# Current State

Living snapshot. Update at the end of every chunk. Do not list features that do not exist.

## Phase and chunk

- **Current phase:** Phase 0 — Foundation (complete)
- **Completed chunks:** Chunk 0 — Documentation and repository skeleton; Chunk 1 — Python Project Bootstrap, Dependency Management, Typed Configuration, and Minimal Application Health Check; Chunk 2 — Canonical Domain Contracts and Value Objects; Chunk 3 — Error Contracts, Diagnostics, and Observability Foundation
- **Next recommended chunk:** Chunk 4 — Adapter Ports and Structured Ingestion Boundary

## What this repository is

A reproducible Python 3.12 application skeleton with typed settings, a FastAPI factory, process health, canonical domain contracts, transport-neutral application errors, a standard API error envelope, correlation IDs, and structured JSON logging. It is **not** a running trading platform.

## What is not implemented

- Structured adapters
- Unstructured adapters
- Semantic schema mapping
- Time-series cleaning pipeline
- Runtime DLQ / DLQ persistence
- Business agents
- LangGraph
- ML implementations
- Databases (PostgreSQL / TimescaleDB)
- Redis
- Qdrant
- Docker
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
- Domain and application architecture dependency tests
- Initial automated quality/test toolchain: pytest, pytest-asyncio, HTTPX, Ruff, mypy

## Pending work

Everything from Chunk 4 onward in `ROADMAP.md`. Highest priority: adapter ports and the structured ingestion boundary (start of Phase 1 — Anti-Corruption Layer). Do not install LangGraph, databases, ML stacks, or Docker services until those chunks.

## Known issues

- Armenian DAM official products, gate times, bid envelope, currency, and settlement math are **unverified** and must not be hardcoded.
- Concrete external API providers are **not** selected.
- WSL2 RAM cap vs future Compose services is an operational risk (see `ARCHITECTURE.md`).

## Architectural constraints (in force)

- Clean Architecture: `domain` ← `application` ← `api` / composition root; `infrastructure` and `ml` implement application ports and use domain contracts
- Mandatory Anti-Corruption Layer
- Canonical Pydantic contracts (implemented)
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

None implemented. Thirteen agents are specified in `AGENTS.md` only. They will consume the implemented canonical contracts.

## Current ML models

None. No experiments have been run (`EXPERIMENT_LOG.md`).
