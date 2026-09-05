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
