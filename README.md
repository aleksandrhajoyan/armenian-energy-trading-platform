# AI Energy Trading Platform (Armenian Day-Ahead Market)

Multi-agent decision-support system for participation in Armenia’s electricity Day-Ahead Market (DAM). The long-term design is a 13-agent workflow: regulatory and commercial constraints, parallel market-intelligence ingestion, ML-based load and price forecasts, portfolio risk, bid strategy, clearing, and settlement.

## Architectural philosophy

- **Clean Architecture.** Domain is innermost. Application depends on domain and owns ports. Infrastructure and `ml` are outer implementation layers wired by the API / composition root. Domain rules do not depend on frameworks, databases, or vendors.
- **Anti-Corruption Layer (ACL).** External data never reaches agents, ML models, or domain services directly. Infrastructure adapters normalize every source into canonical Pydantic contracts.
- **ML ≠ LLM.** Numerical forecasts are produced by ML components behind application ports. Language models reason over documents and news; they do not invent megawatts or prices. Agents never import concrete ML libraries.
- **Thin orchestration.** LangGraph (planned) routes work and owns retries/fallback. Nodes depend on application abstractions. Business formulas live in domain, application services, or ML — not in graph nodes.

## Technology direction

Python 3.12, uv, FastAPI, asyncio, Pydantic, LangGraph (planned), PostgreSQL/TimescaleDB, Qdrant, Redis, XGBoost, LightGBM, optional Prophet baseline, n8n/Python scrapers, Docker Compose. Development target: Windows 11 + WSL2 under tight local RAM/VRAM budgets.

Only the Python 3.12 / uv / FastAPI health slice, canonical domain contracts, and structured-ingestion application ports are installed and wired. Do not expect CSV/Excel adapters, databases, Docker, agents, or ML runtimes yet.

## Current status

**Phase 1 / Chunk 4.** The repository has a reproducible Python 3.12 project, typed application settings, a FastAPI application factory, `GET /api/v1/health`, canonical Pydantic domain contracts, transport-neutral application errors, a standard API error envelope, correlation IDs, structured JSON logging, and an application-facing structured ingestion boundary (`StructuredIngestionPort`, `StructuredIngestionResult`, `DeadLetterQueuePort`). There are no source adapters, no CSV/Excel/API parsers, no agents, no ML models, and no Docker stack.

See [`CURRENT_STATE.md`](CURRENT_STATE.md) and [`ROADMAP.md`](ROADMAP.md).

## Development bootstrap

Requires [uv](https://docs.astral.sh/uv/) on the PATH. The project pins CPython 3.12 via `.python-version`. uv will provision that interpreter; do not point the project at a machine-specific Python path.

```text
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Run the HTTP app (process health only):

```text
uv run uvicorn energy_trading.api.app:app --reload
```

Then `GET /api/v1/health`. A 200 response means this process is serving; it does not mean PostgreSQL, Redis, Qdrant, or models are available.

Copy [`.env.example`](.env.example) to `.env` locally if you want to override settings. `.env` is gitignored and is not required for startup.

## Documentation

| Document | Role |
| --- | --- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Architecture source of truth |
| [`AGENTS.md`](AGENTS.md) | 13-agent specifications |
| [`DATA_CONTRACTS.md`](DATA_CONTRACTS.md) | Canonical data contracts (implemented) |
| [`API_CONTRACTS.md`](API_CONTRACTS.md) | API contracts (`GET /api/v1/health` and the standard error envelope implemented) |
| [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md) | Test boundaries and quality toolchain |
| [`DECISIONS.md`](DECISIONS.md) | Architecture Decision Records |
| [`ROADMAP.md`](ROADMAP.md) | Implementation chunks |
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | What exists vs what does not |
| [`EXPERIMENT_LOG.md`](EXPERIMENT_LOG.md) | ML experiment notebook |
| [`PRESENTATION_NOTES.md`](PRESENTATION_NOTES.md) | Demo and presentation tracking |
| [`.cursorrules`](.cursorrules) | Mandatory implementation rules |

## Warning

This is not a working trading platform. Do not add Docker, databases, or ML stacks until their implementation chunks.
