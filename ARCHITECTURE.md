# Architecture — AI Energy Trading Platform

This document is the architecture source of truth. Implementation chunks must not contradict it. Unverified Armenian market rules are marked as such and must not be hardcoded.

## System purpose

Support a market participant in Armenia’s electricity Day-Ahead Market (DAM) by:

- ingesting heterogeneous external data through an Anti-Corruption Layer
- applying regulatory and commercial constraints
- forecasting consumer load and DAM prices with ML
- assessing portfolio risk and forming bids
- recording clearing outcomes and settlement

The system is a decision-support and workflow platform. It is not a substitute for an official market-management system. Official DAM products, gate times, bid formats, currencies, and settlement rules remain **TBD until verified** against primary sources.

## Architectural goals

- Keep domain logic independent of vendors, frameworks, and file formats.
- Make every external schema explicit at the infrastructure boundary.
- Prefer small, reviewable chunks over premature platforms.
- Separate numerical forecasting (ML) from language reasoning (LLM).
- Remain operable on a constrained Windows 11 + WSL2 workstation.
- Fail safely: malformed external data goes to a Dead Letter Queue (DLQ), not into agents or models.

## Clean Architecture layers

| Layer | Package | Responsibility |
| --- | --- | --- |
| Domain | `src/energy_trading/domain` | Canonical models, value objects, domain services. No I/O, no frameworks. |
| Application | `src/energy_trading/application` | Use cases, agents, LangGraph orchestration, ports (interfaces). |
| ML | `src/energy_trading/ml` | Feature pipelines and forecast models. Outer implementation layer: implements application forecasting ports; uses canonical domain contracts. |
| Infrastructure | `src/energy_trading/infrastructure` | Adapters, persistence, cache, vector store, messaging, scrapers, file readers. |
| API | `src/energy_trading/api` | HTTP transport and composition root. Invokes use cases; wires implementations into ports. No business logic. |
| Shared | `src/energy_trading/shared` | Configuration and observability that must not become a dumping ground for domain rules. |

Agents belong to the application layer. LangGraph orchestration belongs to the application layer. Concrete database clients, API clients, scrapers, Redis, Qdrant, filesystem readers, Excel readers, and PDF readers belong to infrastructure. Concrete ML libraries and model classes belong to `ml`, not to agents.

## Dependency rule

```text
domain
  ↑
application
  ↑
api / composition root

infrastructure ──→ application ports + domain contracts
ml             ──→ application ports + domain contracts
```

- `domain` is the innermost layer. It depends on nothing application-specific or infrastructure-specific.
- `application` depends inward on `domain` and the narrow `shared` kernel (typed settings types, logging facades) — never on infrastructure or ML implementations.
- `application` owns interfaces/ports needed by use cases and agents.
- `infrastructure` implements application ports and may use domain contracts.
- `ml` is an outer implementation layer for forecasting/model execution. It may depend on application port interfaces and canonical domain contracts. It must not depend on LLM agents or LangGraph.
- Application agents must never import XGBoost, LightGBM, Prophet, concrete model classes, or other concrete ML implementations. ML-backed agents receive forecasting services through dependency injection.
- `api` / the application composition root wires concrete infrastructure and ML implementations into application abstractions. It may invoke use cases/orchestration and must not contain business logic.
- LangGraph nodes must depend on application abstractions, not concrete infrastructure or ML packages.
- `shared` must not accumulate domain rules, adapters, or agent logic.
- No domain or application module may import a concrete infrastructure adapter or a concrete ML implementation.
- LLMs must not perform numerical forecasting that belongs to ML models.

This rule will be enforced by architecture tests in a later chunk (`tests/architecture`).

## Initial folder tree

```text
.
├── .cursorrules
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── README.md
├── ARCHITECTURE.md
├── CURRENT_STATE.md
├── ROADMAP.md
├── EXPERIMENT_LOG.md
├── PRESENTATION_NOTES.md
├── DECISIONS.md
├── API_CONTRACTS.md
├── DATA_CONTRACTS.md
├── AGENTS.md
├── TESTING_STRATEGY.md
├── src/
│   └── energy_trading/
│       ├── domain/
│       │   ├── models/
│       │   ├── services/
│       │   └── value_objects/
│       ├── application/
│       │   ├── agents/
│       │   ├── orchestration/
│       │   ├── ports/
│       │   └── use_cases/
│       ├── ml/
│       │   ├── common/
│       │   ├── load_forecast/
│       │   └── price_forecast/
│       ├── infrastructure/
│       │   ├── adapters/
│       │   │   ├── structured/
│       │   │   ├── unstructured/
│       │   │   └── external_services/
│       │   ├── persistence/
│       │   ├── cache/
│       │   ├── vector_store/
│       │   └── messaging/
│       ├── api/
│       │   ├── app.py
│       │   ├── routers/
│       │   │   └── health.py
│       │   └── dependencies/
│       └── shared/
│           ├── config/
│           │   └── settings.py
│           └── observability/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── architecture/
│   └── fixtures/
├── scripts/
└── docs/
```

Python packaging is in place: `pyproject.toml`, `uv.lock`, `.python-version` (CPython 3.12), and `__init__.py` only in packages that currently contain code. Empty architectural directories still use `.gitkeep`.

## Anti-Corruption Layer

**Mandatory.** External data must NEVER reach internal application agents, ML models, or domain services directly.

All external inputs pass through infrastructure adapters. That includes APIs, CSV, Excel, PDFs, HTML, scraped data, renamed columns, Armenian headers, inconsistent units, and malformed timestamps.

Structured adapters normalize external data into canonical internal Pydantic contracts (see `DATA_CONTRACTS.md`). Application and domain code speak only those contracts.

## Canonical data contracts

Canonical contracts are Pydantic models owned by the domain layer (implemented in a later chunk). They are the only payloads agents, ML, and use cases may exchange.

Planned contracts (not yet implemented): `ConsumptionRecord`, `WeatherRecord`, `HydroRecord`, `GenerationAvailabilityRecord`, `MarketPriceRecord`, `NewsEvent`, `RegulatoryConstraint`, `LoadForecastPoint`, `PriceForecastPoint`, `RiskAssessment`, `MarketBid`, `MarketClearingResult`, `SettlementResult`, `AdapterDiagnostic`, `DLQRecord`.

Canonical power unit is **MW** unless a future verified business contract explicitly requires another representation. Energy, when needed, is **MWh** over an explicit interval. Timestamps must become timezone-aware canonical timestamps. Currency, DAM interval length, and market timezone interpretation of gate closure remain TBD until verified.

## Structured ingestion conceptual flow

```
External Source
  → Source Adapter
  → Schema Detection / Semantic Mapping
  → Validation
  → Unit Normalization
  → Timezone Normalization
  → Time-Series Cleaning
  → Canonical Model
  → Application / Agent / ML layer
```

This pipeline is documented, not implemented. Failures that cannot safely be normalized are sent to a DLQ rather than crashing the workflow.

## Unstructured / RAG conceptual flow

```
PDF / Document
  → Extraction / OCR Adapter
  → structured metadata / chunks
  → embedding / indexing
  → Qdrant
  → Regulatory Intelligence Agent retrieval
```

Document bytes, vendor OCR schemas, and raw chunk dictionaries stay inside infrastructure. The Regulatory Intelligence Agent receives canonical `RegulatoryConstraint` (and related retrieval DTOs defined later), never raw PDFs.

## DLQ conceptual behavior

- A record that fails validation, unit conversion, timezone normalization, or time-series cleaning after adapter retries is written as a `DLQRecord`.
- The workflow continues for remaining records.
- DLQ records retain source identity, stage, error, correlation/workflow ID, and a payload reference.
- Reprocessing is an explicit later operation. Silent drops are forbidden.
- Transport for the DLQ (outbox table, Redis stream, etc.) is an infrastructure decision; application code depends only on a port.

## ML / LLM separation

| Concern | Owner |
| --- | --- |
| Load forecast numbers | `ml/load_forecast` behind application ports, invoked by Consumer Load Forecast Agent |
| DAM price forecast numbers | `ml/price_forecast` behind application ports, invoked by DAM Price Forecast Agent |
| Regulatory interpretation, news sense-making | LLM-backed application agents |
| Bid quantities and prices | Deterministic application/domain services using ML outputs and constraints |
| Graph routing, retries, fallback | Chief Orchestrator Agent / LangGraph |

An LLM may summarize why a forecast looks unusual. It may not generate the forecast.

## LangGraph orchestration boundary

LangGraph is planned as the application-layer workflow engine. It is **not implemented**. Graph nodes must remain thin: they load canonical state, call an agent or use case, write canonical state, and record diagnostics. Nodes depend on application abstractions, not on concrete infrastructure or ML packages.

Conceptual graph:

```
Contract phase
  → parallel ingestion phase
  → ML forecasting phase
  → portfolio / risk
  → trading strategy
  → market-clearing input / result
  → settlement
```

The **Chief Orchestrator Agent** owns graph state, routing, retries, fallback behavior, diagnostics, and workflow status. It does not embed market formulas or ML training.

## 13-agent workflow

See `AGENTS.md` for full specifications. Names below are canonical and must not be aliased.

1. Regulatory Intelligence Agent
2. Pricing & Sales Agent
3. Weather & Renewable Forecast Agent
4. Hydro Resources Agent
5. Generation Availability Agent
6. News Intelligence Agent
7. Market Monitoring Agent
8. Consumer Load Forecast Agent
9. DAM Price Forecast Agent
10. Portfolio & Risk Agent
11. Trading Strategy Agent
12. Billing & Settlement Agent
13. Chief Orchestrator Agent

## Five business phases

These are business phases, not giant implementation units. Each will be split into reviewable engineering chunks (`ROADMAP.md`).

| Phase | Business intent | Primary agents |
| --- | --- | --- |
| 1. Contract & regulatory alignment | Eligible products, constraints, commercial terms | Regulatory Intelligence Agent, Pricing & Sales Agent |
| 2. Parallel market-intelligence ingestion | Situational picture for the delivery day | Weather & Renewable Forecast Agent, Hydro Resources Agent, Generation Availability Agent, News Intelligence Agent, Market Monitoring Agent (plus historical consumption via adapters) |
| 3. Forecasting | Consumer load and DAM price | Consumer Load Forecast Agent, DAM Price Forecast Agent |
| 4. Portfolio, risk & strategy | Limits, scenarios, bid construction | Portfolio & Risk Agent, Trading Strategy Agent |
| 5. Clearing, billing & settlement | Official results and financial outcome | Billing & Settlement Agent |

The Chief Orchestrator Agent spans all five phases.

## Parallel Phase 2 ingestion concept

Phase 2 agents have no inherent sequential dependency on each other. The orchestrator should run their ingestion/normalization work **in parallel**, then join on canonical outputs (and DLQ diagnostics) before forecasting. A failure in one source must not block unrelated sources; it must surface as diagnostics + DLQ, with fallback policy owned by the orchestrator.

## Storage responsibilities

| Store | Responsibility | Not for |
| --- | --- | --- |
| PostgreSQL / TimescaleDB | Relational records and time-series (canonical facts, forecasts, bids, settlements, DLQ/outbox) | Unstructured document search |
| Qdrant | Regulatory/document retrieval embeddings and payloads | Authoritative time-series or financial books |
| Redis | Ephemeral workflow state, cache, short-lived locks | System of record |

No store is running in this chunk.

## API boundary

FastAPI is the HTTP surface (`/api/v1`). The application factory `create_app` in `src/energy_trading/api/app.py` is the current composition root: it constructs a testable FastAPI app, registers versioned routers, and will later wire infrastructure and ML implementations into application ports. It must not contain business logic and must not initialize databases, caches, vector stores, ML models, agents, or LangGraph.

Implemented now: process/application health at `GET /api/v1/health`. That endpoint does not report infrastructure readiness. Remaining business endpoints are TBD (`API_CONTRACTS.md`). Routers translate HTTP ↔ canonical contracts and call application use cases. The API layer must not parse vendor CSV/Excel/PDF formats.

## Configuration and secrets

- Configuration through environment variables and a typed `AppSettings` layer (`pydantic-settings`). Only application-level fields exist today (name, environment, API prefix, log level). Database, Redis, Qdrant, ML, and LLM settings are reserved until those systems exist.
- No hardcoded business configuration in domain or agents.
- Secrets never in source control. `.env.example` is the committed template; `.env` is local-only.

## Error handling

- Typed application errors distinct from infrastructure transport errors.
- Never silently swallow exceptions.
- Ingestion: retry transient I/O; DLQ for unrecoverable normalization failures.
- Orchestration: retries and fallback at the graph, with diagnostics on workflow state.
- API: standard error envelope and correlation/workflow ID (see `API_CONTRACTS.md`).

## Observability

- Structured logging (JSON or equivalent). No operational `print()`.
- Correlation/workflow IDs propagate from API or scheduler through adapters, agents, and ML jobs.
- Adapter diagnostics (`AdapterDiagnostic`) are first-class, not log-only afterthoughts.
- Metrics/tracing exporters are optional later; local RAM budget argues against heavy always-on stacks.

## Testing boundaries

See `TESTING_STRATEGY.md`. Default tests use fixtures, not live external APIs. Architecture tests will lock the dependency rule.

## Runtime baseline (implemented)

- **Python 3.12** is the interpreter baseline (`.python-version`, `requires-python = ">=3.12,<3.13"`). Chosen as a mature, ML-stack-friendly release that remains practical on Windows 11 and WSL2.
- **uv** is the project and dependency manager. `uv.lock` is the source of truth for resolved versions. Local `.venv` is gitignored. Do not introduce `requirements.txt`, Poetry, Pipenv, or Conda files unless a future ADR changes this.
- Quality toolchain: pytest, pytest-asyncio, HTTPX (ASGI), Ruff, mypy. Commands run via `uv run` so a separately activated virtualenv is not required.

## Windows / WSL development constraints

| Constraint | Implication |
| --- | --- |
| 16 GB system RAM; WSL2 capped at 8 GB RAM and 8 processors | Do not run PostgreSQL, Redis, Qdrant, n8n, and Jupyter all the time. Compose profiles / on-demand services later. |
| NVIDIA RTX 5060 Laptop GPU, 8 GB VRAM | GPU is for optional local ML, not for always-resident LLM servers. |
| Windows 11 + WSL2 | Application code must not assume bash-only paths, `fork`, or Linux-only shells. Use pathlib and asyncio-friendly I/O. |

## Future Docker deployment approach

Docker Compose is the intended local/dev packaging for PostgreSQL/TimescaleDB, Redis, Qdrant, and later the API. It is **not** introduced in this chunk. Production topology, GPU passthrough, and WSL2 memory interaction with Docker Desktop are open deployment questions — see `DECISIONS.md`. Prefer profiles so unused services stay down.
