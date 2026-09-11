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

- **Status:** Accepted (conceptual selection; first executable skeleton is ADR-038)
- **Context:** Thirteen agents and five business phases need explicit routing, parallel Phase 2 join, retries, fallback, and workflow status.
- **Decision:** LangGraph lives in the application layer. Nodes are thin. The Chief Orchestrator Agent owns graph state and policy. Conceptual flow: contract → parallel ingestion → ML forecasting → portfolio/risk → trading strategy → market-clearing input/result → settlement.
- **Consequences:** LangGraph versioning and debugging become skills for the team. Orchestration could later move to another graph/workflow library without changing domain contracts. Graph must not contain ML training or DAM arithmetic. Chunk 28 / ADR-038 implements only `START → workflow_entry → END`; five-phase routing remains future work.

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

---

## ADR-013 — Transport-neutral errors, API envelopes, and stdlib observability

- **Status:** Accepted
- **Context:** Chunk 3 needed a failure and observability foundation before adapters exist. HTTP status codes must not leak into application or domain types. Client responses must stay free of secrets and stack traces, while operators still need a correlation key into structured logs. Third-party logging/telemetry stacks would add RAM, lock-in, and dependencies the project does not yet need.
- **Decision:**
  - Application failures are `ApplicationError` subclasses with stable machine-readable codes and safe messages. They carry no HTTP status, FastAPI/Starlette types, raw payloads, or stack traces as contract data.
  - HTTP mapping and the public error envelope live only in the API layer. Unexpected exceptions become a generic HTTP 500 (`internal_error`); internals are logged, never returned.
  - Each HTTP request binds a correlation ID in a `contextvars.ContextVar` via pure ASGI middleware. Valid `X-Correlation-ID` values are reused; invalid values are replaced rather than rejecting the request. The ID is also stored on ASGI scope state because Starlette handles `Exception` in outer `ServerErrorMiddleware`, after the ContextVar scope has exited.
  - Structured JSON logs use the Python standard library (`logging` + `json`), configured from the composition root. Request completion logs record method, path, status, duration, and correlation ID. Request bodies, credentials, Authorization headers, cookies, and query strings are not logged.
  - `AdapterDiagnostic` remains a domain ingestion diagnostic and is not reused as the HTTP/application exception format.
  - OpenTelemetry, Sentry, Prometheus, structlog, and loguru are deferred.
- **Consequences:** Operators correlate a sanitized client error with an internal JSON log using the same ID, without a vendor observability stack. Application code stays transport-portable. Stdlib JSON logs are less feature-rich than structlog/OTel; that tradeoff is accepted until a later telemetry chunk. ContextVar isolation depends on not using `BaseHTTPMiddleware`, which can break context propagation.

---

## ADR-014 — Structured ingestion application boundary

- **Status:** Accepted
- **Context:** Phase 1 must stop raw vendor payloads before agents, ML, or use cases see them. Adapters will later read CSV, Excel, and APIs, but the application-facing signature has to be stable now. Record-level normalization failures must not crash an entire DAM ingestion batch, and failed raw bytes must not leak into canonical envelopes.
- **Decision:**
  - The application owns `StructuredIngestionPort[TRecord]` (`typing.Protocol`) and the immutable generic envelope `StructuredIngestionResult[TRecord]`. Infrastructure adapters will implement the protocol structurally; there is no mandatory infrastructure base class.
  - Application-facing signatures contain canonical domain models only, plus `AdapterDiagnostic` and `DLQRecord`. `ingest` accepts no raw payload (`dict`, `bytes`, DataFrame, vendor JSON, file path, or URL).
  - Partial success is first-class: a batch may return canonical records together with diagnostics and DLQ metadata. Complete normalization failure and a valid empty source are also valid results. The port must not raise merely because DLQ entries are present or because the source contained no rows.
  - Raw failed payload stays outside the application and is referenced only through `DLQRecord.payload_reference`.
  - DLQ persistence is abstracted behind `DeadLetterQueuePort`. Application/orchestration may later enqueue `dlq_records` from a result; infrastructure will persist them in a later chunk.
  - Source-specific adapter implementations (CSV, Excel, REST, schema mapping, unit/timezone cleaning) are deferred.
- **Consequences:** Call sites can be written and tested against fakes before any vendor parser exists. Adapters must finish acquisition and normalization before crossing the port. An extra mapping from infrastructure result → application envelope is avoided because the adapter *is* the port implementation. The tradeoff is that configuration (paths, credentials, URLs) cannot appear on the port and must be injected into concrete adapters later. Runtime DLQ transport remains undecided.

---

## ADR-015 — Deterministic-first schema field resolution

- **Status:** Accepted
- **Context:** Structured adapters will later read CSV, Excel, and APIs whose headers are renamed, inconsistently cased, punctuated, or written in Unicode (including Armenian). Chunk 4 already forbids raw schemas on the application ingestion boundary. Field meaning must be interpreted before validation and unit normalization, without guessing, without new fuzzy/LLM dependencies, and without leaking vendor headers into application or domain.
- **Decision:**
  - Schema field interpretation is an infrastructure/ACL responsibility. The engine lives under `energy_trading.infrastructure.adapters.structured.schema_mapping`. No application-layer schema-mapping port is added. Chunk 4's `StructuredIngestionPort` / `StructuredIngestionResult` / `DeadLetterQueuePort` signatures are unchanged.
  - Callers supply `CanonicalFieldSpec` values. There is no production global vendor alias catalog. Canonical names are exact matches even when not repeated as aliases.
  - The implemented path is deterministic and synchronous: Unicode NFKC normalization and `casefold()`, exact alias matching, then `difflib.SequenceMatcher` fuzzy matching. Default `fuzzy_threshold = 0.85` and `ambiguity_margin = 0.05` are resolver constructor parameters, not environment/business settings.
  - Ambiguous and low-confidence matches fail closed: `canonical_field` stays `None`; the resolver does not pick the first candidate. Schema-level missing required fields and destination collisions are reported, not silently overwritten.
  - The resolver performs no unit conversion, record parsing, file I/O, DLQ emission, or canonical-model construction. Aliases such as `Consumption_MW` and `Consumption_kW` may share a destination field; values are not converted here.
  - No new dependency is required. RapidFuzz, pandas, OpenAI, LangChain, LangGraph, embeddings, and transliteration libraries are out of scope.
  - A future optional infrastructure-local semantic/LLM fallback may run after the deterministic path. It must not be required for resolution to work, and any abstraction that carries raw external field names must stay inside infrastructure.
- **Consequences:** CSV/Excel/REST adapters can later call this engine before validating row values. Mapping tables remain adapter configuration. Semantic/LLM mapping, if ever added, cannot push raw headers across the application boundary. Ambiguous source schemas will surface as schema diagnostics rather than invented canonical fields.

---

## ADR-016 — First concrete structured adapter: Consumption CSV

- **Status:** Accepted
- **Context:** Chunk 4 defined the application ingestion port. Chunk 5 provided deterministic header resolution. The platform still needed one real source adapter that acquires a file, maps headers, validates rows into `ConsumptionRecord`, and preserves ACL privacy. Pandas would add a heavy dependency for a narrow CSV job. Blocking the event loop on filesystem I/O would violate the async port. Guessing kW→MW or attaching `Asia/Yerevan` would smuggle unverified semantics into canonical data.
- **Decision:**
  - `ConsumptionCsvAdapter` lives in infrastructure and structurally implements the existing async `StructuredIngestionPort[ConsumptionRecord]`. It does not inherit a base adapter class and does not change the port.
  - Path, `source_name`, optional Consumption field specs, and an optional UTC clock are constructor-injected. `ingest()` accepts no path, file, or raw payload.
  - The Python standard library `csv` reader is sufficient. pandas, Polars, Excel, and HTTP clients are out of scope.
  - Synchronous filesystem parsing runs behind `asyncio.to_thread` so the async port does not block the event loop.
  - Files are opened as UTF-8 with BOM tolerance (`utf-8-sig`, `newline=""`). Encoding detection is not implemented.
  - Chunk 5 `DeterministicFieldResolver` is reused. The default profile requires `consumer_id`, `timestamp`, and `value_mw`, with an exact MW-safe alias `Consumption_MW`. `Consumption_kW`, `Load`, and `Energy Usage` are not default aliases.
  - Ambiguous headers, missing required canonical fields, and destination collisions fail closed: no data rows are interpreted; diagnostics plus one schema-level `DLQRecord` are returned. Unresolved extra columns emit a warning and are ignored. Fuzzy MW-safe mappings are accepted with a warning on the canonical field name.
  - Fuzzy mapping to `value_mw` is accepted only when the source header still explicitly and safely identifies MW (after Chunk 5 normalization, the final token is exactly `mw`). Unit-ambiguous or energy-like headers fail closed. No numeric unit conversion is performed.
  - Row validation uses `ConsumptionRecord.model_validate` on an infrastructure-local three-key dict. Pydantic `ValidationError` is isolated per row. Broad `Exception` is not caught. CSV values must already be MW. Source timestamps must already carry timezone information; naive timestamps fail the row. Bare numeric timestamp strings are not treated as Unix epoch values; they fail closed at the adapter before canonical validation. Canonical UTC normalization remains the domain contract.
  - File acquisition `OSError` becomes `DependencyUnavailableError` with a generic message. Malformed CSV syntax and invalid UTF-8 are normalization failures, not dependency unavailability.
  - Raw headers, rows, cell values, file paths, and Pydantic `input` values must not appear on `StructuredIngestionResult`, `AdapterDiagnostic`, or `DLQRecord`. DLQ metadata uses opaque `csv://<source_name>/...` references. No DLQ persistence is implemented.
- **Consequences:** Application call sites can ingest Consumption CSV through the existing port. Other domains, Excel, REST, unit conversion, timezone inference, and time-series cleaning remain later chunks. A later unit-normalization stage can distinguish `Consumption_kW` because the raw header never becomes canonical MW here.

---

## ADR-017 — Consumption XLSX ingestion with openpyxl

- **Status:** Accepted
- **Context:** Chunk 6 delivered Consumption CSV. The same canonical `ConsumptionRecord` destination must also be reachable from modern Excel workbooks without pandas, Excel application automation, unit conversion, or timezone inference. Excel typed datetime cells are typically naive, so attaching `Asia/Yerevan` or UTC at this boundary would smuggle unverified semantics into canonical data. Formula calculation would require a second engine and is out of scope.
- **Decision:**
  - `ConsumptionExcelAdapter` lives in infrastructure and structurally implements the existing async `StructuredIngestionPort[ConsumptionRecord]`. It does not inherit a base adapter class and does not change the port.
  - Only modern `.xlsx` files are in scope. Legacy `.xls`, pandas, Polars, xlrd, pyxlsb, LibreOffice, and Excel COM automation are out of scope.
  - openpyxl is the reader. Workbooks load with `read_only=True` and `data_only=True`. Cached formula results may be consumed; formulas are not calculated.
  - Path, `source_name`, optional `sheet_name`, optional Consumption field specs, and an optional UTC clock are constructor-injected. `ingest()` accepts no workbook, path, sheet, or raw payload.
  - Explicit `sheet_name` selects that worksheet or fails closed as a source/schema normalization failure. `None` uses the workbook active worksheet. Multi-sheet aggregation is deferred. Requested and available worksheet names do not appear on outward diagnostics.
  - Synchronous openpyxl/filesystem work runs behind `asyncio.to_thread`. The workbook is closed in a `finally` block.
  - CSV and Excel share the infrastructure-local Consumption mapping policy (`DEFAULT_CONSUMPTION_FIELD_SPECS` and the standalone-token `mw` fuzzy-safety predicate). The Chunk 5 resolver is unchanged and still does not understand energy units.
  - Excel-native naive datetimes fail canonical validation. Timezone-aware ISO strings may normalize to UTC. No timezone is attached. Values reaching `value_mw` must already be MW; no conversion is performed.
  - Excel source values are type-narrowed before canonical validation so ambiguous numeric timestamps and boolean measurements are not silently coerced. Timestamp cells must be `str` or `datetime`; `value_mw` rejects `bool`. Numeric Excel serials and Unix epoch numbers are not interpreted. This is not timezone normalization.
  - Malformed workbook ZIP/XML/openpyxl format errors are source normalization failures (`excel_workbook_invalid` plus source-level DLQ metadata). Missing or unreadable files (`OSError`) become `DependencyUnavailableError` with a generic message. Missing configured worksheets fail as schema/source diagnostics, not as a silent active-sheet fallback.
  - Raw workbook paths, worksheet names, header cells, cell values, formula text, and Pydantic `input` values must not appear on `StructuredIngestionResult`, `AdapterDiagnostic`, or `DLQRecord`. DLQ metadata uses opaque `excel://<source_name>/...` references. No DLQ persistence is implemented.
- **Consequences:** Application call sites can ingest Consumption `.xlsx` through the existing port. REST adapters, other domain Excel readers, timezone inference, duplicate/gap repair, and formula engines remain later chunks. Chunk 8 added explicit opt-in kW and IANA timezone normalization on the same adapters; default constructor behavior remains unaware MW-only.

---

## ADR-018 — Explicit deterministic unit and timezone normalization

- **Status:** Accepted
- **Context:** Chunks 6 and 7 ingest Consumption CSV/XLSX into canonical `ConsumptionRecord` without converting units or attaching a timezone. That fail-closed default is correct, but operators still need a deterministic way to accept kW sources and naive local clocks when those semantics are known. Inferring MW vs kW from magnitude, assuming `Asia/Yerevan`, using the machine timezone, or converting energy (MWh/kWh) into power would smuggle unverified market rules into canonical data. DST fall-back and spring-forward local clocks are also ambiguous without an explicit policy.
- **Decision:**
  - Normalization is infrastructure ACL work. A narrow package (`structured/normalization/`) owns power-unit conversion and IANA timezone localization. It does not import application, API, ML, pandas, openpyxl, or domain models. Adapters feed normalized values into existing `ConsumptionRecord` validation.
  - Canonical Consumption power remains MW. Infrastructure `PowerUnit` supports only `MW` and `KW`. kW→MW is deterministic (`1000 kW = 1 MW`) using `Decimal` internally. Energy units (MWh, kWh, Wh) are not power and are never converted. No interval length is assumed; MW is not equated with MWh.
  - `ConsumptionCsvAdapter` and `ConsumptionExcelAdapter` accept `source_power_unit: PowerUnit = PowerUnit.MW` and `source_timezone: str | None = None`. These stay on concrete adapters. `StructuredIngestionPort`, `StructuredIngestionResult`, domain models, `AppSettings`, and the API are unchanged. `ingest()` still takes no configuration arguments.
  - Default constructor configuration preserves Chunk 6/7 behavior: MW in, MW out; `Consumption_kW` fails schema; naive timestamps fail. Conversion and localization occur only when explicitly configured.
  - Default field profiles follow the configured power unit (`Consumption_MW` vs `Consumption_kW`). Header/config mismatches (for example `PowerUnit.KW` with `value_mw`) fail closed. Energy-like headers fail regardless of `PowerUnit`. Fuzzy mapping still requires the last standalone token to be the expected power unit. The Chunk 5 `DeterministicFieldResolver` is not taught electrical-unit semantics.
  - Timezones use stdlib `zoneinfo.ZoneInfo` plus the `tzdata` package so Windows and WSL/Linux share an IANA database. No timezone is inferred or defaulted, including no default `Asia/Yerevan`. Invalid IANA names fail fast as `NormalizationConfigurationError` at construction.
  - Aware source timestamps retain their represented instant and are converted to UTC; a configured fallback zone must not overwrite them. Naive timestamps require an explicit source timezone. Bare numeric timestamps, Unix epoch strings, Excel serial dates, and date-only values remain rejected.
  - DST-ambiguous (fold 0 vs 1 differ) and nonexistent (spring-forward skipped) naive local clocks fail closed as `SourceValueNormalizationError`. Chunk 8 does not invent a fold/repair policy.
  - Configuration failures (unknown zone, unsupported unit) fail at construction. Source-value failures stay row-isolated (diagnostic + DLQ metadata). File `OSError` remains `DependencyUnavailableError`. Diagnostics still must not leak raw values, headers, paths, or exception reprs.
  - Duplicate timestamps, missing intervals, interpolation, resampling, Unix/Excel serial parsing, automatic unit/timezone detection, and DST repair are deferred.
- **Consequences:** Operators can opt into kW and IANA localization without changing canonical contracts. Default paths remain fail-closed. Duplicate/gap/repair policy remains a later chunk. Units and timezones for other domains are still unimplemented. Chunk 9 (ADR-019) later implemented fail-closed duplicate detection and optional interval-grid alignment; missing-interval detection remains deferred.

---

## ADR-019 — Fail-closed duplicate timestamps and explicit interval-grid validation

- **Status:** Accepted
- **Context:** Chunk 8 normalized Consumption units and timezones into canonical `ConsumptionRecord` values, but a batch could still contain duplicate `(consumer_id, timestamp)` observations or timestamps that do not lie on a known reporting cadence. Silently keeping the first or last row, averaging MW, inferring an hourly DAM product, or reporting missing hours would smuggle unverified market policy into the ACL. Application ports must not grow source-cadence configuration.
- **Decision:**
  - Structural time-series validation stays in the infrastructure ACL (`structured/time_series/`). `StructuredIngestionPort`, `StructuredIngestionResult`, domain models, `AppSettings`, and the API are unchanged. `ingest()` still takes no configuration arguments.
  - Duplicate identity is `(consumer_id, canonical UTC timestamp)`. Source offsets that represent the same instant collide after UTC normalization. Different consumers at the same instant are not duplicates.
  - Every member of a duplicate group is rejected. There is no first-wins, last-wins, highest-value, average, or sum policy. Exact duplicate MW values and conflicting MW values are treated the same: all members fail closed with `consumption_duplicate_timestamp`.
  - Interval alignment is opt-in. Adapters accept `interval_grid: IntervalGrid | None = None`. `None` (the default) still detects duplicates but does not impose a cadence. An `IntervalGrid` requires a positive `timedelta` and a timezone-aware anchor; the anchor is normalized to UTC. Naive anchors and non-positive intervals fail at construction as `NormalizationConfigurationError`.
  - Alignment uses exact integer-microsecond arithmetic: `(timestamp - anchor_utc)` converted to microseconds, modulo interval microseconds equals zero. Pre-anchor timestamps are included. Floating-point seconds are not used.
  - Off-grid rows fail individually (`consumption_interval_misaligned`) without discarding unrelated valid rows. Duplicate classification precedes interval classification; one structural reason per rejected candidate is sufficient.
  - Output preserves source order after invalid rows are removed. Out-of-order aligned timestamps are accepted and are not sorted. A two-hour gap on an hourly grid is not a Chunk 9 failure.
  - No Armenian DAM interval is hardcoded. No missing-interval detection, interpolation, resampling, or chronological-ordering policy is implemented. Duplicate detection is per `ingest()` batch only; cross-ingestion and persistence uniqueness are deferred.
  - CSV and Excel adapters collect infrastructure-local `ConsumptionRecordCandidate` values (canonical record + source position), run the synchronous validator, and translate findings into adapter-specific row DLQ URIs. The validator does not know CSV/Excel URI schemes.
- **Consequences:** Operators can reject duplicate Consumption observations and optionally enforce a known reporting lattice without changing canonical contracts. Chunk 10 (ADR-020) later added internal compact gap reporting; leading/trailing coverage windows and repair remain deferred. Other domains still have no time-series cleaner.

---

## ADR-020 — Internal gap detection without automatic repair

- **Status:** Accepted
- **Context:** Chunk 9 rejected duplicate and off-grid Consumption observations but did not describe incompleteness between surviving aligned timestamps. Inferring a DAM delivery window, filling missing hours, or fabricating DLQ rows for timestamps that never existed in the source would smuggle unverified market policy and false provenance into the ACL.
- **Decision:**
  - Gap detection remains an infrastructure ACL responsibility inside `structured/time_series/`. Domain contracts, application ports, `AppSettings`, and the API are unchanged.
  - Detection requires an explicit `IntervalGrid`. `interval_grid=None` still means no cadence and no gap diagnostics. Cadence is never inferred from adjacent records.
  - Detection runs after duplicate groups and off-grid rows are removed. Rejected source rows keep their existing diagnostics and DLQ metadata. The resulting canonical series may then contain an internal gap.
  - Evaluation is independent per `consumer_id`. Timelines are not merged across consumers.
  - Only internal observed-span gaps are detected: between each consumer's earliest and latest surviving timestamps. Leading and trailing coverage cannot be inferred without a future explicit delivery-window contract.
  - Contiguous missing slots are one compact `ConsumptionGap` (`missing_count`, first/last missing timestamp). Missing timestamps are not materialized one-by-one. Gaps separated by valid observations stay separate. Ordering is `consumer_id` then `first_missing_timestamp`.
  - Valid observed records remain in `StructuredIngestionResult.records` in source order. Gap detection does not reject, sort, interpolate, fill, resample, or synthesize `ConsumptionRecord` values.
  - A missing interval has no source row, so adapters emit only a sanitized `AdapterDiagnostic` (`consumption_missing_interval_gap`, severity ERROR, `field_name="timestamp"`, count-only message). No fabricated DLQ URI is created.
  - No Armenian DAM interval is hardcoded. Cross-batch completeness and persistence of gap objects are deferred.
- **Consequences:** Operators can see that an explicitly configured cadence is incomplete inside the observed batch without losing valid observations or inventing source provenance. Delivery-window completeness, gap repair, and other domains remain later work.

---

## ADR-021 — Filesystem-backed DLQ metadata persistence boundary

- **Status:** Accepted
- **Context:** Chunks 4–10 emit canonical `DLQRecord` metadata on `StructuredIngestionResult`, but there was no persistence implementation behind `DeadLetterQueuePort`. Introducing PostgreSQL/TimescaleDB, Redis, a broker, or replay in this slice would expand into Phase 2 infrastructure. Adapters also must not persist DLQ records themselves: that would couple acquisition/normalization to runtime persistence policy. `EntityId` is an opaque string and is not a safe filesystem path component.
- **Decision:**
  - Keep the existing single-record application port: `async enqueue(record: DLQRecord) -> None`. Do not add a batch method, path argument, raw-payload argument, query API, or persistence DTO.
  - Retry idempotency uses the existing canonical `record_id`. Enqueueing an identical canonical record succeeds without creating a second artifact. The same `record_id` with different canonical metadata fails closed as `ConflictError` and does not overwrite the stored record.
  - `FilesystemDeadLetterQueue` is an interim local/development infrastructure adapter. It stores canonical `DLQRecord` metadata only. `payload_reference` remains opaque and is never dereferenced. Raw failed payloads are not stored and are not replayed.
  - Storage is one UTF-8 JSON file per record. The filename is a SHA-256 digest of the UTF-8 `record_id`, not the raw identifier. Exclusive file creation is used so a concurrent writer cannot silently overwrite an existing file. Incomplete newly-created files are removed on a best-effort basis.
  - Blocking filesystem I/O is offloaded from the async `enqueue()` boundary with `asyncio.to_thread`. Expected filesystem availability/integrity failures become sanitized `DependencyUnavailableError`. Messages must not include paths, OS error text, or persisted contents.
  - Each `enqueue()` is independent. No cross-record batch atomicity, distributed locking, SQLite, PostgreSQL, Redis, broker, Docker, API endpoint, or FastAPI composition wiring is introduced.
  - Future application/orchestration owns iteration over `StructuredIngestionResult.dlq_records`. This chunk does not add that use case.
  - This filesystem adapter does not supersede ADR-004. PostgreSQL/TimescaleDB remains the planned system of record for canonical DLQ metadata. ADR-023 later added the first PostgreSQL infrastructure foundation without a DLQ table or PostgreSQL DLQ adapter.
- **Consequences:** Local/dev callers can persist canonical DLQ metadata without a database. At-least-once retries of the same record are safe. Conflicting same-ID writes fail closed. Replay, listing, payload-reference resolution, and production durability remain later chunks. Ingestion CSV/Excel adapters continue to return DLQ metadata without persisting it.

---

## ADR-022 — Unstructured document extraction application boundary

- **Status:** Accepted
- **Context:** Phase 1 must stop PDF/document bytes, OCR-provider schemas, and parser objects before application orchestration, embedding, or regulatory interpretation can see them. Introducing a concrete PDF/OCR adapter, embeddings, Qdrant, or `RegulatoryConstraint` derivation in this slice would collapse later stages into one chunk.
- **Decision:**
  - The application owns `DocumentExtractionPort`, the immutable `ExtractedDocumentChunk` DTO, and the immutable `DocumentExtractionResult` envelope. Infrastructure implementations will satisfy the protocol structurally later; there is no infrastructure base class in this chunk.
  - `async extract() -> DocumentExtractionResult` accepts no raw document input. File paths, URLs, tokens, OCR credentials, and parser selection belong to future concrete adapter constructors.
  - Normalized application output is extracted text plus minimal generic provenance (`document_id`, `chunk_id`, `ordinal`, optional `page_number`). No embeddings, vectors, token IDs, OCR confidence, bounding boxes, paths, URLs, or arbitrary metadata dictionaries.
  - The result envelope reuses canonical `AdapterDiagnostic` and `DLQRecord`. Raw failed bytes remain behind opaque `payload_reference`. Chunk 11's filesystem DLQ adapter is unchanged and is not wired here.
  - Extracted text is not a `RegulatoryConstraint`. Regulatory interpretation, effective dates, numeric limits, currency, and Armenian DAM rules are out of scope.
  - Embedding/indexing, vector-store ports, Qdrant, RAG/retrieval, LLM extraction, and concrete PDF/OCR/HTML/DOCX adapters are deferred. No parser/OCR/embedding dependency is introduced.
- **Consequences:** Application call sites can be written against a fake extractor before any document parser exists. Future adapters must finish acquisition and normalization before crossing the port. Regulatory Intelligence remains a later interpretation stage, not a PDF-to-constraint shortcut.

---

## ADR-023 — Async PostgreSQL/TimescaleDB persistence foundation

- **Status:** Accepted
- **Context:** ADR-004 selected PostgreSQL/TimescaleDB as the system of record for relational and time-series canonical data. Chunk 13 needed a production-style but lightweight persistence foundation before any canonical repository, business table, or FastAPI database wiring exists. A running database service, Docker Compose, Redis, and Qdrant remain out of scope. Process health (`create_app()`, `GET /api/v1/health`) must keep working without database environment variables.
- **Decision:**
  - ADR-004 is not superseded. This ADR implements its first infrastructure foundation.
  - Runtime persistence uses SQLAlchemy 2's async API (`AsyncEngine`, `AsyncSession`, `async_sessionmaker`) with the psycopg 3 driver (`postgresql+psycopg`). The `sqlalchemy[asyncio]` extra supplies greenlet. Alembic owns migrations. asyncpg, psycopg2, SQLModel, and other ORMs are not used.
  - `DatabaseSettings` is a separate typed settings object (`ENERGY_DB_*`) with `SecretStr` password handling. It is not required by `AppSettings` or `create_app()`. Host, database, username, and password have no implicit defaults; pool/port/timeout values have safe non-secret defaults.
  - Infrastructure exposes factories only: `build_postgres_url`, `create_postgres_engine`, `create_session_factory`. There is no global engine, no connection on import or construction, and no FastAPI lifespan/session injection yet.
  - SQLAlchemy URL objects are built with `URL.create(...)`. Callers must not log password-bearing DSN strings.
  - The first Alembic revision bootstraps `CREATE EXTENSION IF NOT EXISTS timescaledb` and `CREATE SCHEMA IF NOT EXISTS energy_trading`. It creates no canonical business tables, DLQ tables, or ORM models (`target_metadata = None`).
  - Downgrade drops the dedicated `energy_trading` schema without `CASCADE` if the schema is empty enough for PostgreSQL to allow it. The TimescaleDB extension is never dropped automatically; it may be shared by other schemas or workloads.
  - Application repository ports, concrete repositories, Unit of Work, and PostgreSQL-backed DLQ are deferred. Chunk 11's `FilesystemDeadLetterQueue` remains the implemented DLQ adapter.
  - Docker Compose remains deferred (ADR-009). Default tests require no PostgreSQL/TimescaleDB process. Live migration execution belongs to a later Compose/integration slice.
- **Consequences:** Later repository chunks can add tables and ports against a known driver, migration tool, and settings contract. Operators still should not start TimescaleDB until a chunk needs a running service. Alembic `upgrade` against an arbitrary developer database is not part of default validation.

---

## ADR-024 — Canonical Consumption PostgreSQL persistence identity

- **Status:** Accepted
- **Context:** Chunk 13 established SQLAlchemy async factories, psycopg 3, and an Alembic bootstrap. The first canonical aggregate that must be persisted is `ConsumptionRecord`. A generic repository, other domain tables, FastAPI wiring, and a running TimescaleDB service would expand this slice past a reviewable write path. Consumption adapters already reject duplicates inside one `ingest()` batch; they do not query PostgreSQL.
- **Decision:**
  - The first concrete canonical database aggregate is Consumption. Application owns `ConsumptionRepositoryPort`. The initial contract is intentionally write-focused: `async save_many(records: tuple[ConsumptionRecord, ...]) -> None`.
  - Infrastructure maps the contract with SQLAlchemy Core, not ORM declarative models and not a domain shadow schema. Table `energy_trading.consumption_observations` stores only canonical fields: `consumer_id`, `timestamp`, `value_mw`.
  - Persistence identity is `(consumer_id, timestamp)`. The composite primary key includes the Timescale partition key `timestamp`.
  - Canonical `NonNegativeMW` is a finite Python `float`, so PostgreSQL `DOUBLE PRECISION` is used. A CHECK constraint rejects negative MW and non-finite IEEE values. The domain type is not changed to accommodate storage.
  - One `save_many()` call is one transaction. Identical canonical retries succeed as no-ops. The same identity with a different canonical value is `ConflictError`. There is no last-write-wins path.
  - Inserts use PostgreSQL `ON CONFLICT (consumer_id, timestamp) DO NOTHING`, never `DO UPDATE`. After the conflict-safe insert, the repository reads persisted rows and reconstructs `ConsumptionRecord` as the semantic authority. Exact match succeeds; a differing stored value raises `ConflictError` and rolls back the call; unreadable/corrupt storage is a sanitized `DependencyUnavailableError`.
  - Timescale conversion uses `create_hypertable(..., 'timestamp', if_not_exists => TRUE)` without an explicit chunk interval, hash/space partitioning, compression, or continuous aggregates. Chunk 15 pins a compatible runtime (`timescale/timescaledb:2.29.2-pg17`) and exercises this migration live.
  - Adapter cross-batch duplicate detection is still not implemented. CSV/Excel adapters are not wired to this port. `create_app()` is unchanged. Filesystem DLQ remains the only DLQ adapter.
- **Consequences:** Callers persist canonical Consumption observations with deterministic identity and conflict semantics. Chunk 15 runs those semantics against a pinned local TimescaleDB. Historical-range reads, other aggregates, and orchestration wiring remain later chunks.

---

## ADR-025 — Pinned local TimescaleDB service profile and live persistence validation

- **Status:** Accepted
- **Context:** Chunks 13–14 delivered SQLAlchemy factories, Alembic 0001/0002, and `PostgresConsumptionRepository` without a running database. Live migration execution, hypertable proof, and real transaction/concurrency semantics require a pinned local TimescaleDB. Redis, Qdrant, and an API container would expand this slice past infrastructure validation. WSL2 RAM is limited, so the database must not be an always-on dependency.
- **Decision:**
  - Local TimescaleDB uses the exact image `timescale/timescaledb:2.29.2-pg17` (PostgreSQL 17, TimescaleDB 2.29.2). The pin is a release tag, not `latest`, `latest-pg17`, a HA image, or a digest.
  - Compose defines one service, `timescaledb`, gated on profile `postgres`. It is started with `docker compose --profile postgres up -d timescaledb` and is not an implicit always-on dependency.
  - The published port is loopback-only (`127.0.0.1` plus `ENERGY_DB_PORT`). Password authentication remains required. `POSTGRES_HOST_AUTH_METHOD=trust` is not used. Credentials come from existing `ENERGY_DB_*` interpolation; Compose does not hardcode a password.
  - PostgreSQL data uses the Compose named volume `timescale-data`. It is not bind-mounted into the Git tree.
  - Health uses `pg_isready` against the configured user and database, without a password in the healthcheck.
  - Host `uv run alembic` applies migrations. On Windows, `alembic/env.py` selects `WindowsSelectorEventLoopPolicy` because psycopg async cannot use ProactorEventLoop. `create_app()` is unchanged.
  - Live tests live under `tests/integration/persistence/postgres/`, use marker `postgres_integration`, and require `ENERGY_RUN_POSTGRES_INTEGRATION=1`. They cover Alembic upgrade/downgrade/upgrade, PostgreSQL 17 and TimescaleDB 2.29.2 runtime versions, hypertable registration, repository insert, exact idempotent retry, conflict preservation, mixed-batch rollback, concurrent exact retry, concurrent conflicting writers, CHECK defense for negative MW, and timezone-aware instant round-trip. Default `uv run pytest` stays service-independent. testcontainers and the Docker SDK are not used.
  - The database is not intended to remain running under the WSL RAM budget. Redis and Qdrant remain deferred.
- **Consequences:** Developers can prove Consumption persistence against a compatible TimescaleDB without starting unrelated services. Other canonical repositories, API readiness, and remaining Compose profiles remain later chunks. This ADR does not supersede ADR-004, ADR-023, or ADR-024.

---

## ADR-026 — Application-owned cache boundary precedes Redis implementation

- **Status:** Accepted
- **Context:** ADR-006 selected Redis as the local/dev technology for ephemeral cache/state infrastructure. Chunk 16 needed a reviewable application contract before any Redis package, client, settings class, Compose service, or `create_app()` wiring. A broad ephemeral-state port, CAS/versioning, and distributed locks would mix distinct semantics into one abstraction.
- **Decision:**
  - Application owns `CachePort[TValue]`, a generic `typing.Protocol`. Infrastructure may later implement it structurally. Implementations are not required to inherit from an application or infrastructure base class.
  - The public async operations are `get(key) -> TValue | None`, `set(key, value, *, ttl: timedelta) -> None`, and `delete(key) -> None`.
  - `key` is an opaque application identifier. After surrounding whitespace is ignored it must be non-empty. Redis key syntax, prefixes, hashes, database numbers, cluster slots, and hashing algorithms are not part of the contract.
  - `TValue` is a static generic. The application layer does not serialize. Bytes, JSON dictionaries, mappings, `Any`, and Redis response types are forbidden on the port.
  - Every `set` requires a `timedelta` TTL strictly greater than zero. There is no non-expiring cache API. Cache loss or expiry is acceptable. PostgreSQL/TimescaleDB remains the system of record (ADR-004).
  - A cache miss or expired entry returns `None`; that is not an exception. `set` may replace cached data for the same key and reset TTL; that overwrite is not compare-and-set for authoritative orchestration state. `delete` of a missing/expired key is a successful no-op.
  - Invalid caller input (blank key or non-positive TTL) is `InvalidRequestError` for conforming implementations. Expected backend unavailability is `DependencyUnavailableError`. No Redis-specific application errors are added.
  - This port is ordinary cache behavior only. Generic workflow-state/CAS and distributed-lock/lease contracts are deliberately omitted and will be defined separately if Phase 3 requirements demonstrate a need.
  - Chunk 16 introduces no Redis Python dependency, Redis settings, Redis DSN, Redis Compose service, serializer, health check, use case, agent, or API composition wiring. ADR-006 remains Accepted and is not superseded: Redis is still the planned local/dev implementation technology for this port.
  - The cache is not approved for secret storage. Credentials, authorization material, raw vendor payloads, and document bytes are not part of the port.
- **Consequences:** Application call sites and tests can use a structural fake before any Redis adapter exists. A later Redis infrastructure chunk can implement this port without changing application signatures. Orchestration checkpoints and locks cannot silently reuse cache overwrite semantics.

---

## ADR-027 — Async Redis cache infrastructure remains outside application

- **Status:** Accepted
- **Context:** ADR-006 selected Redis as the local/dev cache technology. ADR-026 published application-owned `CachePort[TValue]` without a concrete adapter. Chunk 17 needed a reviewable redis-py implementation before any Compose service, live integration, or `create_app()` wiring. Pickle and other executable serializers would turn the cache into an unsafe object store. Application keys must not become visible Redis key names. Cache overwrite is not CAS for orchestration state.
- **Decision:**
  - The official `redis` package (`redis>=8,<9`, redis-py async API) implements the cache. `hiredis`, RedisOM, fakeredis, and `aioredis` are out of scope. ADR-006 and ADR-026 remain Accepted and are not superseded.
  - `RedisSettings` is loaded separately from `AppSettings` (`REDIS_` prefix). `create_app()` does not require or load Redis settings. There is no process-wide Redis settings cache.
  - `create_redis_client(settings)` returns `redis.asyncio.Redis` with keyword construction (`decode_responses=False`). It does not connect on import, does not `PING`, and does not build or log a password-bearing DSN. A future composition root owns `await client.aclose()`. The factory and `RedisCache` do not close the shared client.
  - Serialization is an injected infrastructure-local `CacheCodec[TValue]` (`encode`/`decode` bytes). `CacheCodecError` is infrastructure-only and must not appear on `CachePort`. There is no default pickle/marshal/shelve/`Any`/dict serializer.
  - `RedisCache[TValue]` structurally implements `CachePort[TValue]` and does not inherit it. Backend keys are `energy-trading:cache:` plus the SHA-256 hex digest of the normalized UTF-8 application key.
  - Positive `timedelta` TTL converts to integer Redis `PX` milliseconds. Sub-millisecond positive durations round up to 1 ms. Blank keys and non-positive TTL are `InvalidRequestError` before backend I/O.
  - Redis `RedisError`, codec failures, non-byte GET payloads, and unsuccessful SET outcomes become sanitized `DependencyUnavailableError`. No Redis-specific application errors. No retries in the adapter.
  - Chunk 17 adds no Redis Compose service, live integration marker, API wiring, orchestration state, CAS, or distributed locks. PostgreSQL/TimescaleDB remains the system of record. Cache loss/flush/expiry is acceptable.
- **Consequences:** Offline tests can exercise Redis settings, client construction, and adapter semantics with fakes. Operators still must not start Redis until a later service-profile chunk. Application code remains Redis-type-free.

---

## ADR-028 — Pinned local Redis service profile and live cache validation

- **Status:** Accepted
- **Context:** Chunk 17 published redis-py `RedisCache` without a running server. Live proof required a pinned, on-demand Compose service that cannot become a system of record, cannot share a profile with TimescaleDB, and cannot be reached from the LAN. WSL2 RAM remains limited, so Redis must not be always-on. Application `CachePort` and `RedisCache` public semantics stay unchanged.
- **Decision:**
  - Local Redis uses the exact Docker Official Image `redis:8.2.9-alpine`. The pin is a patch tag, not `latest`, `redis:8`, `redis:8-alpine`, `redis:8.2`, Redis Stack, Bitnami, Sentinel, or Cluster.
  - Compose defines one cache service, `redis`, gated on profile `redis`. Start with `docker compose --profile redis up -d redis`. Stop/remove with `docker compose --profile redis stop redis` and `docker compose --profile redis rm -f redis` so an independently running TimescaleDB is undisturbed.
  - The published port is loopback-only (`127.0.0.1` plus `REDIS_PORT`). Local Compose Redis requires a non-empty `REDIS_PASSWORD` interpolated into the container. `RedisSettings.password` remains optional for other future providers. Healthcheck uses `redis-cli ping` and `PONG`, authenticating via container `REDISCLI_AUTH`, not `redis-cli -a`.
  - Persistence is disabled (`save ""`, `appendonly no`). There is no Redis named volume and no `/data` bind mount. Cache loss on container removal is acceptable. PostgreSQL/TimescaleDB remains the system of record (ADR-004).
  - TimescaleDB (`postgres` profile) and Redis (`redis` profile) have no `depends_on` relationship.
  - Live tests live under `tests/integration/cache/redis/`, use marker `redis_integration`, and require `ENERGY_RUN_REDIS_INTEGRATION=1`. They cover authenticated PING, exact version `8.2.9`, unauthenticated rejection, disabled AOF/RDB, and real `RedisCache` set/get/overwrite/delete/expiry. They accept only `127.0.0.1`/`localhost`, use unique keys, and never `FLUSHALL`/`FLUSHDB`/`KEYS *`. Default `uv run pytest` stays service-independent. testcontainers, the Docker SDK, and fakeredis are not used.
  - `create_app()` remains unwired. No Redis readiness endpoint, orchestration state, CAS, or locks.
  - ADR-006, ADR-026, and ADR-027 remain Accepted and are not superseded.
- **Consequences:** Developers can prove the published Redis adapter against a compatible local server without starting TimescaleDB, Qdrant, or the API. API cache injection remains a later chunk.

---

## ADR-029 — Document embedding generation is separate from vector storage/retrieval

- **Status:** Accepted
- **Context:** ADR-005 selected Qdrant as the local/dev vector database for regulatory/document retrieval. Chunk 12 published application-owned document extraction without embeddings. Hiding embedding generation inside a future Qdrant or generic `VectorStore` abstraction would collapse distinct responsibilities: text-to-vector generation, persistence of vectors, and later search. Selecting a model SDK now would add a heavy dependency before any retrieval contract exists.
- **Decision:**
  - ADR-005 remains Accepted and is not superseded. Qdrant is still the planned local/dev vector database.
  - Application owns `DocumentEmbeddingPort`. Infrastructure or `ml` may later implement it structurally. There is no infrastructure base class.
  - The port embeds only already-normalized `ExtractedDocumentChunk` values. It does not accept document bytes, paths, URLs, OCR payloads, credentials, vendor dictionaries, or Qdrant objects.
  - Output is `DocumentChunkEmbedding` (`document_id`, `chunk_id`, finite float `vector`). This is an application orchestration DTO, not a domain contract and not a `RegulatoryConstraint`.
  - Embedding generation is not hidden inside Qdrant and is not a vector-index or search operation. No persistence or retrieval occurs through this port.
  - No concrete embedding model or provider is selected. No model SDK, OpenAI, SentenceTransformers, HuggingFace, torch, tensorflow, or NumPy dependency is added.
  - Vector indexing/storage is deferred to its own application boundary. Retrieval/search is deferred separately. Query embedding semantics are deferred until retrieval requirements are designed.
  - No RAG, reranking, hybrid search, BM25, LangChain, LangGraph, agent, or LLM regulatory interpretation is added.
  - Invalid caller input is `InvalidRequestError`. Unavailable or unusable embedding backends become sanitized `DependencyUnavailableError`. Public messages must not include chunk text, secrets, provider bodies, stack traces, model paths, or URLs. Retries are not part of this boundary.
- **Consequences:** Application call sites and tests can use a structural fake before any embedding adapter exists. A later concrete implementation can satisfy this port without changing application signatures. Qdrant remains a future infrastructure concern behind a still-to-be-designed indexing/storage boundary, not behind this embedding port.

---

## ADR-030 — Application vector indexing boundary precedes Qdrant infrastructure

- **Status:** Accepted
- **Context:** ADR-005 selected Qdrant as the local/dev vector database. ADR-029 published application-owned embedding generation without persistence. Hiding indexing behind Qdrant collection/point/payload types, or collapsing write and search into a generic `VectorStore`, would couple application orchestration to one vendor and mix distinct consumers. Retrieval/search needs its own later contract.
- **Decision:**
  - ADR-005 remains Accepted and is not superseded. Qdrant remains the chosen local/dev vector-store technology. Concrete Qdrant implementation is still deferred.
  - Application first owns vendor-neutral indexing semantics through `DocumentVectorIndexPort` and `DocumentVectorIndexEntry`.
  - Indexing pairs a normalized `ExtractedDocumentChunk` with the matching `DocumentChunkEmbedding`. Nested DTOs are reused; there is no shadow document schema.
  - Logical identity is `(document_id, chunk_id)`. Exact retries of the same application entry are idempotent. The same identity with different chunk or vector content fails closed as `ConflictError` rather than overwrite. There is no last-write-wins, replace, or reindex API in this chunk.
  - There is no generic `VectorStore`, generic `Repository`, or Unit of Work.
  - Retrieval/search is a separate future application concern. This port exposes only `index()`.
  - Collection names, point IDs, payload schema, distance metric, and client objects remain infrastructure concerns and are absent from the public contract.
  - Invalid batch semantics such as mixed vector dimensions are `InvalidRequestError`. Expected backend failure in a future adapter is sanitized `DependencyUnavailableError`. No retry policy belongs on the port.
- **Consequences:** Application call sites and tests can exercise indexing identity, idempotency, and conflict rules with a structural fake. A later Qdrant adapter can implement this port without changing application signatures. Query embeddings remain deferred. Search is owned by a separate retrieval port (ADR-031).

---

## ADR-031 — Vector retrieval exposes ranked normalized chunks, not backend search types

- **Status:** Accepted
- **Context:** ADR-005 selected Qdrant as the local/dev vector database. ADR-029 published application-owned embedding generation. ADR-030 published application-owned indexing without retrieval. Exposing Qdrant point IDs, payloads, collection names, distance metrics, or raw similarity scores on an application search port would couple orchestration to one vendor and leak backend ranking types into agents. Combining indexing and search into a generic `VectorStore` would mix distinct consumers. Embedding query text on this port would collapse deferred query-embedding work into retrieval.
- **Decision:**
  - ADR-005 remains Accepted and is not superseded. Qdrant remains the chosen local/dev vector-store technology. Concrete Qdrant implementation is still deferred and is now the next infrastructure concern.
  - Application owns retrieval/search through `DocumentVectorSearchPort` and `DocumentVectorSearchQuery`.
  - Search consumes an already-embedded numeric query vector plus a positive `limit`. Query-text embedding remains a separate deferred concern and does not extend `DocumentEmbeddingPort`.
  - The port returns ranked normalized `ExtractedDocumentChunk` values. Tuple order conveys ranking. There is no score DTO and no raw similarity/distance score on the application contract.
  - Collection names, point IDs, filters, distance metrics, score thresholds, pagination, namespace/tenant, and Qdrant objects are absent from the public contract.
  - Indexing remains `DocumentVectorIndexPort`. Retrieval remains `DocumentVectorSearchPort`. There is no generic `VectorStore`.
  - Zero matches are a valid empty tuple, not `ResourceNotFoundError`. Logical identity `(document_id, chunk_id)` is unique within one response.
  - A query vector incompatible with a configured index dimension, when clearly a request incompatibility, is sanitized `InvalidRequestError`. Unusable backend results (duplicate identities, too many hits, malformed payloads, reconstructable-chunk failures) are sanitized `DependencyUnavailableError`. No retry policy belongs on the port.
- **Consequences:** Application call sites and tests can exercise ranking, limit, uniqueness, empty-result, and sanitized failure semantics with a structural fake before any vector database exists. A later Qdrant adapter can implement this port without changing application signatures. Query embedding, collection configuration, filters, and live Qdrant remain later work.

---

## ADR-032 — Official async Qdrant client remains infrastructure-only and does not perform embedding

- **Status:** Accepted
- **Context:** ADR-005 selected Qdrant as the local/dev vector database. Chunks 19–21 published application-owned embedding, indexing, and retrieval ports without a concrete vector database. Introducing Qdrant types into domain, application, API, or ML, or using Qdrant/FastEmbed inference, would collapse `DocumentEmbeddingPort` into the storage client and couple inner layers to one SDK. Collection dimension and distance cannot be chosen until an embedding model exists.
- **Decision:**
  - ADR-005 remains Accepted and is not superseded. Qdrant remains the chosen local/dev vector-store technology.
  - The official `qdrant-client` library (`>=1.19,<2`) is the Python integration. `AsyncQdrantClient` is used.
  - Client construction is lazy: `create_qdrant_client(settings)` performs no eager Qdrant command, version check, health probe, collection call, or upsert/query. There is no module-global client and no `lru_cache` of a client.
  - REST is the initial transport (`prefer_grpc=False`). Local embedded mode (`location=":memory:"` / filesystem `path`) is not used as production infrastructure.
  - Application, API, domain, and ML never import Qdrant SDK types. `QdrantSettings` is separate from `AppSettings` and does not import `qdrant_client`. Process health does not require Qdrant environment variables.
  - The optional API key is `SecretStr | None`. Callers must not build or log a credential-bearing URL.
  - FastEmbed, Qdrant `models.Document` inference, and `cloud_inference` are not used. Embeddings remain produced through `DocumentEmbeddingPort`.
  - Collection schema, vector-size provisioning in Qdrant, and distance metric remain deferred. Point identity, closed payload, and insert-only writes are specified in ADR-033. A running Qdrant service remains deferred to the service-profile slice.
- **Consequences:** Tests can construct `AsyncQdrantClient` against an unreachable host without a server. Chunk 23 adapters implement `DocumentVectorIndexPort` and `DocumentVectorSearchPort` using this factory without changing application signatures. Compose Qdrant and live tests are still future work.

---

## ADR-033 — Qdrant document points use deterministic identity and insert-only verified writes

- **Status:** Accepted
- **Context:** ADR-005 selected Qdrant as the local/dev vector database. ADR-029/030/031 published application-owned embedding, indexing, and retrieval ports. ADR-032 added an infrastructure-only `AsyncQdrantClient` without points or collections. Ordinary Qdrant upsert overwrite would violate application exact-retry/conflict semantics. Exposing Qdrant scores, point IDs, or open metadata payloads would leak infrastructure into application DTOs. Collection creation and distance choice still cannot be made until embedding-model/provisioning work exists.
- **Decision:**
  - ADR-005, ADR-029, ADR-030, ADR-031, and ADR-032 remain Accepted and are not superseded.
  - Application ports remain Qdrant-free. Concrete adapters `QdrantDocumentVectorIndex` and `QdrantDocumentVectorSearch` structurally implement the existing ports in infrastructure.
  - There is no generic `VectorStore`, `DocumentVectorStorePort`, or `QdrantVectorStorePort`. Index and search stay separate application abstractions and may share one client and one infrastructure `QdrantDocumentVectorConfig` (`collection_name`, `vector_size`).
  - Qdrant point UUID derives deterministically (UUID5 over an unambiguous JSON encoding) from application identity `(document_id, chunk_id)`. Raw document/chunk strings are never used as point IDs. Point IDs do not appear on application DTOs.
  - Payload is closed to normalized chunk fields plus an integrity fingerprint: `document_id`, `chunk_id`, `ordinal`, `text`, `page_number`, `content_sha256`. No arbitrary metadata, paths, URLs, OCR/provider objects, scores, or embedding-model fields.
  - Exact application-entry fingerprint is SHA-256 over a deterministic serialization of `DocumentVectorIndexEntry`, including the embedding vector via exact stable `float.hex()` representation. The fingerprint is stored as hex `content_sha256`; the vector is not duplicated in payload for conflict detection. Qdrant's stored float representation is not compared.
  - Ordinary Qdrant upsert overwrite semantics are not used. Writes use `UpdateMode.INSERT_ONLY` with `wait=True`.
  - Pre-read and post-write retrieval (`with_payload=True`, `with_vectors=False`) enforce exact retry versus conflict. Matching fingerprint is an idempotent no-op. Differing fingerprint for the same identity is `ConflictError`. Malformed stored payload is `DependencyUnavailableError`, not an application conflict.
  - There is no cross-entry transactional guarantee. Partial physical effects from concurrent writers are acceptable under existing port semantics. Exact retries remain safe.
  - Search uses `query_points` with already-produced numeric query vectors. Qdrant scores remain infrastructure-only and are discarded. Result order is the backend ranking order. Returned values are existing `ExtractedDocumentChunk` objects.
  - Collection creation, vector-size provisioning inside Qdrant, and distance choice are separate deployment infrastructure concerns. These adapters assume a future-provisioned collection.
  - Qdrant inference remains disabled. Embeddings stay behind `DocumentEmbeddingPort`. Query-text embedding remains deferred.
  - Adapters do not own `AsyncQdrantClient` lifecycle. A future composition root remains responsible for `await client.close()`. `create_app()` stays unwired.
- **Consequences:** Offline fakes can prove identity, fingerprint, insert-only conflict, concurrent-writer, and search-translation behavior without a Qdrant process. Live collection provisioning, distance selection, Compose, and API wiring remain later work.

---

## ADR-034 — Local Qdrant runs as an authenticated opt-in profile with test-only collection provisioning

- **Status:** Accepted
- **Context:** ADR-005 selected Qdrant as the local/dev vector database. Chunks 22–23 delivered an infrastructure-only `AsyncQdrantClient` plus insert-only document index/search adapters without a running server. Live proof requires a pinned, on-demand Compose service that cannot become a system of record, cannot share a profile with TimescaleDB or Redis, and cannot be reached from the LAN. WSL2 RAM remains limited, so Qdrant must not be always-on. Production collection schema and embedding distance still cannot be chosen until an embedding model exists. Application ports and Chunk 22/23 adapter semantics stay unchanged.
- **Decision:**
  - ADR-005, ADR-029, ADR-030, ADR-031, ADR-032, and ADR-033 remain Accepted and are not superseded.
  - Local/dev Qdrant uses the exact image `qdrant/qdrant:v1.19.1`. The pin is a patch tag, not `latest`, `v1`, `v1.19`, `dev`, `master`, a GPU image, or an unprivileged variant.
  - Compose defines one vector service, `qdrant`, gated on profile `qdrant`. Start with `docker compose --profile qdrant up -d qdrant`. Stop with `docker compose --profile qdrant stop qdrant` so independently running TimescaleDB or Redis is undisturbed.
  - Only REST port 6333 is host-published, loopback-only (`127.0.0.1` plus `QDRANT_PORT`). Ports 6334 and 6335 are not published. The production Python client remains REST (`prefer_grpc=False`).
  - The local profile requires a non-empty `QDRANT_API_KEY` interpolated as `QDRANT__SERVICE__API_KEY`. An empty read-only API key is not configured. `QdrantSettings.api_key` remains optional for other future providers.
  - Local HTTP plus API key is acceptable only because the published port is loopback-only. This is local development/test infrastructure, not the production Qdrant security architecture. Production requires appropriately secured networking/TLS.
  - Telemetry is disabled for the local project service (`QDRANT__TELEMETRY_DISABLED=true`).
  - Storage uses the Compose named volume `qdrant-data` mounted at `/qdrant/storage`. There is no Windows host bind mount and no snapshots volume in this chunk.
  - The service is opt-in. Process health and `create_app()` do not require Qdrant. Default pytest does not contact Qdrant.
  - Live tests live under `tests/integration/infrastructure/vector_store/qdrant/`, use marker `qdrant_integration`, and require `ENERGY_RUN_QDRANT_INTEGRATION=1`. They use `QdrantSettings` and `create_qdrant_client()`, poll `get_collections()` with a bounded 30-second timeout, and accept only `127.0.0.1`/`localhost`. They never print the API key.
  - Temporary test collections are uniquely named per fixture and deleted in cleanup. Test-only vector configuration is size `3` and `models.Distance.DOT`. That fixture metric does **not** select a production embedding distance and is not added to `QdrantSettings` or `QdrantDocumentVectorConfig` defaults.
  - Production Qdrant modules still do not create, recreate, or delete collections and still do not reference `VectorParams` or distance enums. Production collection provisioning remains deferred.
  - Application ports/contracts remain unchanged. `create_app()` remains unwired. Qdrant inference remains disabled. Query-text embedding, RAG, and agents remain deferred.
  - Default `uv run pytest` stays service-independent. testcontainers and the Docker SDK are not used.
- **Consequences:** Developers can prove the published document index/search adapters against a compatible local Qdrant without starting TimescaleDB, Redis, or the API. Production distance selection, collection bootstrap, embedding models, and API composition remain later chunks.

---

## ADR-035 — n8n is an opt-in outer acquisition service and cannot bypass the ingestion ACL

- **Status:** Accepted
- **Context:** The architecture needs a local n8n service for future external acquisition / ETL workflow execution. Adding workflows, source credentials, FastAPI callbacks, Redis-backed n8n queues, or sharing the platform Timescale database would collapse later acquisition work into this foundation slice. n8n must not become a shortcut around the Anti-Corruption Layer, and it must not replace Chief Orchestrator / LangGraph application orchestration.
- **Decision:**
  - n8n stable image is pinned to `n8nio/n8n:2.37.10` for this checkpoint. The pin is a patch tag, not `latest`, `stable`, `2`, `2.37`, `nightly`, or `beta`. No custom n8n Dockerfile and no Python n8n SDK.
  - Compose defines one service, `n8n`, gated on profile `n8n`. Start with `docker compose --profile n8n up -d n8n`. Default `docker compose up` does not start n8n. TimescaleDB, Redis, and Qdrant remain independently profile-gated with no `depends_on` relationship to n8n.
  - Host exposure is loopback-only HTTP (`127.0.0.1` plus overridable `N8N_HOST_PORT`, default 5678). The container n8n port remains exactly 5678 (`N8N_PORT=5678`). Custom host ports such as `N8N_HOST_PORT=5680` must publish `127.0.0.1:5680 -> 5678`.
  - A deployment `N8N_ENCRYPTION_KEY` is required through Compose required-variable interpolation. There is no default key. The key protects n8n's own stored credentials/configuration. It is not an application API secret and is not consumed by Python settings (`N8nSettings` / `load_n8n_settings` are not created).
  - Persistence uses the Compose named volume `n8n-data` mounted at `/home/node/.n8n`. There is no Windows host bind mount. n8n may use its own local SQLite/metadata inside that volume; that store is n8n internal orchestration metadata only and is not the platform energy-data system of record. PostgreSQL/TimescaleDB remains the system of record (ADR-004). n8n is not configured to share the application Timescale database.
  - n8n is outer infrastructure for future source acquisition/scheduling. Raw external data must still pass application-approved ACL/adapters before becoming canonical domain truth. n8n workflows may not directly establish canonical domain truth, write vendor payloads into application DTOs, Timescale canonical tables, or Qdrant application-facing payloads.
  - No workflow/API handoff is selected yet. No workflows, credentials, owner bootstrap, webhooks, or FastAPI callbacks are added.
  - Local diagnostics, version notifications, templates, and personalization are disabled (`N8N_DIAGNOSTICS_ENABLED`, `N8N_VERSION_NOTIFICATIONS_ENABLED`, `N8N_TEMPLATES_ENABLED`, `N8N_PERSONALIZATION_ENABLED` all false). Ask-AI, n8n Cloud, and external template libraries are not enabled.
  - No LangGraph or agent ownership is assigned to n8n. n8n does not replace Chief Orchestrator/LangGraph application orchestration (ADR-007).
  - Live tests live under `tests/integration/infrastructure/orchestration/n8n/`, use marker `n8n_integration`, and require `ENERGY_RUN_N8N_INTEGRATION=1`. They prove service readiness only (`GET /healthz` and `GET /healthz/readiness` return HTTP 200) against `127.0.0.1` with a bounded ~60-second readiness poll. Default pytest stays service-independent. testcontainers and the Docker SDK are not used.
  - This local HTTP profile is development/test infrastructure, not the production n8n security architecture. Production deployment/security remains separate future work.
- **Consequences:** Developers can start a pinned local n8n and prove readiness without TimescaleDB, Redis, Qdrant, or the API. Future acquisition workflows must still terminate at an infrastructure/application ACL boundary. Operators must not treat n8n SQLite as canonical energy data.

---

## ADR-036 — Agent invocation is application-owned, structurally typed, and framework-neutral

- **Status:** Accepted
- **Context:** Phase 3 needs a reviewable invocation seam before any concrete agent, LangGraph runtime, shared workflow snapshot, retry policy, or LLM SDK exists. Letting LangGraph, LangChain, or a generic payload dictionary define agent interfaces would couple orchestration to one framework and collapse 13 different request/result shapes into an untyped envelope. An inheritance-based `BaseAgent` would force a shared constructor, logger, and lifecycle that the architecture does not yet have.
- **Decision:**
  - Exactly 13 canonical agent identities exist. They match `AGENTS.md` display names and are not renamed or aliased.
  - `AgentName` is an application-level `enum.StrEnum`. It is not a domain entity and not a runtime lookup table.
  - The shared contract is generic `AgentPort[TRequest, TResult]`, a `typing.Protocol`.
  - Only identity (`name`) and async `run(request)` are common. There is no `execute`/`invoke`/`stream` surface.
  - No base class or inheritance is required. Future agents satisfy the protocol structurally.
  - Request and result types remain specific to later agents. This chunk does not constrain them to one canonical model.
  - There is no generic payload dictionary, `Any`, `Mapping`, or shared `AgentResult` envelope.
  - LangGraph does not define agent interfaces. When it invokes agents, it must call them through `AgentPort`.
  - Chunk 28 installs LangGraph for a no-op graph skeleton only (ADR-038). No LangChain, OpenAI, Anthropic, or other agent SDK is installed as a direct dependency, and no agent is wired.
  - No registry, factory, shared workflow snapshot, retry, or fallback policy is added.
  - Existing `ApplicationError` types remain the expected-failure vocabulary. No `AgentError` hierarchy is introduced.
- **Consequences:** Orchestration and tests can type against `AgentPort` with structural fakes before any agent exists. Each later agent can introduce a precise request/result pair without changing this seam. Graph runtime, snapshots, and retries stay later chunks.

---

## ADR-037 — Orchestration workflow state is application-owned, minimal, immutable, and framework-neutral

- **Status:** Accepted
- **Context:** Phase 3 requires an application-owned workflow snapshot before a graph runtime (planned LangGraph, ADR-007) is installed. Letting LangGraph, Redis, PostgreSQL, or an untyped payload dictionary define that snapshot would couple identity, delivery context, and diagnostics to one framework and invite a speculative global state object. ADR-036 deferred the snapshot; Chunk 27 implements it without execution semantics.
- **Decision:**
  - Application owns `WorkflowPhase`, `WorkflowStatus`, and frozen `WorkflowState`. These are orchestration DTOs, not domain entities and not LangGraph state.
  - `WorkflowPhase` has exactly the five already-documented business phases: `contract`, `ingestion`, `forecasting`, `risk_and_bid`, `settlement`. Clearing, initialization, completion, degradation, retry, agent names, and graph node names are not phases.
  - `WorkflowStatus` is coarse lifecycle vocabulary only: `pending`, `running`, `succeeded`, `failed`. Cancelled, paused, retrying, degraded, partial, waiting, and skipped are omitted until later lifecycle requirements exist.
  - `WorkflowState` carries explicit `workflow_id`, `portfolio_id`, `delivery_date`, `correlation_id`, `phase`, `status`, and accumulated canonical `AdapterDiagnostic` values. Identifiers are opaque non-empty strings after surrounding whitespace is stripped; UUID syntax and FastAPI `X-Correlation-ID` rules are not duplicated. `delivery_date` is an actual `datetime.date`, not a `datetime` and not a timezone-bearing instant. No DAM interval is inferred.
  - There is no generic payload bag (`dict`, `Mapping`, `Any`, `TState`, metadata/artifacts/context). Phase-specific canonical output slots (`weather_records`, forecasts, bids, settlements, and similar) are not pre-created.
  - Construction validates field types and identifier non-emptiness only. There is no state machine: phase and status are not cross-validated, and there are no `advance`/`transition`/`mark_*` helpers.
  - No Redis/PostgreSQL persistence, CAS, locks, retries, fallback, routing, or graph compilation is implied. LangGraph must consume this contract rather than redefine it. ADR-007 and ADR-036 remain Accepted and are not superseded. Chunk 28 / ADR-038 consumes this snapshot as the graph schema without changing it.
- **Consequences:** Tests and later graph nodes can hold a typed snapshot before any runtime exists. A different orchestration framework can reuse the same contract. Transition policy, persistence, and concrete agents remain later chunks.

---

## ADR-038 — LangGraph is a thin application-layer runtime over application-owned workflow state

- **Status:** Accepted
- **Context:** ADR-007 selected LangGraph conceptually as the application orchestration engine. Chunk 26 published `AgentPort`. Chunk 27 published framework-neutral `WorkflowState`. Installing LangGraph without a deliberately tiny first seam would invite five-phase routing, agent wiring, retries, and persistence in one drop. The first executable integration must prove only that LangGraph can consume the already-published snapshot.
- **Decision:**
  - ADR-007, ADR-036, and ADR-037 remain Accepted and are not superseded. Chunk 28 implements only LangGraph's first executable skeleton, not the Chief Orchestrator and not five-phase routing.
  - LangGraph is a direct application-runtime dependency with constraint `langgraph>=1.2.11,<1.3`. That range is the current reviewed pin, not a claim that 1.2.x is permanent; later upgrades require normal dependency review.
  - LangGraph belongs to application orchestration. Production imports are confined to `energy_trading.application.orchestration.graph`. `state.py`, agents, domain, infrastructure, ML, and API remain LangGraph-free.
  - Chunk 27 `WorkflowState` remains framework-neutral and authoritative. LangGraph consumes that contract as `state_schema`. There is no second graph state schema, TypedDict shadow, or Pydantic copy.
  - The public factory is `build_workflow_graph()`. Every call constructs and compiles a fresh graph. There is no module-global compiled graph, singleton, or registry.
  - Initial topology is only `START → workflow_entry → END`. `workflow_entry` is a private async no-op node: it performs no I/O, does not mutate state, and returns an empty LangGraph state update. The update changes no application state.
  - Compilation is plain. No checkpointer, store, cache, interrupt, durable execution, Redis saver, or PostgreSQL saver is configured.
  - No concrete agent is wired. The graph does not import `AgentPort` / `AgentName` and does not call use cases.
  - No five-phase routing, conditional edges, retries, fallback, LangChain messages, or LLM provider dependency is added. Direct `langchain` is not a project dependency. Transitive `langchain-core` may exist because LangGraph requires it; project source must not import it.
  - Future graph expansion (phase nodes, retries/fallback, agent invocation, persistence) must happen in separate reviewed chunks.
- **Consequences:** The repository can compile and asynchronously invoke a no-op graph over frozen `WorkflowState` without encoding business workflow. Later chunks can add routing and policy without redefining state.

---

## ADR-039 — Retry/fallback decisions are application-owned policy, separate from execution

- **Status:** Accepted
- **Context:** Chief Orchestrator will eventually own failure handling. Chunk 28 installed a no-op LangGraph skeleton. Letting LangGraph `RetryPolicy`, Tenacity, or a raw exception object define business retry/fallback semantics would couple orchestration policy to one runtime and leak unsanitized failure details into decision-making. Chunk 29 needs a reviewable decision seam before any fallible business node exists.
- **Decision:**
  - Framework runtime must not define business retry/fallback semantics. Application owns `FailureAction`, frozen `FailurePolicyContext`, and async structural `FailurePolicyPort`.
  - `FailurePolicyContext` carries only `phase` (`WorkflowPhase`), a sanitized stable `error_code` string, a 1-based failed `attempt_number`, and optional canonical `agent_name` (`AgentName | None`).
  - Raw exceptions, exception classes, messages, and tracebacks are excluded. Future execution code must translate an observed failure into `error_code` before policy evaluation. This chunk does not implement that translation.
  - `FailureAction` is the closed initial decision set: `RETRY`, `FALLBACK`, and `FAIL`. Continue/skip/ignore/degraded/abort/pause/cancel are omitted until verified.
  - `FALLBACK` means only that a future runtime may attempt a separately defined fallback path. It does not identify or implement that path.
  - `FailurePolicyPort.decide(context)` is asynchronous and accepts only `FailurePolicyContext`. It does not accept `WorkflowState`, exception objects, dict metadata, graph runtime, Redis, retry callbacks, or fallback callables.
  - No concrete policy exists yet. No fixed retry count, backoff, delay, timeout, fallback target, or degraded-mode semantics exist.
  - LangGraph does not appear in the policy module. The Chunk 28 skeleton remains `START → workflow_entry → END` and does not call the policy. Retry/fallback execution will be introduced only when a real fallible orchestration node justifies it.
- **Consequences:** Future graph nodes can ask a framework-neutral policy whether to retry, fall back, or fail without encoding those rules in LangGraph. Tests can use structural fakes. Concrete rules and execution remain later workflow work.

---

## ADR-040 — First concrete Weather agent consumes canonical records through an application-owned source port

- **Status:** Accepted
- **Context:** Chunks 26–29 established shared application orchestration contracts (`AgentPort`, `WorkflowState`, a no-op LangGraph skeleton, and a failure-policy decision hook) but no concrete agent. Phase 4 now needs the first concrete agent pattern. Choosing an HTTP weather provider, or allowing raw weather payloads into application, would violate the Anti-Corruption Layer. Persistence, graph invocation, retry/fallback execution, and ML are separate concerns and must not ride along with the first agent slice.
- **Decision:**
  - The first concrete agent is Weather & Renewable Forecast Agent. It structurally satisfies `AgentPort[WeatherAndRenewableForecastRequest, WeatherAndRenewableForecastResult]` and does not inherit a base class.
  - Agent-specific request/result remain frozen application DTOs. The request carries only opaque `location_id` plus explicit `horizon_start` / `horizon_end`. The result contains a canonical `WeatherRecord` tuple.
  - `WeatherRecordSourcePort` is application-owned. `fetch` is keyword-only and returns only already-canonical `WeatherRecord` values. External adapters remain infrastructure.
  - Empty results are valid. The port and agent do not sort, interpolate, resample, infer cadence, or assume an Armenian DAM interval.
  - No weather provider, persistence, graph wiring, retry/fallback execution, ML, or LLM numerical calculation is added. No new dependency is added.
  - Canonical identity remains the existing `AgentName.WEATHER_AND_RENEWABLE_FORECAST` display value `Weather & Renewable Forecast Agent`.
- **Consequences:** The first concrete agent pattern is proven without vendor coupling. A future infrastructure weather adapter can satisfy `WeatherRecordSourcePort`. Graph, persistence, and provider work remain separately reviewable. Hydro and other agents must not be auto-generated from this pattern until individually reviewed.

---

## ADR-041 — First concrete Hydro agent consumes canonical records through an application-owned source port

- **Status:** Accepted
- **Context:** Chunk 30 established the first concrete Weather agent pattern: a thin application agent structurally satisfying `AgentPort`, consuming already-canonical records through an application-owned source port. Phase 4 now needs Hydro without leaking raw telemetry into application. Hydrological calculation, provider selection, persistence, graph invocation, retry/fallback execution, and Generation Availability coupling are separate concerns and must not ride along with this first Hydro slice. Two similar agents are not sufficient justification for a generic ingestion-agent framework.
- **Decision:**
  - The second concrete agent is Hydro Resources Agent. It structurally satisfies `AgentPort[HydroResourcesRequest, HydroResourcesResult]` and does not inherit a base class.
  - Agent-specific request/result remain frozen application DTOs. The request carries only opaque `resource_id` plus explicit `horizon_start` / `horizon_end`. The result contains a canonical `HydroRecord` tuple.
  - `HydroRecordSourcePort` is application-owned. `fetch` is keyword-only and returns only already-canonical `HydroRecord` values. External adapters remain infrastructure.
  - Empty results are valid. The port and agent do not sort, interpolate, resample, infer cadence, fabricate missing records, or assume an Armenian DAM interval.
  - The agent does not calculate reservoir level, river flow, available generation, head, turbine efficiency, discharge policy, or water-to-power conversion. Optional canonical `available_generation_mw` is passed through unchanged if already present.
  - No hydro provider, persistence, graph wiring, retry/fallback execution, ML, LLM, or Generation Availability coupling is added. No new dependency is added.
  - Weather and Hydro are not generalized into a shared ingestion-agent base class, registry, or factory.
  - Canonical identity remains the existing `AgentName.HYDRO_RESOURCES` display value `Hydro Resources Agent`.
- **Consequences:** The second concrete deterministic ingestion-agent pattern is proven without vendor coupling. A future infrastructure hydro adapter can satisfy `HydroRecordSourcePort`. Canonical Hydro can later feed other workflows through explicit reviewed boundaries. Generation Availability interaction remains later. Other agents remain separately reviewed.

---

## ADR-042 — First concrete Generation Availability agent consumes canonical records through an application-owned source port

- **Status:** Accepted
- **Context:** Chunks 30–31 established provider-neutral Weather and Hydro application-agent patterns: thin agents structurally satisfying `AgentPort`, consuming already-canonical records through application-owned source ports. Generation Availability is the next deterministic ingestion agent. External outage and plant-availability schemas must remain inside the infrastructure ACL. Hydro-derived capacity, status-to-MW rules, missing-asset semantics, and fleet-completeness policy are premature. Graph wiring, persistence, retry/fallback execution, and provider selection remain separate concerns and must not ride along with this first Generation slice. Three similar agents are not sufficient justification for a generic ingestion-agent framework.
- **Decision:**
  - The third concrete agent is Generation Availability Agent. It structurally satisfies `AgentPort[GenerationAvailabilityRequest, GenerationAvailabilityResult]` and does not inherit a base class.
  - Agent-specific request/result remain frozen application DTOs. The request carries only opaque `asset_id` plus explicit `horizon_start` / `horizon_end`. The result contains a canonical `GenerationAvailabilityRecord` tuple.
  - `GenerationAvailabilityRecordSourcePort` is application-owned. `fetch` is keyword-only and returns only already-canonical `GenerationAvailabilityRecord` values. External adapters remain infrastructure.
  - Empty results are valid. Tuple order is preserved as returned by the future implementation. The port and agent do not sort, interpolate, resample, aggregate, infer cadence, fabricate missing assets or time points, or assume an Armenian DAM interval.
  - The agent does not infer status, calculate `available_capacity_mw` or `total_capacity_mw`, apply derates, assume missing-asset availability or outage, or implement fleet-completeness policy. Canonical status and capacity fields are passed through unchanged if already present.
  - There is no Hydro coupling: the Generation agent does not import `HydroResourcesAgent`, `HydroRecordSourcePort`, or `HydroRecord`, and does not construct generation records from Hydro output.
  - No generation provider, persistence, graph wiring, retry/fallback execution, ML, LLM, or generic ingestion-agent abstraction is added. No new dependency is added.
  - Weather, Hydro, and Generation are not generalized into a shared ingestion-agent base class, registry, or factory.
  - Canonical identity remains the existing `AgentName.GENERATION_AVAILABILITY` display value `Generation Availability Agent`.
- **Consequences:** The third concrete deterministic ingestion-agent boundary is proven without vendor coupling. A future infrastructure generation adapter may satisfy `GenerationAvailabilityRecordSourcePort`. Hydro/Generation composition remains future reviewed work. Partial fleet completeness must be defined explicitly later. Remaining agents continue to be added individually.

---

## ADR-043 — First concrete News Intelligence agent consumes canonical News records through an application-owned source port

- **Status:** Accepted
- **Context:** Chunks 30–32 established three concrete provider-neutral ingestion agents: thin application agents structurally satisfying `AgentPort`, consuming already-canonical records through application-owned source ports. News Intelligence is the next Phase 4 ingestion agent. Text and “intelligence” concepts make accidental LLM, embedding, scraper, and provider coupling particularly risky. Raw feeds, HTML, and vendor article objects must remain behind the ACL. The application must consume the already-published canonical `NewsEvent` only. Chunk 33 must not invent a new News domain schema (`NewsRecord`, `NewsArticle`, relevance, impact, URL, sentiment) and must not reconcile `AGENTS.md` narrative wording about future extractable relevance/entities with the existing typed `NewsEvent` contract.
- **Decision:**
  - The fourth concrete agent is News Intelligence Agent. It structurally satisfies `AgentPort[NewsIntelligenceRequest, NewsIntelligenceResult]` and does not inherit a base class.
  - Canonical domain type remains existing `NewsEvent` (`energy_trading.domain.models.observations`). Fields remain `event_id`, `timestamp`, `headline`, `summary`, optional `category`, and optional `severity`. Provider/source identity, URL, body text, sentiment, relevance, and impact are not canonical fields and are not added.
  - Application-owned source port is `NewsEventSourcePort` in `application/ports/news_events.py`. `fetch` is keyword-only and accepts only `horizon_start` / `horizon_end` because `NewsEvent` is temporal and not entity-scoped. It returns only already-canonical `NewsEvent` tuples.
  - Agent-specific request/result remain frozen application DTOs. `NewsIntelligenceRequest` carries only explicit `horizon_start` / `horizon_end`. `NewsIntelligenceResult` contains only `records: tuple[NewsEvent, ...]`.
  - Empty results are valid. Tuple order is preserved as returned by the future implementation. The port and agent do not sort, filter, deduplicate, scrape, parse HTML/RSS, summarize, classify, score, embed, vectorize, translate, fabricate missing events, or assume publication cadence.
  - The agent does not infer sentiment, relevance, market impact, urgency, credibility, or topic. Existing canonical headline, summary, category, and severity pass through unchanged.
  - No news provider, RSS/scraper, HTTP client, persistence, embeddings, Qdrant News indexing, graph wiring, retry/fallback execution, ML, or LLM is added. No new dependency is added. Existing document RAG/Qdrant ports are not repurposed.
  - Weather, Hydro, Generation, and News are not generalized into a shared ingestion-agent base class, registry, or factory.
  - Canonical identity remains the existing `AgentName.NEWS_INTELLIGENCE` display value `News Intelligence Agent`.
- **Consequences:** The fourth concrete ingestion-agent boundary is established without vendor or LLM coupling. A future infrastructure news adapter may satisfy `NewsEventSourcePort` only after ACL normalization to `NewsEvent`. Future LLM summarization, sentiment/relevance inference, or vector indexing requires separately reviewed ports and implementation. Remaining Phase 4 agents continue to be added individually.

---

## ADR-044 — First concrete Market Monitoring agent consumes canonical MarketPriceRecord values through an application-owned source port

- **Status:** Accepted
- **Context:** Chunks 30–33 established provider-neutral application boundaries for the other Phase 4 ingestion agents: thin application agents structurally satisfying `AgentPort`, consuming already-canonical records through application-owned source ports. Market Monitoring is the fifth ingestion agent. Canonical `MarketPriceRecord` already represents official/historical market observations, not forecasts. Market interval, currency, operator, and DAM product rules are intentionally not hardcoded. Forecasting belongs to DAM Price Forecast Agent. Market clearing belongs elsewhere. Raw operator reports and vendor schemas must remain behind the ACL.
- **Decision:**
  - The fifth concrete agent is Market Monitoring Agent. It structurally satisfies `AgentPort[MarketMonitoringRequest, MarketMonitoringResult]` and does not inherit a base class.
  - Canonical domain type remains existing `MarketPriceRecord` (`energy_trading.domain.models.observations`). Fields remain `market_id`, `timestamp`, `price` (`EnergyPrice`), and optional `volume_mwh`. Currency is explicit on `EnergyPrice`. Interval duration is not part of the contract. AMD is not implied. No market-status, tick, or DAM-price replacement schema is added.
  - Application-owned source port is `MarketPriceRecordSourcePort` in `application/ports/market_price_records.py`. `fetch` is keyword-only and accepts opaque `market_id` plus explicit `horizon_start` / `horizon_end`. It returns only already-canonical `MarketPriceRecord` tuples.
  - Agent-specific request/result remain frozen application DTOs. `MarketMonitoringRequest` carries only `market_id` plus an explicit horizon. `MarketMonitoringResult` contains only `records: tuple[MarketPriceRecord, ...]`.
  - Empty results are valid. Tuple order is preserved as returned by the future implementation. The port and agent do not sort, interpolate, aggregate, resolve duplicates, fill missing hours, infer cadence or interval duration, convert currency, default a currency, forecast prices, clear the market, infer market status, or fabricate missing prices.
  - Canonical `EnergyPrice` objects pass through unchanged, including explicit currency. Optional `volume_mwh` passes through unchanged; missing volume stays missing.
  - No market provider, operator SDK, HTTP client, CSV/Excel adapter, persistence, graph wiring, retry/fallback execution, ML, or LLM is added. No new dependency is added. `PriceForecastPoint` is not constructed.
  - Weather, Hydro, Generation, News, and Market are not generalized into a shared ingestion-agent base class, registry, or factory.
  - Canonical identity remains the existing `AgentName.MARKET_MONITORING` display value `Market Monitoring Agent`.
- **Consequences:** All five Phase 4 ingestion-agent application boundaries now have first concrete slices. Live source acquisition and ACL remain separate. Market Monitoring can later be wired to a verified official source without application-layer vendor coupling. Phase 2 parallel orchestration remains a separately reviewed future chunk. Remaining concrete agents continue to be added individually.

---

## ADR-045 — Parallel ingestion fan-out planning is typed and framework-neutral

- **Status:** Accepted
- **Context:** Chunks 30–34 published five concrete Phase 2 ingestion-agent request DTOs. Chunks 27–29 published `WorkflowState`, a no-op LangGraph skeleton, and a failure-policy decision hook. Letting a future executor derive agent-specific scope from `WorkflowState.portfolio_id`, or packing the five requests into a generic payload/registry, would collapse distinct request contracts into an untyped bag and couple planning to graph runtime. Fan-in/result semantics, retry/fallback execution, and degraded-mode policy are not yet defined and must not ride along with the first planning contract.
- **Decision:**
  - Application owns frozen `ParallelIngestionPlan`. It is an orchestration DTO, not a domain contract, not `WorkflowState`, and not a LangGraph type.
  - The plan contains exactly the five existing strongly typed request DTOs: `WeatherAndRenewableForecastRequest`, `HydroResourcesRequest`, `GenerationAvailabilityRequest`, `NewsIntelligenceRequest`, and `MarketMonitoringRequest`. Those classes are reused; they are not duplicated or shadowed.
  - There is no generic payload dictionary, `Any`, `Mapping`, agent registry, factory, or `(AgentName, request)` collection helper.
  - The plan preserves supplied request objects exactly. It does not derive `location_id`, `resource_id`, `asset_id`, or `market_id` from `portfolio_id`, and it does not invent a portfolio-to-source-scope mapping.
  - Horizons are not required to be equal. Chunk 35 does not invent cross-request horizon policy.
  - The plan does not execute agents. LangGraph remains `START → workflow_entry → END` and does not import or consume the plan.
  - Fan-in/result/outcome contracts are omitted. Failure-policy semantics remain unchanged. `WorkflowState` remains unchanged.
  - A future executor/join remains a separately reviewed chunk. This ADR does not define retry, fallback, degraded, or partial-success execution policy.
- **Consequences:** A later executor can fan out from five already-typed requests without reading `WorkflowState` as a payload bag. Join, retry/fallback execution, graph wiring, and Chief Orchestrator remain future work.

---

## ADR-046 — Successful parallel-ingestion fan-in is a typed application contract

- **Status:** Accepted
- **Context:** Chunk 35 published `ParallelIngestionPlan` with the five existing Phase 2 request DTOs. A later executor will need a typed place to hold successful results. Naming that object `ParallelIngestionResult` / `Outcome` / `Join`, or using `Optional` branches, unions, or exception fields, would imply that failure, degraded, and partial-completion semantics already exist. Those policies are not yet defined and must not ride along with the first success aggregate.
- **Decision:**
  - Application owns frozen `ParallelIngestionSuccess`. It is an orchestration DTO, not a domain contract, not `WorkflowState`, and not a LangGraph type.
  - The aggregate contains exactly the five existing strongly typed result DTOs: `WeatherAndRenewableForecastResult`, `HydroResourcesResult`, `GenerationAvailabilityResult`, `NewsIntelligenceResult`, and `MarketMonitoringResult`. Those classes are reused; they are not duplicated or shadowed.
  - Semantics are all-five-success only. There is no `None` branch placeholder, no generic status field, no `Optional` failure slot, no error envelope, and no degraded flag.
  - There is no generic result wrapper, registry, factory, or payload dictionary.
  - Supplied result objects are preserved exactly. Records are not merged, sorted, deduplicated, or completeness-checked. Cross-result horizons are not equalized. Nothing is derived from `WorkflowState`.
  - The aggregate does not execute agents. LangGraph remains `START → workflow_entry → END` and does not import or consume the plan or success aggregate.
  - `WorkflowState` remains unchanged. Failure-policy semantics remain unchanged.
  - A future executor and any failure/partial/degraded fan-in policy remain separately reviewed chunks. This ADR does not define those behaviors.
- **Consequences:** A later successful join can return one typed object without collapsing five result contracts into a generic bag. Partial-failure representation, retry/fallback execution, graph wiring, and Chief Orchestrator remain future work.

---

## ADR-047 — Parallel ingestion execution is application-owned behind a specific Protocol

- **Status:** Accepted
- **Context:** Chunks 35–36 published typed `ParallelIngestionPlan` and `ParallelIngestionSuccess`. A future runtime will need an application seam between those contracts. Encoding concurrency (`asyncio.gather` vs `TaskGroup`), retries, cancellation, or partial-failure unions on that first seam would freeze implementation policy before it is reviewed. A generic `ParallelIngestionExecutionPort[TPlan, TResult]` would also collapse the Phase 2 contract into an unconstrained payload.
- **Decision:**
  - Application owns non-generic `ParallelIngestionExecutionPort`, a `typing.Protocol` with exactly one public operation: `async execute(self, plan: ParallelIngestionPlan) -> ParallelIngestionSuccess`.
  - There is no ABC, registry, factory, or concrete production executor in this chunk.
  - The port does not encode sequential vs parallel execution, `asyncio.gather`, `TaskGroup`, retries, cancellation, timeout, fallback, degraded mode, or partial success.
  - LangGraph remains `START → workflow_entry → END` and does not import or inject the port. `WorkflowState` remains unchanged. `FailurePolicyPort` remains unconnected. `AgentPort` remains unchanged.
  - A future concrete implementation and any failure/partial/degraded fan-in policy remain separately reviewed chunks. This ADR does not pick an execution strategy.
- **Consequences:** A later executor can implement the already-specific plan-to-success boundary without a generic payload bag. Graph wiring, Chief Orchestrator, and concurrency choice remain future work.

---

## ADR-048 — Phase 2 ingestion execution uses application-layer structured concurrency

- **Status:** Accepted
- **Context:** Chunks 35–37 published `ParallelIngestionPlan`, `ParallelIngestionExecutionPort`, and `ParallelIngestionSuccess`. The five Phase 2 agents already exist as application-layer services. Encoding this first executable slice inside LangGraph, or attaching retry/fallback/degraded unions to the first implementation, would freeze orchestrator policy before it is reviewed. Sequential execution would also hide the intended Phase 2 independence of the five branches.
- **Decision:**
  - Application owns concrete `ConcurrentParallelIngestionExecutor`. It structurally implements the already-published `ParallelIngestionExecutionPort`. It is not a generic executor framework, registry, or factory.
  - Constructor dependencies are exactly the five existing application agents: `WeatherAndRenewableForecastAgent`, `HydroResourcesAgent`, `GenerationAvailabilityAgent`, `NewsIntelligenceAgent`, and `MarketMonitoringAgent`. Source adapters, `FailurePolicyPort`, LangGraph, Redis, persistence, and n8n are not injected.
  - `execute` launches all five `agent.run(plan.<branch>)` calls inside one `asyncio.TaskGroup` before waiting for completion. This ADR scopes `TaskGroup` to this executor; it is not a platform-wide concurrency standard.
  - `ParallelIngestionSuccess` is returned only when all five branches succeed. Result DTO objects are preserved. Records are not merged, sorted, or rewritten.
  - Branch exceptions follow native TaskGroup cancellation and exception-group propagation. This slice does not retry, fall back, degrade, convert errors to empty results, or invent a partial-success aggregate.
  - LangGraph remains `START → workflow_entry → END` and does not import or invoke the executor. `WorkflowState` remains unchanged. `FailurePolicyPort` remains unconnected.
  - Graph join, failure/degraded fan-in contracts, retry/fallback execution, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Callers can run the five current ingestion agents concurrently behind the existing port without a graph runtime. Orchestrator wiring and failure policy remain future work. A later chunk may replace or wrap this executor if reviewed concurrency or policy requirements differ.

---

## ADR-049 — Phase 2 workflow payloads remain outside WorkflowState behind a typed context port

- **Status:** Accepted
- **Context:** Chunks 35–38 published `ParallelIngestionPlan`, `ParallelIngestionExecutionPort`, `ConcurrentParallelIngestionExecutor`, and `ParallelIngestionSuccess`. A future LangGraph node will need to start from `WorkflowState.workflow_id`, obtain the already-prepared plan, call the execution port, and record the all-five-success aggregate. Expanding the published seven-field `WorkflowState` with Phase 2 request/result bags, or introducing a generic dict/payload envelope, would collapse typed contracts into graph state and freeze storage policy before it is reviewed. Redis, PostgreSQL, and LangGraph checkpoint choices are not yet authorized for this seam.
- **Decision:**
  - Application owns non-generic `ParallelIngestionWorkflowContextPort`, a `typing.Protocol` with exactly two public operations: `async resolve_plan(self, workflow_id) -> ParallelIngestionPlan` and `async record_success(self, workflow_id, success: ParallelIngestionSuccess) -> None`.
  - `workflow_id` reuses the published `WorkflowState.workflow_id` type. Chunk 39 does not invent a new workflow-identity type.
  - `WorkflowState` remains the seven-field control snapshot. Plan and success objects are not embedded on it.
  - There is no generic payload dictionary, `Any`, `Mapping`, callback, exception object, or storage-specific method name.
  - The protocol does not choose in-memory, Redis, PostgreSQL, filesystem, cache, or LangGraph checkpoint storage. There is no concrete production implementation in this chunk.
  - LangGraph remains `START → workflow_entry → END` and does not import or inject the context port. The executor, `FailurePolicyPort`, and `create_app()` remain unwired.
  - A future context implementation and any graph-node wiring remain separately reviewed chunks. This ADR does not define missing-plan behavior, retry, fallback, or degraded semantics.
- **Consequences:** A later graph node can use workflow identity plus this typed port instead of stuffing Phase 2 payloads into `WorkflowState`. Concrete context storage, LangGraph Phase 2 join, and Chief Orchestrator remain future work.

---

## ADR-050 — Phase 2 workflow execution is composed in a framework-neutral application step

- **Status:** Accepted
- **Context:** Chunks 35–39 published `ParallelIngestionPlan`, `ParallelIngestionExecutionPort`, `ConcurrentParallelIngestionExecutor`, `ParallelIngestionSuccess`, and `ParallelIngestionWorkflowContextPort`. Callers still had to sequence resolve → execute → record themselves. Putting that composition into LangGraph, or mutating `WorkflowState` phase/status as part of the first composition, would freeze graph topology and routing policy before they are reviewed.
- **Decision:**
  - Application owns concrete `ParallelIngestionWorkflowStep`. It is a small application service, not a LangGraph node, not a generic workflow-step framework, and not the Chief Orchestrator.
  - Constructor dependencies are exactly `ParallelIngestionWorkflowContextPort` and `ParallelIngestionExecutionPort`. The five ingestion agents, `ConcurrentParallelIngestionExecutor`, `FailurePolicyPort`, LangGraph, Redis, PostgreSQL, and API objects are not injected.
  - The only public operation is `async run(self, state: WorkflowState) -> WorkflowState`. Successful execution is exactly `resolve_plan(state.workflow_id)` → `execute(plan)` → `record_success(state.workflow_id, success)`.
  - The original `WorkflowState` object is returned unchanged by identity. Phase, status, diagnostics, and all other fields are not mutated. A replacement snapshot is not constructed.
  - Failures from resolve, execute, or record propagate naturally. Remaining operations do not run after an earlier failure. There is no retry, fallback, degraded continuation, diagnostics append, or `FailurePolicyPort` consultation.
  - LangGraph remains `START → workflow_entry → END` and does not import or invoke the step. Graph integration, phase/status transition, concrete context storage, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Application callers can run one typed Phase 2 workflow step without a graph runtime. Orchestrator wiring and control-state transitions remain future work.

---

## ADR-051 — LangGraph invokes Phase 2 through an injected workflow step

- **Status:** Accepted
- **Context:** Chunk 40 published framework-neutral `ParallelIngestionWorkflowStep`. The graph was still `START → workflow_entry → END` and invoked no Phase 2 work. Expanding `WorkflowState`, importing the executor or five agents into `graph.py`, or adding phase/status transitions in the first graph wiring would freeze storage and routing policy before they are reviewed.
- **Decision:**
  - `build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep)` requires the Phase 2 step through keyword-only dependency injection. The factory does not instantiate the step, a context implementation, `ConcurrentParallelIngestionExecutor`, or any ingestion agent.
  - Topology for this slice is `START → workflow_entry → parallel_ingestion → END`. `workflow_entry` remains an async no-op. `parallel_ingestion` awaits `parallel_ingestion_step.run(state)` and returns that `WorkflowState`.
  - LangGraph depends only on the framework-neutral step for Phase 2. Lower-level execution and context dependencies remain behind the step.
  - `WorkflowState` remains the published seven-field snapshot. The graph performs no phase/status mutation.
  - Failures from the step propagate from `ainvoke`. There is no retry, fallback, degraded continuation, diagnostics append, or `FailurePolicyPort` consultation.
  - Concrete context storage, API/composition wiring, Phase 2 join as phase-complete routing, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Callers who can construct `ParallelIngestionWorkflowStep` can run Phase 2 through LangGraph on the all-success path. Production still has no context implementation and no `create_app()` graph wiring.

---

## ADR-052 — Successful Phase 2 control-state transition stays outside WorkflowState and LangGraph

- **Status:** Accepted
- **Context:** Chunks 40–41 published `ParallelIngestionWorkflowStep` and wired it into LangGraph as `START → workflow_entry → parallel_ingestion → END`. The step still returns the original `WorkflowState` unchanged. Putting `advance()` methods on the snapshot DTO would mix transition policy into a frozen identity record. Putting the first phase movement inside `graph.py` would freeze routing and graph topology before they are reviewed. A generic workflow-transition framework, registry, or state-machine library would over-abstract one Phase-2-specific replacement.
- **Decision:**
  - Application owns `advance_after_parallel_ingestion(state: WorkflowState) -> WorkflowState` in `parallel_ingestion_transition.py`. It is one Phase-2-specific function, not a method on `WorkflowState`, not a Protocol, not a factory, and not a generic state machine.
  - The function is valid only when `state.phase is WorkflowPhase.INGESTION` and `state.status is WorkflowStatus.RUNNING`. Any other phase or status fails closed as existing `InvalidRequestError` with a stable sanitized message that does not include workflow identity, correlation ID, diagnostics, or exception internals.
  - A valid call returns a **new** frozen `WorkflowState` with `phase = WorkflowPhase.FORECASTING` and `status = WorkflowStatus.RUNNING`. Replacement uses `dataclasses.replace`. The input object is not mutated. `workflow_id`, `portfolio_id`, `delivery_date`, `correlation_id`, and `diagnostics` are preserved exactly. Diagnostics are neither appended nor cleared. No Phase 3 payload is derived.
  - `WorkflowState` remains the published seven-field snapshot and gains no `advance()` / `transition()` helpers. `WorkflowPhase` and `WorkflowStatus` members are unchanged.
  - LangGraph remains `START → workflow_entry → parallel_ingestion → END`. `ParallelIngestionWorkflowStep` still returns the original state. Graph wiring of this transition, Phase 3 execution, general status lifecycle (pending/succeeded/failed), retry/fallback, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Application callers can apply the successful Phase 2 control-state transition without a graph runtime. Production still has no LangGraph invocation of the transition and no Phase 3 routing.

---

## ADR-053 — LangGraph applies the published Phase 2 success transition in a thin node

- **Status:** Accepted
- **Context:** Chunk 42 published `advance_after_parallel_ingestion` outside `WorkflowState` and outside LangGraph. Chunk 41 still ended after `parallel_ingestion`. Inlining the replacement in `graph.py`, injecting the transition as a new factory dependency, or adding a Phase 3 forecasting node would mix policy, ports, and later routing into one slice.
- **Decision:**
  - Topology is `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`.
  - `parallel_ingestion_success_transition` is a thin async node whose only application behavior is `advance_after_parallel_ingestion(state)` and return of that `WorkflowState`. It does not reimplement preconditions, `dataclasses.replace`, or phase/status assignment.
  - `build_workflow_graph(*, parallel_ingestion_step: ParallelIngestionWorkflowStep)` is unchanged as a factory signature. The transition is pure application policy, not an injected port.
  - The workflow step still sees the original `ingestion`/`running` snapshot. The transition runs only after that step returns successfully. A successful graph path ends at `forecasting`/`running` and does not execute Phase 3.
  - If `ParallelIngestionWorkflowStep.run` raises, the transition node does not run. The exception propagates without retry, fallback, catch, or status mutation. An invalid state reaching the transition still raises the published `InvalidRequestError`.
  - Conditional edges, five-phase routing, retry/degraded fan-in, checkpointer/store, Chief Orchestrator, and API/composition wiring remain separately reviewed chunks.
- **Consequences:** Callers who can construct `ParallelIngestionWorkflowStep` can run the all-success Phase 2 path through LangGraph and receive a `forecasting`/`running` snapshot. Production still has no concrete context implementation and no Phase 3 agents.

---

## ADR-054 — Process-local in-memory workflow context is local/dev reference infrastructure

- **Status:** Accepted
- **Context:** Chunk 39 published `ParallelIngestionWorkflowContextPort` without choosing storage. Fixture-driven workflow execution and offline orchestration tests need a deterministic adapter before Redis or PostgreSQL is reviewed. Putting that adapter in application would mix a storage choice into the port owner. Wiring it into LangGraph or `create_app()` would freeze composition before a production store is chosen.
- **Decision:**
  - Infrastructure owns `InMemoryParallelIngestionWorkflowContext` in `infrastructure/orchestration/parallel_ingestion_context.py`. It structurally implements the published port and does not inherit it, an ABC, or a generic repository/UoW.
  - The constructor accepts `plans: Mapping[str, ParallelIngestionPlan]`, copies that mapping, and keeps the supplied plan objects by identity. Plans are not derived from `portfolio_id`, delivery date, environment, or providers.
  - `resolve_plan` returns the stored plan for a known workflow ID. An unknown identity fails closed as existing `ResourceNotFoundError` with a stable sanitized message that does not echo workflow identity or plan contents. No default plan is invented.
  - `record_success` stores the first `ParallelIngestionSuccess` for a workflow ID. Equal retries, compared by value, are idempotent no-ops and retain the originally stored object. A different success for the same identity is existing `ConflictError` with a stable sanitized message. There is no last-write-win and no merge.
  - An infrastructure-local `asyncio.Lock` serializes check-and-write inside one process. This is not threading, multiprocessing, Redis locking, or database CAS. There is no durability or cross-process guarantee.
  - Public operations remain only `resolve_plan` and `record_success`. Redis, PostgreSQL, CachePort, filesystem, graph wiring, and API/composition wiring remain separately reviewed chunks.
- **Consequences:** Local/dev and offline tests can resolve prepared plans and record all-five-success output without a database. Production still has no durable workflow-context implementation and no Chief Orchestrator composition root.

---

## ADR-055 — Terminal Phase 2 failure control-state transition stays outside WorkflowState and LangGraph

- **Status:** Accepted
- **Context:** Chunk 42 published the successful Phase 2 replacement `ingestion`/`running` → `forecasting`/`running`. Chunk 43 wired that success path into LangGraph. Chunk 29 still owns only a decision hook (`FailureAction.FAIL`); nothing yet records a terminal failed snapshot. Putting `fail()` methods on `WorkflowState` would mix transition policy into a frozen identity record. Catching graph exceptions, consulting `FailurePolicyPort`, or mapping runtime errors into `AdapterDiagnostic` values would freeze routing, policy execution, and diagnostic authorship before those concerns are reviewed. A generic workflow-transition framework, registry, or state-machine library would collapse two Phase-2-specific policies into an over-abstracted engine.
- **Decision:**
  - Application owns `fail_parallel_ingestion(state: WorkflowState) -> WorkflowState` in `parallel_ingestion_failure_transition.py`. It is one Phase-2-specific function, not a method on `WorkflowState`, not a Protocol, not a factory, and not a generic state machine. It stays separate from `advance_after_parallel_ingestion`.
  - The function is valid only when `state.phase is WorkflowPhase.INGESTION` and `state.status is WorkflowStatus.RUNNING`. Any other phase or status fails closed as existing `InvalidRequestError` with a stable sanitized message that does not include workflow identity, correlation ID, diagnostics, or exception internals. A previously failed snapshot cannot be failed again through this function.
  - A valid call returns a **new** frozen `WorkflowState` with `phase = WorkflowPhase.INGESTION` and `status = WorkflowStatus.FAILED`. Phase remains ingestion because this is a terminal outcome of the current Phase 2 attempt, not a progression into forecasting. Replacement uses `dataclasses.replace`. The input object is not mutated. `workflow_id`, `portfolio_id`, `delivery_date`, `correlation_id`, and `diagnostics` are preserved exactly.
  - Diagnostics remain untouched because converting runtime failures into canonical diagnostics is a separate orchestration concern and has not been specified. The function does not accept an exception or error argument.
  - `FailurePolicyPort` remains a decision hook only. A future execution layer may call this transition after deciding `FailureAction.FAIL`; Chunk 45 does not integrate that hook, execute retries or fallbacks, or continue into Phase 3.
  - `WorkflowState` remains the published seven-field snapshot and gains no `fail()` / `mark_failed()` / `transition()` helpers. `WorkflowPhase` and `WorkflowStatus` members are unchanged.
  - LangGraph remains `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`. If `ParallelIngestionWorkflowStep` raises, the exception still propagates without catch, failure node, or status mutation. Graph wiring of this transition, exception mapping, retry/fallback execution, degraded fan-in, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Application callers can apply a terminal Phase 2 failure snapshot without a graph runtime. Production still has no LangGraph failure handling, no retry/fallback execution, and no complete failure-handling workflow.

---

## ADR-056 — Phase 2 failure-policy decision stays separate from context construction and action execution

- **Status:** Accepted
- **Context:** Chunk 29 published `FailureAction`, `FailurePolicyContext`, and `FailurePolicyPort.decide`. Chunk 45 published `fail_parallel_ingestion` as a terminal control-state replacement. Nothing yet composed those seams for Phase 2. Folding exception inspection, policy decision, and action execution into one service would freeze three independently reviewable concerns: how a runtime failure becomes a sanitized context, which action the policy chooses, and whether that action retries, falls back, or applies `fail_parallel_ingestion`. Wiring that composition into LangGraph now would also freeze catch/conditional routing before those nodes are specified. A general failure engine, registry, or concrete policy would over-abstract a Phase-2-specific decision boundary.
- **Decision:**
  - Application owns `ParallelIngestionFailureDecisionService` in `parallel_ingestion_failure_decision.py`. It is a concrete application service, not a Protocol, not an ABC, not a factory, and not a concrete `FailurePolicyPort` implementation.
  - The only constructor dependency is the published `FailurePolicyPort`. There is no concrete failure policy in this chunk. Tests use structural fakes that do not inherit the Protocol.
  - The only public operation is `async decide(self, context: FailurePolicyContext) -> FailureAction`. That name matches the published port operation. The caller must supply an already-valid published context object. The service does not accept `Exception`, `BaseException`, error strings, or `WorkflowState` for derivation, and it does not construct `FailurePolicyContext`.
  - `decide` awaits `FailurePolicyPort.decide(context)` exactly once and returns the produced `FailureAction` unchanged. `RETRY`, `FALLBACK`, and `FAIL` all pass through without branching, remapping, retry counters, delays, fallback targets, or a call to `fail_parallel_ingestion`.
  - If the injected policy raises an existing application exception, that exception propagates unchanged. The service does not catch, translate, retry, or return a default action. No new exception class is introduced.
  - `fail_parallel_ingestion` remains a separate Chunk 45 operation. A future action-execution chunk may apply it only after this service returns `FailureAction.FAIL`.
  - LangGraph remains `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`. This service is not imported or called by `graph.py`, `parallel_ingestion_workflow.py`, or the terminal-failure transition. Runtime Phase 2 exceptions still propagate. Exception-to-context mapping, action execution, retry/fallback, degraded fan-in, concrete policy, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Application callers can obtain a Phase 2 failure-policy decision from a prepared context without executing that decision. Production still has no exception-to-context mapping, no action execution, no LangGraph failure routing, and no concrete policy.

---

## ADR-057 — Phase 2 failure-policy context construction stays separate from exception capture and policy decision

- **Status:** Accepted
- **Context:** Chunk 29 published `FailurePolicyContext` as a frozen sanitized DTO. Chunk 46 published `ParallelIngestionFailureDecisionService`, which requires an already-constructed context. Folding raw exception inspection, agent-identity guessing, `WorkflowState` extraction, and policy decision into one mapper would freeze independently reviewable concerns: how a runtime failure becomes sanitized typed facts, how those facts become `FailurePolicyContext`, and which `FailureAction` the policy chooses. Parallel Phase 2 fan-out also has no verified rule for which of the five agents failed; inventing `"parallel_ingestion"` or defaulting to Chief Orchestrator would fabricate identity. Graph exception capture remains unspecified.
- **Decision:**
  - Application owns `build_parallel_ingestion_failure_policy_context` in `parallel_ingestion_failure_context.py`. It is one synchronous Phase-2-specific function, not a service class, Protocol, factory, registry, or generic mapper.
  - Keyword-only parameters are a one-for-one source for the published `FailurePolicyContext` fields: `phase: WorkflowPhase`, `error_code: str`, `attempt_number: int`, and `agent_name: AgentName | None = None`. The published optional default for `agent_name` is preserved; omitting it yields `None` rather than a fabricated identity.
  - The function calls the published `FailurePolicyContext(...)` constructor once and returns that object. Existing `__post_init__` validation runs unchanged. The builder does not duplicate strip/type/range checks, increment attempt counters, or infer `FailureAction`.
  - The function does not accept `Exception`, `BaseException`, traceback, `ExceptionGroup`, or raw messages. It does not inspect exception class, `repr`, cause chains, or stack traces. The caller supplies the already-sanitized `error_code`.
  - The function does not accept `WorkflowState`. Control facts required by the published context are passed explicitly. Parallel-ingestion failing-branch identification remains a separately reviewed concern.
  - `FailureAction`, `FailurePolicyContext`, and `FailurePolicyPort` remain unchanged. Chunk 46 still decides; Chunk 45 still owns the terminal transition. This function does not call either.
  - LangGraph remains `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`. Exception capture, graph wiring, action execution, retry/fallback, degraded fan-in, concrete policy, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Application callers can construct a published Phase 2 failure-policy context from typed facts without inspecting exceptions or executing policy. Production still has no graph failure capture, no exception-to-facts mapping, and no action execution.

---

## ADR-058 — Terminal Phase 2 FAIL action execution stays separate from decision and graph routing

- **Status:** Accepted
- **Context:** Chunk 29 published `FailureAction` as a closed decision set. Chunk 45 published `fail_parallel_ingestion` as the terminal control-state replacement. Chunk 46 published `ParallelIngestionFailureDecisionService`, which returns an already-decided `FailureAction` without executing it. Chunk 47 published context construction from sanitized facts. Folding action execution into the decision service, the context builder, or LangGraph would freeze independently reviewable concerns: which action the policy chooses, how that action is applied, and when graph catch/conditional routing exists. Silently treating `RETRY` or `FALLBACK` as a no-op would hide missing mechanics. Duplicating `fail_parallel_ingestion` inside an executor would split terminal-transition ownership.
- **Decision:**
  - Application owns `execute_parallel_ingestion_failure_action(*, state: WorkflowState, action: FailureAction) -> WorkflowState` in `parallel_ingestion_failure_action.py`. It is one synchronous Phase-2-specific function, not a service class, Protocol, registry, command bus, handler hierarchy, or generic action executor.
  - The function receives an already-decided `FailureAction`. It does not accept `FailurePolicyContext`, does not inject `FailurePolicyPort`, does not call `ParallelIngestionFailureDecisionService` or `build_parallel_ingestion_failure_policy_context`, and does not inspect `error_code`, `attempt_number`, `agent_name`, exceptions, or diagnostics.
  - `FailureAction.FAIL` returns `fail_parallel_ingestion(state)` unchanged. Chunk 45 remains the owner of phase/status preconditions, `dataclasses.replace`, identity/diagnostic preservation, and the sanitized invalid-state `InvalidRequestError`. This slice does not reimplement that transition.
  - `FailureAction.RETRY` and `FailureAction.FALLBACK` fail closed as existing `InvalidRequestError` with stable sanitized messages (`Parallel-ingestion retry action is not implemented.` / `Parallel-ingestion fallback action is not implemented.`). They do not retry, sleep, increment attempts, invoke another agent, return the input state, mark the workflow failed, or degrade.
  - Every currently published `FailureAction` member is handled explicitly. There is no silent default that returns success or original state. An unreachable assertion may exist only as a typing exhaustiveness guard.
  - LangGraph remains `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`. This function is not imported or called by `graph.py`, `parallel_ingestion_workflow.py`, the decision service, the context builder, or `fail_parallel_ingestion`. Runtime Phase 2 exceptions still propagate. Retry/fallback execution, graph failure routing, exception capture, and Chief Orchestrator remain separately reviewed chunks.
- **Consequences:** Application callers can apply a terminal Phase 2 `FAIL` decision without a graph runtime. Production still has no retry/fallback mechanics, no LangGraph failure routing, and no complete failure-handling workflow.

---

## ADR-059 — Prepared Phase 2 failure handling is composed before runtime exception routing

- **Status:** Accepted
- **Context:** Chunk 46 published `ParallelIngestionFailureDecisionService`, which returns an already-decided `FailureAction` without executing it. Chunk 47 published context construction from already-sanitized typed facts. Chunk 48 published `execute_parallel_ingestion_failure_action`, which applies terminal `FAIL` and rejects `RETRY` / `FALLBACK` as not implemented. Folding those steps into LangGraph, into exception capture, or into a generic orchestrator would freeze independently reviewable concerns: how sanitized facts become context, which action the policy chooses, how that action is applied, and when graph catch/conditional routing exists. Duplicating `FailureAction` branching or `fail_parallel_ingestion` inside a composition service would split ownership already assigned to Chunks 45 and 48.
- **Decision:**
  - Application owns `ParallelIngestionFailureHandlingService` in `parallel_ingestion_failure_handling.py`. It is one concrete Phase-2-specific service, not a Protocol, ABC, registry, factory, generic handler, or workflow framework.
  - Constructor injects exactly the published `ParallelIngestionFailureDecisionService`. Public operation is keyword-only `async handle(*, state: WorkflowState, context: FailurePolicyContext) -> WorkflowState`.
  - The caller supplies an already-built sanitized `FailurePolicyContext`. This service does not construct context, does not inspect exceptions, and does not invent an agent identity.
  - `handle` awaits `decide(context)` exactly once, then passes the returned `FailureAction` and the supplied `WorkflowState` to `execute_parallel_ingestion_failure_action`. Decision remains owned by `ParallelIngestionFailureDecisionService`. Action semantics remain owned by `execute_parallel_ingestion_failure_action`. Terminal state mutation remains owned by `fail_parallel_ingestion`.
  - The composition service adds no `FailureAction` branching, no retry/fallback loops, no diagnostics mutation, and no exception translation. Policy exceptions and published executor errors propagate unchanged.
  - Raw runtime failure interpretation remains deferred. LangGraph failure routing remains deferred. Retry/fallback execution remains deferred. This slice does not claim failure handling is complete.
  - LangGraph remains `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`. This service is not imported or called by `graph.py`. Runtime Phase 2 exceptions still propagate.
- **Consequences:** Application callers can compose an already-prepared Phase 2 failure path without a graph runtime. Production still has no exception capture, no sanitized-facts derivation from raw failures, no retry/fallback mechanics, no LangGraph failure routing, and no complete failure-handling workflow.

---

## ADR-060 — Phase 2 agent failures are attributed before TaskGroup aggregation

- **Status:** Accepted
- **Context:** `ConcurrentParallelIngestionExecutor` runs the five Phase 2 agents concurrently through `asyncio.TaskGroup`. Native TaskGroup propagation yields an `ExceptionGroup` whose leaves no longer identify which agent owned the failed task. Downstream policy context needs a canonical `AgentName`, but that identity is only known at the executor boundary. Interpreting the `ExceptionGroup`, mapping error codes, or wiring LangGraph catch/conditional edges in the same slice would freeze independently reviewable concerns.
- **Decision:**
  - Application owns `ParallelIngestionAgentFailure` in `parallel_ingestion_agent_failure.py`. It is one Phase-2-specific exception class, not a generic orchestration-failure hierarchy, DTO, or `WorkflowState` field.
  - Constructor input is exactly canonical `AgentName`. The outward message is a stable sanitized sentence that identifies that agent and does not include original exception text, repr, stack, vendor payload, or request/result contents.
  - The original Python failure is retained only through `raise ParallelIngestionAgentFailure(agent_name) from exc`. There is no custom public exception-payload field.
  - Each of the five executor tasks awaits one agent `run(...)` through an internal helper. Ordinary `Exception` failures are attributed. `asyncio.CancelledError` is a `BaseException` and is not wrapped, so sibling TaskGroup cancellation is not classified as agent failure.
  - `ParallelIngestionExecutionPort.execute` remains an all-success contract returning `ParallelIngestionSuccess`. Failure still propagates. This slice does not flatten or interpret `ExceptionGroup`, does not derive `error_code`, does not construct `FailurePolicyContext`, and does not invoke Chunk 46–49 policy/handling surfaces.
  - LangGraph remains `START → workflow_entry → parallel_ingestion → parallel_ingestion_success_transition → END`. Runtime Phase 2 exceptions still propagate from the graph.
- **Consequences:** Callers can recover which Phase 2 agent failed from an attributed leaf while TaskGroup aggregation remains native. Production still has no ExceptionGroup interpretation, no error-code mapping, no policy routing, no LangGraph failure catching, and no complete failure-handling workflow.

---

## ADR-061 — Attributed Phase 2 failures are extracted before classification

- **Status:** Accepted
- **Context:** Chunk 50 attributes ordinary Phase 2 agent failures as `ParallelIngestionAgentFailure` before `asyncio.TaskGroup` aggregates them. Native aggregation yields a possibly nested `ExceptionGroup` / `BaseExceptionGroup`. Folding leaf extraction together with error-code classification, primary-failure selection, attempt tracking, or LangGraph catch/conditional routing would freeze independently reviewable concerns. TaskGroup aggregation and failure classification are separate.
- **Decision:**
  - Application owns `extract_parallel_ingestion_agent_failures(failure: BaseExceptionGroup) -> tuple[ParallelIngestionAgentFailure, ...]` in `parallel_ingestion_exception_group.py`. It is one synchronous Phase-2-specific function, not a DTO, service class, Protocol, visitor, registry, or generic exception framework.
  - Chunk 50 remains the owner of task→agent attribution. Chunk 51 owns only deterministic extraction of already-attributed leaves from an already-created exception group.
  - Traversal is recursive over nested groups, depth-first and left-to-right, preserving native leaf encounter order. Exact original `ParallelIngestionAgentFailure` objects are returned. `__cause__` is not inspected or rewritten.
  - Multiple real failures are preserved. Two attributed leaves with the same `AgentName` are not collapsed, grouped, or sorted.
  - Any non-group leaf that is not `ParallelIngestionAgentFailure` fails closed as existing `InvalidRequestError` with a stable sanitized message. Unattributed leaves are not skipped and do not produce a partial tuple. A cancellation leaf supplied directly is unattributed; this does not redefine native TaskGroup sibling-cancellation behavior.
  - The function does not call `.split()`, `.subgroup()`, or `.derive()`, and does not rebuild exception groups.
  - Exception→`error_code` mapping, selection among multiple failures, attempt tracking, `FailurePolicyContext` construction, policy decision, action execution, diagnostics mutation, and LangGraph routing remain deferred.
- **Consequences:** Callers can recover the attributed Phase 2 leaves from a nested exception group without classifying them. Production still has no error-code mapping, no multi-failure selection policy, no retry/fallback mechanics, no LangGraph failure routing, and no complete failure-handling workflow.

---

## ADR-062 — Phase 2 failure classification produces sanitized facts before policy selection

- **Status:** Accepted
- **Context:** Chunk 50 attributes ordinary Phase 2 agent failures as `ParallelIngestionAgentFailure` with canonical `AgentName` before TaskGroup aggregation. Chunk 51 extracts those already-attributed leaves from a possibly nested exception group. Downstream `FailurePolicyContext` requires a stable sanitized `error_code` plus that agent identity, but exception text, class names, and tracebacks must never become policy facts. Folding one-leaf classification together with multi-failure selection, attempt tracking, `FailurePolicyContext` construction, or LangGraph catch/conditional routing would freeze independently reviewable concerns.
- **Decision:**
  - Application owns frozen `ParallelIngestionFailureFact` and synchronous `classify_parallel_ingestion_agent_failure(failure: ParallelIngestionAgentFailure) -> ParallelIngestionFailureFact` in `parallel_ingestion_failure_fact.py`. This is one Phase-2-specific DTO plus one classifier, not a generic exception framework, registry, factory, or policy service.
  - Chunk 50 remains the owner of task→agent attribution. Chunk 51 remains the owner of ExceptionGroup attributed-leaf extraction. Chunk 52 owns only sanitized classification of exactly one already-extracted leaf.
  - The fact fields are exactly canonical `AgentName` and a stable `error_code`. There is no exception object, message, traceback, attempt number, workflow state, diagnostic, retryable flag, severity, timestamp, or provider/vendor field.
  - When `failure.__cause__` is an `ApplicationError`, the published application error `code` is reused unchanged. There is no second mapping table for existing application errors.
  - Non-application causes and a missing `__cause__` collapse to one stable sanitized code: `parallel_ingestion_unexpected_failure`. Codes are never derived from Python exception class names, module names, messages, repr, traceback, or vendor type names.
  - The classifier inspects only `failure.__cause__`. It does not mutate the attribution wrapper or the chained cause. Exception text never appears on the fact.
  - Multi-failure selection, attempt tracking, `FailurePolicyContext` construction, policy decision, action execution, diagnostics mutation, and LangGraph routing remain deferred.
- **Consequences:** Callers can turn one attributed Phase 2 leaf into a sanitized `AgentName` + `error_code` fact without selecting among failures or invoking policy. Production still has no multi-failure selection policy, no attempt tracking, no exception-capture composition into `FailurePolicyContext`, no retry/fallback mechanics, no LangGraph failure routing, and no complete failure-handling workflow.

---

## ADR-063 — Tuple-level Phase 2 failure classification is a pure composition over one-leaf facts

- **Status:** Accepted
- **Context:** Chunk 50 attributes ordinary Phase 2 agent failures as `ParallelIngestionAgentFailure`. Chunk 51 extracts those already-attributed leaves from a possibly nested exception group. Chunk 52 classifies exactly one extracted leaf into sanitized `ParallelIngestionFailureFact`. Downstream multi-failure policy, if later approved, needs a sanitized fact tuple rather than raw exceptions. Folding tuple composition together with primary-failure selection, ranking, aggregation, attempt tracking, `FailurePolicyContext` construction, or LangGraph catch/conditional routing would freeze independently reviewable concerns.
- **Decision:**
  - Application owns synchronous `classify_parallel_ingestion_agent_failures(failures: tuple[ParallelIngestionAgentFailure, ...]) -> tuple[ParallelIngestionFailureFact, ...]` in `parallel_ingestion_failure_classification.py`. This is one Phase-2-specific composition helper, not a policy service, registry, factory, or generic exception framework.
  - Chunk 50 remains the owner of task→agent attribution. Chunk 51 remains the owner of ExceptionGroup attributed-leaf extraction. Chunk 52 remains the owner of one-leaf error-code classification. Chunk 53 owns only tuple-level composition of already-extracted attributed failures.
  - Each input element is classified by delegating to the existing `classify_parallel_ingestion_agent_failure`. Encounter order, cardinality, and duplicate agent identities are preserved. There is no sorting, deduplication, grouping, ranking, or aggregation.
  - An empty input tuple is valid and returns an empty output tuple. No failure is fabricated.
  - The composer does not inspect `__cause__`, exception messages, class names, or tracebacks, and does not maintain a second error-code mapping.
  - Primary-failure selection, multi-failure policy, attempt tracking, `FailurePolicyContext` construction, policy decision, action execution, diagnostics mutation, and LangGraph routing remain deferred. A later explicitly reviewed multi-failure policy may operate on this sanitized tuple boundary; this ADR does not invent that policy.
- **Consequences:** Callers can turn an attributed Phase 2 failure tuple into a sanitized fact tuple without selecting among failures or invoking policy. Production still has no multi-failure selection policy, no attempt tracking, no exception-capture composition into `FailurePolicyContext`, no retry/fallback mechanics, no LangGraph failure routing, and no complete failure-handling workflow.

---

## ADR-064 — Phase 2 multi-failure resolution uses an explicit selection boundary

- **Status:** Accepted
- **Context:** `asyncio.TaskGroup` can produce multiple simultaneous sanitized Phase 2 failure facts. Existing `FailurePolicyContext` carries one `error_code` and one optional agent identity. Embedding a winner rule into classification, context construction, exception handling, or LangGraph would couple independently reviewable concerns.
- **Decision:**
  - Application owns a Phase-2-specific, LangGraph-free, non-generic Protocol `ParallelIngestionFailureSelectionPort` in `parallel_ingestion_failure_selection.py`.
  - The only public operation is synchronous `select(facts: tuple[ParallelIngestionFailureFact, ...]) -> ParallelIngestionFailureFact`.
  - The port accepts already-sanitized `ParallelIngestionFailureFact` values only and resolves them to exactly one fact before a single-failure `FailurePolicyContext` can later be built.
  - Chunk 54 introduces no concrete implementation, no ABC, no registry, no factory, and no empty-tuple production default.
  - No first-element, last-element, agent-order, error-code, retryability, severity, frequency, majority, or aggregation winner rule is approved. Concrete selection semantics require separate architectural review.
- **Consequences:** Runtime composition gains a stable seam. Tests can use structural fakes without inheriting a production base. Production cannot silently choose among simultaneous failures until a later concrete-policy chunk. Attempt tracking, `FailurePolicyContext` runtime construction, and LangGraph failure routing remain separate deferred concerns.

---

## ADR-065 — Phase 2 attempt number is read through an explicit application boundary

- **Status:** Accepted
- **Context:** Existing `FailurePolicyContext` requires a 1-based `attempt_number`, but current runtime orchestration has no approved source for it. Attempt storage and retry mechanics must not leak into `WorkflowState`, failure classification, failure selection, context construction, or LangGraph nodes.
- **Decision:**
  - Application owns a Phase-2-specific, LangGraph-free, non-generic Protocol `ParallelIngestionAttemptNumberPort` in `parallel_ingestion_attempt_number.py`.
  - The only public operation is async `get_attempt_number(self, workflow_id: str) -> int`.
  - The port accepts only workflow identity and returns the current 1-based parallel-ingestion execution attempt. It is read-only, implementation-free, and storage-neutral.
  - Chunk 55 introduces no concrete implementation, no ABC, no registry, no factory, and no increment/reset/set/record write API.
  - Chunk 55 defines no mutation semantics, concurrency policy, maximum attempts, or durable backend. Concrete tracking requires separate architectural review.
- **Consequences:** Future runtime composition has an explicit seam for the attempt number. Later infrastructure may read from an appropriate store without changing application consumers. How attempts are initialized, when increment occurs, concurrency, reset, retry ownership, and durable implementation remain deferred.

---

## ADR-066 — Phase 2 failure-policy context assembly is a dedicated application composition

- **Status:** Accepted
- **Context:** Runtime failure preparation now has a sanitized fact tuple, an explicit selection boundary, an explicit attempt-number boundary, and an existing context builder. Without a dedicated composition service, future LangGraph code could improperly own selection, attempt lookup, and context construction.
- **Decision:**
  - Application owns Phase-2-specific, LangGraph-free `ParallelIngestionFailureContextResolutionService` in `parallel_ingestion_failure_context_resolution.py`.
  - Constructor injects exactly `ParallelIngestionFailureSelectionPort` and `ParallelIngestionAttemptNumberPort`.
  - The only public operation is keyword-only `async resolve(*, workflow_id: str, phase: WorkflowPhase, facts: tuple[ParallelIngestionFailureFact, ...]) -> FailurePolicyContext`.
  - The service delegates selection once, awaits attempt lookup once, delegates to existing `build_parallel_ingestion_failure_policy_context`, and returns `FailurePolicyContext`.
  - It does not implement selection, attempt tracking, failure-policy decision, action execution, exception inspection, or LangGraph coupling.
- **Consequences:** Future graph/runtime composition can remain thin. Concrete selector and attempt-number implementations remain independently swappable and independently reviewable. Runtime wiring remains a later chunk.

---

## ADR-067 — Phase 2 selection proceeds only when one sanitized failure is unambiguous

- **Status:** Accepted
- **Context:** Concurrent Phase 2 can yield zero, one, or multiple sanitized failure facts. The system has no approved business rule for choosing among simultaneous failures. Allowing first/last/native TaskGroup order to determine policy context would introduce accidental semantics.
- **Decision:**
  - Application owns LangGraph-free `StrictSingleParallelIngestionFailureSelector` in `parallel_ingestion_strict_single_failure_selector.py`.
  - The class satisfies existing `ParallelIngestionFailureSelectionPort` structurally and does not inherit the Protocol.
  - Exactly one sanitized fact is returned as the same instance. Zero facts fail closed. Multiple facts fail closed.
  - Empty and multi-fact inputs raise the same sanitized `InvalidRequestError`.
  - There is no ranking, deduplication, aggregation, first/last winner, agent/error/severity priority, or synthetic combined error.
- **Consequences:** The prepared failure pipeline can proceed for unambiguous single-agent failure cases. Multiple simultaneous failures remain unsupported and explicit. A future multi-failure policy requires separate architectural review and is not defined here. Attempt tracking and LangGraph failure routing remain later work.

---

## ADR-068 — The no-retry Phase 2 runtime resolves the initial attempt as one

- **Status:** Accepted
- **Context:** `FailurePolicyContext` requires an attempt number. The application now has an attempt-number port, but runtime retry execution and attempt tracking do not exist. Introducing mutable or persistent tracking before retries exist would design unsupported semantics.
- **Decision:**
  - Application owns LangGraph-free `InitialParallelIngestionAttemptNumberSource` in `parallel_ingestion_initial_attempt_number_source.py`.
  - The class satisfies existing `ParallelIngestionAttemptNumberPort` structurally and does not inherit the Protocol.
  - The method remains async `get_attempt_number(self, workflow_id: str) -> int`.
  - The source is stateless and returns exactly `1` for every workflow identity.
  - There is no increment, reset, persistence, per-workflow map, or retry ownership.
- **Consequences:** The existing single-failure application pipeline can construct a real `FailurePolicyContext` using concrete selection and concrete initial-attempt resolution. This source is intentionally insufficient for future retry execution. Retry-capable attempt tracking requires separate architectural review.

---

## ADR-069 — Phase 2 exception-group interpretation is composed inside application before runtime routing

- **Status:** Accepted
- **Context:** The application now has individually reviewed stages for attributed-leaf extraction, sanitized failure classification, and failure-context resolution. Future LangGraph runtime code should not duplicate or own these interpretation steps.
- **Decision:**
  - Application owns LangGraph-free `ParallelIngestionFailureContextPreparationService` in `parallel_ingestion_failure_context_preparation.py`.
  - Constructor injects an already-constructed `ParallelIngestionFailureContextResolutionService`.
  - Keyword-only `async prepare(*, workflow_id, phase, failure_group) -> FailurePolicyContext` accepts workflow identity, `WorkflowPhase`, and `BaseExceptionGroup`.
  - The service delegates extraction, tuple-level classification, and context resolution in that order.
  - It does not invoke failure policy, execute a failure action, or mutate `WorkflowState`.
- **Consequences:** Future runtime/LangGraph failure routing can call one application-level entry point. Exception interpretation remains application-owned and testable independently of LangGraph. Multi-failure selection, retries, and graph wiring remain separate reviewed concerns.

---

## ADR-070 — The current no-retry Phase 2 failure policy always terminates

- **Status:** Accepted
- **Context:** The application can now prepare a real `FailurePolicyContext`. However, retry execution does not exist, fallback execution does not exist, retry-capable attempt tracking does not exist, and retryability semantics are not approved. A concrete policy is required before runtime failure handling can be composed.
- **Decision:**
  - Application owns LangGraph-free `InitialParallelIngestionFailurePolicy` in `parallel_ingestion_initial_failure_policy.py`.
  - The class satisfies existing `FailurePolicyPort` structurally and does not inherit the Protocol.
  - The method remains async `decide(self, context: FailurePolicyContext) -> FailureAction`.
  - The policy is stateless and returns exactly `FailureAction.FAIL` for every valid context.
  - It does not branch on phase, error code, attempt number, or agent.
- **Consequences:** The current single-failure application path now has a concrete, honest policy decision. The system does not silently pretend retries or fallback are supported. Future RETRY/FALLBACK behavior requires separate architectural review and supporting runtime mechanisms.

---

## ADR-071 — Phase 2 application failure handling is composed before LangGraph routing

- **Status:** Accepted
- **Context:** All current single-failure application components now exist independently: context preparation, a concrete initial policy, and existing handling/action execution. Without an outer application composition service, future graph code would have to orchestrate application internals itself.
- **Decision:**
  - Application owns LangGraph-free `ParallelIngestionFailureRuntimeHandlingService` in `parallel_ingestion_failure_runtime_handling.py`.
  - Constructor injects the published `ParallelIngestionFailureContextPreparationService` and `ParallelIngestionFailureHandlingService`.
  - Keyword-only `async handle(*, state: WorkflowState, failure_group: BaseExceptionGroup) -> WorkflowState` accepts the current snapshot and one exception group.
  - The service delegates context preparation, then existing failure handling, and returns the resulting `WorkflowState`.
  - It does not inspect exceptions, select failures, resolve attempts, decide actions directly, or depend on LangGraph.
- **Consequences:** The single-failure terminal path is executable entirely inside application code. Future LangGraph wiring can remain thin. Multi-failure selection and retry/fallback behavior remain separate concerns.

---

## ADR-072 — LangGraph captures Phase 2 exception groups at the workflow-step boundary and delegates terminal failure handling

- **Status:** Accepted
- **Context:** Chunk 61 published `ParallelIngestionFailureRuntimeHandlingService` as the outer application composition for Phase 2 `BaseExceptionGroup` handling. Without a narrow graph catch and route, successful Phase 2 still reached `FORECASTING` / `RUNNING`, while exception groups still escaped the graph. Duplicating preparation, selection, policy, or `fail_parallel_ingestion` inside `graph.py` would violate the already-published application ownership of those seams.
- **Decision:**
  - `build_workflow_graph` injects the published runtime failure handler through keyword-only dependency injection alongside `ParallelIngestionWorkflowStep`.
  - The graph factory does not construct the handler or any of its dependencies.
  - Node `parallel_ingestion` awaits the injected step and catches only `BaseExceptionGroup`. The exact group object and the original current `WorkflowState` are forwarded to `handle` exactly once.
  - Ordinary non-group exceptions continue to propagate and are not sent through the Phase 2 ExceptionGroup pipeline.
  - A Phase-2-specific conditional edge after `parallel_ingestion` routes `INGESTION` / `RUNNING` to `parallel_ingestion_success_transition` and `INGESTION` / `FAILED` to `END`.
  - Unexpected post-Phase-2 phase/status combinations fail closed as `InvalidRequestError`.
  - Lower-level failure interpretation stays outside `graph.py`.
- **Consequences:** The currently supported one-attributed-failure path can terminate at `INGESTION` / `FAILED` through LangGraph without expanding `WorkflowState` or adding a checkpointer, store, retry/fallback execution, multi-failure selector, diagnostics mapping, or Phase 3. Direct non-group failures retain existing propagation. Multi-failure selection and retry/fallback remain deferred.

---

## ADR-073 — Regulatory Intelligence composes canonical document retrieval with an agent-specific inference port

- **Status:** Accepted
- **Context:** Chunks 30–34 established five provider-neutral Phase 2 ingestion agents. Chunk 21 already published `DocumentVectorSearchPort` over already-embedded `DocumentVectorSearchQuery` values returning ranked `ExtractedDocumentChunk` tuples. Phase 5 now needs the first Regulatory Intelligence application slice. Introducing a Qdrant type, a generic `LLMPort`, query-text embedding, or hardcoded Armenian DAM rules on this first slice would couple the agent to a vendor, collapse distinct retrieval and interpretation seams, or invent unverified market constraints. Empty retrieval must not become fabricated enforceable limits.
- **Decision:**
  - The sixth concrete agent is Regulatory Intelligence Agent. It structurally satisfies `AgentPort[RegulatoryIntelligenceRequest, RegulatoryIntelligenceResult]` and does not inherit a base class.
  - Agent-specific request/result remain frozen application DTOs. `RegulatoryIntelligenceRequest` carries only `search_query: DocumentVectorSearchQuery`. `RegulatoryIntelligenceResult` contains only `constraints: tuple[RegulatoryConstraint, ...]`. Canonical domain type remains existing `RegulatoryConstraint`; it is not shadowed or wrapped.
  - Existing `DocumentVectorSearchPort` is reused. No Qdrant client, collection, score, point ID, or payload type enters the agent. Query-text embedding remains outside this chunk; the caller supplies an already-constructed search query.
  - `RegulatoryConstraintInferencePort` is a narrow application-owned, agent-specific Protocol. `infer` is keyword-only and accepts only `chunks: tuple[ExtractedDocumentChunk, ...]`, returning canonical `RegulatoryConstraint` tuples. It is not a generic `LLMPort`, prompt catalog, or provider hierarchy.
  - Empty retrieval is fail-safe: `search` returning `()` yields `constraints=()` and does not invoke inference. The agent never constructs `RegulatoryConstraint` values itself, does not invent fallback constraints, and does not hardcode Armenian DAM gate times, bid envelopes, price caps, currencies, or license limits.
  - Existing application exceptions from retrieval or inference propagate unchanged. There is no new exception taxonomy and no silent empty-success conversion of inference failure.
  - No concrete inference provider, PDF/OCR, Qdrant composition, graph wiring, API wiring, persistence, retry/fallback execution, or verified Armenian rule extraction is added. No new dependency is added.
  - Weather, Hydro, Generation, News, Market, and Regulatory are not generalized into a shared agent base class, registry, factory, or RAG framework.
  - Canonical identity remains the existing `AgentName.REGULATORY_INTELLIGENCE` display value `Regulatory Intelligence Agent`.
- **Consequences:** The first Regulatory Intelligence application boundary is proven without vendor, LLM-SDK, or hardcoded-rule coupling. A future infrastructure/LLM adapter may satisfy `RegulatoryConstraintInferencePort` only after receiving already-normalized retrieved chunks. Actual RAG runtime, query-preparation composition, and contract-phase graph wiring remain separately reviewed work. Chunk 64 added a dedicated query-text embedding port; it is not wired into this agent.

---

## ADR-074 — Query-text embedding uses a dedicated application port separate from document-chunk embedding

- **Status:** Accepted
- **Context:** Chunk 63 accepts an already-constructed `DocumentVectorSearchQuery` and delegates it to `DocumentVectorSearchPort`. That query DTO requires a finite vector. Chunk 19 already published `DocumentEmbeddingPort` over `ExtractedDocumentChunk` values returning `DocumentChunkEmbedding` (`document_id`, `chunk_id`, `vector`). Broadening that document-chunk port to accept query text, or reusing `DocumentChunkEmbedding` / `DocumentVectorSearchQuery` as a query-embedding result, would collapse distinct use cases, invent fake document identity, or treat a search request as an embedding result. A generic `EmbeddingPort` / `LLMPort` would hide those differences behind a framework the application does not own.
- **Decision:**
  - Query-text embedding is a dedicated application-owned Protocol: `DocumentQueryEmbeddingPort.embed_query(query_text: str) -> DocumentQueryEmbedding`.
  - Document-chunk embedding remains `DocumentEmbeddingPort`. Query embedding does not inherit it, does not accept `ExtractedDocumentChunk`, and does not search or index.
  - Query text and document chunks are separate application use cases. Normalized query text is not a document chunk. Document chunks are not query text.
  - Provider, model, credentials, token limits, HTTP clients, and Qdrant types stay outside application. There is no concrete embedding implementation in this chunk.
  - A generic embedding framework (`EmbeddingPort[T]`, `LLMPort`, `AIProviderPort`) is rejected.
  - Existing vector DTOs were inspected and not reused: `DocumentChunkEmbedding` is document-identity-specific; `DocumentVectorSearchQuery` is a search request (`vector` plus `limit`), not an embedding result. There was no provider-neutral finite-vector-only application value. Chunk 64 therefore introduces minimal frozen `DocumentQueryEmbedding` with exactly `vector: tuple[float, ...]`, using the already-published finite-tuple validation semantics.
  - Query-preparation composition (`DocumentQueryEmbedding` → `DocumentVectorSearchQuery`) remains deferred. Regulatory Intelligence still receives an already-built search query and is not injected with this port.
- **Consequences:** Callers can later compose query text → query embedding → search query without changing document-chunk embedding, vector search, or Regulatory Intelligence in this chunk. A future provider adapter may satisfy `DocumentQueryEmbeddingPort` structurally. No live embedding provider, RAG orchestration, or graph/API wiring is authorized here. Chunk 65 added `DocumentVectorSearchQueryPreparationService` as that composition. Chunk 66 added `RegulatoryIntelligenceQueryExecutionService` as the outer composition over that service plus the unchanged agent; neither is injected into Regulatory Intelligence.

---

## ADR-075 — Vector-search query construction is a narrow application composition over query embedding

- **Status:** Accepted
- **Context:** Chunk 64 published `DocumentQueryEmbeddingPort.embed_query(query_text) -> DocumentQueryEmbedding`. Chunk 63 Regulatory Intelligence still requires an already-constructed `DocumentVectorSearchQuery` (`vector` plus positive `limit`). Folding that construction into the Regulatory agent would make the agent accept raw query text, inject embedding, and stop being a retrieval-plus-inference composition. Invoking `DocumentVectorSearchPort` here would collapse query construction with retrieval. Inventing a new prepared-query DTO, default limit, query rewriting, or a generic RAG/embedding framework would add policy this repository does not own.
- **Decision:**
  - Query preparation is a narrow application-owned service: `DocumentVectorSearchQueryPreparationService`.
  - Constructor injects exactly `DocumentQueryEmbeddingPort`. The service does not inject vector search, Regulatory Intelligence, Qdrant, an LLM, cache, or a generic embedding abstraction.
  - Public operation is keyword-only `async prepare(*, query_text: str, limit: int) -> DocumentVectorSearchQuery`.
  - Sequence is fixed: await `embed_query(query_text)` exactly once, then construct existing `DocumentVectorSearchQuery(vector=embedding.vector, limit=limit)`. Query text is forwarded unchanged. Limit validation stays with the existing query contract. The service does not prevalidate, clamp, or default the limit.
  - The returned object remains existing `DocumentVectorSearchQuery`. No new prepared-query DTO, wrapper, provider/model/prompt/metadata, collection, score, filter, or correlation fields.
  - Search is not invoked. Regulatory Intelligence remains unchanged and still consumes a prebuilt `DocumentVectorSearchQuery`. This service is not injected into that agent.
  - Existing embedding and query-contract failures propagate unchanged. There is no fallback vector or fallback query.
  - Query rewriting, query expansion, tokenization, hybrid lexical/vector retrieval, default search limits, caching, retries, embedding providers, Qdrant wiring, and generic RAG machinery remain deferred.
- **Consequences:** Application callers can compose query text → query embedding → `DocumentVectorSearchQuery` without changing Chunk 63–64 contracts. Regulatory RAG is still not operational: no embedding provider, no graph/API wiring. Chunk 66 added `RegulatoryIntelligenceQueryExecutionService` as an outer composition over this service plus the unchanged Regulatory Intelligence Agent.

---

## ADR-076 — Regulatory query execution composes query preparation with the existing Regulatory Intelligence Agent

- **Status:** Accepted
- **Context:** Chunks 63–65 published query-text embedding, query preparation into `DocumentVectorSearchQuery`, and a Regulatory Intelligence Agent that still consumes that already-built query. Folding query text into the agent would change its typed retrieval-plus-inference boundary. Duplicating embedding, search, or inference inside a new use case would collapse distinct seams. A new request/result DTO or generic RAG/executor framework would invent policy this repository does not own.
- **Decision:**
  - Query execution is a narrow application-owned service: `RegulatoryIntelligenceQueryExecutionService`.
  - Constructor injects exactly `DocumentVectorSearchQueryPreparationService` and `RegulatoryIntelligenceAgent`. It does not inject embedding, search, or inference ports, Qdrant, an LLM, cache, graph, API, or a generic agent registry/executor.
  - Public operation is keyword-only `async execute(*, query_text: str, limit: int) -> RegulatoryIntelligenceResult`.
  - Sequence is fixed: await `prepare(query_text=query_text, limit=limit)` exactly once, construct existing `RegulatoryIntelligenceRequest(search_query=prepared_query)`, await `run(request)` exactly once, and return that `RegulatoryIntelligenceResult` unchanged.
  - The agent remains typed around `DocumentVectorSearchQuery`. Query text never enters the agent. No new DTO is introduced.
  - The service does not call `embed_query`, `.search(...)`, or inference. Those remain owned by query preparation and the agent.
  - Existing preparation and agent errors propagate unchanged. Preparation failure does not invoke the agent. Empty `constraints=()` remains legitimate success.
  - Embedding providers, inference providers, Qdrant/API composition, Phase 1 graph wiring, prompt catalogs, and generic RAG machinery remain deferred.
- **Consequences:** Application callers can compose query text + limit through real published services and the unchanged agent when dependencies are injected. This is application composition, not production RAG readiness. Chunk 67 added API-owned `build_regulatory_intelligence_query_execution` as the explicit object-construction root over the three published application ports.

---

## ADR-077 — Regulatory runtime wiring uses one explicit outer composition root instead of a generic DI framework

- **Status:** Accepted
- **Context:** Chunks 63–66 published the provider-neutral Regulatory path as separately constructed application objects. Tests already assembled that path by hand. Folding construction into the agent or query-execution service would mix object wiring with retrieval/inference policy. A generic container, registry, factory, or decorator DI framework would invent a composition product this repository does not own. Constructing embedding, search, or inference adapters inside the builder would couple the composition root to deferred providers.
- **Decision:**
  - Object construction belongs in the API composition root: `build_regulatory_intelligence_query_execution` in `energy_trading.api.composition`.
  - The builder is a narrow synchronous function. It accepts exactly the three already-published application ports and returns `RegulatoryIntelligenceQueryExecutionService`.
  - Provider instances are injected, not constructed. The builder does not read settings, environment variables, API keys, model names, or endpoints, and it performs no I/O.
  - Construction sequence is fixed: `DocumentVectorSearchQueryPreparationService`, then `RegulatoryIntelligenceAgent`, then `RegulatoryIntelligenceQueryExecutionService`. The builder does not call `.prepare`, `.run`, `.execute`, `.search`, `.infer`, or `.embed_query`.
  - Application does not import the outer builder. `create_app()` does not invoke it. `graph.py` remains unwired.
  - Generic containers, registries, factories, service locators, plugin discovery, and RAG/executor frameworks are rejected.
  - Concrete OpenAI query-embedding adapter construction, inference providers, Qdrant/API provider wiring, HTTP routes, and Phase 1 LangGraph nodes remain deferred from this builder.
- **Consequences:** Callers can assemble the published Regulatory application stack consistently from three port implementations. This is object composition, not production RAG deployment. Chunk 68 added an infrastructure OpenAI query-embedding adapter that can later be injected behind `DocumentQueryEmbeddingPort` without changing this builder.

---

## ADR-078 — OpenAI query embedding is implemented as an infrastructure adapter behind the existing application port

- **Status:** Accepted
- **Context:** Chunk 64 published provider-neutral `DocumentQueryEmbeddingPort`. Chunk 67 published an outer composition root that accepts a concrete implementation of that port. Folding OpenAI types into application would couple Regulatory Intelligence to a vendor SDK. A generic `EmbeddingPort` / `LLMPort` / LiteLLM framework would invent an abstraction this repository does not own. Constructing `AsyncOpenAI` inside the adapter or `create_app()` would mix client lifecycle and secrets with Anti-Corruption conversion.
- **Decision:**
  - Provider decision for query-text embedding is OpenAI.
  - Official async SDK `openai` (`AsyncOpenAI`) is used. The adapter calls `await client.embeddings.create(...)` with `encoding_format="float"`.
  - `OpenAIDocumentQueryEmbeddingAdapter` lives in `energy_trading.infrastructure.embeddings`. It structurally satisfies `DocumentQueryEmbeddingPort` without inheriting it.
  - The adapter injects an already-constructed `AsyncOpenAI` client and an explicit model string. It does not load API keys, read settings, or construct the client.
  - Valid query text is forwarded unchanged. Empty/whitespace-only text is `InvalidRequestError` before any provider call, without echoing the query.
  - Provider responses convert immediately to canonical `DocumentQueryEmbedding` (`tuple` of floats). OpenAI response types do not enter application.
  - `OpenAIError` and subclasses become sanitized `DependencyUnavailableError`. Malformed provider data (empty/multiple embeddings, invalid vectors) is the same dependency failure. Exception chaining follows existing infrastructure adapters (`from exc`) while the application-visible message stays static.
  - No generic embedding/LLM framework, no Qdrant coupling, no retry loop, no dimensions/model fallback, and no `create_app()` / LangGraph / Chunk 67 builder wiring.
- **Consequences:** Application remains OpenAI-independent. Callers can inject the adapter behind the published port when they own client lifecycle. This is not production RAG deployment.

---

## ADR-079 — OpenAI Regulatory constraint inference is an infrastructure adapter behind the agent-specific application port

- **Status:** Accepted
- **Context:** Chunk 63 published provider-neutral `RegulatoryConstraintInferencePort`. Chunk 67 published an outer composition root that accepts a concrete implementation of that port. Folding OpenAI types into the Regulatory Intelligence Agent would couple application to a vendor SDK. A generic `LLMPort` / RAG framework / prompt catalog would invent an abstraction this repository does not own. Hardcoding Armenian DAM rules would violate the unverified-market constraint. Constructing `AsyncOpenAI` inside the adapter or `create_app()` would mix client lifecycle and secrets with Anti-Corruption conversion.
- **Decision:**
  - Provider decision for Regulatory constraint inference is OpenAI, behind the existing agent-specific `RegulatoryConstraintInferencePort`. No generic `LLMPort` is introduced.
  - `OpenAIRegulatoryConstraintInferenceAdapter` lives in `energy_trading.infrastructure.regulatory`. It structurally satisfies the published port without inheriting it.
  - The adapter injects an already-constructed `AsyncOpenAI` client and an explicit model string. It does not load API keys, read settings, or construct the client.
  - One non-empty `infer(*, chunks)` call uses the official Responses structured-output surface `await client.responses.parse(...)` with an infrastructure-local Pydantic envelope. Empty `chunks` returns `()` without a provider call.
  - Provider-local candidates carry the typed fields required to construct canonical `RegulatoryConstraint` plus `evidence_chunk_ids`. Evidence IDs are checked against the supplied normalized chunks before canonical conversion. Unknown IDs fail closed. `evidence_chunk_ids` is not added to the domain model.
  - Validated private candidates map explicitly to canonical `RegulatoryConstraint` in encounter order. Provider objects do not enter application. There is no ranking, merging, or invented defaults.
  - The adapter-local instruction is generic and evidence-bound. It does not contain Armenian DAM values, dates, limits, tariffs, or market-rule constants.
  - `OpenAIError` and unusable structured output (missing parsed result, refusal, invalid candidate, invalid canonical construction) become sanitized `DependencyUnavailableError`. Exception chaining follows existing infrastructure adapters (`from exc`) while the application-visible message stays static.
  - No Qdrant coupling, no retry loop, no prompt catalog, no generic RAG/LLM framework, and no `create_app()` / LangGraph / Chunk 67 builder wiring.
- **Consequences:** Application remains OpenAI-independent and still depends only on `RegulatoryConstraintInferencePort`. Callers can inject the adapter when they own client lifecycle. This is not production RAG deployment and does not claim verified Armenian rule extraction.

---

## ADR-080 — OpenAI client construction uses standalone typed settings and outer-layer lazy factory

- **Status:** Accepted
- **Context:** Chunks 68 and 69 published OpenAI adapters that inject an already-constructed `AsyncOpenAI` client. Folding client construction, API-key loading, or model selection into those adapters, `AppSettings`, `create_app()`, or the Chunk 67 Regulatory builder would mix secrets, provider lifecycle, and Anti-Corruption conversion. A generic LLM/provider registry or DI container would invent an abstraction this repository does not own. The pinned OpenAI SDK enables automatic retries by default; a second hidden retry policy inside provider plumbing would compete with application/orchestration retry ownership.
- **Decision:**
  - Typed `OpenAISettings` lives with the other service-specific settings in `energy_trading.shared.config`. The only field is required `api_key: SecretStr` (`ENERGY_OPENAI_`). There is no production default. Blank and whitespace-only values fail. Nonblank secrets are preserved. The value remains masked in `repr` / `str`.
  - `OpenAISettings` is separate from `AppSettings`. Process health and `create_app()` do not load it. Tests isolate local `.env` with `env_file=None`.
  - The settings module does not import the OpenAI SDK and holds no runtime client object.
  - Infrastructure `create_openai_client(settings: OpenAISettings) -> AsyncOpenAI` is a provider-specific lazy factory. It obtains the key only via `settings.api_key.get_secret_value()`, constructs `AsyncOpenAI(api_key=..., max_retries=0)`, and returns the client. Construction performs no network request and selects no model.
  - There is no global/module-level client. The factory does not own adapter or FastAPI lifecycle. Callers that construct a client must close it.
  - Provider adapters still do not construct the client, load environment variables, or read settings.
  - Model selection, base URL, organization, timeout, and retry/fallback mechanics remain outside this settings object and factory.
  - Implicit SDK retries are disabled (`max_retries=0`) so application orchestration retains retry ownership. This is not an implementation of retry logic.
  - `create_app()`, LangGraph, and `build_regulatory_intelligence_query_execution` remain unwired to OpenAI settings and the factory. Chunk 71's provider-aware builder receives an already-created client and does not call this factory.
- **Consequences:** Client construction capability exists offline. Production OpenAI runtime lifecycle and Regulatory RAG remain absent. Domain, application, and ML remain OpenAI-SDK-free. HTTP routes/`create_app()` remain OpenAI-SDK-free. The approved production OpenAI SDK allowlist is the published OpenAI adapters, this client-factory module, the two exact Regulatory API provider-composition modules (`api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`), and the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`).

---

## ADR-081 — Regulatory provider composition is a separate API-owned outer builder

- **Status:** Accepted
- **Context:** Chunk 67 published a provider-neutral Regulatory application builder that accepts already-constructed application ports. Chunks 68–70 published concrete OpenAI adapters and an OpenAI client factory. Folding OpenAI, Qdrant, settings, or client construction into the Chunk 67 builder would make application composition provider-aware. Folding that construction into agents, LangGraph, or domain would violate Clean Architecture. A generic provider registry, DI container, or runtime-settings DTO would invent an abstraction this repository does not own.
- **Decision:**
  - Provider-aware object composition lives in a separate API composition module: `build_regulatory_intelligence_provider_runtime` in `energy_trading.api.composition.regulatory_intelligence_runtime`.
  - Chunk 67 `build_regulatory_intelligence_query_execution` remains provider-neutral and does not import OpenAI, Qdrant, infrastructure adapters, settings, or client factories.
  - The provider-aware builder is synchronous and keyword-only. It receives already-created `AsyncOpenAI` and `AsyncQdrantClient` instances, existing `QdrantDocumentVectorConfig`, and two explicit model strings (`query_embedding_model`, `constraint_inference_model`).
  - It constructs exactly `OpenAIDocumentQueryEmbeddingAdapter`, `QdrantDocumentVectorSearch`, and `OpenAIRegulatoryConstraintInferenceAdapter`, then delegates application composition to `build_regulatory_intelligence_query_execution` exactly once and returns that service unchanged.
  - Clients are injected. The builder does not call `load_openai_settings`, `create_openai_client`, Qdrant settings loaders, or `create_qdrant_client`. It does not read environment variables or `.env`.
  - Model IDs remain explicit and separate at this composition boundary. They are not placed in `OpenAISettings` and are not inferred from task type.
  - Qdrant adapter configuration is the already-published `QdrantDocumentVectorConfig`. The builder does not create collections, indexes, distance metrics, or payload schemas.
  - Construction performs no provider I/O: no embed, search, infer, execute, run, health, collection, or close/aclose operations.
  - The builder owns no FastAPI lifespan, client lifecycle, or LangGraph wiring. `create_app()` remains unwired.
  - Application, agents, domain, and ML do not import the provider-aware builder. HTTP routes remain provider-SDK-free. The OpenAI/Qdrant SDK exception is limited to the two exact Regulatory API provider-composition modules (`api/composition/regulatory_intelligence_runtime.py` and `api/composition/regulatory_intelligence_configured_runtime.py`), the two exact document-index provider-composition modules (`api/composition/document_vector_index_runtime.py` and `api/composition/document_vector_index_configured_runtime.py`), plus existing approved infrastructure modules.
- **Consequences:** Concrete Regulatory provider object composition exists offline. Production settings loading, client lifecycle, HTTP invocation, LangGraph Phase 1 wiring, document extraction/indexing, and operational RAG remain absent.

---

## ADR-082 — Regulatory runtime configuration is use-case-specific and separate from provider connection settings

- **Status:** Accepted
- **Context:** Chunk 71's provider-aware builder requires an explicit query-embedding model, an explicit constraint-inference model, and existing `QdrantDocumentVectorConfig` (`collection_name`, `vector_size`). Folding those values into `OpenAISettings` would mix use-case model selection with the OpenAI API credential. Folding collection/vector targeting into `QdrantSettings` would mix Regulatory document-runtime identity with generic host/port/API-key connection settings. A generic runtime-settings hierarchy, model catalog, or settings→client DI container would invent an abstraction this repository does not own. Wiring settings into the Chunk 71 builder in this chunk would mix typed configuration with still-deferred client lifecycle.
- **Decision:**
  - Typed `RegulatoryIntelligenceRuntimeSettings` lives in `energy_trading.shared.config` beside the other service-specific settings objects.
  - The object owns exactly four fields: `query_embedding_model`, `constraint_inference_model`, `qdrant_collection_name`, and `qdrant_vector_size`.
  - The environment prefix is dedicated: `ENERGY_REGULATORY_`. Exact variables are `ENERGY_REGULATORY_QUERY_EMBEDDING_MODEL`, `ENERGY_REGULATORY_CONSTRAINT_INFERENCE_MODEL`, `ENERGY_REGULATORY_QDRANT_COLLECTION_NAME`, and `ENERGY_REGULATORY_QDRANT_VECTOR_SIZE`.
  - Model identifiers belong here, not in `OpenAISettings`. Collection name and vector size belong here, not in generic `QdrantSettings`.
  - All four fields are required with no production defaults. String fields strip whitespace and reject blank/whitespace-only values. Vector size must be a strictly positive integer and is not inferred from the embedding model.
  - The two model fields may hold the same value. They remain separate configuration fields.
  - The settings module is SDK-free and runtime-object-free. It does not import OpenAI or Qdrant clients, does not construct `QdrantDocumentVectorConfig`, and does not call Chunk 67 or Chunk 71 builders.
  - `load_regulatory_intelligence_runtime_settings(*, env_file=...)` is uncached and separate from `AppSettings`. Process health and `create_app()` do not load it.
  - Generic configuration frameworks, model catalogs, provider registries, and settings aggregation DTOs are rejected.
- **Consequences:** Callers can load Regulatory runtime-specific values independently of provider connection settings. Production settings→client→runtime wiring, HTTP invocation, and operational RAG remain absent. Chunk 73 adapts an already-constructed settings object without loading environment values.

---

## ADR-083 — Regulatory runtime settings are adapted in a separate configured composition layer

- **Status:** Accepted
- **Context:** Chunk 72 published typed `RegulatoryIntelligenceRuntimeSettings` without constructing `QdrantDocumentVectorConfig` or calling Chunk 71. Folding that translation into the settings module would mix typed configuration with adapter config. Folding it into the Chunk 71 builder would change that explicit five-argument seam. Folding env loading, client factories, or FastAPI lifespan into the same function would mix still-deferred lifecycle with configuration-to-composition adaptation. A generic runtime abstraction, settings registry, or DI container would invent an abstraction this repository does not own.
- **Decision:**
  - Configured composition lives in a separate API composition module: `build_regulatory_intelligence_configured_runtime` in `energy_trading.api.composition.regulatory_intelligence_configured_runtime`.
  - Chunk 72 remains plain typed config. It still does not construct `QdrantDocumentVectorConfig`.
  - Chunk 71 remains unchanged. It still receives already-created clients, existing `QdrantDocumentVectorConfig`, and two explicit model strings.
  - The configured builder is synchronous and keyword-only. It receives already-created `AsyncOpenAI` and `AsyncQdrantClient` instances plus already-constructed `RegulatoryIntelligenceRuntimeSettings`.
  - It constructs exactly one `QdrantDocumentVectorConfig` from `settings.qdrant_collection_name` and `settings.qdrant_vector_size`, then calls `build_regulatory_intelligence_provider_runtime` exactly once with those clients, that config, and `settings.query_embedding_model` / `settings.constraint_inference_model`, and returns that service unchanged.
  - Clients remain injected. The builder does not call settings loaders, client factories, `os.getenv`, or `.env`. It does not construct OpenAI or Qdrant clients.
  - Vector size is not inferred from the embedding model. No score thresholds, filters, distance metrics, collection-creation options, or defaults are added.
  - The builder does not construct provider adapters, the query-preparation service, the Regulatory agent, or the query-execution service. Chunk 71 and Chunk 67 retain those responsibilities.
  - Construction performs no provider I/O and owns no client lifecycle, FastAPI lifespan, or LangGraph wiring. `create_app()` remains unwired.
  - The API provider-composition exception is exactly two modules: `regulatory_intelligence_runtime.py` and `regulatory_intelligence_configured_runtime.py`. It is not broadened to all `api/composition`. HTTP routes remain provider-SDK-free.
  - Generic runtime abstractions, provider registries, and DI containers are rejected.
- **Consequences:** Callers can supply injected clients plus typed Regulatory settings and receive a wired `RegulatoryIntelligenceQueryExecutionService`. Settings loading, client construction, client lifecycle, HTTP invocation, and operational RAG remain absent. Chunk 74 owns client lifetime separately from this adaptation seam.

---

## ADR-084 — Regulatory provider clients are owned by a narrow async managed-runtime boundary

- **Status:** Accepted
- **Context:** Chunk 73 can assemble a Regulatory query-execution service from already-created provider clients plus already-constructed `RegulatoryIntelligenceRuntimeSettings`, but callers still had to construct and close those clients themselves. Folding environment loading into that seam would mix configuration discovery with object composition. Folding FastAPI lifespan into the same function would couple a reusable resource owner to one HTTP framework. A generic DI container, resource registry, provider registry, or `ManagedRuntime[T]` would invent an abstraction this repository does not own. Direct `AsyncOpenAI` / `AsyncQdrantClient` construction in API composition would widen the provider-SDK allowlist beyond the two approved modules.
- **Decision:**
  - Resource lifetime lives in a separate Regulatory-specific API composition module: `managed_regulatory_intelligence_runtime` in `energy_trading.api.composition.regulatory_intelligence_managed_runtime`.
  - The callable is an async context manager (`contextlib.asynccontextmanager`) and is keyword-only. It receives already-loaded `OpenAISettings`, `QdrantSettings`, and `RegulatoryIntelligenceRuntimeSettings`.
  - It does not load environment values, accept an `env_file`, accept caller-supplied clients, or accept loose model/Qdrant arguments.
  - Clients are created through existing `create_openai_client` and `create_qdrant_client`. Direct SDK client constructors are not used. Direct OpenAI/Qdrant SDK type imports are not added to this module.
  - Cleanup is registered immediately after each successful client creation via `AsyncExitStack.push_async_callback(...close)` because both pinned clients expose async `close()`.
  - Service construction delegates exactly once to `build_regulatory_intelligence_configured_runtime`. Chunks 67, 71, and 73 retain object-composition responsibilities.
  - Expected cleanup order is LIFO: Qdrant then OpenAI, provided both were created. If Qdrant construction fails, the OpenAI client is still closed. If Chunk 73 fails, both created clients are closed. Consumer exceptions still close both clients and then propagate. If one cleanup raises, the other registered cleanup is still attempted and the cleanup exception is not suppressed.
  - Entering the context performs no provider I/O. The yielded service is constructed, not executed.
  - FastAPI lifespan, `create_app()`, HTTP routes, app state, and LangGraph remain unwired.
  - Generic lifecycle managers, DI containers, resource registries, and provider registries are rejected.
- **Consequences:** Callers can supply already-loaded typed settings and receive a lifecycle-owned `RegulatoryIntelligenceQueryExecutionService`. Settings loading, FastAPI integration, HTTP invocation, and operational RAG remain absent. Direct provider SDK API-composition imports remain limited to the existing two approved modules.

---

## ADR-085 — Regulatory settings loading is composed above the managed runtime

- **Status:** Accepted
- **Context:** Chunk 74 can own Regulatory provider-client lifetime from already-loaded `OpenAISettings`, `QdrantSettings`, and `RegulatoryIntelligenceRuntimeSettings`, but callers still had to invoke the three existing typed loaders themselves. Folding environment discovery into the managed runtime would mix configuration loading with resource lifetime. Folding FastAPI lifespan into the same function would couple a reusable settings-to-runtime seam to one HTTP framework. A generic settings aggregator, runtime manager, DI container, or provider registry would invent an abstraction this repository does not own. Direct `os.environ` / `dotenv` parsing in API composition would bypass the published loaders.
- **Decision:**
  - Settings loading lives in a separate Regulatory-specific API composition module: `loaded_regulatory_intelligence_runtime` in `energy_trading.api.composition.regulatory_intelligence_loaded_runtime`.
  - The callable is a keyword-only async context manager (`contextlib.asynccontextmanager`). It exposes one `env_file: str | Path | None = ".env"` argument matching the existing three loader contracts and forwards that exact value to each loader.
  - It calls `load_openai_settings`, `load_qdrant_settings`, and `load_regulatory_intelligence_runtime_settings` exactly once each, then delegates resource ownership and service construction to `managed_regulatory_intelligence_runtime`.
  - It does not instantiate settings classes as a substitute for loaders, construct clients, import OpenAI/Qdrant SDK types, call client factories, construct provider adapters, or invoke Chunks 73/71/67 directly.
  - Loader validation failures propagate unchanged. An earlier loader failure does not fabricate settings or enter the managed runtime. Managed-runtime entry failures and consumer exceptions propagate according to normal context-manager semantics. This layer adds no `try/except` translation or suppression.
  - Entering the context performs no provider I/O and does not call `.execute(...)`. The yielded object is the exact `RegulatoryIntelligenceQueryExecutionService` produced by Chunk 74.
  - FastAPI lifespan, `create_app()`, HTTP routes, app state, and LangGraph remain unwired.
  - Generic settings aggregators, runtime/lifecycle managers, DI containers, and provider registries are rejected.
- **Consequences:** Callers can supply an explicit settings source and receive a lifecycle-owned `RegulatoryIntelligenceQueryExecutionService`. FastAPI integration, HTTP invocation, LangGraph routing, document indexing, and operational RAG remain absent. Direct provider SDK API-composition imports remain limited to the existing two approved modules. Chunk 74 continues to own client creation and cleanup.

---

## ADR-086 — FastAPI lifecycle ownership is separated from Regulatory service exposure

- **Status:** Accepted
- **Context:** Chunk 75 can load typed Regulatory settings and own the managed runtime for an `async with` scope, but FastAPI process lifetime still had no dedicated seam. Installing that runtime into `create_app()` in the same slice would couple lifecycle ownership to HTTP application construction before the service-access mechanism is chosen. Storing the yielded service on `app.state`, yielding a Starlette lifespan-state dict, or inventing a generic lifespan/resource/DI framework would pre-commit a later architect-reviewed exposure path. Importing settings loaders, provider SDKs, or lower Regulatory layers in the FastAPI boundary would collapse Chunks 75/74/73/71/67.
- **Decision:**
  - FastAPI-compatible lifecycle ownership lives in a separate Regulatory-specific API composition module: `build_regulatory_intelligence_lifespan` in `energy_trading.api.composition.regulatory_intelligence_lifespan`.
  - The factory is synchronous and keyword-only. It reuses the existing Chunk 75 `env_file: str | Path | None = ".env"` contract and returns a callable compatible with FastAPI's `lifespan=` argument: `Callable[[FastAPI], AbstractAsyncContextManager[None]]`.
  - Constructing the returned callback loads no settings and enters no runtime. Only lifespan startup enters `loaded_regulatory_intelligence_runtime`; lifespan shutdown exits it through ordinary async-context-manager semantics.
  - The composed service yielded by Chunk 75 is intentionally unused. This boundary does not write it to `app.state`, does not yield a lifespan-state dictionary, does not create a request-state key, and does not invoke `.execute(...)` or provider operations.
  - The module may import FastAPI's application type and Chunk 75. It does not import settings loaders, settings objects, provider SDKs, client factories, adapters, or Chunks 74/73/71/67.
  - `create_app()` is unchanged and does not install this lifespan. HTTP routes, health, middleware, error handling, and LangGraph remain unwired.
  - Generic lifespan frameworks, service registries, DI containers, and resource managers are rejected.
- **Consequences:** FastAPI-compatible lifecycle ownership can be proven independently of service exposure. `create_app()` installation, the service-access mechanism, route/dependency wiring, LangGraph routing, and operational RAG remain deferred. Direct provider SDK API-composition imports remain limited to the existing two approved modules. Chunk 75 continues to own settings loading; Chunk 74 continues to own client lifetime.

---

## ADR-087 — Regulatory lifecycle is installed in the app factory before service exposure

- **Status:** Accepted
- **Context:** Chunk 76 defined a FastAPI-compatible Regulatory lifespan that owns Chunk 75 entry/exit without exposing the composed service. Leaving it unwired meant production process lifetime still did not own Regulatory clients. Folding settings, clients, or the query-execution service into `AppSettings` or `app.state` in the same slice would mix HTTP factory construction with provider configuration and pre-commit a service-access mechanism. A generic lifespan registry, DI container, or environment kill-switch would invent abstractions this repository does not own. Existing health/error tests must remain offline and must not require OpenAI/Qdrant credentials.
- **Decision:**
  - Production `create_app()` installs `build_regulatory_intelligence_lifespan()` as the default FastAPI `lifespan=` callback.
  - App construction remains lazy. Calling `create_app()` does not load OpenAI, Qdrant, or Regulatory settings and does not create provider clients. Those actions remain inside Chunk 75, entered only on lifespan startup.
  - A narrow keyword-only `lifespan` argument lets tests inject an explicit no-op/test callback. When that override is supplied, the production Chunk 76 builder is not called. There is no environment flag and no silent skip when settings are absent on the production path.
  - Provider-specific settings do not enter `AppSettings`. `create_app()` does not read OpenAI keys, Qdrant URLs, model names, collection names, or vector size.
  - The composed Regulatory service remains unexposed: no `app.state` key, no lifespan-state dictionary, no request-state mapping, no dependency provider, and no query execution on startup.
  - Generic lifespan frameworks, service registries, and DI containers are rejected.
- **Consequences:** Production FastAPI processes own Regulatory client lifetime through the existing Chunk 76/75/74 stack. HTTP handlers still cannot access the query-execution service. Route DTOs, dependency injection, LangGraph wiring, and operational RAG remain deferred. Transport tests stay credential-free by injecting the explicit no-op lifespan.

---

## ADR-088 — Regulatory service exposure is lifespan-scoped application state

- **Status:** Accepted
- **Context:** Chunk 77 installed the Regulatory FastAPI lifespan so production processes own provider-client lifetime, but the yielded `RegulatoryIntelligenceQueryExecutionService` remained unused. Adding a typed accessor, FastAPI `Depends`, request-state mapping, or HTTP route in the same slice would pre-commit a handler contract before the smallest exposure primitive exists. A global singleton, service registry, DI container, or generic app-state manager would invent abstractions this repository does not own. Leaving a closed service on `app.state` after teardown would retain a stale reference after Chunk 75 exits.
- **Decision:**
  - While the Regulatory lifespan is active, FastAPI `app.state.regulatory_intelligence_query_execution_service` holds the exact object yielded by `loaded_regulatory_intelligence_runtime`.
  - Identity is preserved. The object is not wrapped, cloned, proxied, reconstructed, or placed in a mapping.
  - The attribute does not exist before lifespan startup. A `try`/`finally` deletes it before the inner Chunk 75 context exits, including on body failure.
  - If Chunk 75 entry fails, the attribute is never assigned. If Chunk 75 teardown fails, the attribute is already gone when that failure propagates.
  - There is no global singleton, service registry, typed accessor, FastAPI dependency, request-state key, or HTTP route. `create_app()` does not write `app.state`.
  - The service is not invoked during startup or shutdown.
- **Consequences:** Request handlers still have no published way to retrieve the service. Route DTOs, dependency injection, LangGraph wiring, and operational RAG remain deferred. Lifespan-scoped identity on `app.state` is the only exposure primitive.

---

## ADR-089 — Regulatory request-time service access is a narrow API dependency boundary

- **Status:** Accepted
- **Context:** Chunk 78 stores the exact lifespan-managed `RegulatoryIntelligenceQueryExecutionService` on `app.state.regulatory_intelligence_query_execution_service` while the Regulatory lifespan is active. HTTP handlers still needed a published, typed way to read that object. A global singleton, service registry, DI container, generic state accessor, or production `Depends(...)`/route in the same slice would either invent abstractions this repository does not own or pre-commit an HTTP contract. Raising `HTTPException`, `AttributeError`, or `RuntimeError` from the accessor would leak transport or runtime internals into a request-time application boundary.
- **Decision:**
  - Request-time lookup is a dedicated API dependency function `get_regulatory_intelligence_query_execution_service(request: Request) -> RegulatoryIntelligenceQueryExecutionService`.
  - The accessor reads the exact published state key and returns that exact service identity. It does not wrap, proxy, clone, or reconstruct the object.
  - Missing or wrong-type state fails closed as existing `DependencyUnavailableError` with sanitized message `Regulatory Intelligence service is unavailable.` and published code `dependency_unavailable`. No new exception class is introduced. HTTP translation remains in the existing API mapping layer (503).
  - The accessor is read-only. It does not assign or delete application state, enter or exit lifecycle, load settings, construct clients, or invoke the service.
  - There is no global singleton, service registry, service locator, or generic DI container. Production code does not wrap the accessor in `Depends(...)` and does not add an HTTP Regulatory route.
- **Consequences:** Active FastAPI requests can resolve the lifespan-scoped service through a typed reader. Handlers, query DTOs, query execution, LangGraph wiring, and operational RAG remain deferred.

---

## ADR-090 — Regulatory HTTP contracts are API-owned projections of canonical application contracts

- **Status:** Accepted
- **Context:** Chunk 79 published a typed accessor for the lifespan-scoped query-execution service, but HTTP handlers still lacked a deliberate transport shape. Generating OpenAPI models from application dataclasses, reusing domain `RegulatoryConstraint` as a FastAPI `response_model`, or dynamically reflecting application fields would couple HTTP JSON to inner-layer types and invite provider or vector fields into the public contract. Adding a route, `Depends`, or mapper in the same slice would pre-commit execution before the transport contract exists.
- **Decision:**
  - API owns `RegulatoryIntelligenceQueryRequest` and `RegulatoryIntelligenceQueryResponse` in `api/schemas`.
  - The request DTO mirrors `RegulatoryIntelligenceQueryExecutionService.execute` (`query_text: str`, `limit: int`). Limit positivity follows existing `DocumentVectorSearchQuery` semantics. Query text is not stripped.
  - The response DTO mirrors `RegulatoryIntelligenceResult.constraints` through nested `RegulatoryConstraintResponse` fields already present on canonical `RegulatoryConstraint`. Provider configuration, scores, citations, and invented narrative fields are excluded.
  - Models are frozen with `extra="forbid"`. There is no dynamic DTO generation, generic mapper, or schema factory.
  - Transport and application contracts remain separate. No route, production `Depends`, accessor invocation, or `.execute` exists in this slice.
- **Consequences:** Future HTTP handlers can bind JSON to these DTOs without inventing business fields. Mapping orchestration, route installation, and query execution remain deferred.

---

## ADR-091 — Regulatory HTTP query route is a thin API boundary not installed in create_app()

- **Status:** Accepted
- **Context:** Chunk 80 published HTTP request/response DTOs and Chunk 79 published a typed request-time accessor for the lifespan-scoped query-execution service. HTTP still lacked a handler that binds those DTOs, resolves the service through FastAPI `Depends`, and projects canonical `RegulatoryConstraint` values. Installing that router in production `create_app()` in the same slice would expose an incomplete RAG surface before a separately authorized production-installation chunk. A generic mapper, route factory, service registry, or handler-local exception translation would invent abstractions this repository does not own.
- **Decision:**
  - API owns a dedicated `APIRouter` in `api/routers/regulatory_intelligence.py` with prefix `/regulatory-intelligence` and POST `/query`.
  - The handler accepts exactly `RegulatoryIntelligenceQueryRequest`, obtains `RegulatoryIntelligenceQueryExecutionService` through `Depends(get_regulatory_intelligence_query_execution_service)`, awaits `execute(query_text=request.query_text, limit=request.limit)` exactly once, and returns `RegulatoryIntelligenceQueryResponse`.
  - Canonical constraint fields are projected explicitly into existing `RegulatoryConstraintResponse`. Query text is not stripped. There is no handler-local `try`/`except`, provider logic, or reusable mapping abstraction.
  - Production `create_app()` does not import or `include_router` this router. Tests may install it on a test-only FastAPI application. Existing centralized API exception mapping remains the only HTTP translation path.
- **Consequences:** Isolated HTTP query behavior is proven. Production HTTP exposure remains incomplete. PDF/OCR, document indexing runtime, verified Armenian DAM rules, Regulatory LangGraph wiring, and Pricing & Sales remain deferred.

---

## ADR-092 — Regulatory Intelligence production router installation

- **Status:** Accepted
- **Context:** Chunk 81 published a thin Regulatory HTTP query router, but production `create_app()` still installed only health. Isolated tests could mount the endpoint; the production factory did not. Reconstructing the path, wrapping the accessor, moving provider setup into `create_app()`, or introducing a generic router registry would expand this composition slice.
- **Decision:**
  - Production `create_app()` imports the existing `router` from `api/routers/regulatory_intelligence.py` as `regulatory_intelligence_router` and includes it once with `prefix=resolved_settings.api_prefix`, the same prefix used by health.
  - The handler, DTOs, accessor, HTTP method, endpoint path, and mapping remain unchanged. No second prefix is added in `create_app()`.
  - Construction remains lazy. The existing keyword-only `lifespan` seam remains. The published lifespan still owns service lifecycle. `create_app()` still does not load Regulatory/OpenAI/Qdrant settings, construct clients, call composition builders, assign `app.state`, or invoke `.execute`.
- **Consequences:** `POST /api/v1/regulatory-intelligence/query` is reachable through the production factory when the default prefix is `/api/v1`. Execution still depends on the lifespan-scoped service. Offline tests can inject a no-op lifespan and keep health credential-free; missing service state maps to the published 503. Operational RAG, PDF/OCR, document indexing, verified Armenian DAM rules, Regulatory LangGraph wiring, and Pricing & Sales remain deferred.

---

## ADR-093 — OpenAI document chunk embedding infrastructure adapter

- **Status:** Accepted
- **Context:** Chunk 19 published `DocumentEmbeddingPort` and `DocumentChunkEmbedding` for already-normalized `ExtractedDocumentChunk` values. Query-text embedding already has a concrete OpenAI adapter, and Qdrant already implements indexing/search, but document-chunk vectors still lacked a provider implementation. Folding this adapter into Regulatory runtime composition, `create_app()`, LangGraph, extraction, or a generic embedding hierarchy would pre-commit an indexing pipeline this slice does not own.
- **Decision:**
  - Infrastructure owns `OpenAIDocumentEmbeddingAdapter` in `infrastructure/embeddings/openai_document_embedding.py`.
  - The adapter structurally implements `DocumentEmbeddingPort` without inheriting the Protocol. It injects `AsyncOpenAI` and an explicit model, calls `embeddings.create(..., encoding_format="float")`, forwards stored chunk text unchanged, copies canonical `document_id` / `chunk_id`, and returns `tuple[DocumentChunkEmbedding, ...]`.
  - Empty input returns `()` without a provider call. Provider cardinality mismatches, invalid vectors, and inconsistent dimensions fail closed as sanitized `DependencyUnavailableError`. `OpenAIError` is translated the same way as the query-embedding adapter. There is no retry, settings loading, client construction, or client lifecycle ownership.
  - The adapter remains unwired from `create_app()`, Regulatory runtime composition, LangGraph, document extraction, and Qdrant indexing.
- **Consequences:** Document-chunk embeddings can be produced offline behind the published application port. Operational indexing, PDF/OCR, verified Armenian corpus, Regulatory LangGraph wiring, and Pricing & Sales remain deferred.

---

## ADR-094 — Document vector index-entry preparation service

- **Status:** Accepted
- **Context:** Chunks 19–20 published `DocumentEmbeddingPort` and `DocumentVectorIndexEntry`, and Chunk 83 added a concrete document-chunk embedder. Callers still had no provider-neutral application step that embeds already-normalized chunks and pairs them into index entries. Folding that pairing into `DocumentVectorIndexPort.index()`, Qdrant, OpenAI adapter construction, FastAPI, or a generic indexing/RAG pipeline would pre-commit a write runtime this slice does not own.
- **Decision:**
  - Application owns `DocumentVectorIndexEntryPreparationService` in `application/orchestration/document_vector_index_entry_preparation.py`.
  - The service injects exactly `DocumentEmbeddingPort`. Keyword-only `async prepare(*, chunks) -> tuple[DocumentVectorIndexEntry, ...]` awaits `embed(...)` exactly once, forwards the original chunk tuple unchanged, preserves input order, and constructs existing `DocumentVectorIndexEntry` values from matching `(document_id, chunk_id)` identities.
  - Empty input delegates to the published embedding contract and returns `()`. Cardinality mismatch or identity mismatch fails closed as sanitized `DependencyUnavailableError` without exposing chunk text, identifiers, vectors, or provider details. Existing application errors from `embed(...)` propagate unchanged. There is no retry, fallback, sorting, deduplication, or `.index(...)`.
  - The service remains unwired from `create_app()`, Regulatory runtime composition, the OpenAI document embedding adapter, Qdrant indexing, LangGraph, and extraction.
- **Consequences:** Canonical index entries can be prepared offline behind the published embedding port. Operational document indexing, PDF/OCR, verified Armenian corpus, Regulatory LangGraph wiring, and Pricing & Sales remain deferred.

---

## ADR-095 — Document vector index execution service

- **Status:** Accepted
- **Context:** Chunk 84 can prepare canonical `DocumentVectorIndexEntry` values, and application already owns `DocumentVectorIndexPort.index(...)`. Callers still had no provider-neutral application composition that prepares once and indexes once. Injecting `DocumentEmbeddingPort` directly, reconstructing entries, calling Qdrant, or introducing a generic indexing pipeline would duplicate Chunk 84 and pre-commit a provider runtime this slice does not own.
- **Decision:**
  - Application owns `DocumentVectorIndexExecutionService` in `application/orchestration/document_vector_index_execution.py`.
  - The service injects exactly `DocumentVectorIndexEntryPreparationService` and `DocumentVectorIndexPort`. Keyword-only `async execute(*, chunks) -> None` awaits `prepare(...)` exactly once, forwards the original chunk tuple unchanged, then awaits `index(entries)` exactly once with the exact prepared tuple.
  - Empty input preserves the published contracts: `prepare(())` then `index(())`, both called once, returning `None`. Existing application errors from either dependency propagate unchanged. There is no retry, fallback, `embed(...)`, or `DocumentVectorIndexEntry` construction.
  - The service remains unwired from `create_app()`, Regulatory runtime composition, OpenAI adapters, Qdrant, LangGraph, and extraction.
- **Consequences:** Normalized chunks can be indexed through the published application composition without a provider runtime. Operational corpus ingestion, PDF/OCR, verified Armenian corpus, Regulatory LangGraph wiring, and Pricing & Sales remain deferred.

---

## ADR-096 — Provider-neutral document vector index execution composition

- **Status:** Accepted
- **Context:** Chunks 84 and 85 already provide provider-neutral preparation and execution services. Callers still had to assemble those services manually. Constructing OpenAI or Qdrant adapters, loading settings, or introducing a generic DI container would pre-commit a provider runtime this slice does not own.
- **Decision:**
  - API composition owns `build_document_vector_index_execution` in `api/composition/document_vector_index_execution.py`.
  - The builder is a synchronous keyword-only function over already-constructed `DocumentEmbeddingPort` and `DocumentVectorIndexPort`. It constructs one `DocumentVectorIndexEntryPreparationService` and one `DocumentVectorIndexExecutionService`, then returns that execution service.
  - Construction is inert: no `.embed`, `.prepare`, `.execute`, or `.index`; no settings/env; no client factories; no OpenAI or Qdrant imports. Existing application errors from later `execute` calls propagate unchanged through the published services.
  - The builder is exported from `api/composition/__init__.py`. It remains unwired from `create_app()`, Regulatory runtime composition, LangGraph, extraction, and concrete provider adapters.
- **Consequences:** Callers can assemble the published indexing stack from injected ports without a provider runtime. Operational corpus ingestion, PDF/OCR, verified Armenian corpus, Regulatory LangGraph wiring, and Pricing & Sales remain deferred. Chunk 87 later added provider-aware adapter construction above this builder.

---

## ADR-097 — Provider-aware document vector index composition

- **Status:** Accepted
- **Context:** Chunk 83 published `OpenAIDocumentEmbeddingAdapter`. Chunk 23 published `QdrantDocumentVectorIndex`. Chunk 86 published provider-neutral `build_document_vector_index_execution`. Callers still had to construct those adapters manually. Loading settings, constructing clients, owning lifecycle, or introducing a generic provider/DI framework would expand this slice beyond inert object composition.
- **Decision:**
  - API composition owns `build_document_vector_index_provider_runtime` in `api/composition/document_vector_index_runtime.py`.
  - The builder is a synchronous keyword-only function over already-created `AsyncOpenAI`, `AsyncQdrantClient`, existing `QdrantDocumentVectorConfig`, and an explicit `document_embedding_model` string.
  - It constructs one `OpenAIDocumentEmbeddingAdapter` with `client=` / `model=` and one `QdrantDocumentVectorIndex` with the published positional `(client, config)` constructor, then delegates exactly once to `build_document_vector_index_execution` and returns that `DocumentVectorIndexExecutionService`.
  - Construction is inert: no `.embed`, `.index`, or `.execute`; no settings/env; no client factories; no client close; no collection management. Existing application errors from later `execute` calls propagate unchanged through the published Chunk 86 stack.
  - The builder is exported from `api/composition/__init__.py`. It remains unwired from `create_app()`, Regulatory runtime lifecycle, LangGraph, and document extraction.
- **Consequences:** Callers can assemble the published indexing stack from already-created provider clients without a settings-loaded runtime. Chunk 89 later added configured settings mapping above this builder. Chunk 90 owns client lifetime above Chunk 89. Document acquisition, PDF/OCR, actual corpus indexing, reindex strategy, and Regulatory contract-phase integration remain deferred.

---

## ADR-098 — Document vector index runtime configuration is indexing-specific and separate from provider connection and Regulatory settings

- **Status:** Accepted
- **Context:** Chunk 87's provider-aware builder requires an explicit document-embedding model and existing `QdrantDocumentVectorConfig` (`collection_name`, `vector_size`). Folding those values into `OpenAISettings` would mix indexing model selection with the OpenAI API credential. Folding collection/vector targeting into `QdrantSettings` would mix indexing-runtime identity with generic host/port/API-key connection settings. Folding them into `RegulatoryIntelligenceRuntimeSettings` would mix document-index configuration with Regulatory query-embedding and constraint-inference models. A generic runtime-settings hierarchy, model catalog, or settings→client DI container would invent an abstraction this repository does not own. Wiring settings into the Chunk 87 builder in this chunk would mix typed configuration with still-deferred configured/managed indexing runtime.
- **Decision:**
  - Typed `DocumentVectorIndexRuntimeSettings` lives in `energy_trading.shared.config` beside the other service-specific settings objects.
  - The object owns exactly three fields: `document_embedding_model`, `qdrant_collection_name`, and `qdrant_vector_size`.
  - The environment prefix is dedicated: `ENERGY_DOCUMENT_INDEX_`. Exact variables are `ENERGY_DOCUMENT_INDEX_DOCUMENT_EMBEDDING_MODEL`, `ENERGY_DOCUMENT_INDEX_QDRANT_COLLECTION_NAME`, and `ENERGY_DOCUMENT_INDEX_QDRANT_VECTOR_SIZE`.
  - The document-embedding model identifier belongs here, not in `OpenAISettings`. Collection name and vector size belong here, not in generic `QdrantSettings` and not in `RegulatoryIntelligenceRuntimeSettings`.
  - All three fields are required with no production defaults. String fields strip whitespace and reject blank/whitespace-only values. Vector size must be a strictly positive integer and is not inferred from the embedding model.
  - Query-embedding and constraint-inference fields are not part of this object.
  - The settings module is SDK-free and runtime-object-free. It does not import OpenAI or Qdrant clients, does not construct `QdrantDocumentVectorConfig`, and does not call Chunk 86 or Chunk 87 builders.
  - `load_document_vector_index_runtime_settings(*, env_file=...)` is uncached and separate from `AppSettings`. Process health, `create_app()`, and the Chunk 87 builder do not load it.
  - Generic configuration frameworks, model catalogs, provider registries, and settings aggregation DTOs are rejected.
- **Consequences:** Callers can load document-index runtime-specific values independently of provider connection settings and Regulatory query runtime settings. Chunk 89 and Chunk 90 consume an already-constructed instance without calling the loader. Settings-loaded indexing runtime, HTTP ingestion, and operational corpus indexing remain absent.

---

## ADR-099 — Configured document vector index composition maps typed settings onto the provider-aware builder

- **Status:** Accepted
- **Context:** Chunk 87's provider-aware builder requires already-created clients, existing `QdrantDocumentVectorConfig`, and an explicit document-embedding model. Chunk 88 published `DocumentVectorIndexRuntimeSettings` with those two Qdrant targeting fields plus the model identifier. Loading settings, constructing clients, owning lifecycle, or introducing a generic configured-runtime/DI hierarchy would expand this slice beyond a settings-to-provider-aware mapping seam.
- **Decision:**
  - API composition owns `build_document_vector_index_configured_runtime` in `api/composition/document_vector_index_configured_runtime.py`.
  - The builder is a synchronous keyword-only function over already-created `AsyncOpenAI`, `AsyncQdrantClient`, and already-constructed `DocumentVectorIndexRuntimeSettings`.
  - It constructs exactly one `QdrantDocumentVectorConfig(collection_name=settings.qdrant_collection_name, vector_size=settings.qdrant_vector_size)`, then delegates exactly once to `build_document_vector_index_provider_runtime` with those clients, that config, and `settings.document_embedding_model`, and returns that `DocumentVectorIndexExecutionService` unchanged.
  - Construction is inert: no `.embed`, `.index`, or `.execute`; no settings/env loading; no client factories; no client close; no collection management; no direct adapter construction except `QdrantDocumentVectorConfig`; no direct Chunk 86 call.
  - The builder is exported from `api/composition/__init__.py`. It remains unwired from `create_app()`, FastAPI lifespan, LangGraph, and document extraction.
- **Consequences:** Callers can assemble the published indexing stack from already-created provider clients plus already-constructed typed settings. Chunk 90 owns client lifetime separately from this adaptation seam. Chunk 91 owns settings loading above Chunk 90. Document acquisition, PDF/OCR, actual corpus indexing, collection-management strategy, and Regulatory contract-phase integration remain deferred.

---

## ADR-100 — Document-index provider clients are owned by a narrow async managed-runtime boundary

- **Status:** Accepted
- **Context:** Chunk 89 can assemble a document vector index execution service from already-created provider clients plus already-constructed `DocumentVectorIndexRuntimeSettings`, but callers still had to construct and close those clients themselves. Folding environment loading into that seam would mix configuration discovery with object composition. Folding FastAPI lifespan into the same function would couple a reusable resource owner to one HTTP framework. A generic DI container, resource registry, provider registry, or `ManagedRuntime[T]` would invent an abstraction this repository does not own. Direct `AsyncOpenAI` / `AsyncQdrantClient` construction in API composition would widen the provider-SDK allowlist beyond the approved provider-composition modules.
- **Decision:**
  - Resource lifetime lives in a separate document-index-specific API composition module: `managed_document_vector_index_runtime` in `energy_trading.api.composition.document_vector_index_managed_runtime`.
  - The callable is an async context manager (`contextlib.asynccontextmanager`) and is keyword-only. It receives already-loaded `OpenAISettings`, `QdrantSettings`, and `DocumentVectorIndexRuntimeSettings`.
  - It does not load environment values, accept an `env_file`, accept caller-supplied clients, or accept loose model/Qdrant arguments.
  - Clients are created through existing `create_openai_client` and `create_qdrant_client`. Direct SDK client constructors are not used. Direct OpenAI/Qdrant SDK type imports are not added to this module.
  - Cleanup is registered immediately after each successful client creation via `AsyncExitStack.push_async_callback(...close)` because both pinned clients expose async `close()`.
  - Service construction delegates exactly once to `build_document_vector_index_configured_runtime`. Chunks 86, 87, and 89 retain object-composition responsibilities.
  - Expected cleanup order is LIFO: Qdrant then OpenAI, provided both were created. If OpenAI construction fails, later factories and the configured builder are not called. If Qdrant construction fails, the OpenAI client is still closed. If Chunk 89 fails, both created clients are closed. Consumer exceptions still close both clients and then propagate. If one cleanup raises, the other registered cleanup is still attempted and the cleanup exception is not suppressed.
  - Entering the context performs no provider I/O. The yielded service is constructed, not executed.
  - FastAPI lifespan, `create_app()`, HTTP routes, app state, and LangGraph remain unwired.
  - Generic lifecycle managers, DI containers, resource registries, and provider registries are rejected.
- **Consequences:** Callers can supply already-loaded typed settings and receive a lifecycle-owned `DocumentVectorIndexExecutionService`. Chunk 91 owns settings loading separately from this resource-lifetime seam. FastAPI integration, document acquisition, PDF/OCR, actual corpus indexing, collection-management strategy, and Regulatory contract-phase integration remain absent. Direct provider SDK API-composition imports remain limited to the existing approved provider-composition modules.

---

## ADR-101 — Document-index settings loading is composed above the managed runtime

- **Status:** Accepted
- **Context:** Chunk 90 can own document-index provider-client lifetime from already-loaded `OpenAISettings`, `QdrantSettings`, and `DocumentVectorIndexRuntimeSettings`, but callers still had to invoke the three existing typed loaders themselves. Folding environment discovery into the managed runtime would mix configuration loading with resource lifetime. Folding FastAPI lifespan into the same function would couple a reusable settings-to-runtime seam to one HTTP framework. A generic settings aggregator, runtime manager, DI container, or provider registry would invent an abstraction this repository does not own. Direct `os.environ` / `dotenv` parsing in API composition would bypass the published loaders.
- **Decision:**
  - Settings loading lives in a separate document-index-specific API composition module: `loaded_document_vector_index_runtime` in `energy_trading.api.composition.document_vector_index_loaded_runtime`.
  - The callable is a keyword-only async context manager (`contextlib.asynccontextmanager`). It exposes one `env_file: str | Path | None = ".env"` argument matching the existing three loader contracts and forwards that exact value to each loader.
  - It calls `load_openai_settings`, `load_qdrant_settings`, and `load_document_vector_index_runtime_settings` exactly once each, then delegates resource ownership and service construction to `managed_document_vector_index_runtime`.
  - It does not instantiate settings classes as a substitute for loaders, construct clients, import OpenAI/Qdrant SDK types, call client factories, construct provider adapters, or invoke Chunks 89/87/86 directly.
  - Loader validation failures propagate unchanged. An earlier loader failure does not fabricate settings or enter the managed runtime. Managed-runtime entry failures and consumer exceptions propagate according to normal context-manager semantics. This layer adds no `try/except` translation or suppression.
  - Entering the context performs no provider I/O and does not call `.execute(...)`, `.embed(...)`, or `.index(...)`. The yielded object is the exact `DocumentVectorIndexExecutionService` produced by Chunk 90.
  - FastAPI lifespan, `create_app()`, HTTP routes, app state, and LangGraph remain unwired.
  - Generic settings aggregators, runtime/lifecycle managers, DI containers, and provider registries are rejected.
- **Consequences:** Callers can supply an explicit settings source and receive a lifecycle-owned `DocumentVectorIndexExecutionService`. FastAPI integration, document acquisition, PDF/OCR, actual corpus indexing, collection-management strategy, and Regulatory contract-phase integration remain absent. Direct provider SDK API-composition imports remain limited to the existing approved provider-composition modules. Chunk 90 continues to own client creation and cleanup.

---

## ADR-102 — FastAPI lifecycle ownership is separated from document-index service exposure

- **Status:** Accepted
- **Context:** Chunk 91 can load typed document-index settings and own the managed runtime for an `async with` scope, but FastAPI process lifetime still had no dedicated seam. Installing that runtime into `create_app()` in the same slice would couple lifecycle ownership to HTTP application construction before the service-access mechanism is chosen. Storing the yielded service on `app.state`, yielding a Starlette lifespan-state dict, or inventing a generic lifespan/resource/DI framework would pre-commit a later architect-reviewed exposure path. Importing settings loaders, provider SDKs, or lower document-index layers in the FastAPI boundary would collapse Chunks 91/90/89/87/86.
- **Decision:**
  - FastAPI-compatible lifecycle ownership lives in a separate document-index-specific API composition module: `build_document_vector_index_lifespan` in `energy_trading.api.composition.document_vector_index_lifespan`.
  - The factory is synchronous and keyword-only. It reuses the existing Chunk 91 `env_file: str | Path | None = ".env"` contract and returns a callable compatible with FastAPI's `lifespan=` argument: `Callable[[FastAPI], AbstractAsyncContextManager[None]]`.
  - Constructing the returned callback loads no settings and enters no runtime. Only lifespan startup enters `loaded_document_vector_index_runtime`; lifespan shutdown exits it through ordinary async-context-manager semantics.
  - The composed service yielded by Chunk 91 is intentionally unused. This boundary does not write it to `app.state`, does not yield a lifespan-state dictionary, does not create a request-state key, and does not invoke `.execute(...)`, `.embed(...)`, or `.index(...)`.
  - The module may import FastAPI's application type and Chunk 91. It does not import settings loaders, settings objects, provider SDKs, client factories, adapters, or Chunks 90/89/87/86.
  - `create_app()` is unchanged and does not install this lifespan. HTTP routes, health, middleware, error handling, and LangGraph remain unwired.
  - Generic lifespan frameworks, service registries, DI containers, and resource managers are rejected.
- **Consequences:** FastAPI-compatible lifecycle ownership can be proven independently of service exposure. `create_app()` installation, the service-access mechanism, route/dependency wiring, LangGraph routing, document acquisition, PDF/OCR, and actual corpus indexing remain deferred. Direct provider SDK API-composition imports remain limited to the existing approved provider-composition modules. Chunk 91 continues to own settings loading; Chunk 90 continues to own client lifetime.

---

## ADR-103 — Production FastAPI lifespan composition nests Regulatory outside document-index without a generic lifecycle framework

- **Status:** Accepted
- **Context:** FastAPI supports one application lifespan callback. Production `create_app()` already installs `build_regulatory_intelligence_lifespan`, which owns published Regulatory query-service exposure. Chunk 92 added `build_document_vector_index_lifespan` without installing it. Replacing the Regulatory lifespan would drop published query behavior. Installing the document-index lifespan beside it is not possible at the FastAPI application boundary. A generic `compose_lifespans(...)`, lifespan registry, resource manager, or DI container would invent a framework this repository does not own. Sharing OpenAI/Qdrant clients across the two runtimes would collapse separately published lifetime seams.
- **Decision:**
  - Production-specific nested composition lives in `build_production_lifespan` in `energy_trading.api.composition.production_lifespan`.
  - The factory is synchronous and keyword-only. It reuses the existing `env_file: str | Path | None = ".env"` contract and returns a FastAPI-compatible callback: `Callable[[FastAPI], AbstractAsyncContextManager[None]]`.
  - It delegates only to the two published child factories, forwarding the exact supplied `env_file` unchanged, and nests Regulatory as the outer context and Document Vector Index as the inner context. The same FastAPI `app` is passed to both callbacks. The composite yields `None`.
  - Constructing the factory does not load settings, enter either runtime, create clients, or invoke provider operations. Child lifespan modules retain their own runtime ownership. Ordinary nesting teardown is preserved; lifecycle exceptions are not caught or remapped.
  - This is not a reusable lifespan framework, service locator, or client-pooling refactor. There is no `app.state` assignment in this module.
  - `create_app()` remained unchanged in Chunk 93 and continued to install `build_regulatory_intelligence_lifespan` directly. Installation of the composite was deferred to Chunk 94.
- **Consequences:** Both published lifespans can be owned together without replacing Regulatory behavior. Direct provider SDK API-composition imports remain limited to the existing approved provider-composition modules.

---

## ADR-104 — Production create_app installs the published composite lifespan without duplicating child nesting

- **Status:** Accepted
- **Context:** Chunk 93 published `build_production_lifespan` as the production-specific nesting seam, but `create_app()` still defaulted directly to `build_regulatory_intelligence_lifespan`. Reproducing child-lifespan `async with` nesting inside `app.py` would duplicate Chunk 93. Importing the child factories into `app.py` would collapse that composition boundary. Dropping the keyword-only `lifespan` override would force offline HTTP tests onto provider credentials. Exposing or executing the Document Vector Index service would pre-commit an indexing API that is not authorized.
- **Decision:**
  - Production `create_app()` defaults to `build_production_lifespan()` when no explicit `lifespan` is supplied.
  - A caller-supplied `lifespan` still replaces that default exactly. If `lifespan is not None`, `build_production_lifespan()` is not called.
  - `app.py` does not import `build_regulatory_intelligence_lifespan` or `build_document_vector_index_lifespan` and does not reproduce nested child composition.
  - `create_app()` construction remains lazy: it may construct the composite callback, but it does not load Regulatory or document-index settings, create OpenAI/Qdrant clients, execute provider calls, or index anything.
  - Regulatory query-router installation and lifespan-owned `app.state` exposure are unchanged. The Document Vector Index service remains unexposed and is not executed.
- **Consequences:** Entering the real production application lifespan enters both published child runtimes through Chunk 93. Offline tests can still inject a no-op lifespan. Document-index indexing HTTP routes, shared-client refactoring, and automatic indexing remain deferred.

---

## ADR-105 — Document-index FastAPI app.state exposes the exact lifespan-scoped execution service

- **Status:** Accepted
- **Context:** Chunk 94 enters the document-index lifecycle through `create_app` → `build_production_lifespan` → `build_document_vector_index_lifespan` → `loaded_document_vector_index_runtime`, but the exact yielded `DocumentVectorIndexExecutionService` was discarded. ADR-102 separated FastAPI lifecycle ownership from service exposure. Regulatory already publishes its query service on lifespan-scoped `app.state`. Inventing a generic service registry, DI container, or shared state map would collapse those independently owned attributes. Adding an accessor, HTTP route, or automatic `execute(...)` would expand beyond lifespan-scoped exposure.
- **Decision:**
  - The document-index lifespan callback accepts the real FastAPI `app`, enters `loaded_document_vector_index_runtime` exactly once, captures the exact yielded `DocumentVectorIndexExecutionService`, stores that identity on `app.state.document_vector_index_execution_service`, yields `None`, and deletes that attribute in `finally` before the loaded runtime exits.
  - Factory construction remains lazy. The module does not wrap, proxy, reconstruct, adapt, or invoke the service.
  - Ownership is exclusively `document_vector_index_lifespan.py`. `app.py` and `production_lifespan.py` do not assign or delete the attribute. Regulatory continues to own `app.state.regulatory_intelligence_query_execution_service` independently.
  - No typed accessor, FastAPI dependency, HTTP route, automatic indexing, or generic service registry is added.
- **Consequences:** Production now owns both runtimes, and the exact document-index execution service is available on application state only while that child lifespan is active. Accessor, HTTP ingestion, corpus indexing, PDF/OCR, and LangGraph remain deferred.

---

## ADR-106 — Document-index request-time service access is a narrow API dependency boundary

- **Status:** Accepted
- **Context:** Chunk 95 stores the exact lifespan-managed `DocumentVectorIndexExecutionService` on `app.state.document_vector_index_execution_service` while the document-index lifespan is active. HTTP handlers still needed a published, typed way to read that object. A global singleton, service registry, DI container, generic state accessor, or production `Depends(...)`/route in the same slice would either invent abstractions this repository does not own or pre-commit an HTTP indexing contract. Raising `HTTPException`, `AttributeError`, or `RuntimeError` from the accessor would leak transport or runtime internals into a request-time application boundary.
- **Decision:**
  - Request-time lookup is a dedicated API dependency function `get_document_vector_index_execution_service(request: Request) -> DocumentVectorIndexExecutionService`.
  - The accessor reads the exact published state key and returns that exact service identity. It does not wrap, proxy, clone, or reconstruct the object.
  - Missing or wrong-type state fails closed as existing `DependencyUnavailableError` with sanitized message `Document Vector Index service is unavailable.` and published code `dependency_unavailable`. No new exception class is introduced. HTTP translation remains in the existing API mapping layer (503).
  - The accessor is read-only. It does not assign or delete application state, enter or exit lifecycle, load settings, construct clients, or invoke the service.
  - There is no global singleton, service registry, service locator, or generic DI container. Production code does not wrap the accessor in `Depends(...)` and does not add an HTTP document-index route.
- **Consequences:** Active FastAPI requests can resolve the lifespan-scoped document-index execution service through a typed reader. HTTP indexing transport, route installation, automatic indexing, corpus ingestion, PDF/OCR, and LangGraph remain deferred.

---

## ADR-107 — Document-index HTTP request transport is an API-owned already-normalized chunk contract

- **Status:** Accepted
- **Context:** Chunk 96 published a typed request-time accessor for the lifespan-scoped `DocumentVectorIndexExecutionService`. An HTTP indexing route still needs a public request body that FastAPI can validate. Reusing application `ExtractedDocumentChunk` as the HTTP model would leak application DTO ownership across the API boundary. Adding file-upload, path, URL, provider, embedding, or Qdrant fields would invent an acquisition/indexing surface that is not authorized. Adding a route, mapper, or success response in the same slice would pre-commit HTTP execution and response semantics while `execute(...)` still returns `None`.
- **Decision:**
  - The API layer owns frozen Pydantic request DTOs `DocumentVectorIndexChunkRequest` and `DocumentVectorIndexRequest` in `api/schemas`.
  - Chunk fields are exactly the already-normalized extracted-chunk shape: `document_id`, `chunk_id`, `text`, `ordinal`, and optional `page_number`. The outer request field is exactly `chunks: tuple[DocumentVectorIndexChunkRequest, ...]`.
  - Unknown fields are forbidden. The models do not accept raw files, bytes, paths, URLs, MIME types, OCR options, provider/model identifiers, vectors, embeddings, scores, or metadata bags.
  - FastAPI transport does not accept `ExtractedDocumentChunk` as the public request model. No production mapper, route, accessor usage, `.execute(...)`, or response DTO is added in this slice.
- **Consequences:** HTTP clients can be described against a narrow already-normalized chunk request contract. Indexing route installation, response semantics, document acquisition/PDF/OCR, automatic indexing, and LangGraph remain deferred.

---

## ADR-108 — Document-index HTTP indexing is an unwired route over already-normalized chunks

- **Status:** Accepted
- **Context:** Chunk 97 published API-owned request DTOs for already-normalized extracted chunks. Chunk 96 published a typed accessor for the lifespan-scoped `DocumentVectorIndexExecutionService`. An HTTP route is needed to connect those surfaces without installing production exposure, inventing a success payload, or accepting raw document upload. Reusing a generic mapper, reading `app.state` in the handler, or calling embedding/Qdrant ports directly would collapse the published boundaries.
- **Decision:**
  - The API layer owns a dedicated `APIRouter` that accepts `DocumentVectorIndexRequest`, resolves the service through `Depends(get_document_vector_index_execution_service)`, and explicitly constructs `ExtractedDocumentChunk` values field-by-field.
  - The handler awaits the published `execute(*, chunks=...)` exactly once and returns HTTP 204 No Content because the application service returns `None`.
  - There is no response DTO, raw file/upload surface, or generic mapper. Application and provider exceptions are not translated locally.
  - Production `create_app()` does not import or `include_router` this module. Route existence is not production installation.
- **Consequences:** The indexing HTTP boundary can be unit-tested independently. Production router installation, corpus ingestion, PDF/OCR, automatic indexing, and LangGraph remain deferred.

---

## ADR-109 — Document Vector Index production router installation

- **Status:** Accepted
- **Context:** Chunk 98 published a thin Document Vector Index HTTP indexing router, but production `create_app()` still installed only health and Regulatory Intelligence. Isolated tests could mount the endpoint; the production factory did not. Reconstructing the path, wrapping the accessor, moving provider setup into `create_app()`, or introducing a generic router registry would expand this composition slice.
- **Decision:**
  - Production `create_app()` imports the existing `router` from `api/routers/document_vector_index.py` as `document_vector_index_router` and includes it once with `prefix=resolved_settings.api_prefix`, the same prefix used by health and Regulatory Intelligence.
  - The handler, DTOs, accessor, HTTP method, endpoint path, 204 mapping, and explicit `ExtractedDocumentChunk` projection remain unchanged. No second prefix is added in `create_app()`.
  - Construction remains lazy. The existing keyword-only `lifespan` seam remains. The published document-index lifespan still owns service lifecycle. `create_app()` still does not load document-index/OpenAI/Qdrant settings, construct clients, call composition builders, assign `app.state`, or invoke `.execute`.
- **Consequences:** `POST /api/v1/document-vector-index/index` is reachable through the production factory when the default prefix is `/api/v1`. Execution still depends on the lifespan-scoped service. The request body remains already-normalized chunks only. Offline tests can inject a no-op lifespan and keep health credential-free; missing service state maps to the published 503. Corpus ingestion, PDF/OCR, automatic/background/startup indexing, reindex/replace/delete, Qdrant collection management, verified Armenian DAM rules, Regulatory LangGraph wiring, and Pricing & Sales remain deferred.

---

## ADR-110 — Concrete PDF text-layer extraction adapter, no OCR, unwired

- **Status:** Accepted
- **Context:** Chunk 12 published `DocumentExtractionPort` and canonical `ExtractedDocumentChunk` / `DocumentExtractionResult` contracts. Regulatory Intelligence and document-index HTTP still consume already-normalized chunks. Corpus ingestion cannot start from application-layer PDF parsing, OCR, or a generic document-loader framework without collapsing the ACL. A first concrete adapter is needed for PDFs that already contain a text layer, without wiring extraction into `create_app()`, indexing, OpenAI, Qdrant, or LangGraph.
- **Decision:**
  - Add exactly one production PDF library, `pypdf`, for text-layer extraction. Do not add OCR, Tesseract, cloud OCR, LangChain document loaders, or a second PDF library.
  - Implement `PdfTextExtractionAdapter` in `infrastructure/adapters/unstructured/pdf_text_extraction.py`. It structurally satisfies `DocumentExtractionPort` without subclassing the Protocol.
  - Constructor injection owns the local `.pdf` `Path`, opaque `document_id`, and `source_name`. Public `extract()` remains `async extract() -> DocumentExtractionResult` and offloads blocking parse/extraction through `asyncio.to_thread`.
  - Chunking is deterministic and page-based: one chunk per non-empty normalized page; `chunk_id` is `<document_id>:page:<page_number>`; `ordinal` is zero-based among emitted chunks; `page_number` is one-based physical PDF page. Blank pages are skipped, not failures.
  - A readable PDF with no extractable text returns empty chunks plus a sanitized `pdf_no_extractable_text` diagnostic and no DLQ, matching the published "document that yields no normalized text" result case. Invalid/corrupt/non-PDF bytes return empty chunks, a sanitized `pdf_invalid` diagnostic, and opaque `pdf://{source_name}/source` DLQ metadata. Missing/unreadable files raise sanitized `DependencyUnavailableError`. Page `extract_text` parser failures fail closed at document level.
  - Filesystem paths, raw PDF bytes, parser exceptions, and OCR never appear on application DTOs, diagnostics, error messages, or `DLQRecord.payload_reference`. The adapter does not persist DLQ records.
  - The adapter remains unwired from `create_app()`, Regulatory runtime, document-index runtime, `DocumentVectorIndexExecutionService`, LangGraph, OpenAI, and Qdrant. No HTTP extraction endpoint or settings are added.
- **Consequences:** Local text-layer PDFs can be converted into existing canonical chunks in tests and future composition. OCR, scanned documents, URL/HTTP acquisition, automatic corpus ingestion, production wiring of extraction-to-index composition, and Pricing & Sales remain deferred. Regulatory Intelligence parent capability remains incomplete.

---

## ADR-111 — Application Document Extraction-to-Index Execution Composition

- **Status:** Accepted
- **Context:** Chunk 12 published `DocumentExtractionPort` / `DocumentExtractionResult`. Chunk 85 published `DocumentVectorIndexExecutionService` over already-normalized chunks. Chunk 100 published an unwired PDF text-layer adapter that can return non-empty chunks, empty chunks plus diagnostics, or empty chunks plus DLQ metadata. Callers still had no application-owned use case that composes extraction into indexing without inventing a generic document pipeline, FastAPI route, or automatic corpus ingestion. Wiring that composition into `create_app()`, lifespan, OpenAI, Qdrant, or LangGraph would collapse independently owned boundaries.
- **Decision:**
  - Application owns `DocumentExtractionIndexExecutionService` in `application/orchestration/document_extraction_index_execution.py`.
  - Constructor dependencies are exactly `DocumentExtractionPort` and `DocumentVectorIndexExecutionService`.
  - The only public operation is `async execute(self) -> DocumentExtractionResult`. It accepts no runtime source, path, or bytes.
  - `execute` awaits `DocumentExtractionPort.extract()` exactly once, then awaits `DocumentVectorIndexExecutionService.execute(chunks=result.chunks)` only when `result.chunks` is non-empty, and returns the original `DocumentExtractionResult` object unchanged.
  - Empty `chunks=()` does not invoke index execution. Extraction diagnostics and DLQ records are not rewritten, dropped, or converted into indexing failures.
  - Extraction and indexing exceptions propagate unchanged. There is no local `try/except`, retry, fallback, or new application error.
  - The service remains unwired from `create_app()`, FastAPI routes, production lifespan, Regulatory runtime, document-index runtime composition, LangGraph, `PdfTextExtractionAdapter`, OpenAI, and Qdrant. No composition root, settings, or HTTP endpoint is added.
- **Consequences:** Callers that later compose this service can extract then conditionally index through published application boundaries. Automatic corpus ingestion, OCR, URL/HTTP acquisition, production wiring, collection management, reindex/delete/replace, and Pricing & Sales remain deferred. Regulatory Intelligence parent capability remains incomplete.

---

## ADR-112 — API PDF Extraction-to-Index Composition Root

- **Status:** Accepted
- **Context:** Chunk 100 published `PdfTextExtractionAdapter` for constructor-configured local text-layer PDFs. Chunk 101 published application-owned `DocumentExtractionIndexExecutionService` over `DocumentExtractionPort` plus `DocumentVectorIndexExecutionService`. Callers still had no API composition root that constructed that concrete PDF adapter into the published extraction-to-index service without inventing a generic document pipeline, executing extraction/indexing, loading settings, constructing OpenAI/Qdrant clients, or wiring `create_app()`.
- **Decision:**
  - API owns `build_pdf_document_extraction_index_execution` in `api/composition/pdf_document_extraction_index.py`.
  - The function is synchronous and keyword-only. Inputs are `path: Path`, `document_id: str`, `source_name: str`, and an already-constructed `DocumentVectorIndexExecutionService`. The return type is `DocumentExtractionIndexExecutionService`.
  - Construction sequence is exactly one `PdfTextExtractionAdapter(path=..., document_id=..., source_name=...)` then one `DocumentExtractionIndexExecutionService(adapter, index_execution_service)`. The supplied index execution service identity is preserved. The optional adapter test clock is not exposed.
  - The builder does not call `.extract()` or `.execute()`, inspect file existence, open the PDF, embed, index, load settings, or construct provider clients. Construction therefore works when the supplied PDF path does not exist.
  - The builder remains unwired from `create_app()`, FastAPI routes, production lifespan, `app.state`, dependency accessors, Regulatory runtime, document-index runtime lifecycle, and LangGraph. No owner/lifecycle, route, or startup execution is added.
- **Consequences:** Callers can later compose a local PDF path into the published extraction-to-index application service. OCR, URL/file-upload/directory acquisition, automatic/startup/background corpus ingestion, production wiring, collection management, reindex/replace/delete, and Pricing & Sales remain deferred. Regulatory Intelligence parent capability remains incomplete.

---

## ADR-113 — Settings-Loaded PDF Extraction-to-Index Runtime Composition

- **Status:** Accepted
- **Context:** Chunk 91 published `loaded_document_vector_index_runtime`, which loads typed settings and yields `DocumentVectorIndexExecutionService` while the existing managed runtime owns provider-client lifetime. Chunk 102 published `build_pdf_document_extraction_index_execution`, which constructs `PdfTextExtractionAdapter` plus `DocumentExtractionIndexExecutionService` from a local path, identities, and an already-constructed index execution service. Callers still had no settings-loaded composition that nested those two published seams without executing extraction/indexing, inventing PDF-specific settings, constructing OpenAI/Qdrant clients, duplicating settings loading, or wiring `create_app()`.
- **Decision:**
  - API owns `loaded_pdf_document_extraction_index_runtime` in `api/composition/pdf_document_extraction_index_loaded_runtime.py`.
  - The function is a keyword-only async context manager. Inputs are `path: Path`, `document_id: str`, `source_name: str`, and the existing `env_file: str | Path | None = ".env"` contract from `loaded_document_vector_index_runtime`. The yielded type is `DocumentExtractionIndexExecutionService`.
  - The context manager enters `loaded_document_vector_index_runtime(env_file=env_file)` exactly once, calls `build_pdf_document_extraction_index_execution` exactly once with the supplied path/identities and the exact yielded index execution service, and yields that builder result unchanged. Inner runtime teardown occurs after the outer yield, including when the Chunk 102 builder raises.
  - Chunk 103 does not own provider clients, close clients, register cleanup, load settings itself, call `.extract()` or `.execute()`, or inspect the filesystem. Provider lifetime remains owned by the existing document-index loaded/managed chain. No PDF-specific environment variables are added.
  - The runtime remains unwired from `create_app()`, FastAPI routes, production lifespan, `app.state`, dependency accessors, Regulatory runtime, and LangGraph. No lifespan factory, accessor, route, or startup execution is added.
- **Consequences:** Callers can later obtain a constructed PDF extraction-to-index application service from settings plus a local path without entering real extraction or indexing in this composition layer. OCR, URL/file-upload/directory acquisition, automatic/startup/background corpus ingestion, production wiring, collection management, reindex/replace/delete, and Pricing & Sales remain deferred. Regulatory Intelligence parent capability remains incomplete.

---

## ADR-114 — Explicit One-Shot Loaded PDF Extraction-to-Index Execution

- **Status:** Accepted
- **Context:** Chunk 101 published application-owned `DocumentExtractionIndexExecutionService.execute()`, which extracts once and indexes only non-empty chunks. Chunk 103 published `loaded_pdf_document_extraction_index_runtime`, which constructs that service from settings plus a local PDF path without invoking it. Callers still had no explicit one-shot API composition function that entered that loaded runtime and executed the application use case exactly once without inventing HTTP upload, startup/background ingestion, directory scanning, retry/fallback, or `create_app()` wiring.
- **Decision:**
  - API owns `execute_loaded_pdf_document_extraction_index` in `api/composition/pdf_document_extraction_index_execute.py`.
  - The function is keyword-only and async. Inputs are `path: Path`, `document_id: str`, `source_name: str`, and the existing `env_file: str | Path | None = ".env"` contract from Chunk 103. The return type is `DocumentExtractionResult`.
  - The function enters `loaded_pdf_document_extraction_index_runtime(...)` exactly once, awaits `service.execute()` exactly once with no arguments, and returns that exact result object. Nested extraction and index-execution rules remain owned by Chunk 101. Provider lifetime remains owned by the existing document-index loaded/managed chain.
  - Runtime-entry failures and `execute()` failures propagate unchanged. Inner runtime teardown still occurs after a failed `execute()`. There is no local `try/except`, retry, fallback, result reconstruction, or new diagnostic.
  - The function remains unwired from `create_app()`, FastAPI routes, production lifespan, `app.state`, dependency accessors, Regulatory runtime, LangGraph, scheduler, background tasks, and n8n. No automatic/startup/background caller is installed.
- **Consequences:** An explicit external caller can now run one local text-layer PDF through extraction → embedding → vector-index execution. OCR, URL/file-upload/directory acquisition, automatic/startup/background corpus ingestion, production trigger wiring, collection management, reindex/replace/delete, and Pricing & Sales remain deferred. Regulatory Intelligence parent capability remains incomplete.

---
