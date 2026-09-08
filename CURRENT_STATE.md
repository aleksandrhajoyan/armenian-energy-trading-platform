# Current State

Living snapshot. Update at the end of every chunk. Do not list features that do not exist.

## Phase and chunk

- **Current phase:** Phase 4 — Ingestion agents (in progress)
- **Completed chunks:** Chunk 0 — Documentation and repository skeleton; Chunk 1 — Python Project Bootstrap, Dependency Management, Typed Configuration, and Minimal Application Health Check; Chunk 2 — Canonical Domain Contracts and Value Objects; Chunk 3 — Error Contracts, Diagnostics, and Observability Foundation; Chunk 4 — Adapter Ports and Structured Ingestion Boundary; Chunk 5 — Semantic Schema Mapping and Field Resolution Engine; Chunk 6 — CSV Structured Ingestion Adapter; Chunk 7 — Excel Structured Ingestion Adapter; Chunk 8 — Deterministic Consumption Unit and Timezone Normalization; Chunk 9 — Duplicate Timestamp Policy and Interval Validation; Chunk 10 — Missing-Interval Detection and Gap Reporting; Chunk 11 — DLQ Persistence Boundary; Chunk 12 — Unstructured Document Extraction Boundary; Chunk 13 — Async PostgreSQL/TimescaleDB Persistence Foundation; Chunk 14 — Consumption PostgreSQL Persistence Slice; Chunk 15 — PostgreSQL/TimescaleDB Service Profile and Live Persistence Integration; Chunk 16 — Application Cache Port Boundary; Chunk 17 — Async Redis Cache Infrastructure (Offline); Chunk 18 — Redis Service Profile and Live Cache Integration; Chunk 19 — Application Document Embedding Port Boundary; Chunk 20 — Application Document Vector Indexing Boundary; Chunk 21 — Application Document Vector Retrieval Boundary; Chunk 22 — Async Qdrant Client Foundation (Offline); Chunk 23 — Qdrant Document Vector Index/Search Adapter (Offline); Chunk 24 — Qdrant Service Profile and Live Vector Integration; Chunk 25 — n8n Local Service Foundation and Live Readiness; Chunk 26 — Application Agent Execution Contract Boundary; Chunk 27 — Application Orchestration State Contract — LangGraph-free; Chunk 28 — Minimal LangGraph Skeleton; Chunk 29 — Application Orchestration Failure Policy Hooks; Chunk 30 — Weather & Renewable Forecast Agent Application Boundary and First Concrete Agent; Chunk 31 — Hydro Resources Agent Application Boundary and First Concrete Hydro Agent; Chunk 32 — Generation Availability Agent Application Boundary and First Concrete Generation Agent; Chunk 33 — News Intelligence Agent Application Boundary and First Concrete News Agent; Chunk 34 — Market Monitoring Agent Application Boundary and First Concrete Market Agent; Chunk 35 — Parallel Ingestion Fan-Out Plan Contract — LangGraph-free; Chunk 36 — Parallel Ingestion Successful Fan-In Contract — LangGraph-free; Chunk 37 — Parallel Ingestion Execution Boundary — LangGraph-free; Chunk 38 — Concurrent Parallel Ingestion Executor — All-Success Path, LangGraph-free; Chunk 39 — Parallel Ingestion Workflow Context Boundary — LangGraph-free; Chunk 40 — Parallel Ingestion Workflow Step — Framework-neutral; Chunk 41 — LangGraph Phase 2 Workflow-Step Invocation — all-success path; Chunk 42 — Parallel Ingestion Success Phase Transition — LangGraph-free; Chunk 43 — LangGraph Phase 2 Success Transition Wiring; Chunk 44 — In-Memory Parallel Ingestion Workflow Context Adapter — Local/Dev Reference; Chunk 45 — Parallel Ingestion Terminal Failure Transition — LangGraph-free; Chunk 46 — Parallel Ingestion Failure-Policy Decision Boundary — Application-only, LangGraph-free; Chunk 47 — Parallel Ingestion Failure-Policy Context Construction — Application-only, LangGraph-free; Chunk 48 — Parallel Ingestion Terminal FAIL Action Execution — Application-only, LangGraph-free; Chunk 49 — Prepared Parallel-Ingestion Failure Handling Composition — Application-only, LangGraph-free; Chunk 50 — Parallel Ingestion Agent Failure Attribution — Application-only, LangGraph-free; Chunk 51 — Parallel Ingestion ExceptionGroup Attribution Extraction — Application-only, LangGraph-free; Chunk 52 — Parallel Ingestion Sanitized Failure Fact Classification — Application-only, LangGraph-free; Chunk 53 — Parallel Ingestion Tuple Failure-Fact Classification Composition — Application-only, LangGraph-free; Chunk 54 — Parallel Ingestion Failure-Fact Selection Contract — Application-only, LangGraph-free; Chunk 55 — Parallel Ingestion Attempt-Number Source Contract — Application-only, LangGraph-free; Chunk 56 — Parallel Ingestion Failure-Policy Context Resolution Service — Application-only, LangGraph-free; Chunk 57 — Strict Single-Failure Fact Selector — Application-only, LangGraph-free; Chunk 58 — Initial Parallel Ingestion Attempt-Number Source — Application-only, LangGraph-free; Chunk 59 — Parallel Ingestion Failure Context Preparation Service — Application-only, LangGraph-free
- **Next recommended chunk:** Next Phase 4 implementation slice to be selected after Chunk 59 review.

## What this repository is

A reproducible Python 3.12 application skeleton with typed settings, a FastAPI factory, process health, canonical domain contracts, transport-neutral application errors, a standard API error envelope, correlation IDs, structured JSON logging, an application-facing structured ingestion boundary, a deterministic infrastructure-local schema field-resolution engine, a concrete Consumption CSV adapter, a concrete Consumption Excel `.xlsx` adapter, explicit Consumption MW/kW plus IANA timezone normalization, fail-closed Consumption duplicate detection, optional interval-grid alignment, per-consumer internal gap reporting, an unwired filesystem-backed DLQ metadata persistence adapter, an application-owned unstructured document extraction boundary with no concrete PDF/OCR adapter, an application-owned document embedding port with no concrete embedding implementation, an application-owned document vector indexing port structurally implemented by `QdrantDocumentVectorIndex`, an application-owned document vector retrieval port structurally implemented by `QdrantDocumentVectorSearch`, an unwired Qdrant HTTP client foundation (`QdrantSettings`, `qdrant-client==1.19.0`, lazy `create_qdrant_client()`), concrete Qdrant document adapters (deterministic UUID point identity, closed payload, SHA-256 entry fingerprint, insert-only verified writes), an on-demand Compose Qdrant profile with opt-in live index/search tests, an unwired async PostgreSQL/TimescaleDB persistence foundation, an unwired Consumption PostgreSQL repository, an on-demand Compose TimescaleDB profile with live migration/repository tests, an application-owned vendor-neutral cache port, an unwired Redis cache adapter (`RedisSettings`, redis-py async factory, infrastructure codec, `RedisCache`), an on-demand Compose Redis profile with opt-in live cache tests, and an on-demand Compose n8n profile with opt-in live readiness tests, and an application-owned framework-neutral agent invocation boundary (`AgentName`, `AgentPort[TRequest, TResult]`), five concrete application agents (`WeatherAndRenewableForecastAgent`, `HydroResourcesAgent`, `GenerationAvailabilityAgent`, `NewsIntelligenceAgent`, and `MarketMonitoringAgent`) with typed request/result DTOs and application-owned canonical source ports (`WeatherRecordSourcePort`, `HydroRecordSourcePort`, `GenerationAvailabilityRecordSourcePort`, `NewsEventSourcePort`, `MarketPriceRecordSourcePort`) and no weather-, hydro-, generation-, news-, or market-provider implementation, an application-owned framework-neutral workflow snapshot (`WorkflowPhase`, `WorkflowStatus`, `WorkflowState`), a LangGraph runtime (`build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep)`, `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`) that consumes that snapshot as its state schema, delegates Phase 2 to the injected workflow step, and then applies the published successful Phase 2 control-state transition, and an application-owned framework-neutral failure-policy decision hook (`FailureAction`, `FailurePolicyContext`, `FailurePolicyPort`) with no concrete policy and no retry/fallback execution, and application-owned framework-neutral parallel-ingestion contracts (`ParallelIngestionPlan` for the five typed Phase 2 request DTOs, `ParallelIngestionExecutionPort` for `async execute(plan) -> ParallelIngestionSuccess`, and `ParallelIngestionSuccess` for the all-five-success result aggregate) plus a concrete LangGraph-free `ConcurrentParallelIngestionExecutor` that injects the five application agents and runs them concurrently with `asyncio.TaskGroup`, plus a framework-neutral `ParallelIngestionWorkflowContextPort` for resolving a prepared Phase 2 plan and recording all-five-success output by workflow identity, plus an unwired process-local `InMemoryParallelIngestionWorkflowContext` local/dev reference adapter, plus a framework-neutral `ParallelIngestionWorkflowStep` that composes resolve → execute → record and returns the original `WorkflowState` unchanged, plus a framework-neutral successful Phase 2 control-state transition (`advance_after_parallel_ingestion`) that maps `ingestion`/`running` to `forecasting`/`running` on a new seven-field `WorkflowState`, plus a framework-neutral terminal Phase 2 failure transition (`fail_parallel_ingestion`) that maps `ingestion`/`running` to `ingestion`/`failed` on a new seven-field `WorkflowState` without mutating diagnostics, plus a Phase-2-specific failure-policy decision service (`ParallelIngestionFailureDecisionService`) that accepts an already-constructed `FailurePolicyContext`, delegates exactly once to `FailurePolicyPort.decide`, and returns the published `FailureAction` unchanged, plus a Phase-2-specific pure constructor (`build_parallel_ingestion_failure_policy_context`) that builds that published context from already-sanitized typed failure facts without inspecting exceptions or inventing an agent identity, plus a Phase-2-specific failure-action executor (`execute_parallel_ingestion_failure_action`) that applies terminal `FailureAction.FAIL` by delegating to `fail_parallel_ingestion` and rejects `RETRY` / `FALLBACK` as not implemented, plus a Phase-2-specific prepared failure-handling composition (`ParallelIngestionFailureHandlingService`) that awaits the published decision service exactly once and forwards the returned action to that executor, plus Phase-2-specific agent-failure attribution (`ParallelIngestionAgentFailure`) that preserves canonical `AgentName` at the concurrent executor boundary, plus Phase-2-specific ExceptionGroup attributed-leaf extraction (`extract_parallel_ingestion_agent_failures`) that returns already-attributed leaves in depth-first encounter order without classifying them, plus Phase-2-specific sanitized one-leaf failure classification (`classify_parallel_ingestion_agent_failure`) that produces frozen `ParallelIngestionFailureFact` (`AgentName` + stable `error_code`) without selecting among failures, plus Phase-2-specific tuple-level failure-fact classification (`classify_parallel_ingestion_agent_failures`) that maps `tuple[ParallelIngestionAgentFailure, ...]` to `tuple[ParallelIngestionFailureFact, ...]` by delegating each element to that one-leaf classifier without selecting among failures, plus a Phase-2-specific failure-fact selection contract (`ParallelIngestionFailureSelectionPort`) that accepts that sanitized fact tuple and returns one `ParallelIngestionFailureFact` without first/last/priority winner semantics, plus a Phase-2-specific strict single-failure selector (`StrictSingleParallelIngestionFailureSelector`) that structurally satisfies that contract by returning the unique fact unchanged or failing closed on zero or multiple facts, plus a Phase-2-specific attempt-number source contract (`ParallelIngestionAttemptNumberPort`) that accepts only `workflow_id` and returns the current 1-based attempt as `int` with no increment/reset semantics on the port, plus a Phase-2-specific initial attempt-number source (`InitialParallelIngestionAttemptNumberSource`) that structurally satisfies that contract and always returns `1`, plus a Phase-2-specific failure-policy context resolution service (`ParallelIngestionFailureContextResolutionService`) that injects the selection and attempt-number ports, selects once, awaits attempt lookup once, and delegates to `build_parallel_ingestion_failure_policy_context`, plus a Phase-2-specific failure-context preparation service (`ParallelIngestionFailureContextPreparationService`) that injects that resolution service and composes extraction → tuple classification → context resolution from a `BaseExceptionGroup` into `FailurePolicyContext` without invoking policy or executing an action. LangGraph node `parallel_ingestion_success_transition` applies that published success function after a successful workflow step. The failure transition, the failure-policy decision service, the context builder, the failure-context resolution service, the failure-context preparation service, the failure-action executor, the prepared failure-handling composition, the ExceptionGroup extractor, the sanitized-fact classifier, the tuple-level classifier, the failure-fact selection port, the strict single-failure selector, the attempt-number source port, and the initial attempt-number source are not wired into LangGraph. Runtime Phase 2 exceptions still propagate from the graph because Chunk 59 implements only the application-level ExceptionGroup preparation composition and does not implement retry-capable tracking, increment/reset semantics, multi-failure selection, or graph routing. It is **not** a running trading platform.

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
- Concrete document embedding implementation / provider / model
- Query-text embedding
- Production Qdrant collection configuration / creation
- Production vector distance selection
- Production Qdrant deployment/security design
- Document reindex / replacement / delete
- Search filters, score thresholds, pagination
- RAG / regulatory interpretation
- API/composition embedding wiring
- API/composition vector-index wiring
- API/composition vector-search wiring
- API/composition Qdrant wiring
- The other 8 concrete agents
- Chief Orchestrator Agent
- Agent execution / AgentPort invocation from the graph
- Business-phase routing / five-phase graph
- LangGraph / orchestrator Phase 2 join
- General workflow status lifecycle transitions (pending/succeeded/failed)
- Phase 3 execution / forecasting-phase routing
- Production/durable parallel-ingestion workflow-context implementation
- Partial / failure / degraded fan-in contract
- Actual retry execution
- Actual fallback execution
- Concrete retry/fallback rules
- Exception-to-`FailurePolicyContext` mapping from raw exceptions
- LangGraph wiring of `fail_parallel_ingestion`
- LangGraph wiring of `ParallelIngestionFailureDecisionService`
- LangGraph wiring of `build_parallel_ingestion_failure_policy_context`
- LangGraph wiring of `execute_parallel_ingestion_failure_action`
- LangGraph wiring of `ParallelIngestionFailureHandlingService`
- LangGraph wiring of `extract_parallel_ingestion_agent_failures`
- LangGraph wiring of `classify_parallel_ingestion_agent_failure`
- LangGraph wiring of `classify_parallel_ingestion_agent_failures`
- LangGraph wiring of `ParallelIngestionFailureSelectionPort`
- LangGraph wiring of `ParallelIngestionAttemptNumberPort`
- LangGraph wiring of `ParallelIngestionFailureContextResolutionService`
- LangGraph wiring of `ParallelIngestionFailureContextPreparationService`
- LangGraph wiring of `StrictSingleParallelIngestionFailureSelector`
- LangGraph wiring of `InitialParallelIngestionAttemptNumberSource`
- Concrete multi-failure selection policy after sanitized fact classification
- Retry-capable Phase 2 attempt tracking / increment / reset / persistence
- LangGraph exception capture / runtime invocation of failure-context preparation
- Failure-policy action execution for `RETRY` / `FALLBACK`
- Backoff / delay / maximum-attempt policy
- Fallback targets
- Degraded-mode policy
- Persistence / checkpointing / Redis orchestration state
- API/composition LangGraph wiring
- Agent registry / factory
- LLM provider
- ML execution wiring
- API/composition agent wiring
- Running PostgreSQL / TimescaleDB service as an always-on process
- Canonical database tables other than Consumption observations
- Repositories other than Consumption
- API database wiring / readiness checks
- PostgreSQL DLQ
- Running Redis service as an always-on process
- API/composition Redis wiring
- Application use case using the cache
- Redis-backed workflow checkpoints / CAS / locks
- Redis readiness endpoint
- Running Qdrant service as an always-on process
- Running n8n service as an always-on process
- Actual n8n workflows
- External acquisition credentials
- Weather HTTP/API provider
- Weather ACL adapter
- Weather persistence
- n8n weather workflow
- Weather graph node
- Weather ML / LLM calculation
- Hydro HTTP/API provider
- Hydro ACL adapter
- Hydro persistence
- n8n hydro workflow
- Hydro graph node
- Hydro hydrological calculation
- Generation Availability coupling from Hydro
- Hydro ingestion beyond the application agent boundary
- Generation HTTP/API provider
- Generation ACL adapter
- Generation persistence
- n8n generation workflow
- Generation graph node
- Hydro→Generation coupling
- Generation fleet completeness policy
- Generation status/capacity calculation
- Generation ingestion beyond the application agent boundary
- News provider/API
- RSS/scraper
- News ACL infrastructure adapter
- News persistence
- n8n news workflow
- News graph node
- LLM summarization
- sentiment/relevance inference
- embedding/Qdrant News indexing
- News ingestion beyond the application agent boundary
- Market provider/API
- Market ACL infrastructure adapter
- Market persistence
- n8n market workflow
- Market graph node
- market-status contract
- currency conversion
- DAM-rule implementation
- price forecasting from Market Monitoring
- Market ingestion beyond the application agent boundary
- Application callback/API boundary for n8n
- FastAPI Docker image
- ML implementations
- External integrations
- OpenTelemetry / Sentry / Prometheus
- Authentication

## Implemented artifacts

- Root living docs, `.cursorrules`, `.gitignore`, `.env.example`
- Python 3.12 project baseline (`.python-version`, `requires-python = ">=3.12,<3.13"`)
- uv dependency management with committed `uv.lock`
- Typed application settings (`AppSettings`)
- Typed PostgreSQL settings (`DatabaseSettings`) loaded separately from process health
- Typed Redis settings (`RedisSettings`) loaded separately from process health
- Typed Qdrant settings (`QdrantSettings`) loaded separately from process health
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
- Application-owned document embedding port (`DocumentEmbeddingPort`)
- Immutable `DocumentChunkEmbedding` application DTO (opaque document/chunk identity plus a finite float vector; no provider/model/distance fields)
- Application-owned document vector indexing port (`DocumentVectorIndexPort`)
- Immutable `DocumentVectorIndexEntry` application DTO (paired `ExtractedDocumentChunk` + matching `DocumentChunkEmbedding`; identity `(document_id, chunk_id)`)
- Application-owned document vector retrieval port (`DocumentVectorSearchPort`)
- Immutable `DocumentVectorSearchQuery` application DTO (finite query vector plus a positive `limit`; no query text, provider, dimension, score, or filter fields)
- Ranked `ExtractedDocumentChunk` search output (tuple order is relevance; no backend scores)
- Official `qdrant-client==1.19.0` (`>=1.19,<2`) as an infrastructure-only dependency
- Lazy `create_qdrant_client()` returning `AsyncQdrantClient` over REST (`prefer_grpc=False`, `cloud_inference=False`)
- Infrastructure-local `QdrantDocumentVectorConfig` (`collection_name`, `vector_size`)
- Concrete `QdrantDocumentVectorIndex` structurally implementing `DocumentVectorIndexPort`
- Concrete `QdrantDocumentVectorSearch` structurally implementing `DocumentVectorSearchPort`
- Deterministic UUID5 Qdrant point identity from `(document_id, chunk_id)`
- Closed normalized Qdrant payload (`document_id`, `chunk_id`, `ordinal`, `text`, `page_number`, `content_sha256`)
- SHA-256 application-entry fingerprint including exact `float.hex()` vector members
- Insert-only upsert (`UpdateMode.INSERT_ONLY`, `wait=True`) with pre-read/post-write verification
- Ranked `query_points` translation that discards Qdrant scores
- On-demand Compose `qdrant` profile (`qdrant` service, image `qdrant/qdrant:v1.19.1`, loopback REST 6333, required API key, telemetry disabled, named volume `qdrant-data`)
- Live authenticated Qdrant readiness, unauthenticated rejection, index, exact retry, conflict, ranking, and limit tests (opt-in)
- Qdrant client-foundation architecture tests (inner layers Qdrant-free; API unwired)
- Qdrant document-vector adapter architecture tests (ports implemented in infrastructure; no collection management, inference, or API wiring)
- Compose Qdrant profile and live-integration architecture tests
- On-demand Compose `n8n` profile (`n8n` service, image `n8nio/n8n:2.37.10`, loopback HTTP 5678, required encryption key, diagnostics/version/templates/personalization disabled, named volume `n8n-data`)
- Live n8n `/healthz` and `/healthz/readiness` tests (opt-in)
- Compose n8n profile architecture tests
- Application-owned `AgentName` (`StrEnum` of the 13 canonical identities)
- Application-owned generic `AgentPort[TRequest, TResult]` (identity + async `run(request)` only)
- Agent-contract unit and architecture tests (structural fake; no live services)
- Application-owned `WorkflowPhase` (`StrEnum` of the five business phases)
- Application-owned `WorkflowStatus` (`StrEnum` of pending/running/succeeded/failed)
- Application-owned frozen `WorkflowState` snapshot (identity, delivery date, phase, status, canonical diagnostics)
- Orchestration-state unit and architecture tests (no live services)
- Direct `langgraph>=1.2.11,<1.3` application-runtime dependency (resolved `langgraph==1.2.11`)
- Factory `build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep)` compiling a fresh graph over `WorkflowState`
- Topology `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`; `workflow_entry` remains an async no-op; `parallel_ingestion` delegates to the injected step; `parallel_ingestion_success_transition` applies `advance_after_parallel_ingestion`
- LangGraph unit and architecture tests (async `ainvoke` success path to `forecasting`/`running`, node order, step-failure short-circuit, `InvalidRequestError` propagation, import ownership)
- Application-owned `FailureAction` (`StrEnum`: retry / fallback / fail)
- Application-owned frozen `FailurePolicyContext` (phase, sanitized error code, 1-based attempt number, optional `AgentName`)
- Application-owned async structural `FailurePolicyPort.decide(context)` with no concrete policy
- Failure-policy unit and architecture tests (structural fake; no retry/fallback execution; LangGraph-free)
- Application-owned frozen `ParallelIngestionPlan` (exactly the five existing Phase 2 request DTOs; no execution, no LangGraph)
- Application-owned frozen `ParallelIngestionSuccess` (exactly the five existing Phase 2 result DTOs; all-five-success only; no execution, no failure/degraded semantics, no LangGraph)
- Application-owned non-generic `ParallelIngestionExecutionPort` (`async execute(plan: ParallelIngestionPlan) -> ParallelIngestionSuccess`; Protocol only)
- Concrete application `ConcurrentParallelIngestionExecutor` (injects the five Phase 2 application agents; `asyncio.TaskGroup`; all-success only; ordinary failures attributed as `ParallelIngestionAgentFailure`; LangGraph-free)
- Application-owned non-generic `ParallelIngestionWorkflowContextPort` (`async resolve_plan(workflow_id: str) -> ParallelIngestionPlan` and `async record_success(workflow_id: str, success: ParallelIngestionSuccess) -> None`; Protocol only in application; storage-neutral)
- Infrastructure `InMemoryParallelIngestionWorkflowContext` (process-local in-memory structural implementation; constructor-prepared plans; missing plan is `ResourceNotFoundError`; equal success retry is idempotent; differing success is `ConflictError`; `asyncio.Lock` on writes; local/dev reference only; unwired)
- Concrete application `ParallelIngestionWorkflowStep` (injects context and execution ports; `async run(state) -> state`; resolve → execute → record; original `WorkflowState` returned unchanged; LangGraph-free)
- Application-owned `advance_after_parallel_ingestion(state) -> WorkflowState` (LangGraph-free; valid only for `ingestion`/`running`; returns a new snapshot at `forecasting`/`running`; identity/date/diagnostics preserved; invalid phase/status is `InvalidRequestError`)
- Application-owned `fail_parallel_ingestion(state) -> WorkflowState` (LangGraph-free; valid only for `ingestion`/`running`; returns a new snapshot at `ingestion`/`failed`; identity/date/diagnostics preserved unchanged; invalid phase/status is `InvalidRequestError`; not wired into the graph; does not map exceptions or consult `FailurePolicyPort`)
- Concrete application `ParallelIngestionFailureDecisionService` (injects `FailurePolicyPort`; `async decide(context) -> FailureAction`; exact once-only delegation; returns the published action unchanged; no context construction; no action execution; LangGraph-free; unwired)
- Application-owned `build_parallel_ingestion_failure_policy_context(...) -> FailurePolicyContext` (LangGraph-free; keyword-only typed facts matching published fields; caller supplies `phase`, `error_code`, `attempt_number`, and optional `AgentName`; no exception inspection; no fabricated agent identity; no `WorkflowState` input; published constructor validation preserved; unwired)
- Application-owned `execute_parallel_ingestion_failure_action(*, state, action) -> WorkflowState` (LangGraph-free; executes already-decided `FailureAction`; `FAIL` delegates to `fail_parallel_ingestion`; `RETRY` and `FALLBACK` raise `InvalidRequestError` as not implemented; no policy decision; no context construction; no diagnostics mutation; unwired)
- Concrete application `ParallelIngestionFailureHandlingService` (injects `ParallelIngestionFailureDecisionService`; keyword-only `async handle(*, state, context) -> WorkflowState`; decides then executes; no `FailureAction` branching; no context construction; no diagnostics mutation; LangGraph-free; unwired)
- Application-owned `ParallelIngestionAgentFailure` (canonical `AgentName` only; sanitized message; original failure retained through exception chaining; LangGraph-free)
- Application-owned `extract_parallel_ingestion_agent_failures` (recursive ExceptionGroup / BaseExceptionGroup traversal; exact attributed-leaf identity and encounter order; unattributed leaves fail closed as `InvalidRequestError`; LangGraph-free; unwired)
- Application-owned `ParallelIngestionFailureFact` and `classify_parallel_ingestion_agent_failure` (one attributed leaf → canonical `AgentName` + stable `error_code`; `ApplicationError` codes reused; non-application/missing causes collapse to `parallel_ingestion_unexpected_failure`; LangGraph-free; unwired)
- Application-owned `classify_parallel_ingestion_agent_failures` (already-extracted attributed-failure tuple → sanitized fact tuple; delegates to the one-leaf classifier; preserves order/cardinality/duplicates; empty input remains empty; LangGraph-free; unwired)
- Application-owned `ParallelIngestionFailureSelectionPort` (non-generic Protocol; `select(facts: tuple[ParallelIngestionFailureFact, ...]) -> ParallelIngestionFailureFact`; no first/last/agent/error/severity winner rule; LangGraph-free; unwired)
- Application-owned `StrictSingleParallelIngestionFailureSelector` (structural implementation of that selection contract; exactly one fact returns the same instance; zero or multiple facts fail closed as sanitized `InvalidRequestError`; no ranking/deduplication/aggregation; LangGraph-free; unwired)
- Application-owned `ParallelIngestionAttemptNumberPort` (non-generic Protocol; `async get_attempt_number(workflow_id: str) -> int`; read-only; no increment/reset semantics on the port; LangGraph-free; unwired)
- Application-owned `InitialParallelIngestionAttemptNumberSource` (structural implementation of that attempt-number contract; async; stateless; returns exactly `1` for every workflow identity; reflects the current no-retry runtime; not a tracker; no increment/reset/persistence; LangGraph-free; unwired)
- Application-owned `ParallelIngestionFailureContextResolutionService` (injects `ParallelIngestionFailureSelectionPort` and `ParallelIngestionAttemptNumberPort`; keyword-only `async resolve(*, workflow_id, phase, facts) -> FailurePolicyContext`; selects once; awaits attempt lookup once; delegates to `build_parallel_ingestion_failure_policy_context`; does not auto-wire the strict selector or initial attempt source; LangGraph-free; unwired)
- Application-owned `ParallelIngestionFailureContextPreparationService` (injects `ParallelIngestionFailureContextResolutionService`; keyword-only `async prepare(*, workflow_id, phase, failure_group) -> FailurePolicyContext`; delegates extraction → tuple classification → context resolution; does not invoke policy or execute an action; LangGraph-free; unwired)
- `ConcurrentParallelIngestionExecutor` attributes ordinary Phase 2 agent failures as `ParallelIngestionAgentFailure` before native TaskGroup aggregation; sibling cancellation is not wrapped
- Parallel-ingestion plan/success/execution-port/executor/context-port/workflow-step/success-transition/failure-transition/failure-decision/failure-context/failure-action/failure-handling/agent-failure/exception-group-extraction/failure-fact-classification/tuple-failure-classification/failure-fact-selection/strict-single-failure-selector/attempt-number-source/initial-attempt-number-source/failure-context-resolution/failure-context-preparation unit and architecture tests (real request/result DTOs; real agents behind source fakes; structural context/execution/policy/selection/attempt-number fakes plus the concrete strict selector and initial attempt source in Chunk 57–59 tests; no live services)
- Application-owned `WeatherRecordSourcePort` (keyword-only `fetch` of canonical `WeatherRecord` tuples)
- Frozen `WeatherAndRenewableForecastRequest` / `WeatherAndRenewableForecastResult` application DTOs
- Concrete `WeatherAndRenewableForecastAgent` structurally satisfying `AgentPort` (provider-neutral, unwired)
- Weather source-port, agent, and architecture-boundary tests (structural fake; no live provider)
- Application-owned `HydroRecordSourcePort` (keyword-only `fetch` of canonical `HydroRecord` tuples)
- Frozen `HydroResourcesRequest` / `HydroResourcesResult` application DTOs
- Concrete `HydroResourcesAgent` structurally satisfying `AgentPort` (provider-neutral, unwired)
- Hydro source-port, agent, and architecture-boundary tests (structural fake; no live provider)
- Application-owned `GenerationAvailabilityRecordSourcePort` (keyword-only `fetch` of canonical `GenerationAvailabilityRecord` tuples)
- Frozen `GenerationAvailabilityRequest` / `GenerationAvailabilityResult` application DTOs
- Concrete `GenerationAvailabilityAgent` structurally satisfying `AgentPort` (provider-neutral, unwired)
- Generation source-port, agent, and architecture-boundary tests (structural fake; no live provider; explicit no-Hydro-coupling assertions)
- Application-owned `NewsEventSourcePort` (keyword-only `fetch` of canonical `NewsEvent` tuples)
- Frozen `NewsIntelligenceRequest` / `NewsIntelligenceResult` application DTOs
- Concrete `NewsIntelligenceAgent` structurally satisfying `AgentPort` (provider-neutral, unwired)
- News source-port, agent, and architecture-boundary tests (structural fake; no live provider; no LLM/embedding/Qdrant/scraping)
- Application-owned `MarketPriceRecordSourcePort` (keyword-only `fetch` of canonical `MarketPriceRecord` tuples)
- Frozen `MarketMonitoringRequest` / `MarketMonitoringResult` application DTOs
- Concrete `MarketMonitoringAgent` structurally satisfying `AgentPort` (provider-neutral, unwired)
- Market source-port, agent, and architecture-boundary tests (structural fake; no live provider; no forecast, clearing, currency conversion, or DAM-rule inference)
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
- Document embedding architecture tests (application port has no Path/bytes/Qdrant/provider/model/NumPy/search surface; `embed()` accepts only extracted chunks)
- Document vector indexing architecture tests (application port has no Path/bytes/Qdrant/collection/point/search surface; `index()` accepts only paired index entries)
- Document vector retrieval architecture tests (application port has no Path/bytes/Qdrant/collection/score/filter/query-text surface; `search()` accepts only `DocumentVectorSearchQuery`)
- PostgreSQL persistence architecture tests (domain/application/API unwired; settings have no engine objects)
- Consumption repository architecture tests (port has no SQLAlchemy/session surface; repository is infrastructure-only)
- Compose TimescaleDB profile architecture tests
- Async redis-py client factory (`create_redis_client`) without eager network I/O
- Infrastructure-local cache codec protocol (`CacheCodec[TValue]`, `CacheCodecError`)
- Concrete `RedisCache[TValue]` structurally implementing `CachePort[TValue]`
- SHA-256 Redis backend-key derivation and millisecond `PX` TTL conversion
- Offline Redis settings, client, codec, and cache adapter tests
- Redis cache infrastructure architecture tests
- Application-owned generic cache port (`CachePort[TValue]`: async get/set/delete, mandatory positive TTL)
- Cache-port architecture tests (application remains Redis-type-free; API unwired)
- On-demand Compose `redis` profile (`redis` service, image `redis:8.2.9-alpine`, loopback bind, required password, no volume, RDB/AOF disabled, `redis-cli` health)
- Live Redis server, authentication, persistence-disabled, and `RedisCache` round-trip/overwrite/delete/expiry tests (opt-in)
- Compose Redis profile architecture tests
- Domain and application architecture dependency tests
- Initial automated quality/test toolchain: pytest, pytest-asyncio, HTTPX, Ruff, mypy

## Pending work

Everything after Chunk 59 in `ROADMAP.md`. Next is **next Phase 4 implementation slice to be selected after Chunk 59 review**. Phase 4 has begun; it is not complete.

NOW implemented: concurrent invocation of the five Phase 2 application agents through `ConcurrentParallelIngestionExecutor`, all-success collection into `ParallelIngestionSuccess`, canonical failing-agent attribution as `ParallelIngestionAgentFailure` at that executor boundary, deterministic ExceptionGroup attributed-leaf extraction through `extract_parallel_ingestion_agent_failures`, sanitized one-leaf classification through `classify_parallel_ingestion_agent_failure` into `ParallelIngestionFailureFact`, tuple-level classification through `classify_parallel_ingestion_agent_failures` that preserves order/cardinality/duplicates by delegating to that one-leaf classifier, a Phase-2-specific failure-fact selection Protocol (`ParallelIngestionFailureSelectionPort`) that accepts a sanitized fact tuple and returns one fact without first/last/priority winner semantics, a Phase-2-specific strict single-failure selector (`StrictSingleParallelIngestionFailureSelector`) that returns the unique sanitized fact unchanged or fails closed on zero or multiple facts, a Phase-2-specific attempt-number source Protocol (`ParallelIngestionAttemptNumberPort`) that accepts only `workflow_id` and returns the current 1-based attempt with no increment/reset semantics on the port, a Phase-2-specific initial attempt-number source (`InitialParallelIngestionAttemptNumberSource`) that structurally satisfies that Protocol and always returns `1`, a Phase-2-specific failure-policy context resolution service (`ParallelIngestionFailureContextResolutionService`) that injects those two ports, selects once, awaits attempt lookup once, and delegates to the existing context builder, a Phase-2-specific failure-context preparation service (`ParallelIngestionFailureContextPreparationService`) that injects that resolution service and composes extraction → tuple classification → context resolution from a `BaseExceptionGroup` into `FailurePolicyContext` without invoking policy or executing an action, a typed workflow-context boundary (`ParallelIngestionWorkflowContextPort`) for resolving a Phase 2 plan and recording all-success output, a process-local in-memory `InMemoryParallelIngestionWorkflowContext` as local/dev reference infrastructure, a framework-neutral workflow step (`ParallelIngestionWorkflowStep`) composing resolve → execute → record, a LangGraph node `parallel_ingestion` that dependency-injects that step and awaits `run(state)` on the all-success path, a LangGraph node `parallel_ingestion_success_transition` that applies `advance_after_parallel_ingestion` so a successful graph path ends at `forecasting`/`running`, a framework-neutral terminal Phase 2 failure transition (`fail_parallel_ingestion`) that maps `ingestion`/`running` to `ingestion`/`failed` without mutating diagnostics, a Phase-2-specific failure-policy decision service (`ParallelIngestionFailureDecisionService`) that delegates an already-constructed `FailurePolicyContext` to `FailurePolicyPort` exactly once and returns `FailureAction` unchanged, a Phase-2-specific pure constructor (`build_parallel_ingestion_failure_policy_context`) that builds the published `FailurePolicyContext` from already-sanitized typed failure facts, a Phase-2-specific failure-action executor (`execute_parallel_ingestion_failure_action`) that applies terminal `FailureAction.FAIL` by delegating to `fail_parallel_ingestion` and rejects `RETRY` / `FALLBACK` as not implemented, and a Phase-2-specific prepared failure-handling composition (`ParallelIngestionFailureHandlingService`) that awaits that decision service exactly once and forwards the returned action to the published executor.

STILL absent: production/durable workflow-context implementation; graph Phase 2 join for failure/degraded/runtime composition; LangGraph wiring of the terminal failure transition, the failure-policy decision service, the context builder, the failure-context resolution service, the failure-context preparation service, the failure-action executor, the prepared failure-handling composition, the ExceptionGroup extractor, the sanitized-fact classifier, the tuple-level classifier, the failure-fact selection port, the strict single-failure selector, the attempt-number source port, or the initial attempt-number source; a general multi-failure selector; retry-capable attempt tracking; increment/reset semantics; LangGraph exception capture / runtime invocation of failure-context preparation; retry/fallback action execution; exception-to-diagnostic mapping; general status lifecycle transitions; Phase 3 execution; degraded-mode semantics; concrete failure policy; concrete Chief Orchestrator; API/composition wiring; providers/persistence/n8n workflows. Runtime Phase 2 exceptions still propagate from the graph because Chunk 59 is not graph-wired and does not implement retry-capable attempt tracking, increment/reset semantics, or multi-failure selection. One attributed failure is now fully preparable into `FailurePolicyContext` at application level; multiple attributed failures still fail closed; runtime graph invocation is still absent. The preparation service is callable only when a constructed resolution service is injected; the strict selector and initial attempt source exist and can be injected behind that resolution service, but are not auto-wired into the graph or API. Failure handling is not complete. Parallel Phase 2 join is not complete.

Current Phase 2 failure pipeline:

```text
agent runtime failure
→ attribution
→ TaskGroup / ExceptionGroup
→ failure-context preparation service
→ extraction
→ tuple classification
→ context-resolution service
→ strict single selector
   exactly one fact → selected fact
   zero or multiple facts → fail closed
→ initial attempt-number source (`1`)
→ context builder
→ FailurePolicyContext
→ prepared policy/action handling
→ LangGraph runtime failure routing still missing
```

Five concrete application agents remain provider-neutral. LangGraph does not import them; they are invoked only if a caller composes the execution port behind `ParallelIngestionWorkflowStep`. They remain unwired to API, providers, persistence, and n8n. Do not claim the trading workflow runs end-to-end. Do not install embedding SDKs or ML stacks until those chunks.

## Known issues

- Armenian DAM official products, gate times, bid envelope, currency, and settlement math are **unverified** and must not be hardcoded.
- Concrete external API providers are **not** selected.
- WSL2 RAM cap vs future Compose services is an operational risk (see `ARCHITECTURE.md`).
- TimescaleDB is pinned to `timescale/timescaledb:2.29.2-pg17` for local development; it is on-demand, not always running.
- Redis is pinned to `redis:8.2.9-alpine` for local development; it is on-demand, not always running.
- Qdrant is pinned to `qdrant/qdrant:v1.19.1` for local development; it is on-demand, not always running. Local HTTP plus API key is not the production security model.
- n8n is pinned to `n8nio/n8n:2.37.10` for local development; it is on-demand, not always running. Local HTTP plus a deployment encryption key is not the production security model.

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
- Document embedding is an application-owned `DocumentEmbeddingPort` over already-normalized `ExtractedDocumentChunk` values; it is not Qdrant, not a domain contract, and has no concrete provider/model
- Document vector indexing is an application-owned `DocumentVectorIndexPort` pairing a normalized chunk with its matching embedding; logical identity is `(document_id, chunk_id)`; exact retries are idempotent; conflicts fail closed; there is no generic `VectorStore`; infrastructure `QdrantDocumentVectorIndex` is the concrete writer
- Document vector retrieval is an application-owned `DocumentVectorSearchPort`; input is an already-embedded finite query vector plus a positive `limit`; output is ranked `ExtractedDocumentChunk` values with unique `(document_id, chunk_id)` identities; zero matches are valid; backend scores, collection names, filters, and query text do not cross the port; indexing and search remain separate; there is no generic `VectorStore`; infrastructure `QdrantDocumentVectorSearch` is the concrete reader
- Qdrant connectivity is infrastructure-only: typed `QdrantSettings` plus lazy `create_qdrant_client()`; domain/application/API/ML do not import the SDK; Qdrant does not generate embeddings; point identity/payload/fingerprint/insert-only writes exist; Compose `qdrant` profile is optional and on-demand; production collection provisioning, production distance selection, and API wiring do not
- PostgreSQL/TimescaleDB persistence is an infrastructure factory plus the Consumption Core table/repository; Compose `postgres` profile is optional and on-demand; no global engine, no FastAPI wiring, no ingestion→repository wiring
- Consumption persistence identity is `(consumer_id, timestamp)`; exact retries are idempotent; differing values conflict; adapters still do not query PostgreSQL
- Cache is an application-owned `CachePort[TValue]`; infrastructure `RedisCache` is TTL-bound and ephemeral; Compose `redis` profile is optional and on-demand; no API/orchestration wiring, no locks
- n8n is optional outer acquisition/scheduling infrastructure; Compose `n8n` profile is on-demand and loopback-only; n8n internal metadata is not the platform energy-data system of record; n8n must not bypass the ACL; no workflows or application/API/LangGraph wiring exist
- Agent invocation is application-owned: `AgentName` plus structurally typed `AgentPort[TRequest, TResult]`; only `name` and async `run(request)` are shared; no registry, retry, or fallback. Five concrete agents exist (`WeatherAndRenewableForecastAgent`, `HydroResourcesAgent`, `GenerationAvailabilityAgent`, `NewsIntelligenceAgent`, `MarketMonitoringAgent`); the other 8 remain absent
- Weather source access is application-owned: `WeatherRecordSourcePort.fetch` returns canonical `WeatherRecord` tuples only; no provider, ACL adapter, persistence, graph node, or API wiring
- Hydro source access is application-owned: `HydroRecordSourcePort.fetch` returns canonical `HydroRecord` tuples only; no provider, ACL adapter, persistence, graph node, hydrological calculation, Generation Availability coupling, or API wiring
- Generation source access is application-owned: `GenerationAvailabilityRecordSourcePort.fetch` returns canonical `GenerationAvailabilityRecord` tuples only; no provider, ACL adapter, persistence, graph node, status/capacity calculation, fleet-completeness policy, Hydro coupling, or API wiring
- News source access is application-owned: `NewsEventSourcePort.fetch` returns canonical `NewsEvent` tuples only; no provider, RSS/scraper, ACL adapter, persistence, graph node, LLM summarization, sentiment/relevance inference, embedding/Qdrant indexing, or API wiring
- Market source access is application-owned: `MarketPriceRecordSourcePort.fetch` returns canonical `MarketPriceRecord` tuples only; no provider, ACL adapter, persistence, graph node, market-status model, currency conversion, cadence/interval assumption, market clearing, price forecasting, or API wiring
- Workflow snapshot is application-owned: frozen `WorkflowState` with `WorkflowPhase` and `WorkflowStatus`; LangGraph consumes it as `state_schema` and does not redefine it; the snapshot has no transition methods or persistence, and no phase-specific canonical output slots
- Successful Phase 2 control-state transition is application-owned: `advance_after_parallel_ingestion(state)` is valid only for `ingestion`/`running`, returns a new seven-field snapshot at `forecasting`/`running`, preserves identity/date/diagnostics, and fails closed with `InvalidRequestError` otherwise. It is not a generic state machine and is not a method on `WorkflowState`. LangGraph node `parallel_ingestion_success_transition` delegates to this function and does not reimplement it
- Terminal Phase 2 failure transition is application-owned: `fail_parallel_ingestion(state)` is valid only for `ingestion`/`running`, returns a new seven-field snapshot at `ingestion`/`failed`, preserves identity/date/diagnostics unchanged, and fails closed with `InvalidRequestError` otherwise. It does not append diagnostics, map exceptions, consult `FailurePolicyPort`, or imply retry/fallback/degraded continuation. It is not a generic state machine, not a method on `WorkflowState`, and is not wired into LangGraph. Runtime Phase 2 exceptions still propagate from the graph.
- LangGraph is application-owned: `build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep)` compiles `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`; `workflow_entry` is async and no-op; `parallel_ingestion` awaits the injected step and returns its `WorkflowState`; the success-transition node applies `advance_after_parallel_ingestion`; no Phase 3 execution, retry/fallback execution, checkpointer, store, cache, or API wiring
- Failure-policy decisions are application-owned: `FailureAction` plus frozen `FailurePolicyContext` plus async structural `FailurePolicyPort`; no concrete policy, no retry/fallback execution, no LangGraph ownership, and no graph injection
- Phase 2 failure-policy decision composition is application-owned: concrete `ParallelIngestionFailureDecisionService` injects exactly `FailurePolicyPort`. `async decide(context: FailurePolicyContext) -> FailureAction` awaits `policy.decide(context)` exactly once and returns that `FailureAction` unchanged. It does not construct context from exceptions, does not branch on the action, and does not call `fail_parallel_ingestion`. It is not wired into LangGraph. Action execution is owned by `execute_parallel_ingestion_failure_action` and composed by `ParallelIngestionFailureHandlingService`; both remain unwired.
- Phase 2 failure-policy context construction is application-owned: `build_parallel_ingestion_failure_policy_context` is a synchronous, keyword-only function that instantiates the published `FailurePolicyContext` from caller-supplied `phase`, `error_code`, `attempt_number`, and optional `agent_name`. It does not inspect exceptions, does not invent an agent identity, does not accept `WorkflowState`, and does not decide or execute a `FailureAction`. Existing constructor validation is preserved. It is not wired into LangGraph. Application-level ExceptionGroup preparation into that context is owned by `ParallelIngestionFailureContextPreparationService`; LangGraph capture remains deferred.
- Phase 2 failure-action execution is application-owned: `execute_parallel_ingestion_failure_action(*, state, action)` is a synchronous, keyword-only function that receives an already-decided `FailureAction`. `FAIL` returns `fail_parallel_ingestion(state)` without duplicating transition policy. `RETRY` and `FALLBACK` fail closed as `InvalidRequestError` with stable sanitized messages. The function does not construct `FailurePolicyContext`, does not call `FailurePolicyPort` or `ParallelIngestionFailureDecisionService`, does not inspect exceptions or diagnostics, and is not wired into LangGraph. Retry/fallback mechanics remain deferred.
- Phase 2 prepared failure handling is application-owned: concrete `ParallelIngestionFailureHandlingService` injects exactly `ParallelIngestionFailureDecisionService`. `async handle(*, state: WorkflowState, context: FailurePolicyContext) -> WorkflowState` awaits `decide(context)` exactly once and forwards the returned action plus the supplied state to `execute_parallel_ingestion_failure_action`. The service does not construct context, does not branch on `FailureAction`, does not call `fail_parallel_ingestion` directly, and is not wired into LangGraph. Runtime exceptions still propagate from the current graph. Exception capture and retry/fallback execution remain deferred.
- Phase 2 agent-failure attribution is application-owned: `ParallelIngestionAgentFailure` stores canonical `AgentName` only. `ConcurrentParallelIngestionExecutor` wraps ordinary agent `Exception` failures with `raise ... from` and does not wrap cancellation. TaskGroup aggregation still propagates. Attempt tracking, multi-failure selection, and Chunk 46–49 policy/handling invocation remain deferred and unwired. One-leaf error-code classification is owned by `classify_parallel_ingestion_agent_failure` and is not invoked here.
- Phase 2 ExceptionGroup attributed-leaf extraction is application-owned: `extract_parallel_ingestion_agent_failures(failure)` recursively traverses a possibly nested `BaseExceptionGroup` and returns exact original `ParallelIngestionAgentFailure` objects in depth-first left-to-right encounter order. Duplicate agent identities are retained. Unattributed leaves fail closed as `InvalidRequestError`. The helper does not classify failures, select a primary failure, inspect `__cause__`, rebuild groups, or invoke policy. It is not wired into LangGraph or the executor.
- Phase 2 sanitized one-leaf failure classification is application-owned: `classify_parallel_ingestion_agent_failure(failure)` converts exactly one `ParallelIngestionAgentFailure` into frozen `ParallelIngestionFailureFact` with canonical `AgentName` and a stable `error_code`. `ApplicationError` causes reuse their published application error code. Non-application and missing causes collapse to `parallel_ingestion_unexpected_failure`. Exception text, class names, and tracebacks never become policy facts. The classifier does not select among multiple failures, assign attempt numbers, construct `FailurePolicyContext`, or invoke policy. It is not wired into LangGraph.
- Phase 2 tuple-level failure-fact classification is application-owned: `classify_parallel_ingestion_agent_failures(failures)` converts `tuple[ParallelIngestionAgentFailure, ...]` into `tuple[ParallelIngestionFailureFact, ...]` by delegating each already-extracted leaf to `classify_parallel_ingestion_agent_failure`. Encounter order, cardinality, and duplicate agent identities are preserved. An empty input returns an empty output. The composer does not inspect `__cause__`, does not duplicate error-code mapping, does not sort/deduplicate/group, does not select a primary failure, does not assign attempt numbers, and does not construct `FailurePolicyContext`. It is not wired into LangGraph.
- Phase 2 failure-fact selection is application-owned: non-generic `ParallelIngestionFailureSelectionPort` exposes only synchronous `select(facts: tuple[ParallelIngestionFailureFact, ...]) -> ParallelIngestionFailureFact`. Implementations satisfy the Protocol structurally. There is no first/last/agent/error/retryability/severity winner rule and no empty-tuple production default. The port does not inspect exceptions, does not assign attempt numbers, and does not construct `FailurePolicyContext`. It is not wired into LangGraph.
- Phase 2 strict single-failure selection is application-owned: concrete `StrictSingleParallelIngestionFailureSelector` structurally satisfies that Protocol without inheriting it. Exactly one sanitized fact is returned as the same instance. Zero facts and two-or-more facts fail closed as sanitized `InvalidRequestError`. Duplicate agent identities and value-equal facts are still multiple facts. There is no ranking, deduplication, aggregation, or priority table. Simultaneous multi-failure resolution remains unresolved. The selector is not wired into LangGraph.
- Phase 2 attempt-number sourcing is application-owned: non-generic `ParallelIngestionAttemptNumberPort` exposes only async `get_attempt_number(workflow_id: str) -> int`. Implementations satisfy the Protocol structurally. The returned value is the current 1-based parallel-ingestion execution attempt. The port itself has no increment/reset/set/record write API. The port does not accept `WorkflowState`, failure facts, or policy types. It is not wired into LangGraph.
- Phase 2 initial attempt-number resolution is application-owned: concrete `InitialParallelIngestionAttemptNumberSource` structurally satisfies that Protocol without inheriting it. The method remains async. The source is stateless and returns exactly `1` for every workflow identity because the published runtime has no retry execution. Workflow ID content is not inspected, hashed, validated, or persisted. There is no increment, reset, per-workflow map, or storage. Future retry support requires separately reviewed tracking semantics and likely a different concrete implementation. The source is not wired into LangGraph.
- Phase 2 failure-policy context resolution is application-owned: concrete `ParallelIngestionFailureContextResolutionService` injects exactly `ParallelIngestionFailureSelectionPort` and `ParallelIngestionAttemptNumberPort`. Keyword-only `async resolve(*, workflow_id: str, phase: WorkflowPhase, facts: tuple[ParallelIngestionFailureFact, ...]) -> FailurePolicyContext` selects once, awaits attempt lookup once, and delegates to `build_parallel_ingestion_failure_policy_context` with the supplied phase, selected error code and agent name, and resolved attempt number. The service implements no selection algorithm, no attempt tracking, no policy decision, and no action execution. Direct `FailurePolicyContext` construction is not duplicated here. The strict selector and initial attempt source exist and can be injected, but are not auto-wired. It is not wired into LangGraph.
- Phase 2 failure-context preparation is application-owned: concrete `ParallelIngestionFailureContextPreparationService` injects exactly `ParallelIngestionFailureContextResolutionService`. Keyword-only `async prepare(*, workflow_id: str, phase: WorkflowPhase, failure_group: BaseExceptionGroup) -> FailurePolicyContext` extracts attributed leaves, classifies the resulting tuple, and awaits context resolution. The service does not traverse groups itself, does not inspect causes, does not select among facts, does not resolve attempt numbers, does not invoke policy, and does not execute an action. Direct `FailurePolicyContext` construction is not duplicated here. It is not auto-wired into LangGraph. One attributed failure is fully preparable into context at application level; multiple attributed failures still fail closed; runtime graph invocation is still absent.
- Parallel Phase 2 fan-out planning is application-owned: frozen `ParallelIngestionPlan` composes the five existing typed request DTOs; it is not `WorkflowState`, does not execute agents, does not use LangGraph, and does not derive source-scope IDs from `portfolio_id`
- Parallel Phase 2 successful fan-in is application-owned: frozen `ParallelIngestionSuccess` composes the five existing typed result DTOs for the all-five-success case only; it is not `WorkflowState`, does not execute agents, does not use LangGraph, and does not encode partial/failure/degraded semantics
- Parallel Phase 2 execution is application-owned: non-generic `ParallelIngestionExecutionPort` exposes only `async execute(plan: ParallelIngestionPlan) -> ParallelIngestionSuccess`. Concrete `ConcurrentParallelIngestionExecutor` injects the five application agents and uses `asyncio.TaskGroup` for the all-success path only. Ordinary agent failures are wrapped as `ParallelIngestionAgentFailure` with canonical `AgentName` and `raise ... from` chaining. Sibling cancellation is not wrapped. Native TaskGroup failure propagation still applies. There is no retry/fallback/degraded policy, no error-code classification inside the executor, no LangGraph wiring, and no `WorkflowState` expansion
- Parallel Phase 2 workflow context is application-owned: non-generic `ParallelIngestionWorkflowContextPort` exposes only `async resolve_plan(workflow_id) -> ParallelIngestionPlan` and `async record_success(workflow_id, success) -> None`. `workflow_id` reuses the published `WorkflowState.workflow_id` type. Plan and success stay outside the seven-field `WorkflowState` snapshot. Infrastructure `InMemoryParallelIngestionWorkflowContext` is a process-local structural implementation for local/dev use; it is not durable storage, not Redis/PostgreSQL, not wired into LangGraph/`create_app()`, and does not encode failure/degraded semantics. Production/durable workflow-context implementation remains absent.
- Parallel Phase 2 workflow composition is application-owned: concrete `ParallelIngestionWorkflowStep` injects exactly `ParallelIngestionWorkflowContextPort` and `ParallelIngestionExecutionPort`. `async run(state: WorkflowState) -> WorkflowState` is resolve → execute → record, then return of the original state object. There is no phase/status mutation, no `FailurePolicyPort`, and no retry/fallback/degraded policy. LangGraph injects the step into `parallel_ingestion`; it does not reconstruct the sequence inside the node
- UTC timestamps; MW vs MWh; Decimal money; explicit currency codes
- Application/domain exceptions contain no HTTP semantics; HTTP translation is API-only
- Unexpected exception details are never sent to clients
- Correlation IDs propagate through logs and error responses
- ML ≠ LLM for numerical forecasts; agents never import concrete ML implementations
- No secrets in git; `.env` must not be committed
- Avoid always-on heavy local services

## Current services

TimescaleDB is available on demand under the Compose `postgres` profile (`timescale/timescaledb:2.29.2-pg17`, loopback-only). Redis is available on demand under the Compose `redis` profile (`redis:8.2.9-alpine`, loopback-only, password required, non-persistent). Qdrant is available on demand under the Compose `qdrant` profile (`qdrant/qdrant:v1.19.1`, loopback-only REST 6333, API key required, telemetry disabled, named `qdrant-data`). n8n is available on demand under the Compose `n8n` profile (`n8nio/n8n:2.37.10`, loopback-only HTTP 5678, encryption key required, telemetry/template/version/personalization disabled, named `n8n-data`). None is assumed to be running continuously. The local Qdrant and n8n profiles are not production-ready. The n8n container does not implement ingestion.

## Current APIs

- `GET /api/v1/health` — process liveness only (`API_CONTRACTS.md`)
- Standard error envelope and `X-Correlation-ID` on API responses, including health and unknown routes

## Current agents

Five concrete application agents exist:

1. Weather & Renewable Forecast Agent (`WeatherAndRenewableForecastAgent`). It is provider-neutral and unwired: it consumes `WeatherAndRenewableForecastRequest`, calls `WeatherRecordSourcePort`, and returns `WeatherAndRenewableForecastResult` wrapping canonical `WeatherRecord` values. No weather provider, ACL adapter, persistence, or graph/API wiring exists.
2. Hydro Resources Agent (`HydroResourcesAgent`). It is provider-neutral and unwired: it consumes `HydroResourcesRequest`, calls `HydroRecordSourcePort`, and returns `HydroResourcesResult` wrapping canonical `HydroRecord` values. It does not calculate reservoir behavior or available generation. No hydro provider, ACL adapter, persistence, graph/API wiring, or Generation Availability coupling exists.
3. Generation Availability Agent (`GenerationAvailabilityAgent`). It is provider-neutral and unwired: it consumes `GenerationAvailabilityRequest`, calls `GenerationAvailabilityRecordSourcePort`, and returns `GenerationAvailabilityResult` wrapping canonical `GenerationAvailabilityRecord` values. It does not infer status, calculate capacity, assume missing-asset completeness, or derive records from Hydro. No generation provider, ACL adapter, persistence, graph/API wiring, or Hydro coupling exists.
4. News Intelligence Agent (`NewsIntelligenceAgent`). It is provider-neutral and unwired: it consumes `NewsIntelligenceRequest`, calls `NewsEventSourcePort`, and returns `NewsIntelligenceResult` wrapping canonical `NewsEvent` values. It does not scrape, summarize, classify, infer sentiment/relevance/impact, or call an LLM. No news provider, ACL adapter, persistence, graph/API wiring, or embedding/Qdrant indexing exists.
5. Market Monitoring Agent (`MarketMonitoringAgent`). It is provider-neutral and unwired: it consumes `MarketMonitoringRequest`, calls `MarketPriceRecordSourcePort`, and returns `MarketMonitoringResult` wrapping canonical `MarketPriceRecord` values. It does not convert currency, assume cadence or interval duration, fabricate missing prices, clear the market, or forecast prices. No market provider, ACL adapter, persistence, graph/API wiring, or market-status contract exists.

LangGraph does not call these agents or `AgentPort` directly. It injects `ParallelIngestionWorkflowStep` into node `parallel_ingestion` and awaits `run(state)`. That step can invoke the five agents only when a caller has composed `ParallelIngestionExecutionPort` (typically `ConcurrentParallelIngestionExecutor`) and a context port behind it. After a successful step, node `parallel_ingestion_success_transition` applies `advance_after_parallel_ingestion`, so a valid `ingestion`/`running` graph run ends at `forecasting`/`running`. Phase 3 forecasting is not executed. Application-owned `fail_parallel_ingestion` can replace a valid `ingestion`/`running` snapshot with `ingestion`/`failed` without changing diagnostics; the graph does not call it, and runtime Phase 2 exceptions still propagate. Application-owned `ParallelIngestionFailureDecisionService` can decide a `FailureAction` from an already-constructed `FailurePolicyContext` without executing it; the graph does not call it. Application-owned `build_parallel_ingestion_failure_policy_context` can construct that published context from already-sanitized typed facts; the graph does not call it. Application-owned `execute_parallel_ingestion_failure_action` can apply terminal `FailureAction.FAIL` by delegating to `fail_parallel_ingestion` and rejects `RETRY` / `FALLBACK` as not implemented; the graph does not call it. Application-owned `ParallelIngestionFailureHandlingService` can compose an already-built `FailurePolicyContext` through the published decision service and action executor; the graph does not call it. Application-owned `ConcurrentParallelIngestionExecutor` attributes ordinary Phase 2 agent failures as `ParallelIngestionAgentFailure` with canonical `AgentName` before TaskGroup aggregation; the graph does not interpret those leaves. Application-owned `extract_parallel_ingestion_agent_failures` can extract those attributed leaves from a possibly nested exception group without classifying them; the graph does not call it. Application-owned `classify_parallel_ingestion_agent_failure` can convert one attributed leaf into sanitized `ParallelIngestionFailureFact`; the graph does not call it. Application-owned `classify_parallel_ingestion_agent_failures` can classify an already-extracted attributed-failure tuple by delegating each element to that one-leaf classifier; it preserves order/cardinality/duplicates, does not select a primary failure, and the graph does not call it. Application-owned `ParallelIngestionFailureSelectionPort` can accept that sanitized fact tuple and return one `ParallelIngestionFailureFact`; there is no first/last/priority winner rule, and the graph does not call it. Application-owned `StrictSingleParallelIngestionFailureSelector` implements that contract for the unambiguous one-fact case only; zero or multiple facts fail closed, simultaneous multi-failure selection remains unresolved, and the graph does not call it. Application-owned `ParallelIngestionAttemptNumberPort` can return the current 1-based attempt for a workflow identity; there is no increment/reset API on the port, and the graph does not call it. Application-owned `InitialParallelIngestionAttemptNumberSource` implements that contract for the current no-retry runtime by returning exactly `1`; it is not a tracker, and the graph does not call it. Application-owned `ParallelIngestionFailureContextResolutionService` can compose a sanitized fact tuple, that selection port, that attempt-number port, and the published context builder into one `FailurePolicyContext`; the strict selector and initial attempt source exist but are not auto-wired, and the graph does not call it. Application-owned `ParallelIngestionFailureContextPreparationService` can compose a `BaseExceptionGroup` through extraction, tuple classification, and that resolution service into one `FailurePolicyContext`; it does not invoke policy or execute an action, and the graph does not call it. `InMemoryParallelIngestionWorkflowContext` exists as unwired local/dev infrastructure. There is no production/durable workflow-context implementation, no API/composition wiring, and no retry/fallback execution. `ParallelIngestionWorkflowContextPort` can resolve a plan and record all-five-success output by workflow identity without embedding Phase 2 payloads in `WorkflowState`. Failure/degraded fan-in policy does not exist. Failure handling is not complete. None of these agents constitutes complete production ingestion.

The other 8 concrete agents remain absent. Thirteen canonical identities are captured by application `AgentName`. Future agents will structurally satisfy `AgentPort` and consume canonical contracts through application ports; they must not parse raw source schemas.

## Current ML models

None. No experiments have been run (`EXPERIMENT_LOG.md`).
