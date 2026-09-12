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
| Infrastructure | `src/energy_trading/infrastructure` | Adapters, persistence, cache, vector store, messaging, scrapers, file readers. SQLAlchemy async, psycopg 3, and Alembic are infrastructure-only. |
| API | `src/energy_trading/api` | HTTP transport and composition root. Invokes use cases; wires implementations into ports. No business logic. |
| Shared | `src/energy_trading/shared` | Configuration and observability that must not become a dumping ground for domain rules. |

Agents belong to the application layer. LangGraph orchestration belongs to the application layer. Concrete database clients, API clients, scrapers, Redis, Qdrant, filesystem readers, Excel readers, and PDF readers belong to infrastructure. SQLAlchemy, psycopg, and Alembic are infrastructure concerns and must not be imported by domain or application. Concrete ML libraries and model classes belong to `ml`, not to agents.

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

This rule is enforced by AST import inspection:

- `tests/architecture/test_domain_dependencies.py` — domain imports none of `api`, `application`, `infrastructure`, `ml`, `shared`, or FastAPI.
- `tests/architecture/test_application_dependencies.py` — application (including ports) imports none of `api`, `infrastructure`, `ml`, FastAPI, or Starlette.
- `tests/architecture/test_structured_ingestion_boundary.py` — structured-ingestion application ports expose no raw-source types (CSV/Excel/HTTP/HTML libraries, `DataFrame`, `bytes`, `dict`, `Mapping`, `Any`).
- `tests/architecture/test_schema_mapping_boundary.py` — the infrastructure schema-mapping package imports none of OpenAI/LangChain/LangGraph, pandas/Polars/openpyxl, FastAPI/Starlette, database clients, or application/domain contracts.
- `tests/architecture/test_csv_adapter_boundary.py` — the Consumption CSV adapter imports none of pandas/Polars/openpyxl, HTTP clients, FastAPI/Starlette, database clients, LangChain/LangGraph/OpenAI, or ML libraries. Application ingestion ports still accept no CSV/path/raw-row types.
- `tests/architecture/test_excel_adapter_boundary.py` — the Consumption Excel adapter may import openpyxl and the shared Consumption mapping helper, but none of pandas/Polars/xlrd, HTTP clients, FastAPI/Starlette, database clients, LangChain/LangGraph/OpenAI, or ML libraries. Application ingestion ports still accept no Workbook/Worksheet/Cell/path types.
- `tests/architecture/test_structured_normalization_boundary.py` — the Consumption unit/timezone normalization package imports none of application/API/ML, pandas/openpyxl, HTTP clients, databases, or LLM/graph libraries. Application ports still expose no `PowerUnit`, `ZoneInfo`, or normalization config.
- `tests/architecture/test_time_series_validation_boundary.py` — the Consumption time-series validation package imports none of application/API/ML, pandas/openpyxl, HTTP clients, databases, or LLM/graph libraries. Application ports still expose no `IntervalGrid`, duplicate policy, source-position configuration, or `ConsumptionGap`.
- `tests/architecture/test_time_series_gap_boundary.py` — gap reports stay infrastructure-local; application ports expose no gap ranges, missing-timestamp collections, or coverage windows.
- `tests/architecture/test_dlq_persistence_boundary.py` — application `DeadLetterQueuePort` stays free of filesystem/raw-payload/database types; `FilesystemDeadLetterQueue` may depend on application errors and domain contracts but not on FastAPI, pandas/openpyxl, HTTP clients, databases, brokers, LLM/graph libraries, ML libraries, or Consumption CSV/Excel adapters.
- `tests/architecture/test_document_extraction_boundary.py` — application `DocumentExtractionPort` and extraction DTOs expose no Path/bytes/URL/dict/OCR/PDF/Qdrant/LLM surface; `extract()` accepts only `self`.
- `tests/architecture/test_pdf_text_extraction_boundary.py` — infrastructure `PdfTextExtractionAdapter` may import `pypdf` plus existing extraction contracts/errors/diagnostics; it must not import FastAPI, API/composition, LangGraph, OpenAI, Qdrant, Redis, SQLAlchemy, ML, OCR libraries, embedding/index/search ports, or Regulatory agents; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_document_embedding_boundary.py` — application `DocumentEmbeddingPort` and `DocumentChunkEmbedding` expose no Path/bytes/URL/dict/Qdrant/provider/model/NumPy/search surface; `embed()` accepts only `self` and already-normalized `ExtractedDocumentChunk` values.
- `tests/architecture/test_document_query_embedding_boundary.py` — application `DocumentQueryEmbeddingPort` and `DocumentQueryEmbedding` expose no Path/bytes/URL/dict/Qdrant/provider/model/NumPy/search/query-text-result surface; `embed_query()` accepts only `self` and `query_text: str`; the port is a non-generic Protocol with no document-chunk, search, or generic `EmbeddingPort`/`LLMPort` hierarchy; `create_app()`, `graph.py`, and `RegulatoryIntelligenceAgent` remain unwired.
- `tests/architecture/test_document_vector_search_query_preparation_boundary.py` — application `DocumentVectorSearchQueryPreparationService` injects exactly `DocumentQueryEmbeddingPort`; the only public operation is keyword-only async `prepare(*, query_text: str, limit: int) -> DocumentVectorSearchQuery`; AST proves `embed_query` then existing query construction with no `.search(...)`, no vector mutation, and no `try/except` fallback; no infrastructure/API/ML/Qdrant/LLM/NumPy/`Any`/`dict`/`Mapping`/generic RAG surface; `create_app()`, `graph.py`, and `RegulatoryIntelligenceAgent` remain unwired.
- `tests/architecture/test_document_vector_index_entry_preparation_boundary.py` — application `DocumentVectorIndexEntryPreparationService` injects exactly `DocumentEmbeddingPort`; the only public operation is keyword-only async `prepare(*, chunks: tuple[ExtractedDocumentChunk, ...]) -> tuple[DocumentVectorIndexEntry, ...]`; AST proves exactly one `embed(...)` call and no `.index(...)`; no infrastructure/API/ML/Qdrant/OpenAI/LangGraph/`Any`/`dict`/`Mapping`/generic indexing/RAG surface; `create_app()`, Regulatory runtime composition, LangGraph, extraction, and Qdrant indexing remain unwired.
- `tests/architecture/test_document_vector_index_execution_boundary.py` — application `DocumentVectorIndexExecutionService` injects exactly `DocumentVectorIndexEntryPreparationService` and `DocumentVectorIndexPort`; the only public operation is keyword-only async `execute(*, chunks: tuple[ExtractedDocumentChunk, ...]) -> None`; AST proves exactly one `prepare(...)` then one `index(...)`, with no `embed(...)` and no `DocumentVectorIndexEntry` construction; no infrastructure/API/ML/Qdrant/OpenAI/LangGraph/`Any`/`dict`/`Mapping`/generic indexing/RAG surface; `create_app()`, Regulatory runtime composition, LangGraph, extraction, and Qdrant indexing remain unwired.
- `tests/architecture/test_document_extraction_index_execution_boundary.py` — application `DocumentExtractionIndexExecutionService` injects exactly `DocumentExtractionPort` and `DocumentVectorIndexExecutionService`; the only public operation is async `execute(self) -> DocumentExtractionResult`; AST proves exactly one `extract()`, conditional `execute(chunks=result.chunks)` only when chunks exist, and return of the original result; no reconstruction of chunks/results/entries, no `try/except`, no infrastructure/API/ML/FastAPI/LangGraph/OpenAI/Qdrant/pypdf/pathlib/`PdfTextExtractionAdapter` surface; `create_app()`, document-index HTTP router, Regulatory runtime, production lifespan, and LangGraph remain unwired.
- `tests/architecture/test_pdf_document_extraction_index_composition_boundary.py` — API-owned `build_pdf_document_extraction_index_execution` lives in `api/composition`; it injects local `Path`, `document_id`, `source_name`, and an already-constructed `DocumentVectorIndexExecutionService`; AST proves exactly one `PdfTextExtractionAdapter` construction and one `DocumentExtractionIndexExecutionService` construction, with the supplied index service forwarded unchanged; no `.extract()`/`.execute()`/file open/exists, settings/env, FastAPI routes/lifespan, OpenAI/Qdrant, or generic factory/registry/DI; application does not import the builder; infrastructure does not import API composition; `create_app()`, production lifespan, document-index HTTP router/runtime, Regulatory runtime, and LangGraph remain unwired.
- `tests/architecture/test_pdf_document_extraction_index_loaded_runtime_boundary.py` — API-owned `loaded_pdf_document_extraction_index_runtime` lives in `api/composition`; it is a keyword-only async context manager over local `Path`, `document_id`, `source_name`, and the existing `env_file` loader contract; AST proves exactly one `loaded_document_vector_index_runtime` entry with forwarded `env_file` and exactly one `build_pdf_document_extraction_index_execution` call with forwarded path/identities and the yielded index execution service; no `.extract()`/`.execute()`, no direct `PdfTextExtractionAdapter` construction, no settings loaders, no client factories, no provider SDKs, no FastAPI/lifespan/generic registry; application does not import the runtime; infrastructure does not import API composition; `create_app()`, production lifespan, document-index HTTP router/runtime, Regulatory runtime, and LangGraph remain unwired.
- `tests/architecture/test_pdf_document_extraction_index_execute_boundary.py` — API-owned `execute_loaded_pdf_document_extraction_index` lives in `api/composition`; it is a keyword-only async function over local `Path`, `document_id`, `source_name`, and the existing `env_file` loader contract; AST proves exactly one `loaded_pdf_document_extraction_index_runtime` entry with forwarded path/identities/`env_file` and exactly one awaited `service.execute()`; the original `DocumentExtractionResult` is returned; no `.extract()`, no nested index execution, no PDF adapter/provider/settings construction, no loop/background/scheduler, no FastAPI/lifespan/generic runner; application does not import the function; infrastructure does not import API composition; `create_app()`, production lifespan, HTTP routers, Regulatory runtime, and LangGraph remain unwired.
- `tests/architecture/test_document_vector_index_runtime_composition_boundary.py` — API-owned `build_document_vector_index_provider_runtime` lives in `api/composition`; it injects already-created `AsyncOpenAI` and `AsyncQdrantClient` plus existing `QdrantDocumentVectorConfig` and an explicit document-embedding model string; AST proves construction of `OpenAIDocumentEmbeddingAdapter` and `QdrantDocumentVectorIndex` and exactly one delegation to `build_document_vector_index_execution`; no settings/env/client factories, no `.embed`/`.index`/`.execute`, no FastAPI routes, no LangGraph; application does not import the builder; `create_app()`, Regulatory runtime, extraction, and `graph.py` remain unwired.
- `tests/architecture/test_document_vector_index_configured_runtime_composition_boundary.py` — API-owned `build_document_vector_index_configured_runtime` lives in `api/composition`; it injects already-created `AsyncOpenAI` and `AsyncQdrantClient` plus already-constructed `DocumentVectorIndexRuntimeSettings`; AST proves exactly one `QdrantDocumentVectorConfig` construction from `settings.qdrant_collection_name` / `settings.qdrant_vector_size` and exactly one delegation to `build_document_vector_index_provider_runtime` with the document-embedding model forwarded; no settings loaders, client factories, adapters, Chunk 86, FastAPI, LangGraph, or provider runtime methods; application does not import the builder; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_document_vector_index_managed_runtime_boundary.py` — API-owned `managed_document_vector_index_runtime` lives in `api/composition`; it is a keyword-only async context manager over already-loaded `OpenAISettings`, `QdrantSettings`, `DocumentVectorIndexRuntimeSettings`, and `QdrantDocumentVectorDistanceSettings`; AST proves existing factory construction, immediate async-close registration, one awaited Chunk 110 ensure on the managed Qdrant client, and exactly one Chunk 89 delegation after that ensure; no direct OpenAI/Qdrant SDK imports, settings loaders, mapper, Chunk 106/107/108, env/`.env`, FastAPI, LangGraph, adapters, Chunk 87/86, or generic lifecycle/DI abstractions; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_document_vector_index_loaded_runtime_boundary.py` — API-owned `loaded_document_vector_index_runtime` lives in `api/composition`; it is a keyword-only async context manager with the existing `env_file` loader contract; AST proves exactly one call to each of the four published settings loaders, including `load_qdrant_document_vector_distance_settings`, and exactly one delegation to `managed_document_vector_index_runtime`; no provider SDK types, client factories, collection ensure, adapters, Chunk 89/87/86, FastAPI, LangGraph, or provider runtime methods; `create_app()` and `graph.py` remain unwired; provider-SDK API-composition allowlist remains the existing document-index and Regulatory provider-composition modules.
- `tests/architecture/test_document_vector_index_runtime_collection_provisioning_boundary.py` — Chunk 111 ownership: managed runtime may import `QdrantDocumentVectorDistanceSettings` and `ensure_configured_document_vector_index_collection_ready`; it awaits that Chunk 110 function once with the locally managed Qdrant client before the configured builder; loaded runtime loads distance settings and forwards them without calling ensure; `create_app()`, production lifespan, and document-index lifespan do not own ensure.
- `tests/architecture/test_document_vector_index_lifespan_boundary.py` — API-owned `build_document_vector_index_lifespan` lives in `api/composition`; it is a synchronous keyword-only factory returning a FastAPI-compatible async lifespan callback; AST proves lazy construction, exactly one Chunk 91 entry with forwarded `env_file`, assignment of that exact service to `app.state.document_vector_index_execution_service` inside the loaded runtime, `yield` while that reference exists, and `finally` deletion before Chunk 91 exit; FastAPI is the only new framework import; no settings loaders, settings objects, provider SDKs, client factories, adapters, Chunk 90/89/87/86, LangGraph, Redis/PostgreSQL/ML, agents, routers, yielded lifespan-state dict, or generic registry/DI; HTTP routes and `create_app()` remain unwired to this child factory; `app.py` and `production_lifespan.py` do not assign or delete the service; Chunk 96 may read the published state attribute from `api/dependencies` but must not assign or delete it; `graph.py` remains unwired; provider-SDK API-composition allowlist remains the existing document-index and Regulatory provider-composition modules.
- `tests/architecture/test_document_vector_index_dependency_boundary.py` — API-owned `get_document_vector_index_execution_service` lives in `api/dependencies`; it is a synchronous one-argument reader of `request.app.state.document_vector_index_execution_service` returning exact `DocumentVectorIndexExecutionService` identity; AST proves no assignment/deletion, no `.execute`, no `Depends`, no route decorator, no HTTPException, no provider SDKs, no composition/lifecycle imports, no LangGraph, and no infrastructure; missing/wrong-type state uses existing `DependencyUnavailableError`; `create_app()`, health, and the Regulatory query router remain unwired to the accessor.
- `tests/architecture/test_document_vector_index_http_schema_boundary.py` — API-owned `DocumentVectorIndexChunkRequest` / `DocumentVectorIndexRequest` live in `api/schemas`; they are frozen Pydantic models with `extra="forbid"`; AST proves chunk fields are exactly `document_id`, `chunk_id`, `text`, `ordinal`, `page_number` and the outer request field is exactly `chunks: tuple[DocumentVectorIndexChunkRequest, ...]`; no route decorator, `APIRouter`, `Depends`, `Request`, accessor, `.execute`, provider SDKs, settings loaders, LangGraph, Path/bytes/URL/UploadFile/multipart, vector/embedding/collection fields, `Any`/`dict`/`Mapping`, or response DTO; application/domain/`create_app()`/health/Regulatory router remain unaware of the schema module; Chunk 98's dedicated indexing router uses these DTOs.
- `tests/architecture/test_document_vector_index_http_route_boundary.py` — API-owned Document Vector Index router lives in `api/routers`; it uses `APIRouter` with prefix `/document-vector-index` and POST `/index`; AST proves `Depends(get_document_vector_index_execution_service)`, explicit `ExtractedDocumentChunk` projection of the five published fields, exactly one awaited `.execute(chunks=chunks)`, HTTP 204 with no response DTO, no `app.state` access, no provider SDKs, no infrastructure, no settings loaders, no lifespan/composition builders, no LangGraph, no generic mapper, and no local `try/except`; production include of that router is proven in `test_document_vector_index_app_wiring.py`.
- `tests/architecture/test_document_vector_index_app_wiring.py` — production `create_app()` imports the published Document Vector Index router and includes it exactly once with `prefix=resolved_settings.api_prefix`; health and Regulatory router installation remain; construction does not import the schema, accessor, execution-service, settings-loader, provider-SDK, adapter, or child-lifespan modules; `create_app()` itself performs no `app.state` assignment, `.execute`, path reconstruction, or generic DI/registry.
- `tests/architecture/test_production_lifespan_composition_boundary.py` — API-owned `build_production_lifespan` lives in `api/composition`; it is a synchronous keyword-only factory returning a FastAPI-compatible async lifespan callback; AST proves lazy construction, exactly one call to each published child lifespan factory with forwarded `env_file`, Regulatory wrapping Document Vector Index, the same FastAPI `app` passed to both callbacks, one application `yield`, and no `app.state` assignment; FastAPI is the only framework import besides the two child lifespan modules; no settings loaders, settings objects, provider SDKs, client factories, adapters, generic lifespan/registry/DI abstractions, LangGraph, Redis/PostgreSQL/ML, agents, or routers; production `create_app()` imports and defaults to `build_production_lifespan()` and does not import or call the child factories; `graph.py` remains unwired; provider-SDK API-composition allowlist remains the existing document-index and Regulatory provider-composition modules.
- `tests/architecture/test_regulatory_intelligence_query_execution_boundary.py` — application `RegulatoryIntelligenceQueryExecutionService` injects exactly `DocumentVectorSearchQueryPreparationService` and `RegulatoryIntelligenceAgent`; the only public operation is keyword-only async `execute(*, query_text: str, limit: int) -> RegulatoryIntelligenceResult`; AST proves `prepare` then existing `RegulatoryIntelligenceRequest` construction then `run` with no `embed_query`, no `.search(...)`, no inference call, and no `try/except` fallback; no infrastructure/API/ML/Qdrant/LLM/NumPy/`Any`/`dict`/`Mapping`/generic RAG/executor surface; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_regulatory_intelligence_workflow_step_boundary.py` — application `RegulatoryIntelligenceWorkflowStep` lives in `application/orchestration`; it injects an already-constructed `RegulatoryIntelligenceQueryExecutionService`; public operations are `name` and async `run(request)` returning existing `RegulatoryIntelligenceResult`; AST proves exactly one awaited `execute(query_text=request.query_text, limit=request.limit)` with no `try/except`, no API/composition/infrastructure/provider/config/LangGraph imports, no new generic port, and no `WorkflowState` mutation; graph topology, production runtime, and HTTP remain unwired.
- `tests/architecture/test_regulatory_intelligence_workflow_context_boundary.py` — application `RegulatoryIntelligenceWorkflowContextPort` lives in `application/orchestration`; it is a non-generic Protocol with exactly two public async operations: keyword-only `resolve_request(*, state: WorkflowState) -> RegulatoryIntelligenceWorkflowRequest` and `record_result(*, state: WorkflowState, result: RegulatoryIntelligenceResult) -> None`; AST proves no defaults, no concrete production implementation, no `Any`/`dict`/`Mapping`/`TypedDict`/generic type parameter, no API/infrastructure/config/LangGraph/provider/DB/cache imports; `WorkflowState` remains the seven-field snapshot and does not import the port; graph topology, HTTP, and `create_app()` remain unwired.
- `tests/architecture/test_regulatory_intelligence_composition_boundary.py` — API-owned `build_regulatory_intelligence_query_execution` lives in `api/composition`; it injects exactly the three published application ports and returns `RegulatoryIntelligenceQueryExecutionService`; AST proves construction of query preparation, the agent, and query execution with no runtime method calls, no vendor SDKs, no settings/environment access, and no FastAPI routes; application does not import the builder; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_regulatory_intelligence_runtime_composition_boundary.py` — API-owned `build_regulatory_intelligence_provider_runtime` lives in `api/composition`; it injects already-created `AsyncOpenAI` and `AsyncQdrantClient` plus existing `QdrantDocumentVectorConfig` and two explicit model strings; AST proves construction of the three published concrete adapters and exactly one delegation to `build_regulatory_intelligence_query_execution`; no settings/env/client factories, no provider runtime methods, no FastAPI routes, no LangGraph; application does not import the builder; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_regulatory_intelligence_configured_runtime_composition_boundary.py` — API-owned `build_regulatory_intelligence_configured_runtime` lives in `api/composition`; it injects already-created `AsyncOpenAI` and `AsyncQdrantClient` plus already-constructed `RegulatoryIntelligenceRuntimeSettings`; AST proves exactly one `QdrantDocumentVectorConfig` construction from `settings.qdrant_collection_name` / `settings.qdrant_vector_size` and exactly one delegation to `build_regulatory_intelligence_provider_runtime` with the two model fields forwarded; no settings loaders, client factories, adapters, Chunk 67, FastAPI, LangGraph, or provider runtime methods; application does not import the builder; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_regulatory_intelligence_managed_runtime_boundary.py` — API-owned `managed_regulatory_intelligence_runtime` lives in `api/composition`; it is a keyword-only async context manager over already-loaded `OpenAISettings`, `QdrantSettings`, `RegulatoryIntelligenceRuntimeSettings`, and `QdrantDocumentVectorDistanceSettings`; AST proves existing factory construction, immediate async-close registration, one awaited Chunk 112 verify on the managed Qdrant client, and exactly one Chunk 73 delegation after that verify; no direct OpenAI/Qdrant SDK imports, settings loaders, mapper, Chunk 106/107/108, env/`.env`, FastAPI, LangGraph, adapters, Chunk 71/67, or generic lifecycle/DI abstractions; `create_app()` and `graph.py` remain unwired.
- `tests/architecture/test_regulatory_intelligence_loaded_runtime_boundary.py` — API-owned `loaded_regulatory_intelligence_runtime` lives in `api/composition`; it is a keyword-only async context manager with the existing `env_file` loader contract; AST proves exactly one call to each of the four published settings loaders, including `load_qdrant_document_vector_distance_settings`, and exactly one delegation to `managed_regulatory_intelligence_runtime`; no provider SDK types, client factories, collection verification, adapters, Chunk 73/71/67, FastAPI, LangGraph, or provider runtime methods; `create_app()` and `graph.py` remain unwired; provider-SDK API-composition allowlist remains the existing two modules.
- `tests/architecture/test_regulatory_intelligence_lifespan_boundary.py` — API-owned `build_regulatory_intelligence_lifespan` lives in `api/composition`; it is a synchronous keyword-only factory returning a FastAPI-compatible async lifespan callback; AST proves lazy construction, exactly one Chunk 75 entry with forwarded `env_file`, assignment of that exact service to `app.state.regulatory_intelligence_query_execution_service` inside the inner runtime, and `finally` deletion before Chunk 75 exit; FastAPI is the only new framework import; no settings loaders, settings objects, provider SDKs, client factories, adapters, Chunk 74/73/71/67, LangGraph, Redis/PostgreSQL/ML, agents, routers, or yielded lifespan-state dict; HTTP routes, graph, and lower Regulatory layers remain unwired to Chunk 75; provider-SDK API-composition allowlist remains the existing two modules; Chunk 79 may read the published state attribute from `api/dependencies` but must not assign or delete it.
- `tests/architecture/test_regulatory_intelligence_app_lifespan_wiring.py` — production `create_app()` imports `build_production_lifespan` and installs the returned composite lifespan into `FastAPI(..., lifespan=...)`; it also imports the published Regulatory query router and Document Vector Index indexing router and includes each exactly once with `prefix=resolved_settings.api_prefix`; construction does not call child lifespan factories, Chunk 75/74/73/71/67, settings loaders, client factories, or provider SDKs; a keyword-only optional `lifespan` seam exists for tests; `create_app()` itself performs no `app.state` service assignment, `.execute`, nested `async with` composition, path reconstruction, accessor/schema import, or generic DI/registry; lifespan-scoped Regulatory state exposure lives only in the Chunk 76/78 lifespan module; health router remains provider-unaware and does not import the Chunk 79 accessor; graph remains unwired; provider-SDK allowlist remains the existing two modules.
- `tests/architecture/test_regulatory_intelligence_dependency_boundary.py` — API-owned `get_regulatory_intelligence_query_execution_service` lives in `api/dependencies`; it is a synchronous one-argument reader of `request.app.state.regulatory_intelligence_query_execution_service` returning exact `RegulatoryIntelligenceQueryExecutionService` identity; AST proves no assignment/deletion, no `.execute`, no `Depends`, no route decorator, no HTTPException, no provider SDKs, no Chunk 74–78 composition/lifecycle imports, no LangGraph, and no infrastructure; missing/wrong-type state uses existing `DependencyUnavailableError`; `create_app()` and health remain unwired to the accessor; Chunk 81's dedicated query router uses `Depends` on that accessor.
- `tests/architecture/test_regulatory_intelligence_http_schema_boundary.py` — API-owned `RegulatoryIntelligenceQueryRequest` / `RegulatoryIntelligenceQueryResponse` live in `api/schemas`; they are frozen Pydantic models with `extra="forbid"`; AST proves no route decorator, `APIRouter`, `Depends`, `Request`, Chunk 79 accessor, Chunk 78 lifespan, `.execute`, provider SDKs, settings loaders, LangGraph, agents, or generic mapper/schema factory; application/domain/`create_app()`/health remain unaware of the schema module; Chunk 81's dedicated query router uses these DTOs.
- `tests/architecture/test_regulatory_intelligence_http_route_boundary.py` — API-owned Regulatory query router lives in `api/routers`; it uses `APIRouter` with prefix `/regulatory-intelligence` and POST `/query`; AST proves `Depends(get_regulatory_intelligence_query_execution_service)`, exactly one `.execute(...)` forwarding `request.query_text` and `request.limit`, explicit `RegulatoryConstraintResponse` projection, no provider SDKs, no infrastructure, no settings loaders/client factories, no lifespan/composition builders, no LangGraph, no generic mapper/factory/registry, and no local `try/except`; production include of that router is proven in `test_regulatory_intelligence_app_lifespan_wiring.py`.
- `tests/architecture/test_openai_query_embedding_boundary.py` — `OpenAIDocumentQueryEmbeddingAdapter` lives in `infrastructure/embeddings`; OpenAI SDK imports are confined to the four approved OpenAI infrastructure modules (`infrastructure/embeddings/openai_query_embedding.py`, `infrastructure/embeddings/openai_document_embedding.py`, `infrastructure/regulatory/openai_constraint_inference.py`, and `infrastructure/openai/client.py`) plus the two exact Regulatory API provider-composition modules (`api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`) and the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`); domain/application/ML remain OpenAI-free; HTTP routes/`create_app()` remain provider-SDK-free; the adapter structurally satisfies `DocumentQueryEmbeddingPort` without inheriting it; public result is `DocumentQueryEmbedding`; AST proves `embeddings.create` with `encoding_format="float"`, no chat/completions/responses, no client construction, no API-key/environment access, no retry loop; Chunk 67 builder and `graph.py` remain unwired.
- `tests/architecture/test_openai_document_embedding_boundary.py` — `OpenAIDocumentEmbeddingAdapter` lives in `infrastructure/embeddings`; it structurally satisfies `DocumentEmbeddingPort` without inheriting it; public result is `tuple[DocumentChunkEmbedding, ...]`; OpenAI SDK imports remain confined to those four infrastructure modules plus the two exact Regulatory API provider-composition modules and the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`); domain/application/ML remain OpenAI-free; HTTP routes/`create_app()` remain provider-SDK-free; AST proves `embeddings.create` with `encoding_format="float"`, no chat/completions/responses, no client construction, no API-key/environment access, no retry loop, no generic `EmbeddingPort`/`RAGPort`; `create_app()`, Regulatory runtime composition, and `graph.py` remain unwired.
- `tests/architecture/test_openai_regulatory_constraint_inference_boundary.py` — `OpenAIRegulatoryConstraintInferenceAdapter` lives in `infrastructure/regulatory`; it structurally satisfies `RegulatoryConstraintInferencePort` without inheriting it; public result is `tuple[RegulatoryConstraint, ...]`; OpenAI SDK imports remain confined to the four approved infrastructure modules plus the two exact Regulatory API provider-composition modules (`api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`) and the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`); domain/application/ML remain OpenAI-free; HTTP routes/`create_app()` remain provider-SDK-free; AST proves `responses.parse` with a private `text_format`, no embeddings/chat/completions, no client construction, no API-key/environment access, no retry loop, no generic `LLMPort`; evidence checking is infrastructure-local; Chunk 67 builder and `graph.py` remain unwired.
- `tests/architecture/test_openai_client_boundary.py` — `OpenAISettings` lives in `shared/config` and imports no OpenAI SDK; `create_openai_client` lives in `infrastructure/openai` and may import only typed OpenAI settings plus the OpenAI SDK; SDK retries are disabled (`max_retries=0`); the factory has no environment/`.env` access, no global client, no model selection, no adapter/Qdrant/Redis/SQL/LangGraph/FastAPI/ML coupling; the provider-aware and configured builders do not call the factory; Chunk 74's managed runtime and Chunk 90's managed document-index runtime may import the factory and settings without importing the OpenAI SDK; Chunk 75's loaded runtime and Chunk 91's loaded document-index runtime may call `load_openai_settings` without importing the OpenAI SDK or the factory; `create_app()`, Chunk 67 builder, and `graph.py` remain unwired.
- `tests/architecture/test_regulatory_intelligence_runtime_settings_boundary.py` — `RegulatoryIntelligenceRuntimeSettings` lives in `shared/config`; exactly four required fields (`query_embedding_model`, `constraint_inference_model`, `qdrant_collection_name`, `qdrant_vector_size`); dedicated `ENERGY_REGULATORY_*` prefix and exact environment names; no production defaults, secrets, clients, adapters, or `QdrantDocumentVectorConfig` construction; SDK/infrastructure/application/ML/FastAPI/LangGraph-free; no generic runtime-settings hierarchy or model catalog; `create_app()`, Chunk 71 builder, and `graph.py` remain unwired; Chunk 73 and Chunk 74 consume already-constructed settings; Chunk 75 loads these settings through the published loader.
- `tests/architecture/test_document_vector_index_runtime_settings_boundary.py` — `DocumentVectorIndexRuntimeSettings` lives in `shared/config`; exactly three required fields (`document_embedding_model`, `qdrant_collection_name`, `qdrant_vector_size`); dedicated `ENERGY_DOCUMENT_INDEX_*` prefix and exact environment names; no production defaults, secrets, clients, adapters, query/inference models, or `QdrantDocumentVectorConfig` construction; SDK/infrastructure/application/ML/FastAPI/LangGraph-free; no generic runtime-settings hierarchy or model catalog; `create_app()`, Chunk 87 builder, and `graph.py` remain unwired; Chunk 89 and Chunk 90 consume already-constructed settings; Chunk 91 loads these settings through the published loader; `RegulatoryIntelligenceRuntimeSettings` remains unchanged.
- `tests/architecture/test_document_vector_index_boundary.py` — application `DocumentVectorIndexPort` and `DocumentVectorIndexEntry` expose no Path/bytes/URL/dict/Qdrant/collection/point/search/filter surface; `index()` accepts only `self` and `DocumentVectorIndexEntry` values.
- `tests/architecture/test_document_vector_search_boundary.py` — application `DocumentVectorSearchPort` and `DocumentVectorSearchQuery` expose no Path/bytes/URL/dict/Qdrant/collection/point/score/filter/offset/cursor/query-text surface; `search()` accepts only `self` and `DocumentVectorSearchQuery`; the port is a non-generic Protocol with no indexing method.
- `tests/architecture/test_postgres_persistence_boundary.py` — domain/application/API do not import SQLAlchemy, psycopg, Alembic, or the PostgreSQL factory package; `DatabaseSettings` stays free of runtime engine objects; PostgreSQL infrastructure imports none of FastAPI, agents, ML, ingestion adapters, Redis, or Qdrant.
- `tests/architecture/test_consumption_repository_boundary.py` — `ConsumptionRepositoryPort` exposes no SQLAlchemy/session/raw-source types; `PostgresConsumptionRepository` may import application errors and canonical Consumption contracts but not FastAPI, adapters, Redis, Qdrant, or agents.
- `tests/architecture/test_postgres_compose_profile.py` — `compose.yaml` pins `timescale/timescaledb:2.29.2-pg17`, gates `timescaledb` on the `postgres` profile, binds 127.0.0.1 only, uses a named volume and `pg_isready`, and defines no FastAPI/admin services. n8n is a separate independently gated Compose service.
- `tests/architecture/test_cache_boundary.py` — application `CachePort` is a generic Protocol with no Redis/client/pool/`bytes`/`dict`/`Any` surface; API/`create_app()` remains unwired.
- `tests/architecture/test_redis_cache_boundary.py` — domain/application/API/ML do not import redis-py or infrastructure cache; `RedisSettings` is runtime-free; Redis cache modules may use redis-py and application errors but not FastAPI, SQLAlchemy, Qdrant, agents, LangGraph, or ML; the codec has no pickle/marshal/shelve/Redis client types; `create_app()` still creates no Redis client.
- `tests/architecture/test_redis_compose_profile.py` — `compose.yaml` pins `redis:8.2.9-alpine`, gates `redis` on the `redis` profile, binds 127.0.0.1 only, requires interpolated `REDIS_PASSWORD`, disables persistence/volume, uses authenticated `redis-cli` health, and keeps TimescaleDB, Qdrant, and n8n independently profile-gated.
- `tests/architecture/test_qdrant_client_boundary.py` — domain/application/ML do not import `qdrant_client` or Qdrant infrastructure; HTTP routes/`create_app()` remain Qdrant-client-free; the two exact Regulatory API provider-composition modules may import `AsyncQdrantClient` and `QdrantDocumentVectorConfig`; the Chunk 71 module may also import the published search adapter; the two exact document-index provider-composition modules may import `AsyncQdrantClient` and `QdrantDocumentVectorConfig`; the Chunk 87 module may also import the published index adapter; the document-vector distance mapper may import Qdrant `Distance` and `QdrantDocumentVectorDistance` without constructing clients or calling create/verify/ensure; the configured document-index collection-ensure composition may import `AsyncQdrantClient` and `QdrantDocumentVectorConfig` and call the published mapper plus Chunk 108 ensure without constructing clients; the configured Regulatory collection-readiness composition may import `AsyncQdrantClient` and `QdrantDocumentVectorConfig` and call the published mapper plus Chunk 107 verify without constructing clients; Chunk 74's managed runtime and Chunk 90's managed document-index runtime may import `QdrantSettings` and `create_qdrant_client` without importing the Qdrant SDK; Chunk 90 may also import `QdrantDocumentVectorDistanceSettings` and await Chunk 110 ensure without importing the Qdrant SDK; Chunk 75's loaded runtime and Chunk 91's loaded document-index runtime may call `load_qdrant_settings` without importing the Qdrant SDK or the factory; Chunk 91 may also call `load_qdrant_document_vector_distance_settings`; `QdrantSettings` is runtime-client-free; `client.py` may import `qdrant_client` and `QdrantSettings` but not FastAPI, SQLAlchemy, Redis, agents, LangGraph, ML, application errors, or application document index/search/embedding contracts; `create_app()` remains unwired; Qdrant inference and local embedded mode are disabled.
- `tests/architecture/test_qdrant_document_vector_boundary.py` — concrete `QdrantDocumentVectorIndex` / `QdrantDocumentVectorSearch` may import application errors and the extraction/index/search ports plus `qdrant_client`, but not FastAPI, SQLAlchemy, Redis, agents, LangGraph, ML, NumPy, PDF/OCR, embedding-port modules, collection management, or inference APIs; `create_app()` still constructs no Qdrant client or document-vector adapter; the Chunk 71 provider-aware Regulatory composition module may construct `QdrantDocumentVectorSearch` from an injected client and existing config; the Chunk 73 configured module may construct `QdrantDocumentVectorConfig` only; the Chunk 87 provider-aware document-index composition module may construct `QdrantDocumentVectorIndex` from an injected client and existing config; the Chunk 89 configured module may construct `QdrantDocumentVectorConfig` only.
- `tests/architecture/test_qdrant_live_integration_boundary.py` — `compose.yaml` pins `qdrant/qdrant:v1.19.1`, gates `qdrant` on the `qdrant` profile, publishes loopback REST 6333 only, requires interpolated `QDRANT_API_KEY`, disables telemetry, uses named volume `qdrant-data`, and keeps TimescaleDB/Redis/n8n independently profile-gated. `collection_creation.py` may construct `VectorParams` and call `create_collection` with a caller-supplied `Distance` type; `collection_readiness.py` may inspect `VectorParams` and the `Distance` type without mutating collections; `collection_ensure.py` may import the `Distance` type and call `collection_exists` without constructing `VectorParams` or calling `create_collection` / `get_collection`. Other production Qdrant modules still must not call `create_collection`. Concrete `Distance` members remain forbidden in all production Qdrant infrastructure modules; the composition distance mapper is the only production module allowed to contain `Distance.COSINE` / `DOT` / `EUCLID` / `MANHATTAN`. Live tests own ephemeral collections. `create_app()` remains unwired.
- `tests/architecture/test_qdrant_document_collection_readiness_boundary.py` — `verify_qdrant_document_collection_ready` lives in Qdrant infrastructure as the only public production function. AST proves one `get_collection` call, `VectorParams` inspection without construction, keyword-only `client`/`config`/`distance` with no default, existing vector distance compared to caller `distance`, no hardcoded `Distance` members, no collection mutation, and no runtime/HTTP/LangGraph wiring.
- `tests/architecture/test_qdrant_document_collection_creation_boundary.py` — `create_qdrant_document_collection` lives in Qdrant infrastructure as the only public production function. AST proves one `VectorParams` construction, one `create_collection` call, no hardcoded `Distance` members, no existence lookup, no ensure/recreate/update/delete, and no runtime/HTTP/LangGraph wiring.
- `tests/architecture/test_qdrant_document_collection_ensure_boundary.py` — `ensure_qdrant_document_collection_ready` lives in Qdrant infrastructure as the only public production function. AST proves one `collection_exists` probe, one create-if-missing branch, one verify-if-present branch, exact `client`/`config`/`distance` forwarding, no `VectorParams`, no direct `create_collection`/`get_collection`, no hardcoded `Distance` members, no retry, and no runtime/HTTP/LangGraph wiring. Creation and readiness must not import ensure.
- `tests/architecture/test_qdrant_document_vector_distance_boundary.py` — provider-neutral `QdrantDocumentVectorDistanceSettings` lives in `shared/config` and imports no `qdrant_client`; API composition `map_qdrant_document_vector_distance` is the only production module allowed to contain concrete `Distance.COSINE` / `DOT` / `EUCLID` / `MANHATTAN`; the mapper is total, has no default, and does not call create/verify/ensure; Chunk 111 authorizes the loaded document-index runtime to load distance settings and the managed runtime to receive them already constructed; Chunk 112 may call the mapper from the Regulatory collection-readiness composition; Chunk 113 authorizes the loaded Regulatory runtime to load distance settings and the managed runtime to receive them already constructed; the mapper, `create_app()`, production/document-index/Regulatory lifespans, HTTP, and LangGraph remain unwired from mapping.
- `tests/architecture/test_document_vector_index_collection_ensure_composition_boundary.py` — `ensure_configured_document_vector_index_collection_ready` lives under `energy_trading.api.composition` as the only public async function. AST proves keyword-only `client` / `runtime_settings` / `distance_settings`, one `QdrantDocumentVectorConfig` from collection name and vector size, one mapper invocation, one awaited Chunk 108 ensure, injected-client forwarding, no settings loaders, no client factories, no concrete `Distance` members, no FastAPI/LangGraph/OpenAI/PDF, and no manager/registry types. Chunk 111's managed document-index runtime is the sole runtime caller; `create_app()`, production/document-index lifespans, loaded runtime, Regulatory runtime, and LangGraph do not call it directly.
- `tests/architecture/test_regulatory_intelligence_collection_readiness_composition_boundary.py` — `verify_configured_regulatory_intelligence_collection_ready` lives under `energy_trading.api.composition` as the only public async function. AST proves keyword-only `client` / `runtime_settings` / `distance_settings`, one `QdrantDocumentVectorConfig` from Regulatory collection name and vector size, one mapper invocation, one awaited Chunk 107 verify, injected-client forwarding, no settings loaders, no client factories, no create/ensure/`collection_exists`, no concrete `Distance` members, no FastAPI/LangGraph/OpenAI/PDF, and no manager/registry types. Chunk 113's managed Regulatory runtime is the sole runtime caller; `create_app()`, production/document-index/Regulatory lifespans, loaded runtime, HTTP, PDF execution, and LangGraph do not call it directly.
- `tests/architecture/test_regulatory_intelligence_runtime_collection_readiness_boundary.py` — Chunk 113 ownership: managed runtime may import `QdrantDocumentVectorDistanceSettings` and `verify_configured_regulatory_intelligence_collection_ready`; it awaits that Chunk 112 function once with the locally managed Qdrant client before the configured builder; loaded runtime loads distance settings and forwards them without calling verify; `create_app()`, production lifespan, and Regulatory lifespan do not own verify.
- `tests/architecture/test_n8n_compose_profile.py` — `compose.yaml` pins `n8nio/n8n:2.37.10`, gates `n8n` on the `n8n` profile, publishes loopback HTTP 5678 only, requires interpolated `N8N_ENCRYPTION_KEY`, disables diagnostics/version/templates/personalization, uses named volume `n8n-data`, and keeps TimescaleDB/Redis/Qdrant independently profile-gated. Production Python does not import an n8n SDK. `create_app()` remains unwired. No production workflow artifacts.
- `tests/architecture/test_agent_boundary.py` — application `AgentName` / `AgentPort[TRequest, TResult]` import none of infrastructure/ML/API/domain, FastAPI/Starlette, LangGraph/LangChain, LLM SDKs, Qdrant/Redis/SQLAlchemy, ML libraries, HTTP clients, or n8n. The port is a generic Protocol, not an ABC; public operations are only `name` and async `run(self, request)`. No `Any`/`dict`/`Mapping` payload surface and no `create_app()` wiring.
- `tests/architecture/test_orchestration_state_boundary.py` — application `WorkflowState` is a non-generic frozen snapshot importing only stdlib plus canonical `AdapterDiagnostic`. It exposes exactly `workflow_id`, `portfolio_id`, `delivery_date`, `correlation_id`, `phase`, `status`, and `diagnostics`. No payload/dict/`Any`/Mapping bag, no agent request/result fields, no retry/fallback/routing fields, no persistence/cache fields, no LangGraph types, no `create_app()` wiring, and no agent class in the orchestration package. The orchestration package may import LangGraph only from the graph module; `state.py` stays LangGraph-free.
- `tests/architecture/test_langgraph_boundary.py` — production `langgraph` imports are allowed only in `application/orchestration/graph.py`. `state.py`, `failure_policy.py`, `parallel_ingestion.py`, `parallel_ingestion_context.py`, `parallel_ingestion_executor.py`, `parallel_ingestion_workflow.py`, `parallel_ingestion_failure_context.py`, `parallel_ingestion_failure_context_resolution.py`, `parallel_ingestion_failure_context_preparation.py`, `parallel_ingestion_failure_decision.py`, `parallel_ingestion_failure_transition.py`, `parallel_ingestion_failure_action.py`, `parallel_ingestion_failure_handling.py`, `parallel_ingestion_agent_failure.py`, `parallel_ingestion_exception_group.py`, `parallel_ingestion_failure_fact.py`, `parallel_ingestion_failure_classification.py`, `parallel_ingestion_failure_selection.py`, `parallel_ingestion_attempt_number.py`, `parallel_ingestion_strict_single_failure_selector.py`, `parallel_ingestion_initial_attempt_number_source.py`, `parallel_ingestion_initial_failure_policy.py`, `parallel_ingestion_failure_runtime_handling.py`, `regulatory_intelligence_context.py`, `regulatory_intelligence_workflow_step.py`, agent base, domain, infrastructure, ML, API, and unrelated application ports/use cases remain LangGraph-free. The graph module consumes `WorkflowState`, injects `ParallelIngestionWorkflowStep` and `ParallelIngestionFailureRuntimeHandlingService`, and delegates the success-transition node to `advance_after_parallel_ingestion`. It imports no agents/infrastructure/ML/API/LangChain/`ParallelIngestionPlan`/`ParallelIngestionSuccess`/`ParallelIngestionExecutionPort`/`ParallelIngestionWorkflowContextPort`/`ConcurrentParallelIngestionExecutor`/`FailurePolicyPort`/`fail_parallel_ingestion`/`ParallelIngestionFailureDecisionService`/`build_parallel_ingestion_failure_policy_context`/`ParallelIngestionFailureContextResolutionService`/`ParallelIngestionFailureContextPreparationService`/`InitialParallelIngestionFailurePolicy`/`execute_parallel_ingestion_failure_action`/`ParallelIngestionFailureHandlingService`/`ParallelIngestionAgentFailure`/`extract_parallel_ingestion_agent_failures`/`classify_parallel_ingestion_agent_failure`/`classify_parallel_ingestion_agent_failures`/`ParallelIngestionFailureFact`/`ParallelIngestionFailureSelectionPort`/`ParallelIngestionAttemptNumberPort`/`StrictSingleParallelIngestionFailureSelector`/`InitialParallelIngestionAttemptNumberSource`/`RegulatoryIntelligenceWorkflowContextPort`/`RegulatoryIntelligenceWorkflowStep`. It may use one Phase-2-specific conditional edge after `parallel_ingestion` and may import `WorkflowPhase`/`WorkflowStatus`/`InvalidRequestError` for fail-closed routing. It does not use messages, reducers, checkpointers, stores, or `AgentPort`. AST proves the graph catches `BaseExceptionGroup` rather than broad `Exception`/`BaseException`. Factory `build_workflow_graph` requires keyword-only `parallel_ingestion_step` and `parallel_ingestion_failure_runtime_handler`. Topology is `START → workflow_entry → parallel_ingestion`, then `ingestion`/`running` → `parallel_ingestion_success_transition` → `END` or `ingestion`/`failed` → `END`. `create_app()` remains unwired.
- `tests/architecture/test_failure_policy_boundary.py` — application `FailureAction` / `FailurePolicyContext` / `FailurePolicyPort` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, LLM/ML libraries, or Tenacity. Context fields are exactly `phase`, `error_code`, `attempt_number`, and optional `agent_name`. No exception objects, delay/backoff/max-attempt fields, `WorkflowState`, or callbacks. The port is a non-generic Protocol whose only public operation is async `decide`. The contract module remains implementation-free and does not inherit a concrete policy. Chunk 60's `InitialParallelIngestionFailurePolicy` lives in a separate module and does not inherit the Protocol. The skeleton graph does not inject the port. `failure_policy.py` does not import `ParallelIngestionFailureDecisionService`.
- `tests/architecture/test_weather_agent_boundary.py` — `WeatherAndRenewableForecastAgent` and `WeatherRecordSourcePort` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, or ML/LLM libraries. The source port is a non-generic Protocol whose only public operation is keyword-only async `fetch` returning `tuple[WeatherRecord, ...]`. No provider implementation, no `Any`/`dict`/`Mapping` payload, no graph or `create_app()` wiring.
- `tests/architecture/test_hydro_agent_boundary.py` — `HydroResourcesAgent` and `HydroRecordSourcePort` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, or ML/LLM libraries. The source port is a non-generic Protocol whose only public operation is keyword-only async `fetch` returning `tuple[HydroRecord, ...]`. No provider implementation, no hydrological calculation, no Generation Availability coupling, no `Any`/`dict`/`Mapping` payload, no graph or `create_app()` wiring.
- `tests/architecture/test_generation_availability_agent_boundary.py` — `GenerationAvailabilityAgent` and `GenerationAvailabilityRecordSourcePort` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, or ML/LLM libraries. The source port is a non-generic Protocol whose only public operation is keyword-only async `fetch` returning `tuple[GenerationAvailabilityRecord, ...]`. No provider implementation, no status inference, no capacity calculation, no fleet-completeness policy, no Hydro coupling, no `Any`/`dict`/`Mapping` payload, no graph or `create_app()` wiring.
- `tests/architecture/test_news_intelligence_agent_boundary.py` — `NewsIntelligenceAgent` and `NewsEventSourcePort` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, scrapers/feed parsers, or ML/LLM libraries. The source port is a non-generic Protocol whose only public operation is keyword-only async `fetch` returning `tuple[NewsEvent, ...]`. No provider implementation, no HTML/RSS/vendor payload, no summarization, no sentiment/relevance/impact inference, no embedding/Qdrant coupling, no `Any`/`dict`/`Mapping` payload, no graph or `create_app()` wiring.
- `tests/architecture/test_market_monitoring_agent_boundary.py` — `MarketMonitoringAgent` and `MarketPriceRecordSourcePort` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, or ML/LLM libraries. The source port is a non-generic Protocol whose only public operation is keyword-only async `fetch` returning `tuple[MarketPriceRecord, ...]`. No provider implementation, no currency/interval/cadence configuration, no `PriceForecastPoint` coupling, no market-status model, no `Any`/`dict`/`Mapping` payload, no graph or `create_app()` wiring.
- `tests/architecture/test_regulatory_intelligence_agent_boundary.py` — `RegulatoryIntelligenceAgent` and `RegulatoryConstraintInferencePort` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, OpenAI/Anthropic, or ML/LLM libraries. The inference port is a non-generic Protocol whose only public operation is keyword-only async `infer` returning `tuple[RegulatoryConstraint, ...]`. No generic `LLMPort`, no Qdrant client type, no `Any`/`dict`/`Mapping` payload, no hardcoded Armenian DAM-rule constants, no `RegulatoryConstraint` construction in the agent, no graph or `create_app()` wiring. The application agent remains OpenAI-free; the concrete OpenAI inference adapter lives in infrastructure. Production `langgraph` imports remain confined to the existing graph module.
- `tests/architecture/test_parallel_ingestion_plan_boundary.py` — application `ParallelIngestionPlan`, `ParallelIngestionExecutionPort`, and `ParallelIngestionSuccess` import none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, or ML/LLM libraries. The plan DTO has exactly the five existing typed request fields and annotations. The success DTO has exactly the five existing typed result fields and annotations. The execution port is a non-generic Protocol whose only public operation is `async execute(self, plan: ParallelIngestionPlan) -> ParallelIngestionSuccess`. The contract module has no concrete executor, `asyncio.gather`/`TaskGroup`, agent `.run()` invocation, `Any`/`dict`/`Mapping` payload, callbacks, exception objects, graph/runtime types, generic outcome types, or partial/failure/degraded fields. `WorkflowState`, the skeleton graph, `FailurePolicyPort`, and `create_app()` remain unwired to the contract module.
- `tests/architecture/test_parallel_ingestion_executor_boundary.py` — `ConcurrentParallelIngestionExecutor` imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, or Tenacity. Constructor owns exactly the five existing application agents. `execute` is async and typed `ParallelIngestionPlan` → `ParallelIngestionSuccess`. Production uses `asyncio.TaskGroup` and five `create_task` calls, not `asyncio.gather`/`wait`/`as_completed`/`to_thread`/thread pools. Ordinary agent failures are wrapped as `ParallelIngestionAgentFailure` with `raise ... from`. Cancellation is not wrapped. No `FailurePolicyPort`, `WorkflowState`, `ExceptionGroup` interpretation, registry/factory, or `create_app()` wiring. Graph remains unwired.
- `tests/architecture/test_parallel_ingestion_agent_failure_boundary.py` — `ParallelIngestionAgentFailure` is the only production class in `parallel_ingestion_agent_failure.py`. Constructor accepts exactly `AgentName`. The module may import canonical `AgentName`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, `WorkflowState`, `FailurePolicyContext`/`FailurePolicyPort`/`FailureAction`, decision/handling services, or traceback/payload fields. There is no generic failure hierarchy or exception DTO. `graph.py` and `create_app()` remain unwired. The executor and the ExceptionGroup extractor may import the exception.
- `tests/architecture/test_parallel_ingestion_exception_group_boundary.py` — `extract_parallel_ingestion_agent_failures` is the only public production function in `parallel_ingestion_exception_group.py`. There is no public class, Protocol, ABC, registry, factory, or visitor. Input is a `BaseExceptionGroup`; return type is `tuple[ParallelIngestionAgentFailure, ...]`. The module may import `InvalidRequestError` and `ParallelIngestionAgentFailure`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, `WorkflowState`, `FailurePolicyContext`/`FailurePolicyPort`/`FailureAction`, decision/handling services, the five agents, or the executor. Traversal is recursive over `.exceptions` without `.split()` / `.subgroup()` / `.derive()`, without inspecting exception text or `__cause__`, and without error-code mapping. `graph.py`, the executor, the sanitized-fact classifier, and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_failure_fact_boundary.py` — `ParallelIngestionFailureFact` is the only production DTO class and `classify_parallel_ingestion_agent_failure` is the only public function in `parallel_ingestion_failure_fact.py`. DTO fields are exactly `agent_name` and `error_code`; the DTO is frozen. The module may import stdlib dataclass, `AgentName`, `ApplicationError`, and `ParallelIngestionAgentFailure`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `WorkflowState`, `FailurePolicyContext`/`FailurePolicyPort`/`FailureAction`, decision/handling services, the context builder, the action executor, the executor implementation, the ExceptionGroup extractor, or the five concrete agents. There is no Protocol/ABC/registry/factory, no traceback inspection, no exception-message parsing, and no exception-class-name-derived code. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_failure_classification_boundary.py` — `classify_parallel_ingestion_agent_failures` is the only public production function in `parallel_ingestion_failure_classification.py`. There is no public class, Protocol, ABC, registry, or factory. Input is `tuple[ParallelIngestionAgentFailure, ...]`; return type is `tuple[ParallelIngestionFailureFact, ...]`. The module may import `ParallelIngestionAgentFailure`, `ParallelIngestionFailureFact`, and `classify_parallel_ingestion_agent_failure`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `ApplicationError`, `WorkflowState`, `FailurePolicyContext`/`FailurePolicyPort`/`FailureAction`, decision/handling services, the context builder, the action executor, the ExceptionGroup extractor, the executor implementation, or the five concrete agents. There is no ExceptionGroup traversal/rebuilding, no `__cause__` inspection, no second error-code mapping, and no sorting/deduplication/grouping/selection machinery. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_failure_selection_boundary.py` — `ParallelIngestionFailureSelectionPort` is the only public production Protocol in `parallel_ingestion_failure_selection.py`. There is no public function, concrete class, enum, registry, factory, or selector implementation. The only public operation is synchronous `select(self, facts: tuple[ParallelIngestionFailureFact, ...]) -> ParallelIngestionFailureFact`. The module may import typing `Protocol` and `ParallelIngestionFailureFact`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `ApplicationError`, `WorkflowState`, `FailurePolicyContext`/`FailurePolicyPort`/`FailureAction`, decision/handling services, the context builder, the action executor, attribution/extraction/classification, the executor implementation, or the five concrete agents. There is no `[0]`/`[-1]` indexing, `min`/`max`/`sorted`, priority tables, or winner semantics. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_attempt_number_boundary.py` — `ParallelIngestionAttemptNumberPort` is the only public production Protocol in `parallel_ingestion_attempt_number.py`. There is no public function, concrete class, enum, registry, factory, or tracker implementation. The only public operation is async `get_attempt_number(self, workflow_id: str) -> int`. The module may import typing `Protocol` only. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `ApplicationError`, `WorkflowState`/`WorkflowPhase`/`WorkflowStatus`, `FailurePolicyContext`/`FailurePolicyPort`/`FailureAction`, decision/handling services, the context builder, the action executor, attribution/extraction/classification/selection, the executor implementation, or the five concrete agents. There is no increment/reset/set/record write API and no storage backend. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_failure_context_resolution_boundary.py` — `ParallelIngestionFailureContextResolutionService` is the only production class in `parallel_ingestion_failure_context_resolution.py`. Constructor injects exactly `ParallelIngestionFailureSelectionPort` and `ParallelIngestionAttemptNumberPort`. Public operation is keyword-only `async resolve(*, workflow_id: str, phase: WorkflowPhase, facts: tuple[ParallelIngestionFailureFact, ...]) -> FailurePolicyContext`. The module may import `WorkflowPhase`, `FailurePolicyContext`, `ParallelIngestionFailureFact`, the two injected ports, and `build_parallel_ingestion_failure_policy_context`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `WorkflowState`, `FailureAction`/`FailurePolicyPort`, decision/handling services, the action executor, attribution/extraction/classification, the executor implementation, workflow step, workflow context, or the five concrete agents. `resolve` selects once, awaits attempt lookup once, and delegates context construction to the published builder without indexing, sorting, try/except fallback, attempt defaulting, or direct `FailurePolicyContext(...)` construction. The service does not import or construct `StrictSingleParallelIngestionFailureSelector`. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_strict_single_failure_selector_boundary.py` — `StrictSingleParallelIngestionFailureSelector` is the only public production class in `parallel_ingestion_strict_single_failure_selector.py`. The only public operation is synchronous `select(self, facts: tuple[ParallelIngestionFailureFact, ...]) -> ParallelIngestionFailureFact`. The class does not inherit `ParallelIngestionFailureSelectionPort`. Allowed imports are `InvalidRequestError` and `ParallelIngestionFailureFact`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `WorkflowState`/`WorkflowPhase`/`WorkflowStatus`, `FailureAction`/`FailurePolicyContext`/`FailurePolicyPort`, decision/handling/action/builder/resolution services, attempt-number port, attribution/extraction/classification, executor, workflow step, the five agents, or graph. Production code does not use `sorted`/`min`/`max`/`.sort`, priority mappings, sets for deduplication, ranking dictionaries, or counters. Exact-one extraction is allowed only after a cardinality guard equivalent to `len(facts) == 1`. Zero and multiple facts fail closed. There is no first/last/agent/error/severity winner, no deduplication, and no aggregation. Multi-failure resolution remains unresolved. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_initial_attempt_number_source_boundary.py` — `InitialParallelIngestionAttemptNumberSource` is the only public production class in `parallel_ingestion_initial_attempt_number_source.py`. The only public operation is async `get_attempt_number(self, workflow_id: str) -> int`. The class does not inherit `ParallelIngestionAttemptNumberPort`. The module has no production imports. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `WorkflowState`/`WorkflowPhase`/`WorkflowStatus`, failure facts, the selector, context-resolution service, `FailureAction`/`FailurePolicyContext`/`FailurePolicyPort`, decision/handling services, executor, agents, or graph. Production code returns the literal integer `1` with no arithmetic, dictionaries, sets, counters, increment/reset/set/record methods, persistence, locks, timestamps, or randomness. The source is not a tracker. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_failure_context_preparation_boundary.py` — `ParallelIngestionFailureContextPreparationService` is the only public production class in `parallel_ingestion_failure_context_preparation.py`. Constructor injects exactly `ParallelIngestionFailureContextResolutionService`. The only public operation is keyword-only `async prepare(*, workflow_id: str, phase: WorkflowPhase, failure_group: BaseExceptionGroup) -> FailurePolicyContext`. Allowed imports are `WorkflowPhase`, `FailurePolicyContext`, `extract_parallel_ingestion_agent_failures`, `classify_parallel_ingestion_agent_failures`, and `ParallelIngestionFailureContextResolutionService`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `WorkflowState`, `FailureAction`/`FailurePolicyPort`, decision/handling services, action executor, selector, attempt-number port, initial attempt source, executor, workflow step, five agents, or graph. `prepare` extracts once, classifies once, and awaits context resolution once without traversing `.exceptions`, inspecting `__cause__`, constructing `ParallelIngestionFailureFact` or `FailurePolicyContext` directly, selecting via indexing, or hardcoding attempt `1`. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_initial_failure_policy_boundary.py` — `InitialParallelIngestionFailurePolicy` is the only public production class in `parallel_ingestion_initial_failure_policy.py`. The only public operation is async `decide(self, context: FailurePolicyContext) -> FailureAction`. The class does not inherit `FailurePolicyPort`. Allowed imports are `FailureAction` and `FailurePolicyContext`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, `WorkflowState`, decision/handling services, action executor, selector, attempt-number port/source, preparation/resolution services, extractor, classifier, executor, workflow step, five agents, or graph. Production `decide` returns exactly `FailureAction.FAIL` with no `if`/`match` branching, no dictionaries/sets, no `sorted`/`min`/`max`, and no inspection of context fields. It is not a generic policy engine. `graph.py` and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_failure_runtime_handling_boundary.py` — `ParallelIngestionFailureRuntimeHandlingService` is the only public production class in `parallel_ingestion_failure_runtime_handling.py`. Constructor injects exactly `ParallelIngestionFailureContextPreparationService` and `ParallelIngestionFailureHandlingService`. The only public operation is keyword-only `async handle(*, state: WorkflowState, failure_group: BaseExceptionGroup) -> WorkflowState`. Allowed imports are `WorkflowState`, the preparation service, and the handling service. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, selector, attempt-number port/source, initial failure policy, extractor, classifier, context builder, decision service, action executor, `fail_parallel_ingestion`, five agents, executor, workflow step, or graph. There is no Protocol, enum, factory, registry, generic runtime framework, or result wrapper. `handle` awaits preparation exactly once then existing handling exactly once without inspecting exception groups, classifying error codes, selecting facts, resolving attempt numbers, calling `FailurePolicyPort`, branching on `FailureAction`, or constructing a failed `WorkflowState`. It is the outer application composition for Phase 2 failure handling and does not duplicate policy or action ownership. `graph.py` may import and inject this outer service; it must not import preparation, handling, policy, or other lower-level failure internals. `create_app()` remains unwired.
- `tests/architecture/test_parallel_ingestion_context_boundary.py` — `ParallelIngestionWorkflowContextPort` is a non-generic Protocol with exactly two public async operations: `resolve_plan(self, workflow_id) -> ParallelIngestionPlan` and `record_success(self, workflow_id, success) -> None`. The `workflow_id` annotation matches published `WorkflowState.workflow_id`. The application module imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, or ML/LLM libraries. No `Any`/`dict`/`Mapping` payload, callbacks, exception objects, persistence sessions, or graph runtime types. The application module remains Protocol-only. Durable Redis/Postgres/filesystem context classes remain absent. `WorkflowState`, the graph, the executor, `FailurePolicyPort`, and `create_app()` remain unwired to the port.
- `tests/architecture/test_in_memory_parallel_ingestion_context_boundary.py` — infrastructure `InMemoryParallelIngestionWorkflowContext` structurally implements the context port without inheriting it. The module may import stdlib, application errors, and the plan/success DTOs. It imports none of LangGraph/LangChain, FastAPI/Starlette, API, ML, Redis, CachePort, SQLAlchemy/psycopg/Alembic, Qdrant, HTTP clients, n8n, filesystem persistence, ingestion adapters, the five agents, the executor, the workflow step, or `FailurePolicyPort`. Constructor copies `Mapping[str, ParallelIngestionPlan]`. Public operations are only `resolve_plan` and `record_success`. Writes use `asyncio.Lock`. `create_app()` and the graph remain unwired.
- `tests/architecture/test_parallel_ingestion_workflow_boundary.py` — `ParallelIngestionWorkflowStep` is a non-generic concrete class whose only public operation is `async run(self, state: WorkflowState) -> WorkflowState`. Constructor annotations are exactly `ParallelIngestionWorkflowContextPort` and `ParallelIngestionExecutionPort`. The module imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, Tenacity, the five ingestion agents, `ConcurrentParallelIngestionExecutor`, `FailurePolicyPort`, or `ParallelIngestionFailureDecisionService`. `run` does not construct, replace, or mutate `WorkflowState`. The workflow-step module, executor, context Protocol module, `FailurePolicyPort`, and `create_app()` remain unwired to constructing the step. LangGraph may import the step class for injection only.
- `tests/architecture/test_parallel_ingestion_transition_boundary.py` — `advance_after_parallel_ingestion(state: WorkflowState) -> WorkflowState` is the only public surface of `parallel_ingestion_transition.py`. The module may import stdlib `dataclasses.replace`, application errors, and orchestration state types. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, the five ingestion agents, `ParallelIngestionPlan`/`ParallelIngestionSuccess`/`ParallelIngestionExecutionPort`/`ParallelIngestionWorkflowContextPort`/`ConcurrentParallelIngestionExecutor`/`ParallelIngestionWorkflowStep`, or `FailurePolicyPort`. There is no Protocol, factory, registry, or generic state machine. `WorkflowState` still has no transition methods. The transition module remains LangGraph-free. `graph.py` may import and call the published function from node `parallel_ingestion_success_transition` and must not reimplement phase/status assignment. `create_app()` remains unwired.
- `tests/architecture/test_parallel_ingestion_failure_transition_boundary.py` — `fail_parallel_ingestion(state: WorkflowState) -> WorkflowState` is the only public surface of `parallel_ingestion_failure_transition.py`. The module may import stdlib `dataclasses.replace`, application errors, and orchestration state types. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, the five ingestion agents, `ParallelIngestionPlan`/`ParallelIngestionSuccess`/`ParallelIngestionExecutionPort`/`ParallelIngestionWorkflowContextPort`/`ConcurrentParallelIngestionExecutor`/`ParallelIngestionWorkflowStep`, `FailurePolicyPort`, or `ParallelIngestionFailureDecisionService`. There is no Protocol, factory, registry, generic state machine, exception parameter, or diagnostic construction. `WorkflowState` still has no `fail()` / `mark_failed()` methods. The module remains LangGraph-free. `graph.py` does not import or call `fail_parallel_ingestion`. `FailurePolicyPort` remains unwired. `create_app()` remains unwired.
- `tests/architecture/test_parallel_ingestion_failure_decision_boundary.py` — `ParallelIngestionFailureDecisionService` is the only production class in `parallel_ingestion_failure_decision.py`. Constructor injects exactly `FailurePolicyPort`. Public operation is `async decide(self, context: FailurePolicyContext) -> FailureAction`. The module may import existing `FailureAction`, `FailurePolicyContext`, and `FailurePolicyPort`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, the five ingestion agents, `ParallelIngestionPlan`/`ParallelIngestionSuccess`/`ParallelIngestionExecutionPort`/`ParallelIngestionWorkflowContextPort`/`ConcurrentParallelIngestionExecutor`/`ParallelIngestionWorkflowStep`, `WorkflowState`, `fail_parallel_ingestion`, the success-transition function, or `build_parallel_ingestion_failure_policy_context`. There is no concrete policy construction, exception argument, `FailureAction` branching, retry loop, sleep/backoff, or LangGraph coupling. `graph.py`, `parallel_ingestion_workflow.py`, `fail_parallel_ingestion`, and `failure_policy.py` remain unwired to the service. `create_app()` remains unwired.
- `tests/architecture/test_parallel_ingestion_failure_context_boundary.py` — `build_parallel_ingestion_failure_policy_context` is the only public surface of `parallel_ingestion_failure_context.py`. The module may import `FailurePolicyContext`, `WorkflowPhase`, and `AgentName`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, `FailureAction`/`FailurePolicyPort`, `WorkflowState`, `fail_parallel_ingestion`, `ParallelIngestionFailureDecisionService`, the five ingestion agents, or plan/success/execution/context/executor/step types. There is no public class, no exception/`BaseException` parameter, no `try`, no policy decision, no action execution, and no graph coupling. `graph.py`, `parallel_ingestion_workflow.py`, the decision service, `fail_parallel_ingestion`, `failure_policy.py`, and `state.py` remain unwired to the builder. `create_app()` remains unwired.
- `tests/architecture/test_parallel_ingestion_failure_action_boundary.py` — `execute_parallel_ingestion_failure_action` is the only public surface of `parallel_ingestion_failure_action.py`. The module may import `FailureAction`, `WorkflowState`, `fail_parallel_ingestion`, and `InvalidRequestError`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, `FailurePolicyContext`/`FailurePolicyPort`, `ParallelIngestionFailureDecisionService`, the context builder, the success transition, the five ingestion agents, or plan/success/execution/context/executor/step types. There is no public class, Protocol, or service hierarchy. `FAIL` delegates exactly once to `fail_parallel_ingestion` without duplicating phase/status mutation. `RETRY` and `FALLBACK` reject without retry loops, sleep/backoff, or diagnostic construction. `graph.py`, the decision service, the context builder, `fail_parallel_ingestion`, `failure_policy.py`, and `create_app()` remain unwired.
- `tests/architecture/test_parallel_ingestion_failure_handling_boundary.py` — `ParallelIngestionFailureHandlingService` is the only production class in `parallel_ingestion_failure_handling.py`. Constructor injects exactly `ParallelIngestionFailureDecisionService`. Public operation is keyword-only `async handle(*, state: WorkflowState, context: FailurePolicyContext) -> WorkflowState`. The module may import `WorkflowState`, `FailurePolicyContext`, `ParallelIngestionFailureDecisionService`, and `execute_parallel_ingestion_failure_action`. It imports none of infrastructure/ML/API, LangGraph/LangChain, FastAPI/Starlette, Redis/SQLAlchemy/Qdrant, HTTP clients, n8n, ML/LLM libraries, `FailurePolicyPort`, `fail_parallel_ingestion`, or `build_parallel_ingestion_failure_policy_context`. There is no Protocol, ABC, registry, factory, or generic handler. `handle` awaits `decide(context)` exactly once and forwards the returned action without branching. `graph.py` and `create_app()` remain unwired.

Broader ML/agent import rules remain for later chunks.

## Initial folder tree

```text
.
├── .cursorrules
├── .env.example
├── .gitignore
├── .python-version
├── compose.yaml
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
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
│       │   ├── errors.py
│       │   ├── agents/
│       │   │   ├── base.py
│       │   │   ├── generation_availability.py
│       │   │   ├── hydro_resources.py
│       │   │   ├── market_monitoring.py
│       │   │   ├── news_intelligence.py
│       │   │   ├── regulatory_intelligence.py
│       │   │   └── weather_and_renewable_forecast.py
│       │   ├── orchestration/
│       │   │   ├── document_extraction_index_execution.py
│       │   │   ├── document_vector_index_entry_preparation.py
│       │   │   ├── document_vector_index_execution.py
│       │   │   ├── document_vector_search_query_preparation.py
│       │   │   ├── failure_policy.py
│       │   │   ├── graph.py
│       │   │   ├── parallel_ingestion.py
│       │   │   ├── parallel_ingestion_agent_failure.py
│       │   │   ├── parallel_ingestion_attempt_number.py
│       │   │   ├── parallel_ingestion_context.py
│       │   │   ├── parallel_ingestion_exception_group.py
│       │   │   ├── parallel_ingestion_executor.py
│       │   │   ├── parallel_ingestion_failure_action.py
│       │   │   ├── parallel_ingestion_failure_classification.py
│       │   │   ├── parallel_ingestion_failure_context.py
│       │   │   ├── parallel_ingestion_failure_context_preparation.py
│       │   │   ├── parallel_ingestion_failure_context_resolution.py
│       │   │   ├── parallel_ingestion_failure_decision.py
│       │   │   ├── parallel_ingestion_failure_fact.py
│       │   │   ├── parallel_ingestion_failure_handling.py
│       │   │   ├── parallel_ingestion_failure_runtime_handling.py
│       │   │   ├── parallel_ingestion_failure_selection.py
│       │   │   ├── parallel_ingestion_failure_transition.py
│       │   │   ├── parallel_ingestion_initial_attempt_number_source.py
│       │   │   ├── parallel_ingestion_initial_failure_policy.py
│       │   │   ├── parallel_ingestion_strict_single_failure_selector.py
│       │   │   ├── parallel_ingestion_transition.py
│       │   │   ├── parallel_ingestion_workflow.py
│       │   │   ├── regulatory_intelligence_query_execution.py
│       │   │   └── state.py
│       │   ├── ports/
│       │   │   ├── cache.py
│       │   │   ├── consumption_repository.py
│       │   │   ├── dlq.py
│       │   │   ├── document_embedding.py
│       │   │   ├── document_extraction.py
│       │   │   ├── document_query_embedding.py
│       │   │   ├── document_vector_index.py
│       │   │   ├── document_vector_search.py
│       │   │   ├── generation_availability_records.py
│       │   │   ├── hydro_records.py
│       │   │   ├── market_price_records.py
│       │   │   ├── news_events.py
│       │   │   ├── regulatory_constraint_inference.py
│       │   │   ├── structured_ingestion.py
│       │   │   └── weather_records.py
│       │   └── use_cases/
│       ├── ml/
│       │   ├── common/
│       │   ├── load_forecast/
│       │   └── price_forecast/
│       ├── infrastructure/
│       │   ├── adapters/
│       │   │   ├── structured/
│       │   │   │   ├── csv/
│       │   │   │   ├── excel/
│       │   │   │   ├── normalization/
│       │   │   │   ├── time_series/
│       │   │   │   └── schema_mapping/
│       │   │   ├── unstructured/
│       │   │   │   └── pdf_text_extraction.py
│       │   │   └── external_services/
│       │   ├── persistence/
│       │   │   ├── dlq.py
│       │   │   └── postgres/
│       │   │       ├── engine.py
│       │   │       ├── tables.py
│       │   │       └── consumption_repository.py
│       │   ├── cache/
│       │   │   ├── codec.py
│       │   │   ├── redis_cache.py
│       │   │   └── redis_client.py
│       │   ├── orchestration/
│       │   │   └── parallel_ingestion_context.py
│       │   ├── embeddings/
│       │   │   ├── openai_query_embedding.py
│       │   │   └── openai_document_embedding.py
│       │   ├── openai/
│       │   │   └── client.py
│       │   ├── regulatory/
│       │   │   └── openai_constraint_inference.py
│       │   ├── vector_store/
│       │   │   └── qdrant/
│       │   │       ├── client.py
│       │   │       └── document_vector.py
│       │   └── messaging/
│       ├── api/
│       │   ├── app.py
│       │   ├── composition/
│       │   │   ├── regulatory_intelligence.py
│       │   │   └── regulatory_intelligence_runtime.py
│       │   ├── errors.py
│       │   ├── exception_handlers.py
│       │   ├── middleware.py
│       │   ├── routers/
│       │   │   └── health.py
│       │   └── dependencies/
│       └── shared/
│           ├── config/
│           │   ├── settings.py
│           │   ├── database.py
│           │   ├── redis.py
│           │   ├── qdrant.py
│           │   └── openai.py
│           └── observability/
│               ├── correlation.py
│               └── logging.py
├── tests/
│   ├── unit/
│   ├── integration/
│   │   ├── cache/
│   │   │   └── redis/
│   │   ├── infrastructure/
│   │   │   ├── orchestration/
│   │   │   │   └── n8n/
│   │   │   └── vector_store/
│   │   │       └── qdrant/
│   │   └── persistence/
│   │       └── postgres/
│   ├── architecture/
│   └── fixtures/
├── scripts/
└── docs/
```

Python packaging is in place: `pyproject.toml`, `uv.lock`, `.python-version` (CPython 3.12). Domain contracts and value objects are implemented under `src/energy_trading/domain/`. Application structured-ingestion ports are implemented. An application-owned unstructured document extraction boundary (`DocumentExtractionPort`, `DocumentExtractionResult`, `ExtractedDocumentChunk`) is implemented; infrastructure `PdfTextExtractionAdapter` structurally implements that port for local text-layer PDFs only and does not perform OCR or wire `create_app()`. An application-owned document embedding boundary (`DocumentEmbeddingPort`, `DocumentChunkEmbedding`) is implemented; infrastructure `OpenAIDocumentEmbeddingAdapter` structurally implements that port with an injected `AsyncOpenAI` client and explicit model and does not construct the client or wire `create_app()`. An application-owned document vector index-entry preparation service (`DocumentVectorIndexEntryPreparationService`) composes already-normalized chunks through that port into existing `DocumentVectorIndexEntry` values without calling `DocumentVectorIndexPort.index()`. An application-owned document vector index execution service (`DocumentVectorIndexExecutionService`) composes that preparation service with `DocumentVectorIndexPort.index` from already-normalized chunks without embedding or reconstructing entries. An application-owned document extraction-to-index execution service (`DocumentExtractionIndexExecutionService`) awaits `DocumentExtractionPort.extract()` once, awaits index execution only when extracted chunks are non-empty, and returns the original `DocumentExtractionResult` unchanged; it remains unwired from `create_app()`, LangGraph, OpenAI, and Qdrant. An API-owned composition function (`build_pdf_document_extraction_index_execution`) constructs `PdfTextExtractionAdapter` plus that service from a local `Path`, `document_id`, `source_name`, and an already-constructed `DocumentVectorIndexExecutionService` without extracting, indexing, inspecting the filesystem, or wiring `create_app()`. An API-owned settings-loaded runtime (`loaded_pdf_document_extraction_index_runtime`) enters `loaded_document_vector_index_runtime` from the existing `env_file` contract, passes the yielded index execution service plus that local path and identities to the Chunk 102 builder, and yields `DocumentExtractionIndexExecutionService` without extracting, indexing, inspecting the filesystem, constructing provider clients, or wiring `create_app()`. An API-owned one-shot execution function (`execute_loaded_pdf_document_extraction_index`) enters that loaded PDF runtime, awaits `execute()` exactly once, and returns the original `DocumentExtractionResult` without wiring `create_app()`. An application-owned document query-text embedding boundary (`DocumentQueryEmbeddingPort`, `DocumentQueryEmbedding`) is implemented; infrastructure `OpenAIDocumentQueryEmbeddingAdapter` structurally implements that port with an injected `AsyncOpenAI` client and explicit model and does not construct the client or wire `create_app()`. An application-owned document vector-search query preparation service (`DocumentVectorSearchQueryPreparationService`) composes query text plus an explicit limit through that port into existing `DocumentVectorSearchQuery`; it does not search. An application-owned Regulatory Intelligence query execution service (`RegulatoryIntelligenceQueryExecutionService`) composes that preparation with the unchanged `RegulatoryIntelligenceAgent` from query text plus an explicit limit into existing `RegulatoryIntelligenceResult`. An application-owned Regulatory Intelligence workflow step (`RegulatoryIntelligenceWorkflowStep`) structurally satisfies existing `AgentPort` over `RegulatoryIntelligenceWorkflowRequest` → existing `RegulatoryIntelligenceResult` by injecting that query-execution service; it remains unwired from LangGraph. An application-owned Regulatory Intelligence workflow-context Protocol (`RegulatoryIntelligenceWorkflowContextPort`) resolves a typed Chunk 114 request from `WorkflowState` and records the existing `RegulatoryIntelligenceResult` without embedding those values on the snapshot; there is no production context implementation. An application-owned document vector indexing boundary (`DocumentVectorIndexPort`, `DocumentVectorIndexEntry`) is implemented. An application-owned document vector retrieval boundary (`DocumentVectorSearchPort`, `DocumentVectorSearchQuery`) is implemented. There is no generic `VectorStore`. Document-chunk embedding and query-text embedding remain separate ports. An application-owned agent invocation boundary (`AgentName`, generic `AgentPort[TRequest, TResult]`) is implemented. Five concrete application agents exist (`WeatherAndRenewableForecastAgent`, `HydroResourcesAgent`, `GenerationAvailabilityAgent`, `NewsIntelligenceAgent`, `MarketMonitoringAgent`) with typed request/result DTOs and application-owned `WeatherRecordSourcePort` / `HydroRecordSourcePort` / `GenerationAvailabilityRecordSourcePort` / `NewsEventSourcePort` / `MarketPriceRecordSourcePort`; there is no weather, hydro, generation, news, or market provider, registry, or factory. A sixth concrete application agent exists (`RegulatoryIntelligenceAgent`) with typed request/result DTOs composing existing `DocumentVectorSearchPort` and application-owned `RegulatoryConstraintInferencePort`; Regulatory graph/API wiring remains absent. The agent still expects `DocumentVectorSearchQuery` and does not inject `DocumentQueryEmbeddingPort`. `RegulatoryIntelligenceQueryExecutionService` is the outer application composition over query preparation plus that unchanged agent. API-owned `build_regulatory_intelligence_query_execution` constructs that stack from three injected application ports. Infrastructure `OpenAIDocumentQueryEmbeddingAdapter` can satisfy the query-embedding port. Infrastructure `OpenAIRegulatoryConstraintInferenceAdapter` can satisfy the inference port. The builder does not construct `AsyncOpenAI` or either adapter. OpenAI client/API-key/model runtime composition, `create_app()` invocation, and graph wiring remain outside this chunk. An application-owned framework-neutral workflow snapshot (`WorkflowPhase`, `WorkflowStatus`, `WorkflowState`) is implemented; it remains the graph schema and is not redefined by LangGraph. A minimal LangGraph runtime (`build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep, parallel_ingestion_failure_runtime_handler: ParallelIngestionFailureRuntimeHandlingService)`, topology `START → workflow_entry → parallel_ingestion` then `ingestion`/`running` → `parallel_ingestion_success_transition` → `END` or `ingestion`/`failed` → `END`) is implemented; the entry node is an async no-op, `parallel_ingestion` delegates to the injected step and catches only `BaseExceptionGroup` for the injected runtime failure handler, and `parallel_ingestion_success_transition` applies `advance_after_parallel_ingestion`. An application-owned framework-neutral failure-policy decision hook (`FailureAction`, `FailurePolicyContext`, `FailurePolicyPort`) is implemented; there is no concrete policy and no retry/fallback execution. Application-owned framework-neutral parallel-ingestion contracts (`ParallelIngestionPlan` → `ParallelIngestionExecutionPort` → `ParallelIngestionSuccess`) compose the five existing typed Phase 2 request and result DTOs. Concrete `ConcurrentParallelIngestionExecutor` structurally implements that port with `asyncio.TaskGroup` and the five application agents; ordinary agent failures are attributed as `ParallelIngestionAgentFailure`; the graph does not import the executor. Application-owned `ParallelIngestionWorkflowContextPort` is the typed, storage-neutral seam for resolving a prepared plan and recording all-five-success output by `WorkflowState.workflow_id`; there is no concrete context implementation. Application-owned `ParallelIngestionWorkflowStep` composes resolve → execute → record and returns the original `WorkflowState` unchanged; LangGraph injects it into `parallel_ingestion` and does not reconstruct the sequence. Application-owned `advance_after_parallel_ingestion` is the successful Phase 2 control-state transition (`ingestion`/`running` → `forecasting`/`running`); LangGraph node `parallel_ingestion_success_transition` delegates to that function and does not reimplement it. Application-owned `fail_parallel_ingestion` is the terminal Phase 2 failure transition (`ingestion`/`running` → `ingestion`/`failed`); diagnostics remain unchanged, and LangGraph does not call it. Application-owned `ParallelIngestionFailureDecisionService` delegates an already-constructed `FailurePolicyContext` to `FailurePolicyPort.decide` exactly once and returns `FailureAction` unchanged; it does not construct context, does not execute the action, and LangGraph does not call it. Application-owned `build_parallel_ingestion_failure_policy_context` constructs that published context from already-sanitized typed facts; it does not inspect exceptions, does not invent an agent identity, and LangGraph does not call it. Application-owned `execute_parallel_ingestion_failure_action` executes an already-decided `FailureAction`: `FAIL` delegates to `fail_parallel_ingestion`, while `RETRY` and `FALLBACK` fail closed as not implemented; LangGraph does not call it. Application-owned `ParallelIngestionFailureHandlingService` composes an already-built `FailurePolicyContext` through that decision service and action executor; it remains LangGraph-free and unwired. Application-owned `extract_parallel_ingestion_agent_failures` extracts already-attributed `ParallelIngestionAgentFailure` leaves from a possibly nested exception group without classifying them; LangGraph does not call it. Application-owned `classify_parallel_ingestion_agent_failure` converts one attributed leaf into frozen `ParallelIngestionFailureFact` (`AgentName` + `error_code`); LangGraph does not call it. Application-owned `classify_parallel_ingestion_agent_failures` classifies an already-extracted attributed-failure tuple by delegating each element to that one-leaf classifier and returns `tuple[ParallelIngestionFailureFact, ...]`; it does not select among failures, and LangGraph does not call it. Application-owned `ParallelIngestionFailureSelectionPort` is the Phase-2-specific selection contract over that sanitized fact tuple; it returns one `ParallelIngestionFailureFact` without first/last/priority winner semantics, and LangGraph does not call it. Application-owned `StrictSingleParallelIngestionFailureSelector` structurally implements that contract for the unambiguous one-fact case only; zero or multiple facts fail closed, simultaneous multi-failure selection remains unresolved, and LangGraph does not call it. Application-owned `ParallelIngestionAttemptNumberPort` is the Phase-2-specific read-only attempt-number source contract over workflow identity; it returns the current 1-based attempt as `int`, has no increment/reset semantics on the port, and LangGraph does not call it. Application-owned `InitialParallelIngestionAttemptNumberSource` structurally implements that contract for the current no-retry runtime by returning exactly `1`; it is not a tracker, and LangGraph does not call it. Application-owned `ParallelIngestionFailureContextResolutionService` composes that selection port, attempt-number port, and the published context builder into one `FailurePolicyContext`; the strict selector and initial attempt source exist but are not auto-wired, the service does not decide or execute policy, and LangGraph does not call it. There is no business-phase routing, checkpointer/store, Phase 3 execution, or `create_app()` graph wiring. An infrastructure-only Qdrant HTTP client foundation (`QdrantSettings`, lazy `create_qdrant_client()` returning `AsyncQdrantClient`) is implemented. Concrete adapters `QdrantDocumentVectorIndex` and `QdrantDocumentVectorSearch` structurally implement the already-published index/search ports. Production adapters still do not create collections or select a distance metric. There is no `create_app()` Qdrant wiring. An optional Compose `qdrant` profile runs `qdrant/qdrant:v1.19.1` on 127.0.0.1 REST port 6333 only, with required API-key authentication, telemetry disabled, and named volume `qdrant-data`. An optional Compose `n8n` profile runs `n8nio/n8n:2.37.10` on 127.0.0.1 HTTP port 5678 only, with a required deployment encryption key, diagnostics/version/templates/personalization disabled, and named volume `n8n-data`. n8n is outer acquisition/scheduling infrastructure: it does not bypass the ACL, does not store platform energy data, has no workflows yet, and is not wired into `create_app()`. Deterministic schema field resolution lives under `src/energy_trading/infrastructure/adapters/structured/schema_mapping/`. Concrete structured adapters are `ConsumptionCsvAdapter` and `ConsumptionExcelAdapter`. Shared Consumption field-profile/MW-safety policy lives in `consumption_mapping.py` beside those adapters. Explicit Consumption MW/kW and IANA timezone normalization lives under `structured/normalization/`. Consumption duplicate-timestamp policy, optional interval-grid alignment, and internal compact gap reporting live under `structured/time_series/`. Interim filesystem-backed DLQ metadata persistence lives under `infrastructure/persistence/`. Async PostgreSQL/TimescaleDB engine and session factories live under `infrastructure/persistence/postgres/`. Typed `DatabaseSettings` live under `shared/config/database.py` and are loaded separately from process-health `AppSettings`. Typed `RedisSettings` live under `shared/config/redis.py` and are loaded separately from process health. Typed `QdrantSettings` live under `shared/config/qdrant.py` and are loaded separately from process health. Alembic owns a bootstrap migration plus Consumption `energy_trading.consumption_observations` (Timescale hypertable on `timestamp`). Application-owned `ConsumptionRepositoryPort` is implemented by unwired `PostgresConsumptionRepository`. An optional Compose `postgres` profile runs `timescale/timescaledb:2.29.2-pg17` on 127.0.0.1 only. Application-owned `CachePort[TValue]` is an async, generic, TTL-bound cache Protocol. Infrastructure `RedisCache[TValue]` structurally implements that port using redis-py `redis.asyncio.Redis`, an injected infrastructure-local `CacheCodec[TValue]`, and SHA-256 backend keys. Construction is lazy and unwired: no global client and no `create_app()` Redis lifecycle. An optional Compose `redis` profile runs `redis:8.2.9-alpine` on 127.0.0.1 only, with password authentication and persistence disabled. Infrastructure `create_qdrant_client()` lazily returns `qdrant_client.AsyncQdrantClient` from typed `QdrantSettings` without an eager command, collection, or `create_app()` lifecycle. No other canonical tables or repositories exist. Empty architectural directories still use `.gitkeep`.

## Anti-Corruption Layer

**Mandatory.** External data must NEVER reach internal application agents, ML models, or domain services directly.

All external inputs pass through infrastructure adapters. That includes APIs, CSV, Excel, PDFs, HTML, scraped data, renamed columns, Armenian headers, inconsistent units, and malformed timestamps.

The application-facing structured ingestion boundary is:

```text
RAW EXTERNAL WORLD
        ↓
Infrastructure structured adapter
        ↓
canonical normalization boundary
        ↓
StructuredIngestionResult[T]
        ↓
Application / agents / ML
```

Raw payloads do not cross into application. The application never receives CSV rows, Excel rows, pandas DataFrames, arbitrary dictionaries, API JSON, vendor schemas, HTML, raw bytes, or source-specific column names. It receives only canonical domain models, canonical `AdapterDiagnostic` values, and canonical `DLQRecord` metadata (`payload_reference` only).

The application owns `StructuredIngestionPort[TRecord]`. Infrastructure adapters implement that protocol structurally. Concrete implementations are Consumption CSV and Consumption Excel (`.xlsx` only). There is **no** REST adapter yet.

Implemented structured paths:

```text
CSV Consumption Source
  → ConsumptionCsvAdapter
  → DeterministicFieldResolver
  → schema safety
  → explicit unit normalization
  → explicit timezone normalization
  → ConsumptionRecord validation
  → duplicate timestamp validation
  → optional interval-grid alignment
  → internal missing-interval detection and compact gap reporting
  → StructuredIngestionResult[ConsumptionRecord]
  → application

XLSX Consumption Source
  → ConsumptionExcelAdapter
  → worksheet acquisition
  → DeterministicFieldResolver
  → schema safety
  → explicit unit normalization
  → explicit timezone normalization
  → ConsumptionRecord validation
  → duplicate timestamp validation
  → optional interval-grid alignment
  → internal missing-interval detection and compact gap reporting
  → StructuredIngestionResult[ConsumptionRecord]
  → application
```

CSV and Excel acquisition remain infrastructure-only. Paths, worksheet names, `source_power_unit`, `source_timezone`, and `interval_grid` are constructor-injected and never appear on `ingest()`. Both adapters produce `StructuredIngestionResult[ConsumptionRecord]`. Blocking filesystem and library work stays behind async `asyncio.to_thread`. Excel loading uses openpyxl in `read_only=True` and `data_only=True` mode; formulas are not calculated. Raw workbook objects, cells, headers, and filesystem paths do not cross into application. Partial success is supported. Neither adapter infers units, timezones, or interval cadence.

Consumption duplicate identity is `(consumer_id, canonical UTC timestamp)`. Every member of a duplicate group fails closed; there is no first-wins, last-wins, or aggregation policy. Interval-grid alignment and missing-interval detection run only when an explicit infrastructure `IntervalGrid` is configured (positive `timedelta` plus timezone-aware anchor, normalized to UTC internally). The default `interval_grid` is `None`: duplicates are still detected, but cadence is not checked and no gaps are inferred. Off-grid rows fail individually. Source order of surviving records is preserved; out-of-order aligned timestamps are neither sorted nor rejected.

Gap detection is per `consumer_id` and only between that consumer's earliest and latest surviving observations. A compact contiguous range (`missing_count`, first/last missing timestamp) is kept infrastructure-local; missing timestamps are not expanded one-by-one. Surviving observed records remain valid. A missing interval has no source row, so it produces a sanitized `AdapterDiagnostic` (`consumption_missing_interval_gap`) and **no** fabricated DLQ record. Leading/trailing delivery-window completeness is not inferred. No Armenian DAM interval is assumed. Duplicate and gap detection are per `ingest()` batch only. Interpolation and synthetic fill are not implemented. Adapters still do not persist DLQ metadata themselves.

Canonical Consumption output remains MW. `PowerUnit.MW` is the default source unit; `PowerUnit.KW` may convert kW→MW only when explicitly configured. `Consumption_MW` maps to canonical `value_mw` under the MW profile; `Consumption_kW` maps under the kW profile. Energy-like headers (`Consumption_MWh`, `Consumption_kWh`, `Consumption_MW_h`) fail regardless of `PowerUnit`. Header/config mismatches such as `PowerUnit.KW` with `value_mw` fail closed. No MW↔MWh conversion and no interval-length assumption.

Source timezone may be configured with an IANA name (`UTC`, `Europe/Berlin`, `Asia/Yerevan`). No timezone is inferred or defaulted (including no default `Asia/Yerevan`). Aware source timestamps retain their represented instant and are normalized to UTC. Naive timestamps require an explicit source timezone. DST-ambiguous and nonexistent local clocks fail closed. Unix epoch numbers and Excel serial dates are not timestamps.

Deterministic schema field resolution is implemented inside the infrastructure ACL (`DeterministicFieldResolver`). It interprets raw headers only. Raw external field names do not cross into application, domain, `StructuredIngestionPort`, or `DeadLetterQueuePort`. There is no application-layer schema-mapping port.

Field-resolution flow:

```text
raw header
  → Unicode normalization
  → exact aliases
  → deterministic fuzzy matching
  → confidence / ambiguity result
  → later adapter validation / normalization
```

An optional infrastructure-local semantic/LLM fallback remains deferred. No provider SDK is installed. Leading/trailing coverage-window completeness and time-series repair are not implemented.

Partial success is first-class: a batch may contain canonical records together with diagnostics and DLQ references. Complete normalization failure (empty records plus DLQ references) and a valid empty source (all collections empty) are also valid results; they must not crash the workflow by themselves.

DLQ persistence is abstracted behind application-owned `DeadLetterQueuePort`. The port still accepts one canonical `DLQRecord` per `enqueue()`; filesystem paths and raw payloads are not part of that signature. An interim local filesystem implementation (`FilesystemDeadLetterQueue`) lives in infrastructure and persists canonical `DLQRecord` metadata only. `payload_reference` is stored as an opaque string and is never dereferenced. Storage filenames are derived from a SHA-256 digest of `record_id`, not from the raw identifier. Identical retries are idempotent; the same `record_id` with different canonical metadata fails closed as `ConflictError`. The adapter is not wired into ingestion adapters, `create_app()`, or any orchestration runtime. PostgreSQL/TimescaleDB remains the planned system of record (ADR-004); Chunk 13 added engine/session factories and a schema/extension bootstrap only. This filesystem adapter does not replace that decision, and there is no PostgreSQL DLQ implementation yet. DLQ replay is not implemented.

Dependency direction:

```text
Application
  └── StructuredIngestionPort
          ↑ implemented by
Infrastructure Adapter
```

Infrastructure may import application ports. Application must not import infrastructure adapters.

## Canonical data contracts

Canonical contracts are implemented as frozen Pydantic `CanonicalModel` types in `src/energy_trading/domain`. They are the only payloads agents, ML, and use cases may exchange. See `DATA_CONTRACTS.md`.

Implemented contracts: `ConsumptionRecord`, `WeatherRecord`, `HydroRecord`, `GenerationAvailabilityRecord`, `MarketPriceRecord`, `NewsEvent`, `RegulatoryConstraint`, `LoadForecastPoint`, `PriceForecastPoint`, `RiskAssessment`, `MarketBid`, `MarketClearingResult`, `SettlementResult`, `AdapterDiagnostic`, `DLQRecord`.

Internal canonical semantics (independent of external source representation):

- **Power** is MW. **Energy** is MWh. The two are not automatically equated; DAM interval length remains unverified.
- **Timestamps** (`UtcDateTime`) must be timezone-aware on input and are normalized to **UTC**. Naive datetimes are rejected. Consumption adapters may attach an explicit IANA source timezone to naive clocks; they never infer a zone. The domain does not guess.
- **Money and energy prices** use `Decimal` (`MoneyAmount`, `EnergyPrice`) with an explicit ISO-style three-letter `CurrencyCode`. AMD is a valid code, not a hardcoded market assumption. `float` is rejected for monetary amounts.
- **DLQ:** `DLQRecord` carries `payload_reference` only. Raw external payloads must not enter the canonical envelope.

Unknown fields are forbidden. Models are immutable. `NaN` / infinities are rejected.

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
  → StructuredIngestionResult[T]   (application port)
  → Application / Agent / ML layer
```

The application-facing port and immutable result envelope are implemented. Deterministic schema field resolution is implemented inside infrastructure. Concrete structured adapters are `ConsumptionCsvAdapter` (UTF-8 CSV) and `ConsumptionExcelAdapter` (modern `.xlsx` via openpyxl). Concrete unstructured text-layer extraction is `PdfTextExtractionAdapter` (local `.pdf` via `pypdf`; no OCR). Explicit Consumption MW/kW power normalization, explicit IANA source-timezone normalization, fail-closed duplicate timestamp detection, optional interval-grid alignment, and internal compact gap reporting are implemented in infrastructure. They do not construct records for other domains, infer units, timezones, or DAM intervals, calculate Excel formulas, invent leading/trailing coverage, sort output, interpolate missing slots, or persist DLQ entries. REST adapters, semantic/LLM mapping, gap repair, and adapter runtimes for other sources are **not** implemented. Failures that cannot safely be normalized are represented as `DLQRecord` metadata on the result rather than crashing the workflow. File acquisition failures are `DependencyUnavailableError`. Missing intervals have no source row and therefore do not fabricate DLQ records. Canonical DLQ metadata may later be passed to `DeadLetterQueuePort`; a filesystem metadata adapter exists but is not invoked by these source adapters.

Future n8n acquisition, when added, remains outside this application-facing path:

```
external source
  → future n8n acquisition workflow
  → infrastructure acquisition boundary
  → schema interpretation
  → validation
  → deterministic normalization
  → canonical/application DTO
  → application use case
```

n8n is an outer acquisition / scheduling mechanism. It must not write vendor/raw payloads directly into domain, application DTOs, Timescale canonical tables, or Qdrant application-facing payloads. Chunk 25 adds only the local n8n service foundation; no workflow, callback, or ACL handoff is implemented.

## Unstructured / RAG conceptual flow

```
PDF / Document
  → PdfTextExtractionAdapter (text-layer PDFs only; OCR still future)
  → DocumentExtractionPort
  → ExtractedDocumentChunk
  → DocumentEmbeddingPort
  → DocumentChunkEmbedding
  → DocumentVectorIndexEntry
  → DocumentVectorIndexPort
  → Qdrant HTTP client foundation
  → optional Compose Qdrant service (loopback REST, API key, no production collection bootstrap)
  → QdrantDocumentVectorIndex / QdrantDocumentVectorSearch
  → DocumentVectorSearchPort
  → ranked ExtractedDocumentChunk
  → future regulatory interpretation
  → RegulatoryConstraint
```

The application owns extraction, document-chunk embedding, query-text embedding, vector indexing, and vector retrieval abstractions. Concrete extraction/OCR, embedding, and vector-database implementations remain outer-layer concerns. Embedding generation is not a Qdrant responsibility. Document-chunk embedding and query-text embedding are separate application use cases; there is no generic `EmbeddingPort`. Indexing input pairs a normalized `ExtractedDocumentChunk` with its matching `DocumentChunkEmbedding`. Logical identity is `(document_id, chunk_id)`. Exact retries of the same application entry are idempotent. The same identity with different chunk or embedding content fails closed; there is no overwrite or reindex replacement yet. Indexing does not expose Qdrant collection, point, payload, or distance types.

Document-chunk embedding:

```
ExtractedDocumentChunk
  → DocumentEmbeddingPort
  → DocumentChunkEmbedding
```

Document vector index-entry preparation:

```
tuple[ExtractedDocumentChunk, ...]
  → DocumentVectorIndexEntryPreparationService
  → DocumentEmbeddingPort.embed
  → identity-safe DocumentVectorIndexEntry pairing
```

The preparation service does not call `DocumentVectorIndexPort.index()`.

Document vector index execution:

```
tuple[ExtractedDocumentChunk, ...]
  → DocumentVectorIndexExecutionService
  → DocumentVectorIndexEntryPreparationService.prepare
  → DocumentVectorIndexPort.index
```

The execution service does not embed, reconstruct entries, or call a concrete vector database.

Query-text embedding:

```
normalized query text
  → DocumentQueryEmbeddingPort
  → DocumentQueryEmbedding
  → DocumentVectorSearchQueryPreparationService
  → DocumentVectorSearchQuery
```

Infrastructure OpenAI query embedding (SDK types terminate here; application remains OpenAI-independent):

```
query text
  → OpenAI embeddings API (`AsyncOpenAI.embeddings.create`, encoding_format="float")
  → OpenAIDocumentQueryEmbeddingAdapter
  → DocumentQueryEmbedding
```

The adapter receives an already-constructed `AsyncOpenAI` client and an explicit model string. It does not load API keys, construct the client, or become the Chunk 67 composition root. Chunk 70 added the separate typed settings and lazy factory that can construct that client; neither adapter calls it.

Infrastructure OpenAI regulatory constraint inference (SDK types terminate here; application remains OpenAI-independent):

```
tuple[ExtractedDocumentChunk, ...]
  → OpenAI Responses structured output (`AsyncOpenAI.responses.parse`)
  → OpenAIRegulatoryConstraintInferenceAdapter
  → evidence-reference check against supplied chunk_id values
  → tuple[RegulatoryConstraint, ...]
```

The inference adapter receives an already-constructed `AsyncOpenAI` client and an explicit model string. It converts provider structured output inside infrastructure. Evidence references are checked locally against the supplied normalized chunks. It does not load API keys, construct the client, hardcode Armenian DAM rules, or become the Chunk 67 composition root. Empty `chunks` returns `()` without a provider call. Chunk 70 added the separate typed settings and lazy factory that can construct that client; neither adapter calls it.

Application query execution composition (provider-neutral; graph/`create_app()` still unwired):

```
query text + limit
  → DocumentVectorSearchQueryPreparationService
  → RegulatoryIntelligenceRequest
  → RegulatoryIntelligenceAgent
  → retrieval
  → inference
  → RegulatoryIntelligenceResult
```

Outer composition root (depends inward; application does not import it):

```
three application port implementations
  → build_regulatory_intelligence_query_execution
  → RegulatoryIntelligenceQueryExecutionService
```

Provider-aware outer composition (API composition only; clients already created):

```
injected OpenAI client
  → query embedding adapter

injected Qdrant client/config
  → vector search adapter

injected OpenAI client
  → regulatory inference adapter

  → existing provider-neutral Regulatory builder
  → RegulatoryIntelligenceQueryExecutionService
```

The provider-SDK exception is narrow and intentional: only the two exact Regulatory API provider-composition modules (`api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`) and the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`) may import OpenAI/Qdrant client types and the published concrete adapters. HTTP routes and `create_app()` remain provider-SDK-free. Application remains infrastructure-free.

The agent remains typed around an already-built `DocumentVectorSearchQuery`:

```
DocumentVectorSearchQuery
  → RegulatoryIntelligenceAgent
  → DocumentVectorSearchPort
```

Retrieval is application-owned. `DocumentVectorSearchPort.search()` consumes an already-embedded numeric query (`DocumentVectorSearchQuery.vector`) plus a positive result `limit`. It does not convert query text into a vector; that conversion is owned by `DocumentQueryEmbeddingPort` plus `DocumentVectorSearchQueryPreparationService`, not by search and not by `DocumentEmbeddingPort`. Returned `ExtractedDocumentChunk` values are ordered most relevant to least relevant; backend similarity/distance scores do not cross the port. Zero matches are a valid empty tuple. Logical identities are unique within one response. There is no generic `VectorStore`. Indexing and retrieval remain separate ports. `DocumentChunkEmbedding`, `DocumentQueryEmbedding`, `DocumentVectorIndexEntry`, and `DocumentVectorSearchQuery` are application orchestration DTOs: they are not domain contracts and not a `RegulatoryConstraint`.

Chunk 12 implements the application-owned extraction boundary. `DocumentExtractionPort.extract()` accepts no document bytes, path, URL, or provider payload. The application may receive immutable `ExtractedDocumentChunk` values, canonical `AdapterDiagnostic` values, and canonical `DLQRecord` metadata (`payload_reference` only). Document bytes, vendor OCR schemas, bounding boxes, parser objects, and raw chunk dictionaries stay inside infrastructure adapters. Extracted text is **not** a `RegulatoryConstraint`.

Chunk 100 adds the first concrete infrastructure implementation: `PdfTextExtractionAdapter` in `infrastructure/adapters/unstructured/pdf_text_extraction.py`. It structurally satisfies `DocumentExtractionPort` without subclassing it. Constructor injection owns the local `.pdf` `Path`, opaque `document_id`, and `source_name`. Public `extract()` offloads blocking `pypdf` work through `asyncio.to_thread`. Chunking is deterministic and page-based: one `ExtractedDocumentChunk` per non-empty normalized page; `chunk_id` is `<document_id>:page:<page_number>`; `ordinal` is zero-based among emitted chunks; `page_number` is one-based physical PDF page. Blank pages are skipped. A readable PDF with no extractable text returns empty chunks plus a sanitized `pdf_no_extractable_text` diagnostic and no DLQ. Invalid/corrupt/non-PDF bytes return empty chunks, a sanitized `pdf_invalid` diagnostic, and opaque `pdf://{source_name}/source` DLQ metadata. Missing/unreadable files raise sanitized `DependencyUnavailableError`. Page `extract_text` parser failures fail closed at document level. Paths, raw bytes, parser exceptions, and OCR never cross the application boundary. The adapter remains unwired from `create_app()`, Regulatory runtime, document-index runtime, LangGraph, OpenAI, and Qdrant.

Chunk 101 adds the application-owned extraction-to-index execution composition. `DocumentExtractionIndexExecutionService` injects exactly `DocumentExtractionPort` and `DocumentVectorIndexExecutionService`. Public `async execute()` accepts no runtime source, path, or bytes. It awaits `extract()` exactly once, then awaits `DocumentVectorIndexExecutionService.execute(chunks=result.chunks)` only when `result.chunks` is non-empty, and returns the original `DocumentExtractionResult` object unchanged. Empty extraction does not invoke indexing. Extraction and indexing exceptions propagate unchanged. The service does not reconstruct chunks, diagnostics, DLQ records, or the result envelope, and it synthesizes no diagnostics. The application service itself remains unwired from `create_app()`, FastAPI routes, production lifespan, Regulatory runtime, document-index runtime composition, LangGraph, OpenAI, and Qdrant. This is not automatic corpus ingestion.

Chunk 102 adds the API-owned PDF extraction-to-index composition root. `build_pdf_document_extraction_index_execution` is a synchronous keyword-only function in `api/composition`. It receives a local `Path`, opaque `document_id`, `source_name`, and an already-constructed `DocumentVectorIndexExecutionService`. It constructs exactly one `PdfTextExtractionAdapter` with those path/identity arguments, constructs exactly one `DocumentExtractionIndexExecutionService`, injects the new adapter plus the supplied index execution service, and returns that application service. The supplied index execution service identity is preserved. Construction does not call `.extract()` or `.execute()`, inspect file existence, open the PDF, load settings, or construct OpenAI/Qdrant clients. Construction therefore succeeds even when the supplied PDF path does not exist. Application does not import this builder. Infrastructure does not import API composition. `create_app()`, production lifespan, document-index HTTP, Regulatory runtime, document-index runtime lifecycle, and LangGraph remain unwired. OCR, URL/file-upload/directory acquisition, automatic/startup/background corpus ingestion, and Pricing & Sales remain deferred. This is not operational corpus ingestion.

Chunk 103 adds the settings-loaded PDF extraction-to-index runtime composition. `loaded_pdf_document_extraction_index_runtime` is a keyword-only async context manager in `api/composition`. It reuses the existing `env_file: str | Path | None = ".env"` contract from `loaded_document_vector_index_runtime` and also receives a local `Path`, opaque `document_id`, and `source_name`. It enters `loaded_document_vector_index_runtime(env_file=env_file)` exactly once, passes the exact yielded `DocumentVectorIndexExecutionService` plus those path/identity arguments to `build_pdf_document_extraction_index_execution` exactly once, and yields that `DocumentExtractionIndexExecutionService` unchanged. Provider-client lifetime remains owned by the existing document-index loaded/managed chain. The context manager does not call `.extract()` or `.execute()`, inspect file existence, open the PDF, construct OpenAI/Qdrant clients, load settings itself, or register cleanup. Application does not import this runtime. Infrastructure does not import API composition. `create_app()`, production lifespan, document-index HTTP, Regulatory runtime, and LangGraph remain unwired. OCR, URL/file-upload/directory acquisition, automatic/startup/background corpus ingestion, and Pricing & Sales remain deferred. This is not operational corpus ingestion.

Chunk 104 adds the explicit one-shot loaded PDF extraction-to-index execution seam. `execute_loaded_pdf_document_extraction_index` is a keyword-only async function in `api/composition`. It reuses the existing `env_file: str | Path | None = ".env"` contract from Chunk 103 and also receives a local `Path`, opaque `document_id`, and `source_name`. It enters `loaded_pdf_document_extraction_index_runtime(...)` exactly once, awaits `service.execute()` exactly once, and returns the original `DocumentExtractionResult` object unchanged. Runtime-entry failures and execution failures propagate unchanged; inner runtime teardown still occurs after a failed `execute()`. The function does not call `.extract()`, nested index execution, PDF adapters, embedding/index ports, or provider clients, and it does not reconstruct results or add diagnostics. Application does not import this function. Infrastructure does not import API composition. `create_app()`, production lifespan, HTTP routers, startup/background/scheduler, Regulatory runtime, and LangGraph remain unwired. When an explicit caller invokes it, this is a complete local text-layer PDF → extraction → embedding → vector-index execution path. It is not automatic corpus ingestion. OCR, URL/file-upload/directory acquisition, automatic/startup/background corpus ingestion, and Pricing & Sales remain deferred.

Chunk 19 implements the application-owned document-chunk embedding boundary. `DocumentEmbeddingPort.embed()` accepts only already-normalized `ExtractedDocumentChunk` values and returns `DocumentChunkEmbedding` values (opaque `document_id` / `chunk_id` plus a finite float vector).

Chunk 64 implements the application-owned query-text embedding boundary. `DocumentQueryEmbeddingPort.embed_query()` accepts only `query_text: str` and returns `DocumentQueryEmbedding` (a finite float vector). It does not search, index, know Qdrant, or wire Regulatory Intelligence. Application remains OpenAI-independent.

Chunk 68 implements the first concrete infrastructure adapter behind that port. `OpenAIDocumentQueryEmbeddingAdapter` injects `AsyncOpenAI` and an explicit model, calls `embeddings.create(..., encoding_format="float")` exactly once for a valid query, and converts the provider vector into `DocumentQueryEmbedding`. OpenAI SDK types and exceptions terminate in infrastructure as sanitized `InvalidRequestError` / `DependencyUnavailableError`. It does not construct the client, load `OPENAI_API_KEY`, select a default model, or wire `create_app()` / LangGraph / the Chunk 67 builder.

Chunk 83 implements the first concrete infrastructure adapter behind `DocumentEmbeddingPort`. `OpenAIDocumentEmbeddingAdapter` injects `AsyncOpenAI` and an explicit model, calls `embeddings.create(..., encoding_format="float")` for a non-empty tuple of already-normalized `ExtractedDocumentChunk` values, preserves input order and canonical `document_id` / `chunk_id` identity, and converts provider vectors into `DocumentChunkEmbedding`. Empty input returns `()` without a provider call. Cardinality mismatches, invalid vectors, and inconsistent dimensions fail closed as sanitized `DependencyUnavailableError`. It does not construct the client, load settings, parse documents, or wire `create_app()` / Regulatory runtime composition / LangGraph / extraction / Qdrant indexing.

Chunk 84 implements the application-owned document vector index-entry preparation composition. `DocumentVectorIndexEntryPreparationService.prepare(*, chunks)` awaits `DocumentEmbeddingPort.embed` exactly once, preserves input order and canonical `(document_id, chunk_id)` identity, and returns existing `DocumentVectorIndexEntry` values. Empty input returns `()`. Count or identity mismatch fails closed as sanitized `DependencyUnavailableError`. It does not call `DocumentVectorIndexPort.index()`, import OpenAI or Qdrant, or wire `create_app()` / Regulatory runtime / LangGraph / extraction.

Chunk 85 implements the application-owned document vector index execution composition. `DocumentVectorIndexExecutionService.execute(*, chunks)` awaits `DocumentVectorIndexEntryPreparationService.prepare` exactly once, then awaits `DocumentVectorIndexPort.index` exactly once with the exact prepared entries, and returns `None`. Empty input prepares then indexes `()`. It does not call `embed(...)`, construct `DocumentVectorIndexEntry`, import OpenAI or Qdrant, or wire `create_app()` / Regulatory runtime / LangGraph / extraction.

Chunk 86 implements the API-owned provider-neutral document vector index composition root. `build_document_vector_index_execution` is a synchronous keyword-only function that accepts already-constructed `DocumentEmbeddingPort` and `DocumentVectorIndexPort` implementations and returns `DocumentVectorIndexExecutionService`. It constructs `DocumentVectorIndexEntryPreparationService` and `DocumentVectorIndexExecutionService` without calling `.prepare`, `.execute`, `.embed`, or `.index`. Application does not import this builder. `create_app()` does not invoke it. It does not import OpenAI, Qdrant, settings, or client factories.

Chunk 87 implements the provider-aware document vector index object-composition seam. `build_document_vector_index_provider_runtime` is a synchronous keyword-only function in `api/composition`. It receives already-created `AsyncOpenAI` and `AsyncQdrantClient` instances, existing `QdrantDocumentVectorConfig`, and an explicit `document_embedding_model` string. It constructs `OpenAIDocumentEmbeddingAdapter` and `QdrantDocumentVectorIndex`, then calls `build_document_vector_index_execution` exactly once and returns that `DocumentVectorIndexExecutionService`. Construction performs no provider I/O, settings/env loading, client-factory calls, collection creation, embedding, indexing, or client close. Application does not import this builder. It remains offline, synchronous, and inert, and unwired from `create_app()`, Regulatory runtime lifecycle, LangGraph, and document extraction. Chunk 89 added configured settings mapping above this builder. Chunk 90 owns client lifetime above Chunk 89. Document acquisition, PDF/OCR, and actual corpus indexing remain deferred.

Chunk 88 implements typed document vector index runtime settings. `DocumentVectorIndexRuntimeSettings` lives in `shared/config` with exactly three required fields: `document_embedding_model`, `qdrant_collection_name`, and strictly positive `qdrant_vector_size`. The environment prefix is `ENERGY_DOCUMENT_INDEX_*`, separate from `ENERGY_OPENAI_*`, generic `QDRANT_*` connection settings, and `ENERGY_REGULATORY_*`. The module is SDK-free and constructs no clients, adapters, or `QdrantDocumentVectorConfig`. `load_document_vector_index_runtime_settings(*, env_file=...)` is uncached and isolated from `AppSettings`. `create_app()` and the Chunk 87 builder do not load these settings. Chunk 89 and Chunk 90 receive an already-constructed instance and do not call this loader. Chunk 91 loads it through the published loader. Query-embedding and constraint-inference fields are not part of this object. `RegulatoryIntelligenceRuntimeSettings` remains unchanged.

Chunk 89 implements the configured document vector index object-composition seam. `build_document_vector_index_configured_runtime` is a synchronous keyword-only function in `api/composition`. It receives already-created `AsyncOpenAI` and `AsyncQdrantClient` instances plus already-constructed `DocumentVectorIndexRuntimeSettings`. It constructs exactly one `QdrantDocumentVectorConfig(collection_name=settings.qdrant_collection_name, vector_size=settings.qdrant_vector_size)`, then calls `build_document_vector_index_provider_runtime` exactly once with those clients, that config, and `settings.document_embedding_model`, and returns that `DocumentVectorIndexExecutionService`. It does not load environment values, construct clients, construct provider adapters, or call Chunk 86 directly. It remains offline, synchronous, and inert, and unwired from `create_app()`, FastAPI lifespan, LangGraph, and document extraction. It does not execute indexing, own clients, or load settings. Chunk 90 owns client lifetime separately from this adaptation seam. Chunk 91 loads settings above Chunk 90. Document acquisition, PDF/OCR, actual corpus indexing, collection-management strategy, and Regulatory contract-phase integration remain deferred.

Chunk 90 implements the managed document vector index resource-lifetime seam. `managed_document_vector_index_runtime` is a keyword-only async context manager in `api/composition`. It receives already-loaded `OpenAISettings`, `QdrantSettings`, `DocumentVectorIndexRuntimeSettings`, and `QdrantDocumentVectorDistanceSettings`. It constructs clients through existing `create_openai_client` / `create_qdrant_client`, registers each client's async `close()` on `AsyncExitStack` immediately after creation, awaits Chunk 110 `ensure_configured_document_vector_index_collection_ready` once with that same managed Qdrant client plus the injected runtime and distance settings, then delegates once to `build_document_vector_index_configured_runtime`, yields that `DocumentVectorIndexExecutionService` unchanged, and tears clients down in LIFO order (Qdrant, then OpenAI). Collection-ensure failure propagates unchanged, yields no service, skips the configured builder, and still closes both already-created clients. Partial construction and consumer exceptions still close already-created clients. Cleanup exceptions are not suppressed. The manager does not load environment values, import OpenAI/Qdrant SDK types, construct adapters, duplicate create/verify/mapping, or construct a second Qdrant client. Chunk 91 loads settings above this seam.

```text
already-loaded typed settings
        ↓
managed document vector index runtime
        ↓
OpenAI/Qdrant client factories
        ↓
Chunk 110 configured collection ensure (same Qdrant client)
        ↓
Chunk 89 configured runtime
        ↓
Chunk 87
        ↓
Chunk 86
        ↓
DocumentVectorIndexExecutionService
```

Chunk 91 implements the settings-loaded document vector index composition seam. `loaded_document_vector_index_runtime` is a keyword-only async context manager in `api/composition`. It exposes one `env_file: str | Path | None = ".env"` argument matching the four existing loader contracts and forwards that exact value to `load_openai_settings`, `load_qdrant_settings`, `load_document_vector_index_runtime_settings`, and `load_qdrant_document_vector_distance_settings`. It then delegates resource ownership, collection ensure, and service construction to `managed_document_vector_index_runtime` and yields that `DocumentVectorIndexExecutionService` unchanged. It does not construct clients, import OpenAI/Qdrant SDK types, call client factories, own cleanup, call Chunk 110 ensure, call Chunks 89/87/86, execute indexing, or wire FastAPI/`create_app()` / LangGraph. Loader failures short-circuit later loaders and do not enter the managed runtime. Managed-runtime entry failures and consumer exceptions propagate through ordinary context-manager semantics so Chunk 90 still owns client cleanup.

```text
env_file
        ↓
OpenAI / Qdrant / document-index / distance settings loaders
        ↓
Chunk 90 managed runtime
        ↓
DocumentVectorIndexExecutionService
```

The runtime-side document-index composition chain is now:

```text
provider-neutral
→ provider-aware
→ typed settings
→ configured runtime
→ managed runtime
→ settings-loaded runtime
→ lifespan boundary
```

Chunk 92 implements the FastAPI-specific document vector index lifespan seam. `build_document_vector_index_lifespan` is a synchronous keyword-only factory in `api/composition`. It accepts the existing common `env_file: str | Path | None = ".env"` argument and returns a FastAPI-compatible async lifespan callback. Constructing the callback is lazy. Entering the returned lifespan enters Chunk 91; exiting it tears Chunk 91 down. The module imports FastAPI for the application type only and does not import provider SDKs, settings loaders, settings objects, or lower document-index runtime layers.

```text
FastAPI-compatible lifespan
        ↓
Chunk 91 loaded runtime
        ↓
Chunk 90 lifecycle
```

Chunk 95 exposes the exact yielded `DocumentVectorIndexExecutionService` on `app.state.document_vector_index_execution_service` only while that document-index lifespan is active, then removes the state reference before Chunk 91 teardown. Ownership is exclusively `document_vector_index_lifespan.py`. `app.py` does not assign or delete the service. `production_lifespan.py` does not assign or delete it.

Chunk 96 adds a read-only API accessor over that published state attribute. `get_document_vector_index_execution_service(request)` lives in `api/dependencies`. It reads `request.app.state.document_vector_index_execution_service` and returns that exact `DocumentVectorIndexExecutionService` identity. It does not own lifecycle, assign or delete application state, wrap the service, or invoke `.execute(...)`. Missing or wrong-type state fails closed as existing transport-neutral `DependencyUnavailableError`. HTTP status translation remains in the API error-mapping layer. Production `create_app()` does not wrap this accessor in `Depends(...)`. Automatic indexing remains absent. Chunk 98 later added the HTTP indexing route; Chunk 99 later installed it in `create_app()`. The accessor imports FastAPI `Request` and the application service type; it does not import provider SDKs or document-index composition/lifecycle modules.

```text
Request
        ↓
API Document Vector Index service accessor
        ↓
lifespan-scoped app.state service
```

Chunk 97 adds API-owned HTTP request transport DTOs. `DocumentVectorIndexChunkRequest` and `DocumentVectorIndexRequest` live in `api/schemas`. The nested chunk model carries already-normalized extracted-chunk fields only (`document_id`, `chunk_id`, `text`, `ordinal`, `page_number`). The outer request carries `chunks: tuple[DocumentVectorIndexChunkRequest, ...]`. The schemas are frozen Pydantic models with unknown fields forbidden. They do not import FastAPI, the Chunk 96 accessor, or provider SDKs. There is no mapping helper, route, service invocation, raw document upload/acquisition surface, or response DTO.

```text
HTTP request DTO
→ already-normalized chunk fields only
→ future explicit projection
→ ExtractedDocumentChunk
```

Application and domain do not depend on these schemas. Chunk 98 adds a dedicated HTTP indexing router that uses them. Chunk 99 later installs that router in production `create_app()`.

Chunk 98 adds the first thin Document Vector Index HTTP indexing route. `index_document_vectors` lives in `api/routers/document_vector_index.py`. It accepts `DocumentVectorIndexRequest`, resolves `DocumentVectorIndexExecutionService` through `Depends(get_document_vector_index_execution_service)`, explicitly projects each transport chunk into `ExtractedDocumentChunk`, awaits `execute(chunks=chunks)` exactly once, and returns HTTP 204 with no body. There is no handler-local exception translation, provider logic, generic mapper, raw document upload/acquisition surface, or response DTO. At the Chunk 98 checkpoint, production `create_app()` did not install this router.

```text
DocumentVectorIndexRequest
→ route-owned explicit projection
→ normalized application chunks
→ DocumentVectorIndexExecutionService.execute(...)
→ 204 No Content
```

Chunk 99 installs that already-published router in production `create_app()`. The factory imports `router as document_vector_index_router` and includes it once with `prefix=resolved_settings.api_prefix`, the same prefix used by health and Regulatory Intelligence. It does not reconstruct `/document-vector-index/index`, import the accessor or HTTP schemas, assign `app.state`, invoke `.execute`, load document-index/OpenAI/Qdrant settings, or construct provider clients. Construction remains lazy. The existing keyword-only `lifespan` seam remains. Execution still depends on the lifespan-scoped service. With the default API prefix, the production path is `POST /api/v1/document-vector-index/index`. Offline/test lifespans can still avoid provider credentials; missing service state maps to the published 503. The request body remains already-normalized chunks only. There is no raw document/file acquisition surface, PDF/OCR, automatic/background/startup indexing, reindex/replace/delete, or Qdrant collection management.

Chunk 92 originally left the yielded service intentionally unused. That unused-service / no-`app.state` rule is superseded by Chunk 95. HTTP routes, provider calls, and LangGraph remain unwired from this child factory. Application does not import this builder.

Chunk 93 implements the production-specific FastAPI lifespan composition seam. `build_production_lifespan` is a synchronous keyword-only factory in `api/composition`. It forwards the existing common `env_file: str | Path | None = ".env"` argument unchanged to `build_regulatory_intelligence_lifespan` and `build_document_vector_index_lifespan`, then nests those returned callbacks so Regulatory is the outer lifespan and Document Vector Index is the inner lifespan. Constructing the factory is lazy: it does not load settings, enter either runtime, create provider clients, or invoke indexing. The composite callback forwards the exact same FastAPI `app` to both children and yields `None`. This module does not write `app.state`, share OpenAI/Qdrant clients, or invent a generic lifespan/registry/DI framework. Child lifespan modules retain their own runtime ownership.

```text
Regulatory outer lifespan
→ Document Vector Index inner lifespan
→ application yield
```

After Chunk 93, `create_app()` still installed `build_regulatory_intelligence_lifespan` directly. HTTP routes, document-index `app.state` exposure, provider calls, and LangGraph remained unwired from this builder. Application did not import this builder. Chunk 94 later installed the composite as the production default (see below).

Chunk 94 installs that already-published composite as the production `create_app()` default lifespan. `create_app()` calls `build_production_lifespan()` when no override is supplied and passes the returned callback to `FastAPI(..., lifespan=...)`. It does not import or nest the child factories; Chunk 93 owns Regulatory + Document Index nesting. A supplied test lifespan still replaces the production default exactly, and `build_production_lifespan()` is not called in that case. Construction remains lazy: the factory may construct the composite callback, but it does not load Regulatory or document-index settings, create OpenAI/Qdrant clients, or execute indexing. Regulatory query-service exposure remains available because the composite wraps the existing Regulatory lifespan unchanged. After Chunk 95, the Document Vector Index child also exposes its exact execution service on document-index-owned `app.state` while that inner lifespan is active; the composite and `create_app()` still do not assign or delete either state attribute, and indexing is not executed automatically.

```text
api/app.py
    ↓
build_production_lifespan
    ↓
Regulatory lifespan
    ↓
Document Vector Index lifespan
```

Remaining indexing gaps: OCR fallback; URL/HTTP document acquisition; production/API/LangGraph wiring of `DocumentExtractionIndexExecutionService`, `build_pdf_document_extraction_index_execution`, `loaded_pdf_document_extraction_index_runtime`, and `execute_loaded_pdf_document_extraction_index`; automatic/background/startup corpus indexing; reindex/replacement strategy; collection-management strategy; Regulatory contract-phase integration.

Chunk 65 implements the application-owned query-preparation composition. `DocumentVectorSearchQueryPreparationService.prepare(*, query_text, limit)` awaits `DocumentQueryEmbeddingPort.embed_query` exactly once and returns existing `DocumentVectorSearchQuery(vector=embedding.vector, limit=limit)`. It does not search, rewrite query text, default or clamp the limit, or inject into Regulatory Intelligence. Chunk 68 added an infrastructure OpenAI adapter behind the embedding port; OpenAI adapter injection, model runtime selection, and actual regulatory RAG remain deferred.

Chunk 66 implements the application-owned query execution composition. `RegulatoryIntelligenceQueryExecutionService.execute(*, query_text, limit)` awaits `DocumentVectorSearchQueryPreparationService.prepare` exactly once, constructs existing `RegulatoryIntelligenceRequest(search_query=prepared_query)`, awaits `RegulatoryIntelligenceAgent.run` exactly once, and returns that `RegulatoryIntelligenceResult` unchanged. It does not call `embed_query`, `.search(...)`, or inference. Provider implementations, Qdrant/API provider composition, and Phase 1 graph wiring remain outside this chunk.

Chunk 114 adds the application-owned Regulatory workflow-step seam. `RegulatoryIntelligenceWorkflowRequest` is a frozen `query_text` + `limit` DTO with no defaults and no provider/config fields. `RegulatoryIntelligenceWorkflowStep` injects an already-constructed `RegulatoryIntelligenceQueryExecutionService`, structurally satisfies existing `AgentPort[RegulatoryIntelligenceWorkflowRequest, RegulatoryIntelligenceResult]` (`name` + async `run`), awaits `execute` exactly once, and returns that existing result unchanged. Exceptions propagate by identity. The step does not import API composition, infrastructure, settings, or provider SDKs. `WorkflowState` has no typed agent-output slot, so result placement into workflow state is deferred rather than adding an untyped artifact bag. LangGraph topology is unchanged and does not import or instantiate the step. Pricing & Sales remains absent.

Chunk 115 adds the application-owned Regulatory workflow-context Protocol. `RegulatoryIntelligenceWorkflowContextPort` is a non-generic `typing.Protocol` with exactly two public async operations: keyword-only `resolve_request(*, state: WorkflowState) -> RegulatoryIntelligenceWorkflowRequest` and `record_result(*, state: WorkflowState, result: RegulatoryIntelligenceResult) -> None`. It reuses the published snapshot, Chunk 114 request, and existing Regulatory result. Phase-specific Regulatory input/output stay outside `WorkflowState`; no generic artifact/context dictionary is introduced. There is no production implementation, no Redis/PostgreSQL adapter, and no generic `WorkflowContextPort`. The future graph node will coordinate this port and the Chunk 114 step; Chunk 115 does not couple them. LangGraph topology remains unchanged.

Chunk 67 implements the API-owned Regulatory runtime composition root. `build_regulatory_intelligence_query_execution` is a synchronous keyword-only function that accepts already-constructed `DocumentQueryEmbeddingPort`, `DocumentVectorSearchPort`, and `RegulatoryConstraintInferencePort` implementations and returns `RegulatoryIntelligenceQueryExecutionService`. It constructs `DocumentVectorSearchQueryPreparationService`, `RegulatoryIntelligenceAgent`, and `RegulatoryIntelligenceQueryExecutionService` without calling `.prepare`, `.run`, `.execute`, `.search`, `.infer`, or `.embed_query`. Application does not import this builder. `create_app()` does not invoke it. Chunk 71 constructs the published OpenAI and Qdrant adapters and then delegates to this builder; this builder still does not import OpenAI, Qdrant, settings, or client factories. There is still no production RAG runtime.

Chunk 69 implements the first concrete infrastructure adapter behind `RegulatoryConstraintInferencePort`. `OpenAIRegulatoryConstraintInferenceAdapter` injects `AsyncOpenAI` and an explicit model, calls `responses.parse(..., text_format=...)` exactly once for non-empty chunks, checks evidence chunk IDs against the supplied normalized input, and converts private provider candidates into canonical `RegulatoryConstraint` values. OpenAI SDK types and exceptions terminate in infrastructure as sanitized `DependencyUnavailableError`. It does not construct the client, load `OPENAI_API_KEY`, select a default model, invent Armenian DAM rules, or wire `create_app()` / LangGraph / the Chunk 67 builder. OpenAI SDK imports remain confined to the approved infrastructure modules plus the two exact Regulatory API provider-composition modules (`api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`) and the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`).

Chunk 70 implements the missing OpenAI client-construction foundation. Typed `OpenAISettings` lives in `shared/config` with a required `api_key: SecretStr` (`ENERGY_OPENAI_API_KEY`) and no model fields; it is loaded separately from `AppSettings` and is not required for process health or `create_app()`. The settings module does not import the OpenAI SDK. Infrastructure `create_openai_client(settings)` synchronously constructs `AsyncOpenAI` from `settings.api_key.get_secret_value()` with `max_retries=0`, performs no network request, creates no global client, and owns no adapter lifecycle. Production OpenAI SDK imports are the four infrastructure modules plus the two exact Regulatory API provider-composition modules (`api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`) and the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`). Neither adapter, the Chunk 67 builder, the Chunk 71 provider builder, the Chunk 73 configured builder, `create_app()`, nor LangGraph calls this factory. Chunk 74's managed runtime and Chunk 90's managed document-index runtime may call it from already-loaded `OpenAISettings`.

Chunk 71 implements the provider-aware Regulatory object-composition seam. `build_regulatory_intelligence_provider_runtime` is a synchronous keyword-only function in `api/composition`. It receives already-created `AsyncOpenAI` and `AsyncQdrantClient` instances, existing `QdrantDocumentVectorConfig`, and two explicit model strings (`query_embedding_model`, `constraint_inference_model`). It constructs `OpenAIDocumentQueryEmbeddingAdapter`, `QdrantDocumentVectorSearch`, and `OpenAIRegulatoryConstraintInferenceAdapter`, then calls `build_regulatory_intelligence_query_execution` exactly once and returns that service. Construction performs no provider I/O, settings/env loading, client-factory calls, collection creation, or client close. Application does not import this builder. `create_app()` and LangGraph remain unwired.

Chunk 72 implements typed Regulatory Intelligence runtime settings. `RegulatoryIntelligenceRuntimeSettings` lives in `shared/config` with exactly four required fields: `query_embedding_model`, `constraint_inference_model`, `qdrant_collection_name`, and strictly positive `qdrant_vector_size`. The environment prefix is `ENERGY_REGULATORY_*`, separate from `ENERGY_OPENAI_*` and generic `QDRANT_*` connection settings. The module is SDK-free and constructs no clients, adapters, or `QdrantDocumentVectorConfig`. `load_regulatory_intelligence_runtime_settings(*, env_file=...)` is uncached and isolated from `AppSettings`. `create_app()` and the Chunk 71 builder do not load these settings. Chunk 73 and Chunk 74 receive an already-constructed instance and do not call this loader. Chunk 75's `loaded_regulatory_intelligence_runtime` calls this loader and the OpenAI/Qdrant loaders, then delegates to Chunk 74.

Chunk 73 implements the configured Regulatory object-composition seam. `build_regulatory_intelligence_configured_runtime` is a synchronous keyword-only function in `api/composition`. It receives already-created `AsyncOpenAI` and `AsyncQdrantClient` instances plus already-constructed `RegulatoryIntelligenceRuntimeSettings`. It constructs exactly one `QdrantDocumentVectorConfig(collection_name=settings.qdrant_collection_name, vector_size=settings.qdrant_vector_size)`, then calls `build_regulatory_intelligence_provider_runtime` exactly once with those clients, that config, and the two settings model fields, and returns that service. It does not load environment values, construct clients, construct provider adapters, or call Chunk 67 directly.

```text
RegulatoryIntelligenceRuntimeSettings
        +
injected provider clients
        ↓
configured runtime builder
        ↓
QdrantDocumentVectorConfig
        ↓
Chunk 71 provider-runtime builder
        ↓
Chunk 67 provider-neutral builder
        ↓
RegulatoryIntelligenceQueryExecutionService
```

The API provider-composition exception is limited to exactly two Regulatory modules: `api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`, plus the exact document-index module `api/composition/document_vector_index_runtime.py`. HTTP routes and `create_app()` remain provider-SDK-free. Application does not import this builder. `create_app()` and LangGraph remain unwired.

Chunk 74 implements the managed Regulatory resource-lifetime seam. `managed_regulatory_intelligence_runtime` is a keyword-only async context manager in `api/composition`. It receives already-loaded `OpenAISettings`, `QdrantSettings`, `RegulatoryIntelligenceRuntimeSettings`, and `QdrantDocumentVectorDistanceSettings`. It constructs clients through existing `create_openai_client` / `create_qdrant_client`, registers each client's async `close()` on `AsyncExitStack` immediately after creation, awaits Chunk 112 `verify_configured_regulatory_intelligence_collection_ready` once on that same managed Qdrant client, then delegates once to `build_regulatory_intelligence_configured_runtime`, yields that `RegulatoryIntelligenceQueryExecutionService` unchanged, and tears clients down in LIFO order (Qdrant, then OpenAI). Partial construction, verification failure, and consumer exceptions still close already-created clients. Cleanup exceptions are not suppressed. The manager does not load environment values, import OpenAI/Qdrant SDK types, construct adapters, create collections, or wire FastAPI/`create_app()` / LangGraph.

```text
already-loaded typed settings
        ↓
managed Regulatory runtime
        ↓
OpenAI/Qdrant client factories
        ↓
Chunk 73 configured runtime
        ↓
Chunk 71
        ↓
Chunk 67
        ↓
query-execution service
        ↓
LIFO client cleanup
```

Settings loading remains separate from resource lifetime. Direct provider SDK imports remain limited to the existing two approved API composition modules; Chunk 74 uses factories instead. Application does not import this manager. `create_app()` and LangGraph remain unwired.

Chunk 75 implements the settings-loaded Regulatory composition seam. `loaded_regulatory_intelligence_runtime` is a keyword-only async context manager in `api/composition`. It accepts the existing common `env_file: str | Path | None = ".env"` argument, calls `load_openai_settings`, `load_qdrant_settings`, `load_regulatory_intelligence_runtime_settings`, and `load_qdrant_document_vector_distance_settings` exactly once each with that value, then delegates to `managed_regulatory_intelligence_runtime`. It yields the exact `RegulatoryIntelligenceQueryExecutionService` produced by Chunk 74. The module imports no OpenAI/Qdrant SDK types, does not construct clients or adapters, and does not call Chunk 112 verification or Chunks 73/71/67. Entering the context performs no provider I/O and does not execute a Regulatory query.

```text
optional env_file
        ↓
existing typed settings loaders
        ↓
loaded Regulatory runtime
        ↓
Chunk 74 managed runtime
        ↓
client factories + Chunk 73/71/67
        ↓
query-execution service
```

FastAPI lifespan, `create_app()`, HTTP routes, and LangGraph remain unwired from Chunk 75 itself. Application does not import this loader composition.

Chunk 76 implements the FastAPI-specific Regulatory lifespan seam. `build_regulatory_intelligence_lifespan` is a synchronous keyword-only factory in `api/composition`. It accepts the existing common `env_file: str | Path | None = ".env"` argument and returns a FastAPI-compatible async lifespan callback. Constructing the callback is lazy. Entering the returned lifespan enters Chunk 75; exiting it tears Chunk 75 down. Chunk 78 later stores the yielded service on lifespan-scoped `app.state`; this module still does not yield a lifespan-state dict and does not invoke the service. The module imports FastAPI for the application type only and does not import provider SDKs, settings loaders, settings objects, or lower Regulatory runtime layers.

```text
FastAPI-compatible lifespan
        ↓
Chunk 75 loaded runtime
        ↓
Chunk 74 lifecycle
```

`create_app()` does not install this lifespan. HTTP routes, request-state exposure, provider calls, and LangGraph remain unwired. Application does not import this builder.

Chunk 77 installs that FastAPI-compatible lifespan into the production application factory. `create_app()` calls `build_regulatory_intelligence_lifespan()` when no override is supplied and passes the returned callback to `FastAPI(..., lifespan=...)`. Construction remains lazy: the Chunk 76 builder does not load settings or create clients. A keyword-only optional `lifespan` argument lets transport tests inject a no-op callback without provider credentials. The factory does not write the Regulatory service to `app.state`, does not yield lifespan state, and does not execute a query. Health remains process health. Lifespan-scoped `app.state` exposure is added by Chunk 78 inside the lifespan callback, not inside `create_app()`.

```text
create_app
        ↓
Chunk 76 FastAPI lifespan
        ↓
Chunk 75 settings-loaded runtime
        ↓
Chunk 74 managed lifecycle
```

HTTP Regulatory routes, request-state exposure, provider calls, and LangGraph remain unwired.

Chunk 78 exposes the exact Chunk 75 `RegulatoryIntelligenceQueryExecutionService` on FastAPI application state while the installed lifespan is active. The stable attribute is `app.state.regulatory_intelligence_query_execution_service`. Identity is preserved: the stored object is the same instance yielded by `loaded_regulatory_intelligence_runtime`. The attribute does not exist before lifespan startup. A `try`/`finally` deletes it before the inner Chunk 75 context exits, so shutdown cannot retain a closed service. The lifespan still yields no Starlette lifespan-state dict and does not invoke `.execute(...)`. There is no FastAPI `Depends` wiring, request-state key, HTTP route, service registry, or global singleton. `create_app()` remains the already-published Chunk 77 installer and does not write `app.state` itself.

```text
create_app
        ↓
FastAPI Regulatory lifespan
        ↓
Chunk 75 service
        ↓
lifespan-scoped app.state exposure
```

Chunk 79 adds a read-only API accessor over that published state attribute. Chunk 79 itself does not add `Depends`, a Regulatory route, or HTTP query execution.

Chunk 79 introduces the request-time Regulatory service accessor. `get_regulatory_intelligence_query_execution_service(request)` lives in `api/dependencies`. It reads `request.app.state.regulatory_intelligence_query_execution_service` and returns that exact `RegulatoryIntelligenceQueryExecutionService` identity. It does not own lifecycle, assign or delete application state, wrap the service, or invoke `.execute(...)`. Missing or wrong-type state fails closed as existing transport-neutral `DependencyUnavailableError`. HTTP status translation remains in the API error-mapping layer. Production `create_app()` does not wrap this accessor in `Depends(...)`. The accessor imports FastAPI `Request` and the application service type; it does not import provider SDKs or Chunk 74–78 composition modules.

```text
Request
        ↓
API Regulatory service accessor
        ↓
lifespan-scoped app.state service
```

Chunk 80 adds API-owned HTTP transport DTOs. `RegulatoryIntelligenceQueryRequest` and `RegulatoryIntelligenceQueryResponse` live in `api/schemas`. The request mirrors `RegulatoryIntelligenceQueryExecutionService.execute(*, query_text: str, limit: int)`. The response mirrors `RegulatoryIntelligenceResult.constraints` through nested `RegulatoryConstraintResponse` fields already present on canonical `RegulatoryConstraint`. The schemas are frozen Pydantic models with unknown fields forbidden. They do not import FastAPI, the Chunk 79 accessor, or provider SDKs. There is no mapping helper, route, or `.execute`.

```text
HTTP JSON
        ↓
Regulatory API request DTO

Regulatory application result
        ↓
Regulatory API response DTO
        ↓
HTTP JSON
```

Application and domain do not depend on these schemas. Chunk 81 adds a dedicated HTTP query router that uses them.

Chunk 81 adds the first thin Regulatory Intelligence HTTP query router. `query_regulatory_intelligence` lives in `api/routers/regulatory_intelligence.py`. It accepts `RegulatoryIntelligenceQueryRequest`, resolves `RegulatoryIntelligenceQueryExecutionService` through `Depends(get_regulatory_intelligence_query_execution_service)`, awaits `execute(query_text=request.query_text, limit=request.limit)` exactly once, and returns `RegulatoryIntelligenceQueryResponse` after an explicit field-by-field projection of canonical `RegulatoryConstraint` values. Query text is not stripped. There is no handler-local exception translation, provider logic, or generic mapper. Chunk 81 itself did not install this router in production `create_app()`.

```text
RegulatoryIntelligenceQueryRequest
        ↓
Depends(get_regulatory_intelligence_query_execution_service)
        ↓
RegulatoryIntelligenceQueryExecutionService.execute(...)
        ↓
explicit HTTP response projection
        ↓
RegulatoryIntelligenceQueryResponse
```

Chunk 82 installs that published router in production `create_app()`. The factory imports `router as regulatory_intelligence_router` and includes it once with `prefix=resolved_settings.api_prefix`, the same prefix used by health. It does not reconstruct `/regulatory-intelligence/query`, import the accessor or HTTP schemas, assign `app.state`, invoke `.execute`, load Regulatory/OpenAI/Qdrant settings, or construct provider clients. Construction remains lazy. The existing keyword-only `lifespan` seam remains. Execution still depends on the lifespan-scoped service. With the default API prefix, the production path is `POST /api/v1/regulatory-intelligence/query`. Offline/test lifespans can still avoid provider credentials; missing service state maps to the published 503.

```text
create_app()
        ↓
Regulatory lifespan
        ↓
lifespan-scoped app.state service
        ↓
Regulatory router
        ↓
Depends(existing accessor)
        ↓
existing query handler
        ↓
existing query-execution service
```

LangGraph remains unwired. PDF/OCR, document indexing runtime, verified Armenian DAM rule extraction, and Pricing & Sales remain deferred.

Chunk 20 implements the application-owned write/indexing boundary. `DocumentVectorIndexPort.index()` accepts only `DocumentVectorIndexEntry` values.

Chunk 21 implements the application-owned retrieval/search boundary. `DocumentVectorSearchPort.search()` accepts only `DocumentVectorSearchQuery` and returns ranked `ExtractedDocumentChunk` values.

Chunk 22 implements the infrastructure-only Qdrant HTTP client foundation. `qdrant-client` is an infrastructure dependency. `create_qdrant_client()` lazily returns `AsyncQdrantClient` over REST (`prefer_grpc=False`) with cloud/local inference disabled. No module-global client and no `create_app()` wiring exist. Qdrant local embedded mode is not the production architecture.

Chunk 23 implements concrete adapters `QdrantDocumentVectorIndex` and `QdrantDocumentVectorSearch` behind the existing application ports. They share injected `AsyncQdrantClient` plus infrastructure-local `QdrantDocumentVectorConfig` (`collection_name`, `vector_size`). They do not own client lifecycle. Qdrant point IDs are deterministic UUID5 values derived from `(document_id, chunk_id)` and never become application DTO fields. Stored payload is closed to `document_id`, `chunk_id`, `ordinal`, `text`, `page_number`, and `content_sha256`. `content_sha256` is a SHA-256 fingerprint of the exact application index entry, including each vector member via `float.hex()`, so exact retries can be detected without reading Qdrant's stored vector representation. Writes use `UpdateMode.INSERT_ONLY` with `wait=True`, plus pre-read and post-write payload verification: exact retries are idempotent; same-identity different content is `ConflictError`; malformed stored payload is `DependencyUnavailableError`. Search calls `query_points` with already-produced numeric query vectors, reconstructs `ExtractedDocumentChunk`, and discards Qdrant scores. Production adapters still do not create collections or select a distance metric.

Chunk 24 adds the optional Compose `qdrant` profile pinning `qdrant/qdrant:v1.19.1`. REST is published only on loopback port 6333. Local API-key authentication is required. Telemetry is disabled. Storage uses named volume `qdrant-data`. Process health and `create_app()` remain independent of Qdrant. Default pytest does not require a running Qdrant process. Opt-in live tests (`qdrant_integration`, `ENERGY_RUN_QDRANT_INTEGRATION=1`) create and delete unique ephemeral collections using test-only vector size `3` and `Distance.DOT`; that fixture metric is not the platform embedding-distance selection. Production collection provisioning, production distance choice, embedding models, RAG, and the Regulatory Intelligence Agent remain unimplemented.

Chunk 105 adds infrastructure-only `verify_qdrant_document_collection_ready` beside the existing Qdrant document-vector adapters. It is a keyword-only async function over an injected `AsyncQdrantClient` and existing `QdrantDocumentVectorConfig`. It performs one `get_collection` metadata lookup and originally required unnamed SDK `VectorParams` whose size equals `config.vector_size`. Named-vector mappings, sparse-only or missing dense configuration, malformed metadata, and provider failures fail closed as sanitized `DependencyUnavailableError`. The verifier does not construct `VectorParams`, does not create/update/delete collections, does not own client lifetime, and is not an application port. Index/search adapters do not call it. `create_app()`, production/document-index/Regulatory runtimes and lifespans, Chunk 104 execution, HTTP routers, and LangGraph remain unwired. Production collection provisioning and production distance selection remain deferred.

Chunk 106 adds infrastructure-only `create_qdrant_document_collection` beside that verifier. It is a keyword-only async function over an injected `AsyncQdrantClient`, existing `QdrantDocumentVectorConfig`, and an explicit caller-supplied Qdrant `Distance`. It constructs one unnamed dense `VectorParams` (`size=config.vector_size`, `distance=distance`) and calls `create_collection` once with `collection_name=config.collection_name` and that `vectors_config`. It returns `None`. It does not probe existence, recreate/update/delete, default a metric, own client lifetime, or become an application port. An already-existing collection is a sanitized provider failure. Index/search adapters and the Chunk 105 verifier do not call it. `create_app()`, production/document-index/Regulatory runtimes and lifespans, Chunk 104 execution, HTTP routers, and LangGraph remain unwired. Automatic collection provisioning and production distance policy remain deferred.

Chunk 107 evolves that same readiness verifier so compatibility is unnamed dense `VectorParams` whose size equals `config.vector_size` and whose distance equals an explicit keyword-only caller-supplied expected `Distance`. Matching size and distance returns `None`. Distance mismatch uses the same sanitized `DependencyUnavailableError` as size mismatch, named vectors, sparse-only configuration, malformed metadata, and provider lookup failure. The verifier still performs one `get_collection` lookup, still does not construct `VectorParams`, still does not hardcode `Distance` members, still does not default a metric, and still does not call `create_qdrant_document_collection`. No settings, env, runtime, API, or LangGraph wiring is added. Production distance policy remains deferred.

Chunk 108 adds infrastructure-only `ensure_qdrant_document_collection_ready` beside those primitives. It is a keyword-only async function over an injected `AsyncQdrantClient`, existing `QdrantDocumentVectorConfig`, and an explicit caller-supplied Qdrant `Distance`. It probes `collection_exists(collection_name=config.collection_name)` once: `False` delegates to `create_qdrant_document_collection`; `True` delegates to `verify_qdrant_document_collection_ready`. The same `client`, `config`, and `distance` values are forwarded unchanged. The ensure module does not construct `VectorParams`, does not call `create_collection` or `get_collection`, does not default a metric, and does not retry, recreate, update, or delete. Existence-probe provider failures become sanitized `DependencyUnavailableError("Document vector collection availability could not be determined.")`. Delegate failures propagate unchanged. Incompatible existing collections fail closed through Chunk 107. Race conditions are not reconciled. Index/search adapters and Chunks 106/107 do not call ensure. `create_app()`, production/document-index/Regulatory runtimes and lifespans, Chunk 104 execution, HTTP routers, and LangGraph remain unwired. Automatic production provisioning and production distance policy remain deferred. Roles remain: Chunk 106 = create-only; Chunk 107 = verify-only; Chunk 108 = create-if-missing / verify-if-present orchestration.

Chunk 109 adds explicit document-vector distance configuration without selecting a production metric. Shared `QdrantDocumentVectorDistance` / `QdrantDocumentVectorDistanceSettings` accept exactly `cosine`, `dot`, `euclid`, and `manhattan` under `QDRANT_DOCUMENT_VECTOR_DISTANCE`, with no default and no `qdrant_client` dependency. This contract is separate from connection `QdrantSettings` so unrelated Qdrant HTTP consumers are not forced to supply a metric. API composition `map_qdrant_document_vector_distance(*, distance) -> Distance` is a total deterministic table from that validated enum onto Qdrant `COSINE` / `DOT` / `EUCLID` / `MANHATTAN`; unknown values fail closed rather than guessing. The mapper does not load settings, construct clients, or call create/verify/ensure. Roles remain: Chunk 106 = create mechanism; Chunk 107 = verify mechanism; Chunk 108 = ensure orchestration; Chunk 109 = explicit distance configuration + provider mapping.

Chunk 110 adds API composition `ensure_configured_document_vector_index_collection_ready(*, client, runtime_settings, distance_settings) -> None`. It accepts an already-created `AsyncQdrantClient`, already-constructed `DocumentVectorIndexRuntimeSettings`, and already-constructed `QdrantDocumentVectorDistanceSettings`. It constructs one `QdrantDocumentVectorConfig` from `qdrant_collection_name` and `qdrant_vector_size`, maps `document_vector_distance` through Chunk 109, awaits Chunk 108 `ensure_qdrant_document_collection_ready` once with the injected client, that config, and the mapped `Distance`, and returns `None`. It does not load settings, construct or close clients, default a metric, or call create/verify/`collection_exists` directly. Document-embedding model values do not participate. Deployment still supplies the metric.

Chunk 111 extends the existing document-index runtime rather than adding a second lifecycle. `loaded_document_vector_index_runtime` now also loads `QdrantDocumentVectorDistanceSettings` through the published loader using the same `env_file`. `managed_document_vector_index_runtime` receives those already-constructed settings, uses its existing managed Qdrant client, awaits Chunk 110 ensure before constructing/yielding `DocumentVectorIndexExecutionService`, and still closes both clients on failure. There is no second provisioning client. Production application lifespan therefore performs Document Vector Index collection provisioning indirectly through production lifespan → document-index lifespan → loaded runtime → managed runtime. `create_app()`, `production_lifespan.py`, and `document_vector_index_lifespan.py` were not given a second ensure call. Regulatory collection automatic provisioning, shared Regulatory/index collection identity, collection migration, recreate/update/delete, race retry/locking, aliases, payload indexes, schema versioning, OCR, automatic corpus scanning/indexing, Pricing & Sales, and Regulatory LangGraph wiring remain absent. Not all Qdrant collections are automatically provisioned.

Chunk 112 adds API composition `verify_configured_regulatory_intelligence_collection_ready(*, client, runtime_settings, distance_settings) -> None`. It accepts an already-created `AsyncQdrantClient`, already-constructed `RegulatoryIntelligenceRuntimeSettings`, and already-constructed `QdrantDocumentVectorDistanceSettings`. It constructs one `QdrantDocumentVectorConfig` from `qdrant_collection_name` and `qdrant_vector_size`, maps `document_vector_distance` through Chunk 109, awaits Chunk 107 `verify_qdrant_document_collection_ready` once with the injected client, that config, and the mapped `Distance`, and returns `None`. Query-embedding and constraint-inference model values do not participate. It does not load settings, construct or close clients, default a metric, or call create/ensure/`collection_exists`/`create_collection`. A missing or incompatible Regulatory collection fails closed through existing Chunk 107 `DependencyUnavailableError` behavior rather than being created empty.

Chunk 113 extends the existing Regulatory runtime rather than adding a second lifecycle. `loaded_regulatory_intelligence_runtime` now also loads `QdrantDocumentVectorDistanceSettings` through the published loader using the same `env_file`. `managed_regulatory_intelligence_runtime` receives those already-constructed settings, uses its existing managed Qdrant client, awaits Chunk 112 verification before constructing/yielding `RegulatoryIntelligenceQueryExecutionService`, and still closes both clients on failure. There is no second Qdrant client and no collection creation. Production application lifespan therefore performs Regulatory collection readiness verification indirectly through production lifespan → Regulatory lifespan → loaded runtime → managed runtime. `create_app()`, `production_lifespan.py`, and `regulatory_intelligence_lifespan.py` were not given a second verify call. Document Index writers continue to use ensure/create-if-missing; Regulatory query readers use verify-existing/fail-closed. Shared Regulatory/index collection identity, collection migration, recreate/update/delete, race retry/locking, aliases, payload indexes, schema versioning, OCR, automatic corpus scanning/indexing, Pricing & Sales, and Regulatory LangGraph wiring remain absent. Not all Qdrant collections are automatically provisioned.

Chunk 25 adds the optional Compose `n8n` profile pinning `n8nio/n8n:2.37.10`. HTTP is published only on loopback port 5678. Host publication uses overridable `N8N_HOST_PORT` (default 5678); the container always listens on 5678. A deployment `N8N_ENCRYPTION_KEY` is required. Diagnostics, version notifications, templates, and personalization are disabled. Storage uses named volume `n8n-data` at `/home/node/.n8n`. n8n may keep its own local SQLite/metadata inside that volume; that store is n8n internal orchestration metadata only and is not the platform energy-data system of record. n8n remains outer infrastructure for future acquisition/scheduling and must not bypass the ACL. No workflows, credentials, application/API callbacks, or LangGraph/agent integration exist. Process health and `create_app()` remain independent of n8n. Default pytest does not require a running n8n process. Opt-in live tests (`n8n_integration`, `ENERGY_RUN_N8N_INTEGRATION=1`) prove `/healthz` and `/healthz/readiness` only.

## DLQ conceptual behavior

- A record that fails validation, unit conversion, timezone normalization, or time-series cleaning after adapter retries is represented as a `DLQRecord`.
- The workflow continues for remaining records (partial success).
- DLQ records retain source identity, adapter name, diagnostics, correlation ID, and a **payload reference** — not the raw vendor payload.
- Reprocessing is an explicit later operation. Silent drops are forbidden.

Ownership:

| Layer | Owns |
| --- | --- |
| Infrastructure adapter | Reading the external payload, schema interpretation, normalization attempts, `AdapterDiagnostic`, storing/referencing failed raw data, constructing `DLQRecord` metadata |
| Application / orchestration | Receiving `StructuredIngestionResult` and later passing `dlq_records` to `DeadLetterQueuePort` |
| DLQ infrastructure | Persisting canonical DLQ metadata. Current implementation: `FilesystemDeadLetterQueue` writes one canonical JSON file per `record_id`. Not yet invoked by ingestion adapters or API composition. |

Transport for the DLQ is an infrastructure decision; application code depends only on `DeadLetterQueuePort`. The domain `DLQRecord` contract and the application sink port exist. The current sink implementation stores canonical metadata on the local filesystem (`payload_reference` remains an opaque string and is never dereferenced). PostgreSQL/TimescaleDB remains the planned system of record (ADR-004, ADR-023). A persistence foundation exists (async engine factories and a TimescaleDB/schema bootstrap migration), but there is no DLQ table and no PostgreSQL DLQ adapter. Replay, listing, and deletion are not implemented.

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

A LangGraph runtime now exists in the application orchestration layer. Application-owned `WorkflowState` from Chunk 27 remains the authoritative graph schema. Factory `build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep, parallel_ingestion_failure_runtime_handler: ParallelIngestionFailureRuntimeHandlingService)` constructs and compiles a fresh graph on every call. The Phase 2 workflow step and outer runtime failure handler are required through keyword-only dependency injection. Current topology is:

```text
START → workflow_entry → parallel_ingestion
  ingestion/running → parallel_ingestion_success_transition → END
  ingestion/failed  → END
```

`workflow_entry` is an internal async no-op: it does not call an agent, change phase or status, append diagnostics, perform I/O, persist state, or consult `FailurePolicyPort`. `parallel_ingestion` is a thin async node whose application behavior is `await parallel_ingestion_step.run(state)` and, on `BaseExceptionGroup` only, `await parallel_ingestion_failure_runtime_handler.handle(state=state, failure_group=failure_group)`. `parallel_ingestion_success_transition` is a thin async node whose only application behavior is to apply `advance_after_parallel_ingestion(state)` and return that `WorkflowState`. The graph does not construct plans, record success, call agents, inspect exception-group leaves, or reimplement phase/status assignment. A one-attributed-failure group terminates at `ingestion`/`failed`. Direct non-group exceptions still propagate. Compilation is plain (no checkpointer, store, cache, or interrupt). There is no API composition wiring. Direct project dependency is `langgraph>=1.2.11,<1.3`. Direct `langchain` and LLM-provider packages are not project dependencies. Project source must not import `langchain` or `langchain_core`.

Graph nodes must remain thin: they load canonical snapshots, call an agent or use case through application abstractions, write canonical snapshots, and record diagnostics. Nodes depend on application abstractions, not on concrete infrastructure or ML packages. The current Phase 2 node depends only on `ParallelIngestionWorkflowStep` and `ParallelIngestionFailureRuntimeHandlingService`. The success-transition node depends only on `advance_after_parallel_ingestion`. The graph itself still does not know the executor, context implementation, five agents, infrastructure, storage, or lower-level failure internals. Conditional routing exists only after Phase 2.

The current Phase 3/4 orchestration foundation is twenty-four application-owned seams:

1. Agent execution contract (`AgentName`, `AgentPort`)
2. Immutable framework-neutral `WorkflowState`
3. LangGraph runtime (`START → workflow_entry → parallel_ingestion`, then success or terminal-failure routing)
4. Framework-neutral failure-policy decision hook (`FailureAction`, `FailurePolicyContext`, `FailurePolicyPort`)
5. Framework-neutral parallel-ingestion contracts (`ParallelIngestionPlan` → `ParallelIngestionExecutionPort` → `ParallelIngestionSuccess`)
6. Concrete LangGraph-free concurrent executor (`ConcurrentParallelIngestionExecutor`)
7. Framework-neutral parallel-ingestion workflow-context boundary (`ParallelIngestionWorkflowContextPort`)
8. Framework-neutral Phase 2 workflow step (`ParallelIngestionWorkflowStep`)
9. Framework-neutral successful Phase 2 control-state transition (`advance_after_parallel_ingestion`)
10. Framework-neutral terminal Phase 2 failure transition (`fail_parallel_ingestion`)
11. Phase-2-specific failure-policy decision boundary (`ParallelIngestionFailureDecisionService`)
12. Phase-2-specific failure-policy context construction (`build_parallel_ingestion_failure_policy_context`)
13. Phase-2-specific terminal `FAIL` action execution (`execute_parallel_ingestion_failure_action`)
14. Phase-2-specific prepared failure-handling composition (`ParallelIngestionFailureHandlingService`)
15. Phase-2-specific agent-failure attribution (`ParallelIngestionAgentFailure`)
16. Phase-2-specific ExceptionGroup attributed-leaf extraction (`extract_parallel_ingestion_agent_failures`)
17. Phase-2-specific sanitized one-leaf failure classification (`classify_parallel_ingestion_agent_failure` / `ParallelIngestionFailureFact`)
18. Phase-2-specific tuple-level failure-fact classification (`classify_parallel_ingestion_agent_failures`)
19. Phase-2-specific failure-fact selection contract (`ParallelIngestionFailureSelectionPort`)
20. Phase-2-specific attempt-number source contract (`ParallelIngestionAttemptNumberPort`)
21. Phase-2-specific failure-policy context resolution service (`ParallelIngestionFailureContextResolutionService`)
22. Phase-2-specific failure-context preparation service (`ParallelIngestionFailureContextPreparationService`)
23. Phase-2-specific initial terminal-fail failure policy (`InitialParallelIngestionFailurePolicy`)
24. Phase-2-specific runtime failure-handling composition (`ParallelIngestionFailureRuntimeHandlingService`)

No current node calls the failure policy. No current node calls `fail_parallel_ingestion`. No current node calls `ParallelIngestionFailureDecisionService`. No current node calls `build_parallel_ingestion_failure_policy_context`. No current node calls `ParallelIngestionFailureContextResolutionService`. No current node calls `ParallelIngestionFailureContextPreparationService`. No current node calls `InitialParallelIngestionFailurePolicy`. No current node calls `execute_parallel_ingestion_failure_action`. No current node calls `ParallelIngestionFailureHandlingService`. No current node interprets `ParallelIngestionAgentFailure`. No current node calls `extract_parallel_ingestion_agent_failures`. No current node calls `classify_parallel_ingestion_agent_failure`. No current node calls `classify_parallel_ingestion_agent_failures`. No current node calls `ParallelIngestionFailureSelectionPort`. No current node calls `StrictSingleParallelIngestionFailureSelector`. No current node calls `ParallelIngestionAttemptNumberPort`. No current node calls `InitialParallelIngestionAttemptNumberSource`. No retries or fallbacks execute. The graph injects `ParallelIngestionWorkflowStep` and `ParallelIngestionFailureRuntimeHandlingService`. It catches only `BaseExceptionGroup` at the Phase 2 step boundary and delegates that group plus the original `WorkflowState` to the runtime handler. It does not import the plan, execution port, success aggregate, executor, context port, `FailurePolicyPort`, `fail_parallel_ingestion`, `ParallelIngestionFailureDecisionService`, `build_parallel_ingestion_failure_policy_context`, `ParallelIngestionFailureContextResolutionService`, `ParallelIngestionFailureContextPreparationService`, `InitialParallelIngestionFailurePolicy`, `execute_parallel_ingestion_failure_action`, `ParallelIngestionFailureHandlingService`, `ParallelIngestionAgentFailure`, `extract_parallel_ingestion_agent_failures`, `classify_parallel_ingestion_agent_failure`, `classify_parallel_ingestion_agent_failures`, `ParallelIngestionFailureSelectionPort`, `StrictSingleParallelIngestionFailureSelector`, `ParallelIngestionAttemptNumberPort`, or `InitialParallelIngestionAttemptNumberSource`. The executor remains an application-layer coordinator. When a Phase 2 agent raises, `ConcurrentParallelIngestionExecutor` attributes that leaf as `ParallelIngestionAgentFailure` and native TaskGroup aggregation still propagates. Application-owned `extract_parallel_ingestion_agent_failures` can extract those attributed leaves from the aggregated group; the graph does not call it. Application-owned `classify_parallel_ingestion_agent_failure` can turn one extracted leaf into a sanitized `ParallelIngestionFailureFact`; the graph does not call it. Application-owned `classify_parallel_ingestion_agent_failures` can classify an already-extracted attributed-failure tuple by delegating to that one-leaf classifier; the graph does not call it. Application-owned `ParallelIngestionFailureSelectionPort` is the typed seam that can resolve that sanitized fact tuple to one fact; Chunk 57 implements the unambiguous one-fact case with `StrictSingleParallelIngestionFailureSelector`, simultaneous multi-failure selection remains unresolved, and the graph does not call either. Application-owned `ParallelIngestionAttemptNumberPort` is the typed seam that can return the current 1-based attempt for a workflow identity; Chunk 58 implements the no-retry case with `InitialParallelIngestionAttemptNumberSource` that always returns `1`, retry-capable tracking remains unresolved, and the graph does not call either. Application-owned `ParallelIngestionFailureContextResolutionService` can compose a sanitized fact tuple, that selection port, that attempt-number port, and the published context builder into one `FailurePolicyContext`; the strict selector and initial attempt source exist but are not auto-wired, and the graph does not call it. Application-owned `ParallelIngestionFailureContextPreparationService` can compose a `BaseExceptionGroup` through extraction, tuple classification, and that resolution service into one `FailurePolicyContext`; it does not invoke policy or execute an action, and the graph does not call it. Application-owned `InitialParallelIngestionFailurePolicy` can decide `FailureAction.FAIL` for every valid context without inspecting fields or executing the action; the graph does not call it. Application-owned `ParallelIngestionFailureRuntimeHandlingService` composes a `WorkflowState` plus `BaseExceptionGroup` through preparation then existing handling into a terminal `ingestion`/`failed` snapshot on the supported single-failure path; the graph injects this outer service and does not reconstruct its internals. The context port remains Protocol-only in application. Infrastructure provides a process-local `InMemoryParallelIngestionWorkflowContext` that is not wired into the graph or `create_app()`. A successful graph path ends at `forecasting`/`running` and does not execute Phase 3. Direct non-group exceptions still propagate. The remaining runtime gap is retry-capable tracking, multi-failure policy, retry/fallback execution, diagnostics mapping, durable orchestration state, and Phase 3.

Current Phase 2 application composition (delegated by the graph node):

```text
WorkflowState.workflow_id
  → ParallelIngestionWorkflowContextPort.resolve_plan(...)
  → ParallelIngestionExecutionPort.execute(...)
  → ParallelIngestionWorkflowContextPort.record_success(...)
  → same WorkflowState
```

`ParallelIngestionWorkflowStep` coordinates that sequence. It depends only on the two application ports. It returns the original `WorkflowState` object unchanged and performs no phase/status transition. Failures propagate naturally. There is no retry, fallback, or degraded policy. Infrastructure `InMemoryParallelIngestionWorkflowContext` exists as an unwired local/dev adapter. There is no API/composition wiring.

Chunk 44 adds that first concrete context adapter in infrastructure. Application still owns `ParallelIngestionWorkflowContextPort`. `InMemoryParallelIngestionWorkflowContext` structurally implements it without inheriting the Protocol:

```text
Mapping[str, ParallelIngestionPlan]
  → InMemoryParallelIngestionWorkflowContext
  → resolve_plan / record_success
```

The constructor makes a shallow copy of the caller mapping and keeps the supplied plan objects by identity. Unknown workflow IDs fail closed as `ResourceNotFoundError`. First success write stores the exact object. Equal retries are idempotent no-ops and keep the originally stored object. Differing content for the same workflow ID is `ConflictError` and does not last-write-win. `asyncio.Lock` serializes check-and-write inside one process only. There is no durability, no cross-process guarantee, and no Redis/PostgreSQL decision. The adapter is not imported by `graph.py` or `create_app()`.

Chunk 42 adds the Phase-2-specific success transition outside both `WorkflowState` and LangGraph:

```text
ingestion / running
  → advance_after_parallel_ingestion(state)
  → forecasting / running
```

The function requires `WorkflowPhase.INGESTION` and `WorkflowStatus.RUNNING`. It returns a new frozen snapshot via `dataclasses.replace`, preserving `workflow_id`, `portfolio_id`, `delivery_date`, `correlation_id`, and `diagnostics`. Any other phase or status fails closed as `InvalidRequestError`. LangGraph node `parallel_ingestion_success_transition` applies this function after a successful workflow step. Phase 3 is not executed.

Chunk 45 adds the matching Phase-2-specific terminal failure transition outside both `WorkflowState` and LangGraph:

```text
ingestion / running
  → fail_parallel_ingestion(state)
  → ingestion / failed
```

The function requires the same `INGESTION` / `RUNNING` precondition. It returns a new frozen snapshot via `dataclasses.replace` with `phase` still `INGESTION` and `status` `FAILED`. Identity, delivery date, correlation ID, and diagnostics are preserved exactly; diagnostics are neither appended nor cleared. The function does not accept an exception argument, does not consult `FailurePolicyPort`, and does not imply retry, fallback, degraded continuation, or Phase 3. Any other phase or status fails closed as `InvalidRequestError`. LangGraph does not call this function. If the workflow step raises today, the exception still propagates.

Chunk 46 adds the Phase-2-specific failure-policy decision boundary. It owns only policy decision, not context construction and not action execution.

Chunk 47 adds the matching Phase-2-specific context constructor. It owns only published-context construction from already-sanitized typed facts:

```text
1. runtime failure occurs
2. caller obtains sanitized typed failure facts
3. build_parallel_ingestion_failure_policy_context(...)
     → published FailurePolicyContext
4. ParallelIngestionFailureDecisionService.decide(context)
     → FailurePolicyPort.decide(context)
5. published FailureAction is returned unchanged
6. execute_parallel_ingestion_failure_action(...)
     → for FAIL, fail_parallel_ingestion(state)
```

Steps 1→2 remain unimplemented as orchestration behavior. Chunk 48 implements step 6 only for `FAIL`. `RETRY` and `FALLBACK` fail closed as not implemented. Chunk 49 composes steps 4→6 when a caller already holds a sanitized `FailurePolicyContext` and a `WorkflowState`. Application-owned `build_parallel_ingestion_failure_policy_context(*, phase, error_code, attempt_number, agent_name=None) -> FailurePolicyContext` calls the published constructor once. It does not accept `Exception` / `BaseException` / traceback, does not inspect exception class or message, does not invent an `AgentName`, does not extract fields from `WorkflowState`, and does not call the decision service or `fail_parallel_ingestion`. `agent_name` keeps the published optional default of `None`. LangGraph does not import or call this function.

Application-owned `ParallelIngestionFailureDecisionService` injects exactly `FailurePolicyPort`. `async decide(context: FailurePolicyContext) -> FailureAction` awaits the published port operation once and returns that action unchanged. The service does not construct `FailurePolicyContext`. There is no concrete policy class. LangGraph does not import or call this service. If the injected policy raises an existing application exception, that exception propagates unchanged; there is no default action.

Chunk 26 introduced the framework-neutral agent invocation seam that future graph nodes must use:

```text
Application orchestration
        ↓
AgentPort[TRequest, TResult]
        ↓
Concrete application agent
        ↓
narrow application ports
        ↓
infrastructure / ML implementations
```

`AgentName` is the closed set of 13 canonical identities from `AGENTS.md`. `AgentPort` is a generic `typing.Protocol`. The only shared operations are identity (`name`) and `async run(request)`. There is no retry, fallback, registry, or base class. Concrete agents satisfy the protocol structurally. Infrastructure, ML, FastAPI, n8n, and vendor SDK types must not cross this interface.

LangGraph ≠ agent interface. The skeleton does not invoke agents. Six concrete agents exist and remain unwired from API composition. The five Phase 2 agents remain unwired from direct LangGraph calls. Regulatory Intelligence is also unwired from the graph. When later chunks add agent nodes, LangGraph must call them through `AgentPort`; it does not define agent contracts.

Chunk 27 introduced the framework-neutral application workflow snapshot. LangGraph consumes that contract as `state_schema`; it does not define a second state object. `WorkflowState` still has no transition methods and no persistence. Phase-specific canonical output slices remain deferred. Chunk 41 adds a thin Phase 2 node that delegates to `ParallelIngestionWorkflowStep`; the graph still does not call `AgentPort` directly. Chunk 42 adds `advance_after_parallel_ingestion` outside the snapshot type. Chunk 43 wires that function into node `parallel_ingestion_success_transition`.

```text
WorkflowState
  workflow_id / portfolio_id / delivery_date / correlation_id
  phase: WorkflowPhase
  status: WorkflowStatus
  diagnostics: tuple[AdapterDiagnostic, ...]
```

`WorkflowPhase` is exactly the five documented business phases (`contract`, `ingestion`, `forecasting`, `risk_and_bid`, `settlement`). `WorkflowStatus` is coarse lifecycle vocabulary (`pending`, `running`, `succeeded`, `failed`). The graph runtime consumes this contract rather than redefining it. The snapshot has construction-time validation only: no reducers, no `advance()` helpers, and no Redis/PostgreSQL checkpointing.

Chunk 29 introduced the framework-neutral failure-policy decision hook. It answers whether a sanitized application failure should be retried, diverted to a separately defined fallback path, or failed. It does not execute those actions. `FailurePolicyContext` carries only `phase`, sanitized `error_code`, 1-based `attempt_number`, and optional `AgentName`. Raw exceptions do not cross this contract. LangGraph does not own it. Chunk 47 constructs that published context from caller-supplied typed facts. Chunk 46 composes the hook for Phase 2: `ParallelIngestionFailureDecisionService` accepts an already-constructed context and delegates to `FailurePolicyPort.decide`. Chunk 48 executes terminal `FAIL` by delegating to `fail_parallel_ingestion`. Chunk 49 composes decision then action execution for an already-built context. Exception capture and retry/fallback execution remain deferred. The runtime gap still begins before sanitized failure facts exist.

Future execution interaction (not implemented):

```text
future failed operation
  → future sanitized typed failure facts
  → build_parallel_ingestion_failure_policy_context(...)
  → FailurePolicyContext
  → ParallelIngestionFailureDecisionService.decide(...)
  → FailurePolicyPort.decide(...)
  → RETRY | FALLBACK | FAIL
  → execute_parallel_ingestion_failure_action(...)
  → FAIL delegates to fail_parallel_ingestion
```

Prepared composition (LangGraph-free, unwired; does not close the runtime gap):

```text
WorkflowState + already-built FailurePolicyContext
  → ParallelIngestionFailureHandlingService.handle
  → ParallelIngestionFailureDecisionService.decide
  → execute_parallel_ingestion_failure_action
```

Conceptual future graph (not implemented):

```
Contract phase
  → parallel ingestion phase
  → ML forecasting phase
  → portfolio / risk
  → trading strategy
  → market-clearing input / result
  → settlement
```

The **Chief Orchestrator Agent** is still not implemented. Future orchestration will own graph state, routing, retries, fallback behavior, diagnostics, and workflow status. It does not embed market formulas or ML training. Current graph topology is `START → workflow_entry → parallel_ingestion`, then `ingestion`/`running` → `parallel_ingestion_success_transition` → `END` or `ingestion`/`failed` → `END`, with no five-phase routing. Current Chunk 29 policy hook is not wired into that graph. Chunk 46 decision service is not wired into that graph. Chunk 47 context builder is not wired into that graph. Chunk 48 action executor is not wired into that graph. Chunk 49 prepared failure-handling composition is not wired into that graph. Chunk 50 agent-failure attribution exists only at the concurrent executor boundary and is not graph-caught. Chunk 51 attributed-leaf extraction exists as a LangGraph-free helper and is not graph-caught. Chunk 52 sanitized one-leaf classification exists as a LangGraph-free helper and is not graph-caught. Chunk 53 tuple-level classification composition exists as a LangGraph-free helper and is not graph-caught. Chunk 54 failure-fact selection contract exists as a LangGraph-free Protocol and is not graph-caught. Chunk 57 adds a LangGraph-free `StrictSingleParallelIngestionFailureSelector` that implements that contract only for the unambiguous one-fact case; zero or multiple facts fail closed, and the graph does not import or call it. There is no first/last/agent/error/severity winner, no deduplication, and no aggregation. Simultaneous multi-failure resolution remains unresolved. Chunk 55 attempt-number source contract exists as a LangGraph-free Protocol and is not graph-caught. Chunk 58 adds a LangGraph-free `InitialParallelIngestionAttemptNumberSource` that implements that contract by returning exactly `1`; it is not a tracker, has no increment/reset/persistence, and the graph does not import or call it. Retry-capable attempt tracking remains unresolved. Chunk 56 failure-policy context resolution service exists as a LangGraph-free composition and is not graph-caught; it is not auto-wired to the strict selector or to the initial attempt source. Chunk 59 adds a LangGraph-free `ParallelIngestionFailureContextPreparationService` that composes extraction → tuple classification → context resolution from a `BaseExceptionGroup` into `FailurePolicyContext`; it does not invoke policy or execute an action, and the graph does not import or call it. Chunk 60 adds a LangGraph-free `InitialParallelIngestionFailurePolicy` that structurally satisfies `FailurePolicyPort` and returns exactly `FailureAction.FAIL` for every valid context without inspecting fields or executing the action; the graph does not import or call it. Chunk 61 adds a LangGraph-free `ParallelIngestionFailureRuntimeHandlingService` that composes failure-context preparation with existing failure handling from `WorkflowState` plus `BaseExceptionGroup`; it does not duplicate exception interpretation, policy, or action ownership. Chunk 62 injects that outer service into LangGraph, catches only `BaseExceptionGroup` at the Phase 2 step boundary, and routes `ingestion`/`failed` to `END`. Successful Phase 2 control-state transition is applied; the terminal Phase 2 failure transition exists and is applied through the runtime handler on the supported single-failure path, but the graph does not call `fail_parallel_ingestion` or lower-level failure internals directly. Phase 3 forecasting is not executed. Direct non-group exceptions still propagate. Remaining gaps are retry-capable tracking, multi-failure policy, retry/fallback execution, diagnostics mapping, and durable orchestration state. A process-local in-memory context adapter exists for local/dev use and is not composed by a Chief Orchestrator.

Chunk 30 introduced the first concrete application agent. Current path:

```text
WeatherAndRenewableForecastRequest
  → WeatherAndRenewableForecastAgent
  → WeatherRecordSourcePort
  → tuple[WeatherRecord, ...]
  → WeatherAndRenewableForecastResult
```

Future provider acquisition must remain:

```text
external weather source
  → infrastructure ACL adapter
  → canonical WeatherRecord
  → WeatherRecordSourcePort
  → Weather agent
```

After Chunk 30, one concrete Weather agent existed and remained unwired. No weather provider exists. No weather persistence exists. No retry/fallback execution exists.

Chunk 31 introduced the second concrete application agent. Current path:

```text
HydroResourcesRequest
  → HydroResourcesAgent
  → HydroRecordSourcePort
  → tuple[HydroRecord, ...]
  → HydroResourcesResult
```

Future provider acquisition must remain:

```text
external hydro source
  → infrastructure acquisition / ACL
  → canonical HydroRecord
  → HydroRecordSourcePort
  → HydroResourcesAgent
```

The Hydro application layer does not parse telemetry or files. It performs no hydrological computation. Existing optional `available_generation_mw` is consumed only if already present on a canonical `HydroRecord`. Generation Availability Agent is not called. The graph does not import this agent. No hydro provider exists. No hydro persistence exists.

Chunk 32 introduced the third concrete application agent. Current path:

```text
GenerationAvailabilityRequest
  → GenerationAvailabilityAgent
  → GenerationAvailabilityRecordSourcePort
  → tuple[GenerationAvailabilityRecord, ...]
  → GenerationAvailabilityResult
```

Future provider acquisition must remain:

```text
external generation / outage source
  → infrastructure acquisition / ACL
  → canonical GenerationAvailabilityRecord
  → GenerationAvailabilityRecordSourcePort
  → GenerationAvailabilityAgent
```

The Generation application layer does not parse vendor outage or plant-availability sources. It performs no capacity calculation and no status inference. It does not assume a missing plant/unit is available, unavailable, or irrelevant. It does not implement fleet-completeness policy. It does not derive `GenerationAvailabilityRecord` from `HydroRecord`. The graph does not import this agent. No generation provider exists. No generation persistence exists.

Chunk 33 introduced the fourth concrete application agent. Current path:

```text
NewsIntelligenceRequest
  → NewsIntelligenceAgent
  → NewsEventSourcePort
  → tuple[NewsEvent, ...]
  → NewsIntelligenceResult
```

Future provider acquisition must remain:

```text
external news/feed source
  → infrastructure acquisition / ACL
  → canonical NewsEvent
  → NewsEventSourcePort
  → NewsIntelligenceAgent
```

The News application layer does not parse HTML, RSS, or vendor payloads. No raw article/feed object enters application. The agent does not call an LLM or ML model. It does not summarize, classify, translate, or infer sentiment, relevance, or market impact. Canonical `headline`, `summary`, optional `category`, and optional `severity` pass through unchanged if already present on a valid `NewsEvent`. There is no News persistence and no News vector indexing. The graph does not import this agent. No news provider exists.

Chunk 34 introduced the fifth concrete application agent. Current path:

```text
MarketMonitoringRequest
  → MarketMonitoringAgent
  → MarketPriceRecordSourcePort
  → tuple[MarketPriceRecord, ...]
  → MarketMonitoringResult
```

Future provider acquisition must remain:

```text
external official/operator market source
  → infrastructure acquisition / ACL
  → canonical MarketPriceRecord
  → MarketPriceRecordSourcePort
  → MarketMonitoringAgent
```

The Market application layer does not parse operator reports, CSV, Excel, HTML, or vendor payloads. No raw market object enters application. Currency remains explicit on canonical `EnergyPrice`; there is no AMD default and no FX or price conversion. Interval duration and cadence are not assumed. Missing prices are not fabricated. Optional `volume_mwh` passes through unchanged. The agent does not forecast prices, does not construct `PriceForecastPoint`, and does not clear the market. Chunk 34 does not introduce a market-status model. There is no Market persistence. The graph does not import this agent. No market provider exists.

Chunk 63 introduced the sixth concrete application agent. Current path:

```text
RegulatoryIntelligenceRequest
  → RegulatoryIntelligenceAgent
  → DocumentVectorSearchPort.search(query)
  → tuple[ExtractedDocumentChunk, ...]
  → empty → RegulatoryIntelligenceResult(constraints=())
  → otherwise RegulatoryConstraintInferencePort.infer(chunks=...)
  → tuple[RegulatoryConstraint, ...]
  → RegulatoryIntelligenceResult
```

Future provider composition must remain:

```text
PDF/document acquisition
  → infrastructure extraction / ACL
  → ExtractedDocumentChunk
  → embedding / indexing (existing ports)
  → DocumentVectorSearchPort
  → RegulatoryIntelligenceAgent
  → RegulatoryConstraintInferencePort
  → canonical RegulatoryConstraint
```

The Regulatory application layer does not parse PDFs, call an LLM SDK, embed query text, or import Qdrant types. No prompt, provider, model, collection, score, or raw document crosses the agent boundary. Empty retrieval is fail-safe: no evidence yields no constraints, and inference is not invoked. The agent does not construct `RegulatoryConstraint` values and does not hardcode Armenian DAM rules. Application still has no OpenAI import. Chunk 64 added `DocumentQueryEmbeddingPort` as a separate application seam. Chunk 65 added `DocumentVectorSearchQueryPreparationService` as a separate composition of query text → query embedding → `DocumentVectorSearchQuery`. Chunk 66 added `RegulatoryIntelligenceQueryExecutionService` as the outer application composition of query text + limit → that preparation service → `RegulatoryIntelligenceRequest` → the unchanged agent → `RegulatoryIntelligenceResult`. Chunk 67 added API-owned `build_regulatory_intelligence_query_execution` as the object-construction root over the three published application ports. Chunk 68 added infrastructure `OpenAIDocumentQueryEmbeddingAdapter` behind `DocumentQueryEmbeddingPort`; application and the outer builder remain OpenAI-free. Chunk 69 added infrastructure `OpenAIRegulatoryConstraintInferenceAdapter` behind `RegulatoryConstraintInferencePort`; it converts structured OpenAI output into canonical `RegulatoryConstraint` after an infrastructure-local evidence-reference check. Application still depends only on the published inference port. Regulatory Intelligence still receives `DocumentVectorSearchQuery` and does not inject the embedding port or query-preparation service. Application does not import the outer builder. The graph and `create_app()` do not invoke this agent, the query-execution service, the Chunk 114 workflow step, the builder, or either OpenAI adapter. OpenAI client **construction capability** exists as typed settings plus a lazy factory; production client lifecycle, adapter injection, and model runtime selection remain absent. Actual regulatory RAG is not operational.

Six concrete agents exist. LangGraph does not import or call them. It injects `ParallelIngestionWorkflowStep` into node `parallel_ingestion` and awaits `run(state)`. That step can invoke the five Phase 2 agents only when a caller has composed `ParallelIngestionExecutionPort` (typically `ConcurrentParallelIngestionExecutor`) and a context port behind it. Application-owned `ParallelIngestionPlan` can hold the five existing typed Phase 2 requests together. Application-owned `ConcurrentParallelIngestionExecutor` structurally implements `ParallelIngestionExecutionPort`: it injects those five application agents, runs `agent.run(...)` concurrently with `asyncio.TaskGroup`, and returns `ParallelIngestionSuccess` only when all five succeed. Ordinary agent failures become `ParallelIngestionAgentFailure` leaves with canonical `AgentName` and chained causes; native TaskGroup exception/cancellation semantics still apply. Sibling cancellation is not attributed as agent failure. Application-owned `ParallelIngestionWorkflowContextPort` can resolve a prepared plan and record all-five-success output by workflow identity without expanding `WorkflowState`. Application-owned `ParallelIngestionWorkflowStep` composes that resolve → execute → record sequence and returns the original `WorkflowState` unchanged. Application-owned `advance_after_parallel_ingestion` can replace a valid `ingestion`/`running` snapshot with `forecasting`/`running`. LangGraph node `parallel_ingestion_success_transition` applies that function after a successful workflow step. Application-owned `fail_parallel_ingestion` can replace a valid `ingestion`/`running` snapshot with `ingestion`/`failed` without mutating diagnostics; the graph does not call it. Application-owned `ParallelIngestionFailureDecisionService` can decide a `FailureAction` from an already-constructed `FailurePolicyContext` without executing it; the graph does not call it. Application-owned `build_parallel_ingestion_failure_policy_context` can construct that published context from already-sanitized typed facts; the graph does not call it. Application-owned `execute_parallel_ingestion_failure_action` can apply terminal `FailureAction.FAIL` by delegating to `fail_parallel_ingestion` and rejects `RETRY` / `FALLBACK` as not implemented; the graph does not call it. Application-owned `ParallelIngestionFailureHandlingService` can compose an already-built `FailurePolicyContext` through the published decision service and action executor; the graph does not call it. Application-owned `extract_parallel_ingestion_agent_failures` can extract already-attributed `ParallelIngestionAgentFailure` leaves from a possibly nested exception group; the graph does not call it. Application-owned `classify_parallel_ingestion_agent_failure` can convert one attributed leaf into sanitized `ParallelIngestionFailureFact`; the graph does not call it. Application-owned `classify_parallel_ingestion_agent_failures` can classify an already-extracted attributed-failure tuple by delegating each element to that one-leaf classifier; it preserves order, cardinality, and duplicate agent identities, does not select a primary failure, and the graph does not call it. Application-owned `ParallelIngestionFailureSelectionPort` is the Phase-2-specific selection contract over that sanitized fact tuple; it has no first/last/priority winner semantics, and the graph does not call it. Application-owned `StrictSingleParallelIngestionFailureSelector` implements that contract for the unambiguous one-fact case only; zero or multiple facts fail closed, simultaneous multi-failure selection remains unresolved, and the graph does not call it. Application-owned `ParallelIngestionAttemptNumberPort` is the Phase-2-specific read-only attempt-number source contract over workflow identity; it has no increment/reset semantics on the port, and the graph does not call it. Application-owned `InitialParallelIngestionAttemptNumberSource` implements that contract for the current no-retry runtime by returning exactly `1`; it is not a tracker, and the graph does not call it. Application-owned `ParallelIngestionFailureContextResolutionService` composes that selection port, attempt-number port, and the published context builder into one `FailurePolicyContext`; it implements no selection algorithm, no attempt tracking, no policy decision, and no action execution, the strict selector and initial attempt source exist but are not auto-wired, and the graph does not call it. Application-owned `ParallelIngestionFailureContextPreparationService` composes a `BaseExceptionGroup` through extraction, tuple classification, and that resolution service into one `FailurePolicyContext`; it does not duplicate exception interpretation, does not invoke policy, does not execute an action, and the graph does not call it. Phase 3 is not executed. Partial/failure/degraded fan-in semantics are not defined. Infrastructure `InMemoryParallelIngestionWorkflowContext` exists as unwired local/dev reference storage. Production/durable workflow-context implementation does not exist. No weather, hydro, generation, news, or market provider exists. No weather, hydro, generation, news, or market persistence exists. No retry/fallback execution exists. LangGraph Phase 2 join (failure/degraded/runtime composition) remains future work.

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

Chunk 35 adds only the typed fan-out plan. Application-owned `ParallelIngestionPlan` is a frozen composition DTO with exactly:

- `weather_and_renewable_forecast: WeatherAndRenewableForecastRequest`
- `hydro_resources: HydroResourcesRequest`
- `generation_availability: GenerationAvailabilityRequest`
- `news_intelligence: NewsIntelligenceRequest`
- `market_monitoring: MarketMonitoringRequest`

It reuses the existing request DTOs. It is not `WorkflowState`. It does not execute agents, use LangGraph, or derive `location_id` / `resource_id` / `asset_id` / `market_id` from `portfolio_id`. Horizons are not required to be equal.

Chunk 36 adds only the typed all-five-success fan-in aggregate. Application-owned `ParallelIngestionSuccess` is a frozen composition DTO with exactly:

- `weather_and_renewable_forecast: WeatherAndRenewableForecastResult`
- `hydro_resources: HydroResourcesResult`
- `generation_availability: GenerationAvailabilityResult`
- `news_intelligence: NewsIntelligenceResult`
- `market_monitoring: MarketMonitoringResult`

It reuses the existing result DTOs. It is not `WorkflowState`. It does not execute agents, use LangGraph, merge/sort/deduplicate records, or encode partial/failure/degraded/skipped branch semantics.

Chunk 37 adds only the typed execution boundary. Application-owned `ParallelIngestionExecutionPort` is a non-generic `typing.Protocol` with exactly one public operation:

```text
async execute(self, plan: ParallelIngestionPlan) -> ParallelIngestionSuccess
```

Chunk 38 adds the first concrete implementation. Application-owned `ConcurrentParallelIngestionExecutor` structurally satisfies that port:

```text
ParallelIngestionPlan
  → ConcurrentParallelIngestionExecutor
  → ParallelIngestionSuccess
```

Constructor dependencies are exactly the five existing application agents. `execute` creates five `asyncio.TaskGroup` tasks, one per attributed `agent.run(plan.<branch>)`, before waiting for completion. `ParallelIngestionSuccess` is returned only after all five succeed, preserving the result DTO objects. A branch exception is wrapped as `ParallelIngestionAgentFailure` with that branch's canonical `AgentName` and `raise ... from` chaining; sibling cancellation is not wrapped. Native TaskGroup `ExceptionGroup` aggregation still propagates. This slice does not retry, fall back, degrade, invent a partial aggregate, or interpret the `ExceptionGroup`. The executor does not import LangGraph, does not consult `FailurePolicyPort`, and does not expand `WorkflowState`. It is not wired into `graph.py` or `create_app()`.

Chunk 39 adds the typed workflow-context boundary. Application-owned `ParallelIngestionWorkflowContextPort` is a non-generic `typing.Protocol` with exactly:

```text
async resolve_plan(self, workflow_id: str) -> ParallelIngestionPlan
async record_success(self, workflow_id: str, success: ParallelIngestionSuccess) -> None
```

`workflow_id` reuses the published `WorkflowState.workflow_id` type (`str`). The port does not embed plan or success on `WorkflowState` and does not choose storage technology. LangGraph remains `START → workflow_entry → END` in that historical slice.

Chunk 40 adds the first framework-neutral composition of those seams. Application-owned `ParallelIngestionWorkflowStep` injects exactly `ParallelIngestionWorkflowContextPort` and `ParallelIngestionExecutionPort`. Its only public operation is:

```text
async run(self, state: WorkflowState) -> WorkflowState
```

Successful `run` is exactly `resolve_plan` → `execute` → `record_success`, then return of the original `WorkflowState` object by identity. The step does not construct a replacement snapshot, mutate phase/status/diagnostics, consult `FailurePolicyPort`, or import LangGraph. Failures propagate naturally and skip remaining operations. The concrete executor remains a composition-root concern.

Chunk 41 wires that step into LangGraph. Factory `build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep)` compiles:

```text
START → workflow_entry → parallel_ingestion → END
```

`parallel_ingestion` awaits the injected step and returns the resulting `WorkflowState`. Chunk 41 did not import the executor, context port, five agents, `FailurePolicyPort`, or `advance_after_parallel_ingestion`. There is no concrete context implementation and no `create_app()` wiring. Actual orchestrator Phase 2 join remains future work.

Chunk 42 adds the LangGraph-free successful Phase 2 control-state transition. Application-owned `advance_after_parallel_ingestion(state: WorkflowState) -> WorkflowState` is a Phase-2-specific function, not a generic workflow engine and not a method on `WorkflowState`:

```text
advance_after_parallel_ingestion
  requires: phase=ingestion, status=running
  returns: new WorkflowState(phase=forecasting, status=running)
  preserves: workflow_id, portfolio_id, delivery_date, correlation_id, diagnostics
```

Wrong phase or status fails closed as `InvalidRequestError`. The input snapshot is not mutated. Phase 3 agents are not invoked.

Chunk 43 wires that published function into LangGraph as a thin node. Factory `build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep)` now compiles:

```text
START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END
```

`parallel_ingestion_success_transition` applies `advance_after_parallel_ingestion(state)` and returns that `WorkflowState`. It does not reimplement preconditions or `dataclasses.replace`. A successful graph path therefore ends at `forecasting`/`running`. If the workflow step raises, the transition node does not run and the exception propagates without retry or fallback. Phase 3 forecasting is still not executed.

Chunk 44 adds the first concrete context adapter outside application. Infrastructure `InMemoryParallelIngestionWorkflowContext` copies constructor-prepared plans, fails closed on missing workflow identity, records success idempotently for equal retries, and rejects conflicting content. Coroutine-level writes use `asyncio.Lock`. The adapter is local/dev reference infrastructure only: not durable, not Redis/PostgreSQL, and not wired into LangGraph or `create_app()`.

Chunk 45 adds the LangGraph-free terminal Phase 2 failure transition. Application-owned `fail_parallel_ingestion(state: WorkflowState) -> WorkflowState` is a Phase-2-specific function, not a generic workflow engine and not a method on `WorkflowState`:

```text
fail_parallel_ingestion
  requires: phase=ingestion, status=running
  returns: new WorkflowState(phase=ingestion, status=failed)
  preserves: workflow_id, portfolio_id, delivery_date, correlation_id, diagnostics
```

Wrong phase or status fails closed as `InvalidRequestError`. The input snapshot is not mutated. Diagnostics are not rewritten. Exceptions are not mapped. `FailurePolicyPort` is not consulted. LangGraph does not import or call this function. If the workflow step raises, the exception still propagates without a failure node or conditional edge.

Chunk 46 adds the LangGraph-free Phase 2 failure-policy decision boundary. Application-owned `ParallelIngestionFailureDecisionService` injects exactly `FailurePolicyPort` and exposes `async decide(context: FailurePolicyContext) -> FailureAction`:

```text
already-constructed FailurePolicyContext
  → ParallelIngestionFailureDecisionService.decide
  → FailurePolicyPort.decide
  → FailureAction unchanged
```

The service does not construct context, does not interpret or execute the action, and does not call `fail_parallel_ingestion`. Policy exceptions propagate unchanged. There is no concrete policy. LangGraph does not import or call this service.

Chunk 47 adds the LangGraph-free Phase 2 failure-policy context constructor. Application-owned `build_parallel_ingestion_failure_policy_context` is a synchronous function, not a service class and not a Protocol:

```text
typed phase / error_code / attempt_number / optional AgentName
  → build_parallel_ingestion_failure_policy_context
  → published FailurePolicyContext
```

The function does not inspect exceptions, does not invent an agent identity, does not read `WorkflowState`, and does not call the decision service or `fail_parallel_ingestion`. Existing `FailurePolicyContext` validation runs unchanged. LangGraph does not import or call this function.

Chunk 48 adds the LangGraph-free Phase 2 terminal `FAIL` action executor. Application-owned `execute_parallel_ingestion_failure_action` is a synchronous function, not a service class and not a Protocol:

```text
already-decided FailureAction + current WorkflowState
  → execute_parallel_ingestion_failure_action
  → FAIL: fail_parallel_ingestion(state)
  → RETRY / FALLBACK: InvalidRequestError (not implemented)
```

Decision, context construction, and terminal-transition ownership remain separate. `FAIL` does not duplicate Chunk 45 preconditions or `dataclasses.replace`. `RETRY` and `FALLBACK` reject explicitly rather than silently no-op. Diagnostics are not rewritten. LangGraph does not import or call this function. Runtime Phase 2 exceptions still propagate from the graph.

Chunk 49 adds the LangGraph-free Phase 2 prepared failure-handling composition. Application-owned `ParallelIngestionFailureHandlingService` injects exactly `ParallelIngestionFailureDecisionService` and exposes `async handle(*, state: WorkflowState, context: FailurePolicyContext) -> WorkflowState`:

```text
WorkflowState + already-built FailurePolicyContext
  → ParallelIngestionFailureHandlingService.handle
  → ParallelIngestionFailureDecisionService.decide
  → execute_parallel_ingestion_failure_action
  → resulting WorkflowState
```

The service does not construct context, does not branch on `FailureAction`, and does not call `fail_parallel_ingestion` directly. Policy exceptions propagate unchanged. `FAIL` still delegates through the published executor to `fail_parallel_ingestion`. `RETRY` and `FALLBACK` still fail closed as not implemented. LangGraph does not import or call this service. Runtime Phase 2 exceptions still propagate from the graph because this composition is not graph-wired and does not build failure facts. The runtime gap still begins before sanitized failure facts exist.

Chunk 50 adds LangGraph-free Phase 2 agent-failure attribution at the concurrent executor boundary. Application-owned `ParallelIngestionAgentFailure` carries canonical `AgentName` only:

```text
agent runtime failure
  → ConcurrentParallelIngestionExecutor attributes AgentName
  → ParallelIngestionAgentFailure (cause chained)
  → TaskGroup aggregation/propagation
  → still-unimplemented runtime interpretation
  → sanitized facts
  → context construction
  → decision
  → handling/action
```

Sibling cancellation is not classified as agent failure. `ExceptionGroup` interpretation, error-code mapping, attempt tracking, and Chunk 46–49 policy/handling invocation remain deferred. The graph does not catch or route these exceptions.

Chunk 51 adds LangGraph-free attributed-leaf extraction after TaskGroup aggregation. Application-owned `extract_parallel_ingestion_agent_failures` recursively traverses a possibly nested `BaseExceptionGroup` and returns exact original `ParallelIngestionAgentFailure` objects in depth-first left-to-right encounter order:

```text
agent runtime failure
→ ParallelIngestionAgentFailure attribution
→ TaskGroup / ExceptionGroup aggregation
→ attributed-leaf extraction
→ still-unimplemented classification / failure selection
→ sanitized failure facts
→ context construction
→ decision
→ action handling
```

Only the first extraction stage after aggregation exists. The helper does not classify leaves, select a primary failure, map `error_code`, construct `FailurePolicyContext`, or invoke Chunk 46–49 policy/handling. Unattributed leaves fail closed as `InvalidRequestError`. The graph does not call this function. Runtime Phase 2 exceptions still propagate from the graph.

Chunk 52 adds LangGraph-free sanitized one-leaf failure classification after attributed-leaf extraction. Application-owned `classify_parallel_ingestion_agent_failure` converts exactly one `ParallelIngestionAgentFailure` into frozen `ParallelIngestionFailureFact`:

```text
agent runtime failure
→ canonical AgentName attribution
→ TaskGroup / ExceptionGroup aggregation
→ attributed-leaf extraction
→ sanitized one-leaf failure classification
→ still-unimplemented multi-failure selection
→ attempt number
→ FailurePolicyContext
→ decision
→ handling/action
```

`ApplicationError` causes reuse their published application error code. Non-application and missing causes collapse to `parallel_ingestion_unexpected_failure`. Exception text, class names, and tracebacks never become policy facts. The classifier does not select among multiple failures, does not assign attempt numbers, does not construct `FailurePolicyContext`, and does not invoke Chunk 46–49 policy/handling. The graph does not call this function. Runtime Phase 2 exceptions still propagate from the graph.

Chunk 53 adds LangGraph-free tuple-level failure-fact classification after attributed-leaf extraction. Application-owned `classify_parallel_ingestion_agent_failures` converts `tuple[ParallelIngestionAgentFailure, ...]` into `tuple[ParallelIngestionFailureFact, ...]` by delegating each already-extracted leaf to the existing one-leaf classifier:

```text
agent runtime failure
→ attribution
→ ExceptionGroup
→ attributed-leaf extraction
→ tuple-level sanitized classification
→ tuple[ParallelIngestionFailureFact, ...]
→ still-unimplemented multi-failure selection
→ attempt-number source still missing
→ FailurePolicyContext
→ prepared handling
→ LangGraph routing still missing
```

Chunk 53 operates only after extraction has already produced attributed failures. It preserves encounter order, cardinality, and duplicate agent identities. An empty input tuple returns an empty output tuple. It does not inspect `__cause__`, does not duplicate Chunk 52 error-code mapping, does not select a primary failure, does not assign attempt numbers, does not construct `FailurePolicyContext`, and does not invoke Chunk 46–49 policy/handling. The graph does not call this function. Runtime Phase 2 exceptions still propagate from the graph.

Chunk 54 adds a LangGraph-free Phase-2-specific selection contract after tuple-level classification. Application owns non-generic `ParallelIngestionFailureSelectionPort` with a single synchronous operation `select(facts: tuple[ParallelIngestionFailureFact, ...]) -> ParallelIngestionFailureFact`:

```text
agent runtime failure
→ attribution
→ ExceptionGroup
→ attributed-leaf extraction
→ tuple-level sanitized classification
→ tuple[ParallelIngestionFailureFact, ...]
→ selection boundary exists, concrete selection policy still missing
→ attempt-number source still missing
→ FailurePolicyContext
→ prepared decision/action handling
→ LangGraph routing still missing
```

The Protocol consumes already-sanitized facts only and returns one fact. There is no first/last/agent/error/retryability/severity winner rule and no empty-tuple production default in this contract. Chunk 57 later implements the unambiguous one-fact case structurally; simultaneous multi-failure policy remains undefined here. Selection remains separate from attribution, extraction, classification, context construction, failure policy, action execution, and LangGraph. The graph does not import or call this port. Runtime Phase 2 exceptions still propagate from the graph.

Chunk 55 adds a LangGraph-free Phase-2-specific attempt-number source contract after the selection boundary. Application owns non-generic `ParallelIngestionAttemptNumberPort` with a single async operation `get_attempt_number(workflow_id: str) -> int`:

```text
agent runtime failure
→ attribution
→ ExceptionGroup
→ attributed-leaf extraction
→ tuple-level sanitized classification
→ failure-fact selection contract
→ concrete selector still missing
→ attempt-number source contract
→ concrete attempt tracking/source implementation still missing
→ FailurePolicyContext
→ prepared decision/action handling
→ LangGraph routing still missing
```

The Protocol accepts only workflow identity and returns the current 1-based attempt. There is no concrete implementation, no increment/reset/set/record write API, no persistence, no retry ownership, and no empty or invalid-number production default. Attempt-number reading remains separate from classification, selection, context construction, failure policy, action execution, and LangGraph. The graph does not import or call this port. Runtime Phase 2 exceptions still propagate from the graph.

Chunk 56 adds a LangGraph-free Phase-2-specific failure-policy context resolution service after the selection and attempt-number contracts. Application owns concrete `ParallelIngestionFailureContextResolutionService` that injects `ParallelIngestionFailureSelectionPort` and `ParallelIngestionAttemptNumberPort`, then:

```text
agent runtime failure
→ attribution
→ ExceptionGroup
→ attributed-leaf extraction
→ tuple-level sanitized classification
→ failure-context resolution service
→ selection port
→ attempt-number port
→ existing context builder
→ FailurePolicyContext
→ prepared decision/action handling
→ LangGraph routing still missing
```

`async resolve(*, workflow_id, phase, facts)` selects once, awaits attempt lookup once, and delegates construction to `build_parallel_ingestion_failure_policy_context`. Application owns this composition; the service implements no selection algorithm, no attempt tracking, no policy decision, no action execution, and no LangGraph coupling. Context construction is not duplicated. The service is callable only when concrete implementations are injected. Chunk 57 adds `StrictSingleParallelIngestionFailureSelector` as a structural implementation of the selection port; it is not auto-wired into this service. Chunk 58 adds `InitialParallelIngestionAttemptNumberSource` as a structural implementation of the attempt-number port; it is not auto-wired into this service. Retry-capable attempt tracking still does not exist. The graph does not import or call this service. Runtime Phase 2 exceptions still propagate from the graph.

Chunk 57 adds a LangGraph-free Phase-2-specific strict single-failure selector after the published selection contract. Application owns concrete `StrictSingleParallelIngestionFailureSelector` that structurally satisfies `ParallelIngestionFailureSelectionPort` without inheriting it:

```text
agent runtime failure
→ attribution
→ ExceptionGroup
→ attributed-leaf extraction
→ tuple-level sanitized classification
→ strict single-failure selector
   exactly one fact → same fact instance
   zero or multiple facts → fail closed
→ attempt-number source contract
→ initial attempt-number source (`1`)
→ failure-context resolution service
→ FailurePolicyContext
→ prepared decision/action handling
→ LangGraph routing still missing
```

Exactly one sanitized fact is returned unchanged. Zero facts and two-or-more facts raise sanitized `InvalidRequestError`. There is no first/last winner, no agent/error/severity priority, no ranking, no deduplication, and no aggregation. Simultaneous multi-failure resolution remains deliberately unresolved. The selector is not wired into LangGraph. Retry-capable attempt tracking remains absent.

Chunk 58 adds a LangGraph-free Phase-2-specific initial attempt-number source after the published attempt-number contract. Application owns concrete `InitialParallelIngestionAttemptNumberSource` that structurally satisfies `ParallelIngestionAttemptNumberPort` without inheriting it:

```text
sanitized failure tuple
→ strict single selector
→ selected fact
→ initial attempt-number source (`1`)
→ failure-context resolution service
→ FailurePolicyContext
→ prepared failure handling
→ LangGraph routing still missing
```

The source is async and stateless. It returns the literal integer `1` for every workflow identity because the published runtime has no retry execution. It is storage-neutral because it has no storage. It is not a tracker and is not suitable as a future retry tracker. There is no increment, reset, persistence, or graph wiring. Future retry support requires separately reviewed tracking semantics.

Chunk 59 adds a LangGraph-free Phase-2-specific failure-context preparation service after the published extraction, classification, and context-resolution stages. Application owns concrete `ParallelIngestionFailureContextPreparationService` that injects `ParallelIngestionFailureContextResolutionService`, then:

```text
agent runtime failure
→ attribution
→ TaskGroup / ExceptionGroup
→ failure-context preparation service
→ extraction
→ tuple classification
→ context-resolution service
→ strict single selector
→ initial attempt-number source (`1`)
→ context builder
→ FailurePolicyContext
→ prepared policy/action handling
→ LangGraph runtime failure routing still missing
```

`async prepare(*, workflow_id, phase, failure_group)` extracts once, classifies once, and awaits context resolution once. Application owns this composition; the service does not traverse exception groups itself, does not inspect causes, does not select among facts, does not resolve attempt numbers, does not invoke policy, does not execute an action, and has no LangGraph coupling. One attributed failure is fully preparable into context at application level. Multiple attributed failures still fail closed. Runtime graph invocation is still absent.

Chunk 60 adds a LangGraph-free Phase-2-specific initial terminal-fail failure policy after the published `FailurePolicyPort`. Application owns concrete `InitialParallelIngestionFailurePolicy` that structurally satisfies that port without inheriting it:

```text
ExceptionGroup
→ failure-context preparation
→ FailurePolicyContext
→ initial failure policy
→ FailureAction.FAIL
→ prepared action execution exists downstream
→ LangGraph runtime failure routing still missing
```

The policy is async and stateless. It returns exactly `FailureAction.FAIL` for every valid context and does not inspect `phase`, `error_code`, `attempt_number`, or `agent_name`. It has no side effects and does not execute the returned action. It is intentionally conservative because retry and fallback execution do not exist. Future richer policy requires separate architectural review and supporting runtime mechanisms. The graph does not import or call this policy.

Chunk 61 adds a LangGraph-free Phase-2-specific outer runtime failure-handling composition after the published preparation and handling services. Application owns concrete `ParallelIngestionFailureRuntimeHandlingService` that coordinates those services without duplicating them:

```text
Phase 2 ExceptionGroup
→ runtime handling service
→ failure-context preparation
→ FailurePolicyContext
→ existing failure handling
→ initial policy = FAIL
→ existing terminal action
→ INGESTION / FAILED
→ LangGraph routes ingestion/failed to END
```

Keyword-only `async handle(*, state, failure_group)` derives context from `state.workflow_id`, `state.phase`, and the supplied group, then forwards that context plus the original state into `ParallelIngestionFailureHandlingService`. The service does not inspect exception groups, classify error codes, select facts, resolve attempt numbers, call `FailurePolicyPort`, branch on `FailureAction`, or construct a failed `WorkflowState`. One attributed failure is executable end-to-end at application level into terminal `ingestion`/`failed`. Multiple attributed failures still fail closed.

Chunk 62 wires that published runtime handler into LangGraph at the Phase 2 workflow-step boundary. Factory `build_workflow_graph` now requires both `ParallelIngestionWorkflowStep` and `ParallelIngestionFailureRuntimeHandlingService` through keyword-only injection. The graph factory does not construct the handler or any of its dependencies. After `parallel_ingestion`:

```text
START → workflow_entry → parallel_ingestion
  BaseExceptionGroup → runtime handler → INGESTION / FAILED → END
  success → parallel_ingestion_success_transition → FORECASTING / RUNNING → END
```

The node catches only `BaseExceptionGroup`. It does not inspect `.exceptions`, `__cause__`, messages, or traceback. Direct non-group exceptions still propagate. Unexpected post-Phase-2 phase/status combinations fail closed as `InvalidRequestError`. `WorkflowState` remains seven fields. There is no checkpointer, store, reducer, retry/fallback execution, multi-failure selector, Phase 3 execution, or `create_app()` wiring.

## Storage responsibilities

| Store | Responsibility | Not for |
| --- | --- | --- |
| PostgreSQL / TimescaleDB | Relational records and time-series (canonical facts, forecasts, bids, settlements, DLQ/outbox) | Unstructured document search |
| Qdrant | Regulatory/document retrieval embeddings and payloads. Chunk 22 added an infrastructure-only HTTP client foundation (`qdrant-client>=1.19,<2`, typed `QdrantSettings`, lazy `create_qdrant_client()` → `AsyncQdrantClient`, REST/`prefer_grpc=False`, `cloud_inference=False`). Chunk 23 added `QdrantDocumentVectorIndex` / `QdrantDocumentVectorSearch` with deterministic UUID point identity, a closed normalized payload plus SHA-256 entry fingerprint, `INSERT_ONLY` verified writes, and score-discarding `query_points` search. Chunk 24 added an on-demand Compose `qdrant` profile pinning `qdrant/qdrant:v1.19.1`, loopback-only REST port 6333, required local API-key authentication, disabled telemetry, and named volume `qdrant-data`. This local HTTP+API-key profile is development/test infrastructure, not the production Qdrant security architecture. No global client, no `create_app()` wiring, and no local embedded mode. Chunk 111 gives the existing Document Vector Index managed runtime ownership of Chunk 110 collection ensure on that same managed Qdrant client, so production application lifespan indirectly provisions the Document Vector Index collection. Chunk 113 gives the existing Regulatory managed runtime ownership of Chunk 112 verify-existing collection readiness on that same managed Qdrant client, so production application lifespan indirectly fails closed if the Regulatory collection is missing or incompatible. It does not create a missing Regulatory collection. Regulatory collection automatic provisioning, shared Regulatory/index collection identity, collection migration, and production distance defaults remain absent. Chunk 105 added read-only `verify_qdrant_document_collection_ready`. Chunk 106 added explicit create-only `create_qdrant_document_collection` that forwards a caller-supplied `Distance` into unnamed dense `VectorParams` without existence lookup. Chunk 107 evolved that verifier so unnamed dense size and caller-supplied expected `Distance` must both match. Live tests create unique ephemeral collections with test-only size `3` and `Distance.DOT`. Embeddings remain behind `DocumentEmbeddingPort`. | Authoritative time-series or financial books |
| Redis | Ephemeral TTL-bound cache (ADR-006, ADR-026, ADR-027, ADR-028). Application owns vendor-neutral `CachePort[TValue]`. Infrastructure `RedisCache[TValue]` uses redis-py async, an injected `CacheCodec`, and hashed backend keys. Local Compose `redis` profile pins `redis:8.2.9-alpine`, publishes loopback-only, requires a password, and disables RDB/AOF. Cache values are ephemeral; loss, flush, eviction, or expiry is acceptable. This adapter is not an orchestration-state or distributed-lock abstraction. No API wiring. | System of record |
| n8n (outer infrastructure) | Future source acquisition / scheduling only (ADR-035). Local Compose `n8n` profile pins `n8nio/n8n:2.37.10`, publishes loopback-only HTTP 5678, requires `N8N_ENCRYPTION_KEY`, disables diagnostics/version/templates/personalization, and uses named volume `n8n-data`. n8n's internal SQLite/local metadata is not platform energy-data persistence. No workflows or API handoff yet. | Canonical facts, forecasts, bids, settlements, document retrieval, LangGraph/application orchestration |

PostgreSQL/TimescaleDB remains the system-of-record direction (ADR-004). Chunk 13 added typed `DatabaseSettings`, SQLAlchemy async engine/session factories, psycopg 3, Alembic, and a bootstrap migration for the TimescaleDB extension plus the `energy_trading` schema. Chunk 14 added the first canonical persistence slice: application-owned `ConsumptionRepositoryPort`, SQLAlchemy Core table `energy_trading.consumption_observations`, Alembic revision `0002_consumption`, a Timescale hypertable partitioned by `timestamp`, and unwired `PostgresConsumptionRepository`. Chunk 15 added an on-demand Compose `postgres` profile pinning `timescale/timescaledb:2.29.2-pg17` (PostgreSQL 17, TimescaleDB 2.29.2), localhost-only port publishing, a named volume, `pg_isready` health, host-side Alembic execution, and opt-in live migration/repository/concurrency tests. Persistence identity is `(consumer_id, timestamp)`. Exact retries are idempotent; a different canonical value at an existing identity is `ConflictError`. No engine is created on import or in `create_app()`, and ingestion adapters do not call the repository. Chunk 16 added application-owned `CachePort[TValue]` (async get/set/delete, mandatory positive TTL, miss/expiry returns `None`). Chunk 17 added concrete offline Redis infrastructure: `redis>=8,<9`, typed `RedisSettings`, `create_redis_client()` returning `redis.asyncio.Redis` without an eager network command, infrastructure-local `CacheCodec[TValue]`, and unwired `RedisCache[TValue]`. Serialization and Redis bytes stay in infrastructure. Backend keys are `energy-trading:cache:` plus SHA-256 of the normalized application key. Positive TTL converts to Redis `PX` milliseconds with sub-millisecond values rounded up to 1 ms. Redis and codec failures become sanitized `DependencyUnavailableError`. A future composition root owns `await client.aclose()`. Chunk 18 added an on-demand Compose `redis` profile pinning `redis:8.2.9-alpine`, loopback-only `REDIS_PORT` publishing, required `REDIS_PASSWORD`, disabled RDB/AOF, `redis-cli`/`REDISCLI_AUTH` health, and opt-in live `redis_integration` tests. There is still no `create_app()` cache wiring, Redis readiness endpoint, Redis-backed workflow checkpoint, or distributed lock. Application `WorkflowState` is an in-memory snapshot contract only. Application code stays vendor-neutral. TimescaleDB, Redis, and Qdrant Compose profiles are independent. Chunk 24 added an on-demand Compose `qdrant` profile pinning `qdrant/qdrant:v1.19.1`, loopback-only REST 6333, required `QDRANT_API_KEY`, disabled telemetry, named `qdrant-data`, and opt-in live `qdrant_integration` tests. Production Document Vector Index collection provisioning now occurs indirectly through the existing managed runtime. Production Regulatory collection readiness verification now occurs indirectly through the existing managed runtime as verify-existing/fail-closed, not create-if-missing. Regulatory collection automatic provisioning remains absent, and production distance selection remains unresolved. Chunk 25 added an on-demand Compose `n8n` profile pinning `n8nio/n8n:2.37.10`, loopback-only HTTP 5678, required `N8N_ENCRYPTION_KEY`, disabled diagnostics/version/templates/personalization, named `n8n-data`, and opt-in live `n8n_integration` readiness tests. n8n is not a platform store and is not wired into application/API/LangGraph. Canonical DLQ metadata can be written to a local filesystem directory by `FilesystemDeadLetterQueue` when an application caller invokes `DeadLetterQueuePort`; that adapter is not composed into the API or ingestion runtime yet.

## API boundary

FastAPI is the HTTP surface (`/api/v1`). The application factory `create_app` in `src/energy_trading/api/app.py` is the current composition root: it constructs a testable FastAPI app, registers versioned routers, and will later wire infrastructure and ML implementations into application ports. It must not contain business logic and must not initialize databases, caches, vector stores, ML models, agents, or LangGraph.

Implemented now: process/application health at `GET /api/v1/health`, standard error envelope, correlation middleware, and structured request logs. The health endpoint does not report infrastructure readiness. Remaining business endpoints are TBD (`API_CONTRACTS.md`). Routers translate HTTP ↔ canonical contracts and call application use cases. The API layer must not parse vendor CSV/Excel/PDF formats.

## Configuration and secrets

- Configuration through environment variables and typed settings (`pydantic-settings`). `AppSettings` remains process-health configuration (name, environment, API prefix, log level) and does not require database, Redis, Qdrant, OpenAI, or n8n credentials. `DatabaseSettings` is a separate object loaded only when PostgreSQL runtime or Alembic needs it. `RedisSettings` is a separate object loaded only when Redis cache infrastructure is constructed. `QdrantSettings` is a separate object loaded only when Qdrant client infrastructure is constructed. `OpenAISettings` is a separate object loaded only when OpenAI client infrastructure is constructed; it contains only `api_key: SecretStr` and no model selection. There is no `N8nSettings` object; Compose interpolates `N8N_ENCRYPTION_KEY` for the optional n8n service only. ML and remaining LLM settings remain reserved.
- No hardcoded business configuration in domain or agents.
- Secrets never in source control. `.env.example` is the committed template; `.env` is local-only.

## Error handling

Keep these four responsibilities separate:

| Concern | Owner | Role |
| --- | --- | --- |
| Domain diagnostics | `AdapterDiagnostic` / `DLQRecord` | Canonical ingestion diagnostics. Not HTTP exceptions. |
| Application errors | `ApplicationError` hierarchy | Transport-neutral use-case failure semantics. No HTTP status codes. |
| API error responses | API exception translator | HTTP status + standard envelope (`API_CONTRACTS.md`). |
| Operational logs | structured JSON logger | Internal observability. May include exception traces. Never returned to clients. |

Application errors currently implemented: `InvalidRequestError`, `ResourceNotFoundError`, `ConflictError`, `DependencyUnavailableError`. The API translator maps only those explicit subclasses. Bare `ApplicationError` and any unmapped subclass fail closed to a sanitized HTTP 500 (`internal_error`) so a missing mapping cannot be mistaken for a client error. Unexpected programming exceptions are not modeled as application errors; the API boundary also converts them to a sanitized HTTP 500.

Never silently swallow exceptions.

Ingestion (later): retry transient I/O; DLQ for unrecoverable normalization failures. Orchestration: a framework-neutral `FailurePolicyPort` exists for future retry/fallback *decisions*; application-owned `execute_parallel_ingestion_failure_action` executes terminal `FAIL` by delegating to `fail_parallel_ingestion`. Application-owned `ParallelIngestionFailureHandlingService` composes that decision then execution for an already-built context. `RETRY` / `FALLBACK` *execution* remains later work. Chunk 50 attributes failing Phase 2 agents at the executor boundary. Chunk 51 extracts those attributed leaves from a possibly nested exception group. Chunk 52 classifies one extracted leaf into a sanitized `ParallelIngestionFailureFact`. Chunk 53 classifies an already-extracted attributed-failure tuple by delegating to that one-leaf classifier. Chunk 54 defines the Phase-2-specific selection contract over that sanitized fact tuple without a concrete selector or winner semantics. Chunk 57 implements that contract structurally with `StrictSingleParallelIngestionFailureSelector` for the unambiguous one-fact case only; zero or multiple facts fail closed, and simultaneous multi-failure policy remains unresolved. Chunk 55 defines the Phase-2-specific read-only attempt-number source contract over workflow identity without increment/reset semantics on the port. Chunk 58 implements that contract structurally with `InitialParallelIngestionAttemptNumberSource` for the current no-retry runtime only; it returns exactly `1` and is not a tracker. Chunk 56 composes that selection port, attempt-number port, and the published context builder into `ParallelIngestionFailureContextResolutionService` without auto-wiring a selector, tracker, policy decision, or action execution. Chunk 59 composes extraction, tuple classification, and that resolution service into `ParallelIngestionFailureContextPreparationService` without invoking policy, executing an action, or wiring LangGraph. Chunk 60 implements `FailurePolicyPort` structurally with `InitialParallelIngestionFailurePolicy` for the current no-retry runtime only; it returns exactly `FailureAction.FAIL` and does not inspect context fields. Chunk 61 composes that prepared context path with existing handling through `ParallelIngestionFailureRuntimeHandlingService` without duplicating policy or action ownership. Concrete multi-failure selection policy, retry-capable attempt tracking, runtime graph invocation of that composition, and graph routing remain later work. None of that handling is graph-wired.

### Request failure flow

```text
HTTP Request
→ Correlation Middleware
→ API
→ Application
→ ApplicationError (if expected, mapped failure)
→ API Exception Translator
→ Standard Error Envelope

Unmapped ApplicationError
→ Internal structured diagnostic log
→ sanitized HTTP 500

Unexpected Exception
→ Internal structured exception log
→ sanitized HTTP 500
```

## Observability

- Structured JSON logging via the Python standard library (`logging` + `json`). Configured from `create_app`, not on import. No operational `print()`. Third-party telemetry (OpenTelemetry, Sentry, Prometheus, structlog) is deferred.
- Per-request correlation IDs use `contextvars.ContextVar`. Incoming `X-Correlation-ID` is reused when valid; otherwise a UUID is generated. The same ID is written to the response header, error envelope, and log records. The ID is also stored on ASGI request state so Starlette's outer unhandled-exception handler can recover it after the ContextVar scope ends.
- HTTP request completion is logged as `event=http_request_completed` with method, path, status code, duration, and correlation ID. Path only — no query string, body, Authorization header, cookies, or API keys.
- Adapter diagnostics (`AdapterDiagnostic`) remain first-class canonical records, not a substitute for HTTP errors or log lines.
- Metrics/tracing exporters are optional later; local RAM budget argues against heavy always-on stacks.

## Testing boundaries

See `TESTING_STRATEGY.md`. Default tests use fixtures, not live external APIs. Architecture tests lock domain and application import rules, the structured-ingestion ACL boundary, the infrastructure schema-mapping provider/file-I/O boundary, the Consumption CSV adapter provider boundary, the Consumption Excel adapter provider boundary, the Consumption unit/timezone normalization boundary, the Consumption time-series validation and gap-reporting boundary, the filesystem DLQ persistence boundary, the unstructured document extraction boundary, the PDF text-extraction adapter boundary, the document embedding boundary, the document vector indexing boundary, the document vector retrieval boundary, the PostgreSQL persistence foundation boundary, the Consumption repository boundary, the Compose TimescaleDB profile, the application cache-port boundary, the Redis cache infrastructure boundary, the Compose Redis profile, the Qdrant client-foundation boundary, the Qdrant document-vector adapter boundary, the Qdrant document collection readiness boundary, the Qdrant document collection creation boundary, the Qdrant document collection ensure boundary, the Compose Qdrant profile / live-integration boundary, the Compose n8n profile / live-readiness boundary, the application agent-execution-contract boundary, the application orchestration-state boundary, the LangGraph import-ownership boundary, the application failure-policy boundary, the Weather agent / weather-source-port boundary, the Hydro agent / hydro-source-port boundary, the Generation Availability agent / generation-source-port boundary, the News Intelligence agent / news-source-port boundary, the Market Monitoring agent / market-source-port boundary, the Regulatory Intelligence agent / regulatory-inference-port boundary, the document query-text embedding boundary, the document vector-search query-preparation boundary, the document vector index-entry preparation boundary, the document vector index execution boundary, the Regulatory Intelligence query-execution composition boundary, the Regulatory Intelligence runtime composition-root boundary, the parallel-ingestion plan, execution-port, and successful fan-in boundary, the concurrent parallel-ingestion executor boundary, the parallel-ingestion workflow-context boundary, the in-memory parallel-ingestion workflow-context adapter boundary, the parallel-ingestion workflow-step boundary, the parallel-ingestion success-transition boundary, the LangGraph Phase 2 success-transition wiring boundary, the parallel-ingestion terminal-failure-transition boundary, the parallel-ingestion failure-policy decision boundary, the parallel-ingestion failure-policy context-construction boundary, the parallel-ingestion terminal-FAIL action-execution boundary, the parallel-ingestion prepared failure-handling composition boundary, the parallel-ingestion agent-failure attribution boundary, the parallel-ingestion ExceptionGroup attributed-leaf extraction boundary, the parallel-ingestion sanitized failure-fact classification boundary, the parallel-ingestion tuple-level failure-fact classification boundary, and the parallel-ingestion failure-fact selection-contract boundary, the parallel-ingestion attempt-number source-contract boundary, and the parallel-ingestion failure-policy context-resolution boundary. Default tests do not require a running PostgreSQL/TimescaleDB, Redis, Qdrant, or n8n process. Live persistence tests are opt-in (`ENERGY_RUN_POSTGRES_INTEGRATION=1`) after `docker compose --profile postgres up -d timescaledb`. Live Redis cache tests are opt-in (`ENERGY_RUN_REDIS_INTEGRATION=1`) after `docker compose --profile redis up -d redis`. Live Qdrant vector tests are opt-in (`ENERGY_RUN_QDRANT_INTEGRATION=1`) after `docker compose --profile qdrant up -d qdrant`. Live n8n readiness tests are opt-in (`ENERGY_RUN_N8N_INTEGRATION=1`) after `docker compose --profile n8n up -d n8n`.

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

Docker Compose is the intended local/dev packaging for PostgreSQL/TimescaleDB, Redis, Qdrant, n8n, and later the API. Chunk 15 introduced the on-demand `postgres` profile (`timescaledb` service, image `timescale/timescaledb:2.29.2-pg17`, loopback bind, named volume). Chunk 18 introduced the on-demand `redis` profile (`redis` service, image `redis:8.2.9-alpine`, loopback bind, required password, no volume, RDB/AOF disabled). Chunk 24 introduced the on-demand `qdrant` profile (`qdrant` service, image `qdrant/qdrant:v1.19.1`, loopback REST 6333, required API key, telemetry disabled, named `qdrant-data`). Chunk 25 introduced the on-demand `n8n` profile (`n8n` service, image `n8nio/n8n:2.37.10`, loopback HTTP 5678, required encryption key, telemetry/template/version/personalization disabled, named `n8n-data`). The four profiles are independent. The FastAPI application is not containerized. Remaining Compose services remain later chunks. Production topology, GPU passthrough, and WSL2 memory interaction with Docker Desktop are open deployment questions — see `DECISIONS.md`. Prefer profiles so unused services stay down. The local Qdrant HTTP+API-key profile is not the production security architecture; production requires appropriately secured networking/TLS. The local n8n HTTP profile is likewise development/test infrastructure, not production n8n security.
