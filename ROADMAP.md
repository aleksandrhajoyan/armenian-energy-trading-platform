# Implementation Roadmap

Small, reviewable chunks. High-level **phases are not implementation units** — each phase is split into the chunks below (and further chunks if a slice does not fit a single review).

Checkbox legend: `[x]` done · `[ ]` not started.

---

## Phase 0 — Foundation

- [x] **Chunk 0** — Documentation and repository skeleton (this chunk)
- [x] **Chunk 1** — Python Project Bootstrap, Dependency Management, Typed Configuration, and Minimal Application Health Check
- [x] **Chunk 2** — Canonical Domain Contracts and Value Objects
- [x] **Chunk 3** — Error Contracts, Diagnostics, and Observability Foundation

## Phase 1 — Anti-Corruption Layer

Split into reviewable chunks; do not implement as one drop.

- [x] **Chunk 4** — Adapter Ports and Structured Ingestion Boundary
- [x] **Chunk 5** — Semantic Schema Mapping and Field Resolution Engine
- [x] **Chunk 6** — CSV Structured Ingestion Adapter
- [x] **Chunk 7** — Excel Structured Ingestion Adapter
- [x] **Chunk 8** — Deterministic Consumption Unit and Timezone Normalization
- [x] **Chunk 9** — Duplicate Timestamp Policy and Interval Validation
- [x] **Chunk 10** — Missing-Interval Detection and Gap Reporting
- [x] **Chunk 11** — DLQ Persistence Boundary
- [x] **Chunk 12** — Unstructured Document Extraction Boundary

## Phase 2 — Infrastructure

Split into reviewable chunks. Start services only when a chunk needs them (RAM budget).

- [x] **Chunk 13** — Async PostgreSQL/TimescaleDB Persistence Foundation
- [x] **Chunk 14** — Consumption PostgreSQL Persistence Slice
- [x] **Chunk 15** — PostgreSQL/TimescaleDB Service Profile and Live Persistence Integration
- [x] **Chunk 16** — Application Cache Port Boundary (Redis-free)
- [x] **Chunk 17** — Async Redis Cache Infrastructure (Offline)
- [x] **Chunk 18** — Redis Service Profile and Live Cache Integration
- [x] **Chunk 19** — Application Document Embedding Port Boundary
- [x] **Chunk 20** — Application Document Vector Indexing Boundary
- [x] **Chunk 21** — Application Document Vector Retrieval Boundary
- [x] **Chunk 22** — Async Qdrant Client Foundation (Offline)
- [x] Chunk 23 — Qdrant Document Vector Index/Search Adapter (Offline)
- [x] Chunk 24 — Qdrant Service Profile and Live Vector Integration
- [x] **Chunk 25** — n8n Local Service Foundation and Live Readiness

The currently justified local service foundations are complete: TimescaleDB/PostgreSQL, Redis, Qdrant, and n8n. Do not mark any ingestion workflow or agent complete.

## Phase 3 — Application orchestration foundation

- [x] **Chunk 26** — Application Agent Execution Contract Boundary
- [x] **Chunk 27** — Application Orchestration State Contract — LangGraph-free
- [x] **Chunk 28** — Minimal LangGraph Skeleton
- [x] **Chunk 29** — Retries / fallback policy hooks (policy hook only; concrete execution/rules remain later workflow work)

Phase 3 foundation is complete at the roadmap/contract level. That checkbox is not retry execution.

## Phase 4 — Ingestion agents

- [ ] Weather & Renewable Forecast Agent
  - [x] **Chunk 30** — Weather & Renewable Forecast Agent Application Boundary and First Concrete Agent
- [ ] Hydro Resources Agent
  - [x] **Chunk 31** — Hydro Resources Agent Application Boundary and First Concrete Hydro Agent
- [ ] Generation Availability Agent
  - [x] **Chunk 32** — Generation Availability Agent Application Boundary and First Concrete Generation Agent
- [ ] News Intelligence Agent
  - [x] **Chunk 33** — News Intelligence Agent Application Boundary and First Concrete News Agent
- [ ] Market Monitoring Agent
  - [x] **Chunk 34** — Market Monitoring Agent Application Boundary and First Concrete Market Agent
- [ ] Parallel Phase 2 join in the orchestrator
  - [x] **Chunk 35** — Parallel Ingestion Fan-Out Plan Contract — LangGraph-free
  - [x] **Chunk 36** — Parallel Ingestion Successful Fan-In Contract — LangGraph-free
  - [x] **Chunk 37** — Parallel Ingestion Execution Boundary — LangGraph-free
  - [x] **Chunk 38** — Concurrent Parallel Ingestion Executor — All-Success Path, LangGraph-free
  - [x] **Chunk 39** — Parallel Ingestion Workflow Context Boundary — LangGraph-free
  - [x] **Chunk 40** — Parallel Ingestion Workflow Step — Framework-neutral
  - [x] **Chunk 41** — LangGraph Phase 2 Workflow-Step Invocation — all-success path
  - [x] **Chunk 42** — Parallel Ingestion Success Phase Transition — LangGraph-free
  - [x] **Chunk 43** — LangGraph Phase 2 Success Transition Wiring
  - [x] **Chunk 44** — In-Memory Parallel Ingestion Workflow Context Adapter — Local/Dev Reference
  - [x] **Chunk 45** — Parallel Ingestion Terminal Failure Transition — LangGraph-free
  - [x] **Chunk 46** — Parallel Ingestion Failure-Policy Decision Boundary — Application-only
  - [x] **Chunk 47** — Parallel Ingestion Failure-Policy Context Construction — Application-only
  - [x] **Chunk 48** — Parallel Ingestion Terminal FAIL Action Execution — Application-only
  - [x] **Chunk 49** — Prepared Parallel-Ingestion Failure Handling Composition — Application-only, LangGraph-free
  - [x] **Chunk 50** — Parallel Ingestion Agent Failure Attribution — Application-only, LangGraph-free
  - [x] **Chunk 51** — Parallel Ingestion ExceptionGroup Attribution Extraction — Application-only, LangGraph-free
  - [x] **Chunk 52** — Parallel Ingestion Sanitized Failure Fact Classification — Application-only, LangGraph-free
  - [x] **Chunk 53** — Parallel Ingestion Tuple Failure-Fact Classification Composition — Application-only, LangGraph-free
  - [x] **Chunk 54** — Parallel Ingestion Failure-Fact Selection Contract — Application-only, LangGraph-free
  - [x] **Chunk 55** — Parallel Ingestion Attempt-Number Source Contract — Application-only, LangGraph-free
  - [x] **Chunk 56** — Parallel Ingestion Failure-Policy Context Resolution Service — Application-only, LangGraph-free
  - [x] **Chunk 57** — Strict Single-Failure Fact Selector — Application-only, LangGraph-free
  - [x] **Chunk 58** — Initial Parallel Ingestion Attempt-Number Source — Application-only, LangGraph-free
  - [x] **Chunk 59** — Parallel Ingestion Failure Context Preparation Service — Application-only, LangGraph-free
  - [x] **Chunk 60** — Initial Terminal-Fail Parallel Ingestion Failure Policy — Application-only, LangGraph-free
  - [x] **Chunk 61** — Parallel Ingestion Failure Handling Composition Service — Application-only, LangGraph-free
  - [x] **Chunk 62** — LangGraph Phase 2 Single-Failure Terminal Routing

## Phase 5 — Regulatory + pricing

- [ ] Regulatory Intelligence Agent (retrieval against Qdrant when ready)
  - [x] **Chunk 63** — Regulatory Intelligence Agent Application Boundary and First Concrete Regulatory Agent
  - [x] **Chunk 64** — Document Query Embedding Application Boundary
  - [x] **Chunk 65** — Document Vector Search Query Preparation Service — Application-only
  - [x] **Chunk 66** — Regulatory Intelligence Query Execution Service — Application-only
  - [x] **Chunk 67** — Regulatory Intelligence Runtime Composition Root
  - [x] **Chunk 68** — OpenAI Query Embedding Infrastructure Adapter
- [ ] Pricing & Sales Agent
- [ ] Contract-phase graph slice

## Phase 6 — ML feature pipelines and forecasting

- [ ] Shared ML utilities (`ml/common`)
- [ ] Load feature pipeline + model training/inference path
- [ ] Price feature pipeline + model training/inference path
- [ ] Consumer Load Forecast Agent (ML-backed)
- [ ] DAM Price Forecast Agent (ML-backed)

## Phase 7 — Risk + trading

- [ ] Portfolio & Risk Agent
- [ ] Trading Strategy Agent
- [ ] Bid canonical persistence

## Phase 8 — Clearing + settlement

- [ ] Market clearing result ingestion (ACL)
- [ ] Billing & Settlement Agent
- [ ] Settlement canonical persistence

## Phase 9 — FastAPI surface

- [ ] `/api/v1` app shell, error envelope, correlation IDs
- [ ] Endpoints as specified in an updated `API_CONTRACTS.md` (currently TBD)

## Phase 10 — End-to-end workflow

- [ ] Chief Orchestrator Agent wiring across all five business phases
- [ ] Fixture-driven DAM day walkthrough (no live vendor APIs required)

## Phase 11 — Evaluation / hardening

- [ ] Architecture tests, DLQ replay, ML backtesting hooks
- [ ] Resource-usage pass for WSL2 8 GB constraint
- [ ] Failure-mode drills (missing source, duplicate hours)

## Phase 12 — Demo / presentation / deployment documentation

- [ ] Compose demo profile documentation
- [ ] Presentation artifacts (`PRESENTATION_NOTES.md`)
- [ ] Deployment notes (production topology still TBD)

---

## Current pointer

- **Completed:** Chunk 0 through Chunk 68
- **Next:** next Phase 5 Regulatory + Pricing slice or remaining Phase 4 parallel-ingestion work after Chunk 68 Architect review. Do not mark the parent Regulatory Intelligence capability complete. Do not mark Pricing & Sales started. Do not mark the parent Weather, Hydro, Generation Availability, News Intelligence, or Market Monitoring agent capabilities complete. Do not mark the parent Parallel Phase 2 join complete. Do not pre-authorize a concrete LLM/inference implementation, OpenAI client/API-key/model runtime composition, Qdrant/API composition, PDF/OCR, actual RAG workflow, verified Armenian DAM rule extraction, Regulatory graph/API wiring, production/durable workflow-context implementation, general multi-failure selection, retry-capable attempt tracking, increment/reset semantics, retry/fallback execution, LangGraph wiring of lower-level failure internals, Phase 3 execution, or API/composition graph wiring.
