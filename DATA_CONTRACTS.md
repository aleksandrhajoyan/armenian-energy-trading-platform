# Data Contracts — Canonical Models (Implemented)

Canonical contracts are Pydantic models owned by the domain layer (`src/energy_trading/domain`). Application agents, ML components, and use cases speak these contracts only.

External column names, Armenian headers, vendor units, naive timestamps, and file-specific payload shapes stop at the Anti-Corruption Layer. **Source adapters**, not domain models, are responsible for resolving ambiguous or missing source units and timezones. Domain validation fails closed: it does not guess.

Python types live under `energy_trading.domain.models` and `energy_trading.domain.value_objects`.

## Cross-cutting canonical semantics

| Concern | Canonical rule |
| --- | --- |
| Power | **MW**. Types: `NonNegativeMW`, `PositiveMW`. |
| Energy | **MWh**. Type: `NonNegativeMWh`. MW and MWh are not equated. |
| Timestamp | Timezone-aware input, stored/normalized as **UTC** (`UtcDateTime`). Naive datetimes are invalid. |
| Money / price | **`Decimal`**, never `float`. Types: `MoneyAmount`, `EnergyPrice`. |
| Currency | Explicit ISO-style three-letter code (`CurrencyCode`, e.g. `AMD` is valid). Not hardcoded as the market currency. |
| Identifiers | Opaque non-empty strings (`EntityId`). Not vendor primary-key types. |
| Unknown fields | Forbidden on every `CanonicalModel`. |
| Mutability | Models are frozen. |
| Non-finite numbers | `NaN` and infinities are rejected. |

Interval length for Armenian DAM (hourly vs other) remains **TBD until verified**. Domain timestamps are instants, not an assumed market product duration.

Do **not** encode unverified regulator or DAM bid-format, lot-size, gate-closure, or imbalance-price rules in these models.

---

## Value objects and constrained types

| Type | Meaning | Validation |
| --- | --- | --- |
| `UtcDateTime` | Canonical timestamp | Aware datetime required; converted to UTC |
| `EntityId` | Opaque identifier | Non-empty; whitespace stripped |
| `NonEmptyString` | Required text | Non-empty; whitespace stripped |
| `CurrencyCode` | ISO-style currency | Exactly three uppercase letters `A-Z` |
| `NonNegativeMW` | Power in MW | `>= 0`, finite |
| `PositiveMW` | Power in MW | `> 0`, finite |
| `NonNegativeMWh` | Energy in MWh | `>= 0`, finite |
| `UnitInterval` | Score / probability | `0 <= x <= 1`, finite |
| `FiniteDecimal` | Monetary scalar | Finite `Decimal`; `float` rejected |
| `MoneyAmount` | `{amount, currency}` | Finite Decimal amount; explicit currency |
| `EnergyPrice` | `{amount_per_mwh, currency}` | Price per MWh; sign not constrained |

Money and prices do **not** assume non-negativity. Electricity market rules are not yet verified. No FX conversion is performed.

---

## ConsumptionRecord

- **Purpose:** Observed consumer load at one instant.
- **Fields:** `consumer_id` (`EntityId`); `timestamp` (`UtcDateTime`); `value_mw` (`NonNegativeMW`).
- **Units:** MW.
- **Invariants:** non-negative finite MW; UTC timestamp; no source column names.
- **Adapter path:** Consumption CSV/XLSX adapters may convert an explicitly configured source power unit (`MW` or `kW`) to canonical MW and may interpret naive timestamps with an explicit IANA timezone. Units and timezones are never inferred. Domain types are unchanged.

## WeatherRecord

- **Purpose:** Weather observation or forecast point used as operational context and future ML features.
- **Fields:** `location_id` (`EntityId`); `timestamp` (`UtcDateTime`); `temperature_c` (finite °C, may be negative); optional `solar_irradiance_w_m2` (W/m², non-negative); optional `precipitation_mm` (mm, non-negative).
- **Invariants:** no weather-provider identity. Adapters convert foreign units before this contract.

## HydroRecord

- **Purpose:** Hydro storage/flow context and optional available generation.
- **Fields:** `resource_id` (`EntityId`); `timestamp` (`UtcDateTime`); optional `reservoir_level_m` (m, non-negative); optional `river_flow_m3_s` (m³/s, non-negative); optional `available_generation_mw` (`NonNegativeMW`).
- **Invariants:** no hydrological calculations; reservoir operating policy is not assumed.

## GenerationAvailabilityRecord

- **Purpose:** Available capacity of an unnamed asset at one instant.
- **Fields:** `asset_id` (`EntityId`); `timestamp` (`UtcDateTime`); `status` (`GenerationStatus`: `available` \| `maintenance` \| `outage` \| `unknown`); `available_capacity_mw` (`NonNegativeMW`); optional `total_capacity_mw` (`NonNegativeMW`).
- **Invariants:** if `total_capacity_mw` is present, `available_capacity_mw <= total_capacity_mw` (data consistency, not a market rule). No plant names are hardcoded.

## MarketPriceRecord

- **Purpose:** Observed market price (history / official publication), not a forecast.
- **Fields:** `market_id` (`EntityId`); `timestamp` (`UtcDateTime`); `price` (`EnergyPrice`); optional `volume_mwh` (`NonNegativeMWh`).
- **Invariants:** currency is explicit on `EnergyPrice`. Interval length is not assumed. AMD is not implied.

## NewsEvent

- **Purpose:** Qualitative public-information event. Not a substitute for ML forecasts.
- **Fields:** `event_id` (`EntityId`); `timestamp` (`UtcDateTime`); `headline` (`NonEmptyString`); `summary` (`NonEmptyString`); optional `category` (`NonEmptyString`); optional `severity` (`NewsSeverity`: `low` \| `medium` \| `high`).
- **Invariants:** no raw HTML, scrape blobs, or LLM runtime fields.

## RegulatoryConstraint

- **Purpose:** Generic structured constraint. Official PSRC/DAM rule tables are **not** encoded.
- **Fields:** `constraint_id` (`EntityId`); `constraint_type` (`NonEmptyString`); `description` (`NonEmptyString`); `effective_from` (`date`); optional `effective_to` (`date`); optional `minimum_value` / `maximum_value` (finite numbers); optional `unit` (`NonEmptyString`); optional `currency` (`CurrencyCode`); optional `source_document_id` (`EntityId`).
- **Invariants:** if both dates exist, `effective_to >= effective_from`; if both numeric bounds exist, `minimum_value <= maximum_value`. No tariff values, network costs, PSRC IDs, or effective dates are hardcoded.

## LoadForecastPoint

- **Purpose:** Output of a future load-forecast port/model for one target instant.
- **Fields:** `forecast_run_id` (`EntityId`); `consumer_id` (`EntityId`); `generated_at` (`UtcDateTime`); `target_timestamp` (`UtcDateTime`); `value_mw` (`NonNegativeMW`).
- **Invariants:** no XGBoost/LightGBM/Prophet objects. This model does not calculate a forecast.

## PriceForecastPoint

- **Purpose:** Output of a future price-forecast port/model for one target instant.
- **Fields:** `forecast_run_id` (`EntityId`); `market_id` (`EntityId`); `generated_at` (`UtcDateTime`); `target_timestamp` (`UtcDateTime`); `price` (`EnergyPrice`).
- **Invariants:** currency explicit; no ML library types; no forecast calculation.

## RiskAssessment

- **Purpose:** Portfolio risk snapshot for a future Portfolio & Risk Agent. Not a calculator.
- **Fields:** `assessment_id` (`EntityId`); `assessed_at` (`UtcDateTime`); `delivery_timestamp` (`UtcDateTime`); `risk_score` (`UnitInterval`); optional `expected_margin` (`MoneyAmount`); optional `price_volatility` (`FiniteDecimal`); optional `expected_balancing_penalty` (`MoneyAmount`); optional `value_at_risk` (`MoneyAmount`); optional `notes` (`NonEmptyString`).
- **Invariants:** `0 <= risk_score <= 1`. VaR, margin, and Armenian balancing penalties are not computed or invented here.

## MarketBid

- **Purpose:** Intention to buy or sell for one delivery instant.
- **Fields:** `bid_id` (`EntityId`); `created_at` (`UtcDateTime`); `delivery_timestamp` (`UtcDateTime`); `side` (`BidSide`: `buy` \| `sell`); `quantity_mw` (`PositiveMW`); `limit_price` (`EnergyPrice`).
- **Invariants:** `quantity_mw > 0`. Gate closure, lot size, and product rules are not encoded. Nothing is submitted externally.

## MarketClearingResult

- **Purpose:** Canonical internal clearing outcome for a bid. Not an external market-gateway schema.
- **Fields:** `bid_id` (`EntityId`); `delivery_timestamp` (`UtcDateTime`); `cleared_at` (`UtcDateTime`); `status` (`ClearingStatus`: `cleared` \| `partially_cleared` \| `rejected`); `cleared_quantity_mw` (`NonNegativeMW`); optional `clearing_price` (`EnergyPrice`).
- **Invariants:** `clearing_price` is required unless `status` is `rejected`. Clearing is not calculated here.

## SettlementResult

- **Purpose:** Validates a supplied settlement outcome. Does **not** produce one.
- **Fields:** `settlement_id` (`EntityId`); `period_start` / `period_end` (`UtcDateTime`); `delivered_energy_mwh` (`NonNegativeMWh`); `revenue`, `procurement_cost`, `balancing_cost`, `profit` (`MoneyAmount`).
- **Invariants:** `period_end > period_start`; all monetary fields share one currency. `profit` is **not** computed as `revenue - costs`.

## AdapterDiagnostic

- **Purpose:** Canonical diagnostic envelope for a future adapter. Not a Python exception.
- **Fields:** `code` (`NonEmptyString`); `message` (`NonEmptyString`); `severity` (`DiagnosticSeverity`: `info` \| `warning` \| `error`); optional `field_name` (`NonEmptyString`).
- **Invariants:** no stack traces or exception objects.

## DLQRecord

- **Purpose:** Metadata for an ingestion normalization failure.
- **Fields:** `record_id` (`EntityId`); `failed_at` (`UtcDateTime`); `source_name` (`NonEmptyString`); `adapter_name` (`NonEmptyString`); `diagnostics` (tuple of `AdapterDiagnostic`, min length 1); `payload_reference` (`NonEmptyString`); optional `correlation_id` (`EntityId`).
- **Invariants:** at least one diagnostic. **Raw external payloads are forbidden**; infrastructure may store the original bytes/file behind `payload_reference`.
- **Persistence:** The canonical contract is unchanged. An interim infrastructure adapter (`FilesystemDeadLetterQueue`) can persist this metadata as one JSON file per `record_id`. It stores the opaque `payload_reference` string only; it does not store or resolve the failed payload. PostgreSQL/TimescaleDB remains the planned system of record (ADR-004). Replay, listing, and query APIs are not implemented. Ingestion adapters still return `DLQRecord` values on `StructuredIngestionResult`; they do not enqueue them.

---

## Application ingestion envelope (not a domain entity)

`StructuredIngestionResult[T]` is an **application orchestration contract** defined in `energy_trading.application.ports`. It is a frozen generic envelope, not a new persisted domain data entity and not a duplicate of the Pydantic models above.

It references only:

- canonical records (`tuple[T, ...]`, `T` bound to `CanonicalModel`)
- `AdapterDiagnostic`
- `DLQRecord`

It never embeds a raw source payload. Failed raw data stays outside the application and is referenced solely through `DLQRecord.payload_reference`.

Valid batch outcomes include complete success, partial success, complete normalization failure, and a valid empty source. Emptiness is not automatically treated as malformed data.

---

## Application extraction envelope (not a domain entity)

`ExtractedDocumentChunk` and `DocumentExtractionResult` are **application orchestration contracts** defined in `energy_trading.application.ports`. They are frozen dataclasses, not canonical business/domain entities and not a substitute for `RegulatoryConstraint`.

`ExtractedDocumentChunk` fields:

- `document_id` (non-empty opaque identifier; surrounding whitespace stripped)
- `chunk_id` (non-empty opaque identifier; surrounding whitespace stripped)
- `ordinal` (integer `>= 0`; not required to equal page number or be contiguous)
- `text` (non-empty after trimming)
- optional `page_number` (`>= 1` when present)

`DocumentExtractionResult` fields:

- `source_name` (non-empty; surrounding whitespace stripped)
- `document_id` (non-empty; surrounding whitespace stripped)
- `chunks` (`tuple[ExtractedDocumentChunk, ...]`)
- `diagnostics` (`tuple[AdapterDiagnostic, ...]`)
- `dlq_records` (`tuple[DLQRecord, ...]`)

Invariants:

- collection fields are immutable tuples
- every chunk's `document_id` equals the result `document_id`
- `chunk_id` values are unique within one result
- no raw document bytes, filesystem paths, URLs, OCR-provider schemas, embeddings, bounding boxes, or arbitrary metadata dictionaries
- failed raw data stays outside the application and is referenced solely through `DLQRecord.payload_reference`

Extracted text is **not** an authoritative regulatory constraint. Future retrieval/interpretation may later produce `RegulatoryConstraint` values, including optional `source_document_id` provenance.

Valid outcomes include complete success, partial extraction, complete extraction/normalization failure, and a document that yields no normalized text.

---

## Intentionally deferred contracts

Additional contracts (tariff tables, official bid-message envelopes, imbalance components, user/identity) will be added when a chunk has verified requirements. Do not pre-create parallel “shadow” schemas in application code.
