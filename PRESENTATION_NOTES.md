# Presentation Notes

Tracking what is demo-ready versus still conceptual. Update when architecture, ML, or UX becomes showable.

## Current presentation-worthy points (conceptual)

These can be spoken to from documentation and (for contracts) from executable domain models; there is **no running trading demo**.

- **13-agent architecture** covering regulation, pricing, weather/renewables, hydro, availability, news, market monitoring, ML load and price forecasts, risk, strategy, settlement, and a Chief Orchestrator Agent.
- **Clean Architecture** with a strict dependency rule (`domain` isolated; infrastructure behind ports).
- **Anti-Corruption Layer** so CSV/Excel/PDF/API/scrape schemas never reach agents or models.
- **Canonical contracts:** External data variability is isolated by mapping everything into strict canonical contracts before agents/ML see it.
- **Resilience:** Every API failure receives a correlation ID that links a sanitized client response to internal structured logs.
- **ML vs LLM separation:** forecasts from XGBoost/LightGBM (optional Prophet); LLMs for regulatory/news reasoning only.
- **Data-agnostic ingestion strategy:** schema detection and semantic mapping into canonical contracts (MW, UTC timestamps, Decimal money).
- **DLQ / resilience:** unnormalizable records park instead of crashing the DAM workflow.
- **Armenian DAM business flow:** five phases — contract/regulatory alignment → parallel ingestion → forecasting → portfolio/risk/strategy → clearing/billing/settlement.

## Placeholders (not yet available)

| Artifact | Status |
| --- | --- |
| Architecture screenshots | Placeholder — add after diagrams exist |
| Canonical contract diagram | Placeholder — Messy external schemas → Adapter Layer → Canonical Pydantic Contracts → Agents / ML |
| LangGraph visualization | Placeholder — graph not implemented |
| ML metrics | Placeholder — no experiments (`EXPERIMENT_LOG.md`) |
| Forecasting plots | Placeholder |
| API 500 response with correlation ID ↔ matching JSON application log | Placeholder — add after a screenshot exists |
| API demo | Placeholder — health + error envelope exist; business endpoints TBD |
| End-to-end trading demo | Placeholder |
| Settlement example | Placeholder — official rules unverified |

## Talk track notes

- Stress that the platform is **decision support**, not the official market system.
- Do not claim verified Armenian gate times, currencies, or bid formats until they are sourced.
- Hardware story: Windows 11 + WSL2, 8 GB WSL RAM budget, on-demand services rather than a full always-on stack.
