# Architecture Decision Records

Log of significant decisions. Status values: **Proposed**, **Accepted**, **Superseded**. Decisions are reversible with a new ADR; none are claimed permanent.

---

## ADR-001 — Clean Architecture layering

- **Status:** Accepted
- **Context:** The platform will mix DAM business rules, ML, LLMs, scrapers, and several data stores. Without a dependency rule, vendor schemas and framework types will leak into forecasts and agents.
- **Decision:** Structure the codebase as `domain`, `application` (agents, use cases, ports, LangGraph), `ml`, `infrastructure`, and `api`. Domain is innermost and depends on nothing application- or infrastructure-specific. Application depends inward on domain and owns ports. Infrastructure and `ml` are outer implementation layers: both may depend on application ports and domain contracts. The API / composition root wires those implementations into application abstractions. Enforce with `.cursorrules` now and architecture tests later.
- **Consequences:** Extra ports/indirection for simple I/O. Independent evolution of adapters, ML runtimes, and market rules. Import direction becomes a CI concern. Chunk 1 clarified that `ml` is not a sibling of `application` that agents import directly.

---

## ADR-002 — Strict Anti-Corruption Layer / adapter boundary

- **Status:** Accepted
- **Context:** Armenian and vendor sources will arrive as CSV, Excel, PDF, HTML, APIs, scrapers, renamed columns, mixed units, and malformed timestamps. Direct consumption would couple agents and models to each file drop.
- **Decision:** External data never reaches agents, ML, or domain services directly. All inputs pass infrastructure adapters through schema mapping, validation, unit and timezone normalization, and time-series cleaning into canonical models. Unrecoverable rows go to a DLQ.
- **Consequences:** Ingestion work is front-loaded (Phase 1). Mapping tables must be maintained. DLQ operations become part of the product. Safer ML and agent layers.

---

## ADR-003 — Pydantic canonical contracts

- **Status:** Accepted
- **Context:** Layers need a single typed language for records, forecasts, bids, and diagnostics. Untyped dicts will reintroduce external schemas.
- **Decision:** Canonical contracts are Pydantic models owned by the domain. Agents consume and return those models. Implemented in Chunk 2; see `DATA_CONTRACTS.md`.
- **Consequences:** Validation cost at boundaries. Versioning of contracts must be deliberate. Alternative serializers (e.g. msgspec) remain possible later behind the same shapes.

---

## ADR-004 — PostgreSQL / TimescaleDB for relational and time-series data

- **Status:** Accepted (local/dev direction)
- **Context:** DAM workflows need interval time series (load, weather, prices, availability) plus relational entities (bids, settlements, DLQ metadata).
- **Decision:** Use PostgreSQL with TimescaleDB as the system of record for relational and time-series canonical data. Not for unstructured regulatory search.
- **Consequences:** Operational burden of a database. WSL2 8 GB RAM means the DB should be on-demand via Compose profiles, not always-on during documentation/ML-only work. Could be replaced by another SQL+TS store if operations demand it.

---

## ADR-005 — Qdrant for regulatory / document retrieval

- **Status:** Accepted (local/dev direction)
- **Context:** Regulatory PDFs need retrieval-augmented interpretation by the Regulatory Intelligence Agent without putting document search into Postgres primary tables.
- **Decision:** Qdrant holds embeddings and retrieval payloads for regulatory/document chunks. Authoritative structured `RegulatoryConstraint` rows still belong in PostgreSQL once extracted.
- **Consequences:** Second stateful service. Dual-write discipline between chunks and relational constraints. Another vector DB could substitute if operations require it.

---

## ADR-006 — Redis for ephemeral state and cache

- **Status:** Accepted (local/dev direction)
- **Context:** Orchestration, adapter caches, and short-lived locks should not overload TimescaleDB.
- **Decision:** Redis is the ephemeral state/cache layer. It is not the system of record for bids, settlements, or canonical time series.
- **Consequences:** Third service in Compose. Data loss on flush is acceptable for cache, not for financial records. Local RAM budget argues for optional start.

---

## ADR-007 — LangGraph for application orchestration

- **Status:** Accepted (planned; not implemented)
- **Context:** Thirteen agents and five business phases need explicit routing, parallel Phase 2 join, retries, fallback, and workflow status.
- **Decision:** LangGraph lives in the application layer. Nodes are thin. The Chief Orchestrator Agent owns graph state and policy. Conceptual flow: contract → parallel ingestion → ML forecasting → portfolio/risk → trading strategy → market-clearing input/result → settlement.
- **Consequences:** LangGraph versioning and debugging become skills for the team. Orchestration could later move to another graph/workflow library without changing domain contracts. Graph must not contain ML training or DAM arithmetic.

---

## ADR-008 — ML separate from LLM reasoning

- **Status:** Accepted
- **Context:** LLMs are unreliable for numerical load and price forecasts. Tree/boosting models (XGBoost, LightGBM, optional Prophet baseline) are the intended forecasters.
- **Decision:** `ml` is an outer implementation layer. It may depend on application port interfaces and canonical domain contracts, and must not depend on LLM agents or LangGraph. Consumer Load Forecast Agent and DAM Price Forecast Agent call forecasting services through dependency injection. Application agents must never import XGBoost, LightGBM, Prophet, concrete model classes, or other concrete ML implementations. LLMs may explain, not calculate, those numbers.
- **Consequences:** Two pipelines to operate. Feature engineering is first-class. Forbids “just ask the model for tomorrow’s AMD/MWh” as an implementation shortcut. Forbids agents importing `ml` packages directly; the composition root performs wiring. Clarified in Chunk 1 relative to the original “domain contracts only / beside application” wording.

---

## ADR-009 — Docker Compose for local development services

- **Status:** Accepted (planned; not implemented in Chunk 0)
- **Context:** PostgreSQL/TimescaleDB, Redis, and Qdrant should be reproducible on Windows 11 + WSL2 without snowflake installs. RAM is tight (WSL2 8 GB).
- **Decision:** Package supporting services with Docker Compose and **profiles** so unused containers stay down. Application code remains OS-agnostic. GPU LLM serving is not a default Compose service.
- **Consequences:** Docker Desktop/WSL2 memory interaction must be watched. Compose is a development (and later demo) tool, not a claim of production topology. Production orchestration is explicitly undecided.

---

## ADR-010 — Python 3.12 baseline

- **Status:** Accepted
- **Context:** The platform needs a conservative, well-supported interpreter for Windows 11 + WSL2 and a future ML stack (XGBoost, LightGBM, optional Prophet) without chasing the newest CPython while the architecture is still being built.
- **Decision:** Use Python 3.12 as the project baseline. Pin it with `.python-version` (`3.12`) and `requires-python = ">=3.12,<3.13"`. Developers provision the interpreter through uv. Do not record machine-specific absolute Python paths.
- **Consequences:** Python 3.13+ language features are unavailable until a later ADR. uv can install CPython 3.12 on machines that lack it. ML wheels targeting 3.12 are mature. Local and CI environments must use 3.12, not the newest interpreter on the machine.

---

## ADR-011 — uv for project and dependency management

- **Status:** Accepted
- **Context:** The repository needs reproducible installs on Windows and WSL without Poetry, Pipenv, Conda, or a hand-maintained `requirements.txt`.
- **Decision:** Use uv as the project dependency manager. Commit `uv.lock`. Create and use a local `.venv` that remains gitignored. Execute tools with `uv run` so activation of the virtual environment is not required. Do not add Poetry, Pipenv, Conda, or `requirements.txt` unless a future ADR changes this.
- **Consequences:** Contributors must have uv installed; the project does not silently install system software. Lockfile drift is detectable with `uv lock --check`. Dependency additions happen in explicit later chunks rather than opportunistic installs.

---

## ADR-012 — Canonical internal data semantics

- **Status:** Accepted
- **Context:** External Armenian and vendor sources will mix units, timezones, currencies, and file schemas. Agents and ML models need one internal language that does not silently guess missing source metadata.
- **Decision:** Internal canonical semantics are independent of external representation:
  - Timestamps are timezone-aware on input and normalized to **UTC** (`UtcDateTime`). Naive datetimes are rejected. Adapters resolve missing source timezones.
  - Power is **MW**. Energy is **MWh**. The two are not equated; DAM interval length is not assumed.
  - Money and energy prices use **`Decimal`** (`MoneyAmount`, `EnergyPrice`), not `float`.
  - Currency is an explicit ISO-style three-letter code. `AMD` is a valid value, not a hardcoded market default.
  - `DLQRecord` stores a `payload_reference` rather than the raw external payload so vendor schemas cannot leak past the ACL envelope.
- **Consequences:** Adapters must perform unit and timezone conversion before constructing domain models. JSON money should travel as Decimal-safe strings. Unverified DAM product, gate, and tariff rules remain outside these types.
