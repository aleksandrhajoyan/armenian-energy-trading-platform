# Agents — AI Energy Trading Platform

Compact specification for all 13 agents. Names in this file are canonical. Do not rename or invent aliases in code or docs.

**Status:** specification only. No agent is implemented. Canonical input/output contracts are implemented in `energy_trading.domain.models`.

Agents live in the application layer. They consume and return canonical typed contracts (`DATA_CONTRACTS.md`). They never import concrete infrastructure adapters or concrete ML implementations; they depend on application ports. The composition root injects implementations from `infrastructure` and `ml`.

## Agent kinds

| Kind | Meaning |
| --- | --- |
| LLM / reasoning | Uses a language model over canonical text/constraints. Must not emit numerical forecasts. |
| Deterministic service | Rules, arithmetic, and I/O via ports. No LLM required for the core result. |
| ML-backed | Calls forecasting services through injected application ports implemented by `ml`. An LLM must not calculate the forecast. Agents must never import XGBoost, LightGBM, Prophet, or concrete model classes. |
| Orchestration | Owns workflow graph, state, retries, fallback. Thin nodes only. |

Hybrid agents may attach an LLM **narrative** to a deterministic or ML result. The numerical payload remains owned by the non-LLM path.

External tools listed below are **capability classes**, not vendor products. Concrete API providers are not chosen in this chunk.

---

## 1. Regulatory Intelligence Agent

- **Kind:** LLM / reasoning (RAG)
- **Purpose:** Interpret market rules, licenses, and regulatory documents into structured constraints the rest of the workflow can enforce.
- **Canonical inputs:** retrieved document chunks (infrastructure-normalized), `RegulatoryConstraint` drafts, workflow/correlation ID, delivery-day window.
- **Canonical outputs:** `RegulatoryConstraint` set; `AdapterDiagnostic` as needed.
- **External tools/systems (eventual):** unstructured document adapters, OCR/extraction port, Qdrant retrieval port, LLM provider port.
- **Dependencies:** Chief Orchestrator Agent (invocation); unstructured ACL; Qdrant. Does not call ML forecast modules.
- **Failure behavior:** If retrieval or LLM inference fails, emit diagnostics, keep previously valid constraints if the orchestrator policy allows, and never invent enforceable numeric limits. Unreadable documents follow the unstructured ACL / DLQ path.

## 2. Pricing & Sales Agent

- **Kind:** Hybrid — deterministic commercial arithmetic; LLM only for interpreting unstructured commercial terms
- **Purpose:** Translate tariffs, contract positions, and sales commitments into canonical commercial constraints and target volumes/prices for strategy — not unofficial DAM clearing.
- **Canonical inputs:** `RegulatoryConstraint`, contract/tariff canonical records (to be defined when verified), historical `MarketPriceRecord`, optional `LoadForecastPoint`.
- **Canonical outputs:** canonical commercial constraint / pricing intent objects (exact contract TBD when products are verified); never raw spreadsheet rows.
- **External tools/systems (eventual):** structured adapters for contract/tariff files; persistence port; LLM port for narrative clause extraction only.
- **Dependencies:** Regulatory Intelligence Agent outputs; canonical price history. Does not replace DAM Price Forecast Agent.
- **Failure behavior:** Missing tariff tables → DLQ/diagnostics and no silent default prices. LLM extraction failures must not fabricate AMD/MWh (or any currency) figures.

## 3. Weather & Renewable Forecast Agent

- **Kind:** Deterministic service (optional future ML in `ml/`, never LLM-calculated weather)
- **Purpose:** Provide canonical weather and renewable-resource forecasts used as features and operational context.
- **Canonical inputs:** adapter-normalized weather/renewable payloads (never raw vendor schemas); location and horizon identifiers.
- **Canonical outputs:** `WeatherRecord` series.
- **External tools/systems (eventual):** weather/renewable source adapters (HTTP, files, or scrapers — providers TBD), time-series cleaning, persistence.
- **Dependencies:** ACL structured adapters; persistence. Parallel with other Phase 2 agents.
- **Failure behavior:** Source outage → orchestrator fallback (last good forecast, persistence, or skip with degraded-feature flag). Malformed points → DLQ, not interpolated fiction unless a documented cleaning rule applies.

## 4. Hydro Resources Agent

- **Kind:** Deterministic service
- **Purpose:** Normalize hydro storage, inflow/outflow, and hydro generation availability into canonical records for risk and bidding.
- **Canonical inputs:** adapter-normalized hydro telemetry or operator files.
- **Canonical outputs:** `HydroRecord` series.
- **External tools/systems (eventual):** structured file/API adapters, persistence, time-series cleaning.
- **Dependencies:** ACL; Generation Availability Agent may consume hydro MW but must not scrape hydro files itself.
- **Failure behavior:** Unnormalizable hydro files → DLQ. Do not assume reservoir operating policy that has not been verified.

## 5. Generation Availability Agent

- **Kind:** Deterministic service
- **Purpose:** Assemble plant/unit available capacity (planned outages, derates, technology mix) as canonical MW series.
- **Canonical inputs:** `HydroRecord` (optional), adapter-normalized availability/outage records, `RegulatoryConstraint` that affects operable capacity.
- **Canonical outputs:** `GenerationAvailabilityRecord` series (MW).
- **External tools/systems (eventual):** structured adapters for operator/availability files or APIs (TBD), persistence.
- **Dependencies:** Hydro Resources Agent (when hydro is in the portfolio); ACL. Not an LLM.
- **Failure behavior:** Partial fleet coverage is explicit (missing units listed in diagnostics), not silently treated as zero or full availability unless a documented rule says so.

## 6. News Intelligence Agent

- **Kind:** LLM / reasoning
- **Purpose:** Turn news and public-information items into canonical events that may affect load, outages, or prices — as qualitative context, not as a substitute for ML forecasts.
- **Canonical inputs:** adapter-normalized article/text payloads.
- **Canonical outputs:** `NewsEvent` records with timestamps, relevance, and structured entities when extractable.
- **External tools/systems (eventual):** news/HTML/scraper adapters, LLM provider port, persistence. No named news vendors in this spec.
- **Dependencies:** ACL unstructured/structured adapters; orchestrator. Must not write `PriceForecastPoint` or `LoadForecastPoint`.
- **Failure behavior:** Source or LLM failure → empty event set + diagnostics. Do not hallucinate outage MW or prices. Poison/malformed HTML → DLQ.

## 7. Market Monitoring Agent

- **Kind:** Deterministic service
- **Purpose:** Ingest official or operator-published market observations (historical DAM prices, volumes, status) into canonical time series.
- **Canonical inputs:** adapter-normalized market reports/files/APIs (sources TBD).
- **Canonical outputs:** `MarketPriceRecord` series; later, market-status objects if verified.
- **External tools/systems (eventual):** structured adapters, persistence (TimescaleDB).
- **Dependencies:** ACL. Does not clear the market and does not forecast prices.
- **Failure behavior:** Missing hours / duplicate timestamps handled by time-series cleaning rules or DLQ (`TESTING_STRATEGY.md`). Never silently fill prices.

## 8. Consumer Load Forecast Agent

- **Kind:** ML-backed
- **Purpose:** Produce consumer load forecasts in MW for the DAM horizon.
- **Canonical inputs:** `ConsumptionRecord` history, `WeatherRecord`, calendar/features as canonical structures, `NewsEvent` / `RegulatoryConstraint` only as **features or flags**, not as LLM prompts that output MW.
- **Canonical outputs:** `LoadForecastPoint` series (MW).
- **External tools/systems (eventual):** `ml/load_forecast` (XGBoost / LightGBM / optional Prophet baseline) behind application ports; feature store/persistence; not an LLM calculator.
- **Dependencies:** Phase 2 canonical series; forecasting ports injected by the composition root. Chief Orchestrator Agent invokes this agent. The agent must not import XGBoost, LightGBM, Prophet, or concrete model classes.
- **Failure behavior:** ML runtime failure → documented fallback (previous model, naive baseline, or abort per orchestrator policy). LLM is not an allowed fallback for the numeric forecast.

## 9. DAM Price Forecast Agent

- **Kind:** ML-backed
- **Purpose:** Produce Day-Ahead price forecasts for each delivery interval.
- **Canonical inputs:** `MarketPriceRecord` history, `LoadForecastPoint`, `GenerationAvailabilityRecord`, `WeatherRecord`, `HydroRecord`, `NewsEvent` features/flags, `RegulatoryConstraint` flags.
- **Canonical outputs:** `PriceForecastPoint` series (`EnergyPrice`, currency explicit).
- **External tools/systems (eventual):** `ml/price_forecast` behind application ports; persistence. Not an LLM calculator.
- **Dependencies:** Load forecast and Phase 2 series as available; forecasting ports injected by the composition root. The agent must not import XGBoost, LightGBM, Prophet, or concrete model classes.
- **Failure behavior:** Same policy as load forecast: no LLM-generated prices. Degraded feature sets must be explicit on the output metadata.

## 10. Portfolio & Risk Agent

- **Kind:** Deterministic / quantitative service
- **Purpose:** Combine positions, forecasts, availability, and constraints into a `RiskAssessment` (limits, exposures, scenarios).
- **Canonical inputs:** `LoadForecastPoint`, `PriceForecastPoint`, `GenerationAvailabilityRecord`, `HydroRecord`, `RegulatoryConstraint`, commercial constraints from Pricing & Sales Agent.
- **Canonical outputs:** `RiskAssessment`.
- **External tools/systems (eventual):** persistence; scenario engines in domain/application. LLM may later explain the assessment; it must not compute VaR or MW exposure.
- **Dependencies:** Forecast agents; regulatory and pricing agents. Not ML training.
- **Failure behavior:** Missing critical forecast → refuse to certify risk as complete; return partial assessment with explicit gaps. No silent “risk OK”.

## 11. Trading Strategy Agent

- **Kind:** Hybrid application agent — deterministic bid construction; optional LLM narrative. **Not** numerical forecasting.
- **Purpose:** Form DAM `MarketBid` objects consistent with risk limits, availability, load, and constraints.
- **Canonical inputs:** `RiskAssessment`, `LoadForecastPoint`, `PriceForecastPoint`, `GenerationAvailabilityRecord`, `RegulatoryConstraint`, commercial constraints.
- **Canonical outputs:** `MarketBid` set.
- **External tools/systems (eventual):** persistence; later a market-gateway adapter (official interface TBD — do not invent a vendor).
- **Dependencies:** Portfolio & Risk Agent; forecast agents; regulatory/pricing outputs.
- **Failure behavior:** If risk is incomplete or constraints conflict, emit no bid (or a documented safe default only if a verified rule exists — none yet). LLM must not invent bid MW or prices.

## 12. Billing & Settlement Agent

- **Kind:** Deterministic service
- **Purpose:** Compare bids, `MarketClearingResult`, and metered/canonical energy into `SettlementResult`.
- **Canonical inputs:** `MarketBid`, `MarketClearingResult`, `ConsumptionRecord` / delivered energy canonicals, fee/tariff canonicals when verified.
- **Canonical outputs:** `SettlementResult`.
- **External tools/systems (eventual):** structured adapters for official settlement reports, persistence. Not LLM arithmetic.
- **Dependencies:** Clearing results (ingested via ACL); strategy bids. Official settlement rules TBD.
- **Failure behavior:** Unmatched intervals or unverifiable prices → DLQ/diagnostics, never a silently rounded invoice.

## 13. Chief Orchestrator Agent

- **Kind:** Orchestration (LangGraph, planned)
- **Purpose:** Own graph state, phase routing, parallel Phase 2 join, retries, fallback, diagnostics, and workflow status from contract phase through settlement.
- **Canonical inputs:** workflow command (delivery date, portfolio ID, correlation ID); all agent outputs as canonical state slices.
- **Canonical outputs:** workflow status, aggregated diagnostics, final canonical artifacts (`MarketBid`, `SettlementResult`, etc. as the phase produces them).
- **External tools/systems (eventual):** LangGraph runtime, Redis ephemeral state, persistence for workflow records, logging/observability ports.
- **Dependencies:** All other agents via ports/use cases. Must not call concrete adapters or ML trainers directly; it calls agents/use cases. LangGraph nodes must depend on application abstractions, not concrete infrastructure or ML packages.
- **Failure behavior:** Transient agent/I/O failures retry per policy. Unrecoverable ingestion stays in DLQ; graph continues with degraded flags or stops according to explicit phase policy. Never swallow exceptions. Never ask an LLM to replace ML or settlement math.

---

## Phase mapping (reference)

| Business phase | Agents |
| --- | --- |
| 1. Contract & regulatory alignment | Regulatory Intelligence Agent, Pricing & Sales Agent |
| 2. Parallel ingestion | Weather & Renewable Forecast Agent, Hydro Resources Agent, Generation Availability Agent, News Intelligence Agent, Market Monitoring Agent |
| 3. Forecasting | Consumer Load Forecast Agent, DAM Price Forecast Agent |
| 4. Portfolio, risk & strategy | Portfolio & Risk Agent, Trading Strategy Agent |
| 5. Clearing, billing & settlement | Billing & Settlement Agent |
| All phases | Chief Orchestrator Agent |
