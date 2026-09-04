# Data Contracts — Canonical Models (Planned)

This document specifies **planned** canonical contracts. Python/Pydantic models are **not** implemented yet (Chunk 2).

All application agents, ML components, and domain services speak these contracts only. External column names, Armenian headers, vendor units, and file-specific timestamp strings stop at the Anti-Corruption Layer.

## Cross-cutting rules

- **Power:** megawatts (MW) unless a future verified business contract explicitly requires another representation.
- **Energy:** megawatt-hours (MWh) over an **explicit interval**. Interval length for Armenian DAM (hourly vs other) is **TBD until verified**.
- **Timestamps:** adapters must emit timezone-aware canonical timestamps. Naive datetimes are invalid at the domain boundary. Internal storage timezone strategy (UTC vs market-local) will be decided in implementation; market-local civil time is expected to follow `Asia/Yerevan` but must be confirmed before encoding gate-closure rules.
- **Currency and price unit** (e.g. AMD/MWh): **TBD until verified**. Contracts include a currency/unit field rather than assuming a code.
- **Identifiers:** opaque string IDs. Do not embed vendor primary keys as domain types.
- **Provenance:** records that originate from ingestion should retain `source_system` (logical name) and `ingested_at`, not raw vendor payloads.
- Do **not** encode unverified regulator or DAM bid-format, lot-size, or imbalance-price rules here.

---

## ConsumptionRecord

- **Purpose:** Observed consumer load/consumption at a metering or portfolio grain.
- **Important fields:** `record_id`; `portfolio_or_meter_id`; `interval_start`; `interval_end` (or explicit `interval_minutes`); `power_mw` and/or `energy_mwh` (at least one required; the other may be derived when interval is known); `quality_flag`; `source_system`; `ingested_at`.
- **Units:** `power_mw` in MW; `energy_mwh` in MWh.
- **Time:** timezone-aware `interval_start` / `interval_end`. Missing hours and duplicates are cleaning/DLQ concerns, not silent coalescing.

## WeatherRecord

- **Purpose:** Weather observation or forecast point used as operational context and ML features.
- **Important fields:** `record_id`; `location_id`; `issued_at` (forecasts); `valid_at`; `is_forecast`; `temperature_c`; `relative_humidity_pct`; `wind_speed_ms`; `global_horizontal_irradiance_wm2`; `precipitation_mm`; `source_system`.
- **Units:** °C, percent, m/s, W/m², mm. Adapters convert other unit systems before this contract.
- **Time:** timezone-aware `valid_at` / `issued_at`.

## HydroRecord

- **Purpose:** Hydro storage and flow context plus hydro generation availability.
- **Important fields:** `record_id`; `asset_id`; `valid_at`; `water_level_m`; `inflow_m3s`; `outflow_m3s`; `storage_mcm` (million cubic metres, if provided); `available_generation_mw`; `source_system`.
- **Units:** m, m³/s, million m³, MW. Operating constraints (min/max reservoir) are **not** assumed until verified.
- **Time:** timezone-aware `valid_at`.

## GenerationAvailabilityRecord

- **Purpose:** Available capacity of a unit, plant, or aggregated fleet for a delivery interval.
- **Important fields:** `record_id`; `asset_id`; `interval_start`; `interval_end`; `available_capacity_mw`; `installed_capacity_mw` (optional); `outage_or_derate_flag`; `technology` (canonical enum later); `source_system`.
- **Units:** MW.
- **Time:** timezone-aware interval bounds. Unverified technology taxonomies stay as strings until an enum is justified.

## MarketPriceRecord

- **Purpose:** Observed DAM (or other verified market) price and volume points — history and official publications, not forecasts.
- **Important fields:** `record_id`; `market_code` (e.g. conceptual `AM-DAM` — not an official identifier until verified); `interval_start`; `interval_end`; `price`; `price_currency`; `price_unit` (e.g. per MWh); `volume_mwh`; `source_system`.
- **Units:** volume in MWh; price in explicit currency/unit. Do not assume AMD.
- **Time:** timezone-aware interval bounds.

## NewsEvent

- **Purpose:** Canonical news or public-information event for qualitative context and optional ML features/flags.
- **Important fields:** `event_id`; `published_at`; `ingested_at`; `headline`; `summary`; `language`; `source_system`; `relevance_score` (optional, documented scale later); `entities`; `tags`.
- **Units:** none for text; any extracted numeric claims are **not** load or price forecasts.
- **Time:** timezone-aware `published_at` / `ingested_at`. If source TZ is missing, adapter policy must be explicit or the record goes to DLQ.

## RegulatoryConstraint

- **Purpose:** Structured, enforceable or advisory constraint derived from regulation or licenses.
- **Important fields:** `constraint_id`; `source_document_id`; `effective_from`; `effective_to`; `jurisdiction`; `constraint_type`; `severity` (advisory vs blocking — enum later); `summary`; `structured_parameters` (only keys that survived validation); `citation`.
- **Units:** any numeric parameters must declare unit in-field or via a nested unit object. Do not smuggle “as in the PDF”.
- **Time:** timezone-aware effective window. Unparseable legal dates → unstructured ACL / DLQ, not guessed years.

## LoadForecastPoint

- **Purpose:** ML-produced consumer load forecast for one delivery interval.
- **Important fields:** `forecast_id`; `model_id`; `model_version`; `issued_at`; `interval_start`; `interval_end`; `load_mw`; optional `quantile_p10_mw` / `quantile_p90_mw`; `feature_completeness`; `portfolio_or_meter_id`.
- **Units:** MW (quantiles in MW).
- **Time:** timezone-aware `issued_at` and interval bounds. Produced by `ml/load_forecast`, not by an LLM.

## PriceForecastPoint

- **Purpose:** ML-produced DAM price forecast for one delivery interval.
- **Important fields:** `forecast_id`; `model_id`; `model_version`; `issued_at`; `interval_start`; `interval_end`; `price`; `price_currency`; `price_unit`; optional quantiles; `feature_completeness`; `market_code`.
- **Units:** price with explicit currency/unit; not assumed.
- **Time:** timezone-aware `issued_at` and interval bounds. Produced by `ml/price_forecast`, not by an LLM.

## RiskAssessment

- **Purpose:** Portfolio risk snapshot used as a gate before bidding.
- **Important fields:** `assessment_id`; `portfolio_id`; `as_of`; `horizon_start`; `horizon_end`; `exposures` (MW and monetary, units explicit); `limit_breaches`; `scenario_results`; `is_complete`; `gaps`.
- **Units:** MW for volume risk; monetary amounts with currency TBD.
- **Time:** timezone-aware `as_of` and horizon. Incomplete assessments must set `is_complete=false` rather than omitting gaps.

## MarketBid

- **Purpose:** Intention to buy/sell in the DAM for a delivery interval, ready for a future market gateway.
- **Important fields:** `bid_id`; `portfolio_id`; `interval_start`; `interval_end`; `side` (buy/sell); `quantity_mw`; `price`; `price_currency`; `price_unit`; `status` (draft/submitted/cancelled — enum later); `strategy_id`.
- **Units:** quantity in MW; price with explicit currency/unit. Lot size / tick size **TBD until verified**.
- **Time:** timezone-aware interval bounds. Gate-closure time is **not** encoded until verified.

## MarketClearingResult

- **Purpose:** Official (or operator-published) clearing outcome for an interval, ingested via ACL — not computed by an LLM.
- **Important fields:** `result_id`; `market_code`; `interval_start`; `interval_end`; `clearing_price`; `price_currency`; `price_unit`; `cleared_quantity_mw`; `accepted_bid_ids`; `rejected_bid_ids`; `source_system`.
- **Units:** MW; price with explicit currency/unit.
- **Time:** timezone-aware interval bounds.

## SettlementResult

- **Purpose:** Financial and energy settlement outcome for a period.
- **Important fields:** `settlement_id`; `portfolio_id`; `period_start`; `period_end`; `energy_mwh`; `amount`; `currency`; `fees`; `net_position_mwh`; `source_system`; `is_official`.
- **Units:** MWh; monetary `amount`/`fees` with currency TBD. Imbalance components TBD until rules are verified.
- **Time:** timezone-aware period bounds.

## AdapterDiagnostic

- **Purpose:** First-class telemetry for one adapter run (not a substitute for logs).
- **Important fields:** `diagnostic_id`; `adapter_name`; `source_system`; `started_at`; `finished_at`; `correlation_id`; `records_in`; `records_out`; `records_dlq`; `mapping_issues`; `dropped_fields`; `warnings`.
- **Units:** counts dimensionless; durations derived from timestamps.
- **Time:** timezone-aware `started_at` / `finished_at`.

## DLQRecord

- **Purpose:** Poison / unnormalizable payload parked for later reprocessing.
- **Important fields:** `dlq_id`; `correlation_id`; `workflow_id` (optional); `source_system`; `adapter_name`; `failed_stage` (schema/validation/units/timezone/cleaning); `error_type`; `error_message`; `payload_ref` (URI or blob id — not necessarily inline bytes); `occurred_at`; `retry_count`.
- **Units:** n/a.
- **Time:** timezone-aware `occurred_at`. Payload bodies may retain original naive timestamps; the DLQ envelope itself must be timezone-aware.

---

## Intentionally deferred contracts

Additional contracts (tariff tables, official bid-message envelopes, imbalance components, user/identity) will be added when a chunk has verified requirements. Do not pre-create parallel “shadow” schemas in application code.
