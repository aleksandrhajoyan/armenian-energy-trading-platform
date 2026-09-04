# Current State

Living snapshot. Update at the end of every chunk. Do not list features that do not exist.

## Phase and chunk

- **Current phase:** Phase 0 — Foundation
- **Completed chunks:** Chunk 0 — Documentation and repository skeleton; Chunk 1 — Python Project Bootstrap, Dependency Management, Typed Configuration, and Minimal Application Health Check; Chunk 2 — Canonical Domain Contracts and Value Objects
- **Next recommended chunk:** Chunk 3 — Error Contracts, Diagnostics, and Observability Foundation

## What this repository is

A reproducible Python 3.12 application skeleton with typed settings, a FastAPI factory, process health, and canonical domain contracts. It is **not** a running trading platform.

## What is not implemented

- Structured adapters
- Unstructured adapters
- Semantic mapping
- Time-series cleaning pipeline
- Runtime DLQ
- Business agents
- LangGraph
- ML implementations
- Databases (PostgreSQL / TimescaleDB)
- Redis
- Qdrant
- Docker
- External integrations
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
- Domain dependency architecture test
- Initial automated quality/test toolchain: pytest, pytest-asyncio, HTTPX, Ruff, mypy

## Pending work

Everything from Chunk 3 onward in `ROADMAP.md`. Highest priority: error contracts, diagnostics, and observability foundations. Do not install LangGraph, databases, ML stacks, or Docker services until those chunks.

## Known issues

- Armenian DAM official products, gate times, bid envelope, currency, and settlement math are **unverified** and must not be hardcoded.
- Concrete external API providers are **not** selected.
- WSL2 RAM cap vs future Compose services is an operational risk (see `ARCHITECTURE.md`).

## Architectural constraints (in force)

- Clean Architecture: `domain` ← `application` ← `api` / composition root; `infrastructure` and `ml` implement application ports and use domain contracts
- Mandatory Anti-Corruption Layer
- Canonical Pydantic contracts (implemented)
- UTC timestamps; MW vs MWh; Decimal money; explicit currency codes
- ML ≠ LLM for numerical forecasts; agents never import concrete ML implementations
- No secrets in git; `.env` must not be committed
- Avoid always-on heavy local services

## Current services

None.

## Current APIs

- `GET /api/v1/health` — process liveness only (`API_CONTRACTS.md`)

## Current agents

None implemented. Thirteen agents are specified in `AGENTS.md` only. They will consume the implemented canonical contracts.

## Current ML models

None. No experiments have been run (`EXPERIMENT_LOG.md`).
