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
  - [x] **Chunk 69** — OpenAI Regulatory Constraint Inference Infrastructure Adapter
  - [x] **Chunk 70** — Async OpenAI Client & Typed Settings Foundation — Offline
  - [x] **Chunk 71** — Regulatory Intelligence Provider Runtime Composition — Offline
  - [x] **Chunk 72** — Regulatory Intelligence Runtime Settings Boundary — Offline
  - [x] **Chunk 73** — Regulatory Intelligence Configured Runtime Composition — Offline
  - [x] **Chunk 74** — Managed Regulatory Intelligence Runtime Lifecycle — Offline
  - [x] **Chunk 75** — Regulatory Intelligence Settings-Loaded Managed Runtime Composition — Offline
  - [x] **Chunk 76** — Regulatory Intelligence FastAPI Lifespan Boundary — Unwired
  - [x] **Chunk 77** — Regulatory Intelligence `create_app()` Lifespan Installation — No Service Exposure
  - [x] **Chunk 78** — Regulatory Intelligence FastAPI Lifespan Service Exposure
  - [x] **Chunk 79** — Regulatory Intelligence FastAPI Service Accessor Boundary — No HTTP Route
  - [x] **Chunk 80** — Regulatory Intelligence HTTP Query Transport Contracts — Offline
  - [x] **Chunk 81** — Regulatory Intelligence HTTP Query Route Boundary — Unwired
  - [x] **Chunk 82** — Regulatory Intelligence Production Router Installation
  - [x] **Chunk 83** — OpenAI Document Chunk Embedding Infrastructure Adapter
  - [x] **Chunk 84** — Document Vector Index Entry Preparation Service — Application-only
  - [x] **Chunk 85** — Document Vector Index Execution Service — Application-only
  - [x] **Chunk 86** — Document Vector Index Provider-Neutral Composition Root
  - [x] **Chunk 87** — Provider-Aware Document Vector Index Composition — Offline
  - [x] **Chunk 88** — Document Vector Index Runtime Settings Boundary — Offline
  - [x] **Chunk 89** — Document Vector Index Configured Runtime Composition — Offline
  - [x] **Chunk 90** — Managed Document Vector Index Runtime Lifecycle — Offline
  - [x] **Chunk 91** — Settings-Loaded Document Vector Index Runtime — Offline
  - [x] **Chunk 92** — Document Vector Index Lifespan Boundary — Offline
  - [x] **Chunk 93** — Production FastAPI Lifespan Composition Boundary — Unwired
  - [x] **Chunk 94** — Production create_app Composite Lifespan Installation
  - [x] **Chunk 95** — Document Vector Index FastAPI Lifespan Service Exposure
  - [x] **Chunk 96** — Document Vector Index FastAPI Service Accessor Boundary — No HTTP Route
  - [x] **Chunk 97** — Document Vector Index HTTP Request Transport Contract — Offline, No Route
  - [x] **Chunk 98** — Document Vector Index HTTP Route Boundary — Unwired
  - [x] **Chunk 99** — Document Vector Index Production Router Installation
  - [x] **Chunk 100** — Concrete PDF Text Extraction Infrastructure Adapter — No OCR, Unwired
  - [x] **Chunk 101** — Document Extraction → Vector Index Execution Service — Application-only, Unwired
  - [x] **Chunk 102** — PDF Extraction-to-Index Composition Root — API-owned, Unwired
  - [x] **Chunk 103** — Settings-Loaded PDF Extraction-to-Index Runtime Composition — Offline, Unwired
  - [x] **Chunk 104** — One-Shot Loaded PDF Extraction-to-Index Execution — Explicit-call only, Unwired
  - [x] **Chunk 105** — Qdrant Document Collection Readiness Verification — Verify-only, Unwired
  - [x] **Chunk 106** — Qdrant Document Collection Creation — Explicit Distance, Create-only, Unwired
  - [x] **Chunk 107** — Qdrant Document Collection Readiness with Explicit Expected Distance — Verify-only, Unwired
  - [x] **Chunk 108** — Qdrant Document Collection Ensure — Create-if-Missing, Verify-if-Present, Explicit Distance, Unwired
  - [x] **Chunk 109** — Explicit Qdrant Document-Vector Distance Configuration — No Default, Unwired
  - [x] **Chunk 110** — Configured Document-Index Qdrant Collection Ensure Composition — Unwired
  - [x] **Chunk 111** — Document Vector Index Runtime Collection Provisioning — Same Managed Qdrant Client
  - [x] **Chunk 112** — Configured Regulatory Qdrant Collection Readiness Verification — Unwired
  - [x] **Chunk 113** — Regulatory Runtime Collection Readiness Verification — Same Managed Qdrant Client
  - [x] **Chunk 114** — Regulatory Intelligence Workflow Step Contract — Unwired
  - [x] **Chunk 115** — Regulatory Intelligence Workflow Context Port — Unwired
  - [x] **Chunk 116** — Regulatory Intelligence Workflow Node Adapter — Application-only, LangGraph-unwired
  - [x] **Chunk 117** — Regulatory Intelligence LangGraph Contract-Phase Node Wiring — Terminal Slice
- [ ] Pricing & Sales Agent
- [ ] Contract-phase graph slice

## Phase 6 — ML feature pipelines and forecasting

Phase 6 forecasting work is experimental and evidence-driven. This is a **future planning requirement**, not an implementation authorization.

For both Consumer Load Forecast Agent and DAM Price Forecast Agent, the future process should include:

```text
data preparation
→ simple time-series baselines
→ feature engineering
→ walk-forward / rolling backtesting
→ LightGBM experiments
→ XGBoost experiments
→ justified hyperparameter experiments
→ comparison
→ champion model selection
→ serialization
→ inference integration
→ monitoring/retraining policy
```

Do not use naive random train/test splitting if it leaks future information. Prefer chronological expanding/rolling validation. Complex models must beat meaningful simple baselines before being considered successful.

Example baseline families (planning only):

- **Load:** same hour yesterday; same hour previous week; rolling/seasonal baseline
- **Price:** appropriate naive/seasonal DAM-price baselines

No model is considered complete merely because it trains or runs.

Future evaluation should not rely only on one aggregate metric. Where data supports it, evaluate regimes such as peak/off-peak, weekday/weekend, seasonality, extreme temperatures, high-volatility price periods, and generation/hydro stress periods. Later, after risk/trading contracts exist, forecast evaluation should connect to controlled downstream business outcomes:

```text
forecast
→ risk decision
→ bid
→ historical/simulated market outcome
→ P&L / penalties / risk
```

Do not implement trading-objective optimization now.

- [x] **Chunk 118** — Consumer Load Forecast Model Port — Typed ML Boundary, Unwired
- [x] **Chunk 119** — Consumer Load Forecast Agent — Typed Model-Port Delegation, Unwired
- [x] **Chunk 120** — DAM Price Forecast Model Port — Typed ML Boundary, Unwired
- [x] **Chunk 121** — DAM Price Forecast Agent — Typed Model-Port Delegation, Unwired
- [x] **Chunk 122** — Forecasting Plan Contract — Application-only, Framework-neutral, Unwired
- [x] **Chunk 123** — Forecasting Success Aggregate Contract — Application-only, Framework-neutral, Unwired
- [x] **Chunk 124** — Forecasting Execution Port — Async, Application-only, Framework-neutral, Unwired
- [x] **Chunk 125** — Forecasting Workflow Context Port — Typed Plan/Success Context Boundary, Unwired
- [x] **Chunk 126** — Forecasting Workflow Step — Application-only orchestration composition, Unwired
- [x] **Chunk 127** — Forecasting Success Transition — Pure application state transition, Unwired
- [x] **Chunk 128** — LangGraph Phase 3 Forecasting Workflow-Step Invocation — All-Success Path, Success Transition Still Unwired
- [x] **Chunk 129** — LangGraph Phase 3 Forecasting Success Transition Wiring
- [x] **Chunk 130** — In-Memory Forecasting Workflow Context Adapter — Local/Dev Reference
- [x] **Chunk 131** — Consumer Load Forecast Explicit Inference Identity Contract
- [x] **Chunk 132** — Consumer Load Forecast Previous-Day Persistence Baseline — ML-owned, Unwired
- [x] **Chunk 133** — Consumer Load Previous-Day Persistence Backtest Cases — ML-owned, Unwired
- [x] **Chunk 134** — Consumer Load Previous-Day Persistence MAE Evaluation — ML-owned, Unwired
- [x] **Chunk 135** — Consumer Load 24-Hour Lag Feature Rows — ML-owned, Unwired
- [x] **Chunk 136** — Consumer Load Chronological Feature Split — ML-owned, Unwired
- [x] **Chunk 137** — Consumer Load Lag-24h Linear Regression Fit — ML-owned, Unwired
- [x] **Chunk 138** — Consumer Load Lag-24h Linear Regression Prediction — ML-owned, Unwired
- [x] **Chunk 139** — Consumer Load Lag-24h Linear Regression MAE Evaluation — ML-owned, Unwired
- [x] **Chunk 140** — Consumer Load Persistence-vs-Trained OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 141** — Consumer Load Lag-24h + Lag-168h Feature Rows — ML-owned, Unwired
- [x] **Chunk 142** — Consumer Load Lag-24h + Lag-168h Chronological Feature Split — ML-owned, Unwired
- [x] **Chunk 143** — Consumer Load Lag-24h + Lag-168h Linear Regression Fit — ML-owned, Unwired
- [x] **Chunk 144** — Consumer Load Lag-24h + Lag-168h Linear Regression Prediction — ML-owned, Unwired
- [x] **Chunk 145** — Consumer Load Lag-24h + Lag-168h Linear Regression MAE Evaluation — ML-owned, Unwired
- [x] **Chunk 146** — Consumer Load One-Feature OLS vs Two-Feature OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 147** — Consumer Load Persistence vs Two-Feature OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 148** — Consumer Load Three-Way Persistence vs One-Feature OLS vs Two-Feature OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 149** — Consumer Load Lag-24h + Lag-168h OLS Forecast Model Adapter — ML-owned Candidate Live Model, Unwired
- [x] **Chunk 150** — Parallel Forecasting Execution Service — Application-owned Concurrent ForecastingExecutionPort Implementation, Unwired
- [x] **Chunk 151** — Forecasting Failure Transition — Application-owned, Framework-neutral, Unwired
- [x] **Chunk 152** — Forecasting Agent Failure Attribution — Application-owned, LangGraph-free
- [x] **Chunk 153** — Forecasting ExceptionGroup Attribution Extraction — Application-owned, LangGraph-free
- [x] **Chunk 154** — Forecasting Failure Fact and Single-Leaf Classification — Application-owned, Framework-neutral
- [x] **Chunk 155** — Forecasting Tuple Failure Classification — Application-owned, Framework-neutral
- [x] **Chunk 156** — Forecasting Failure Selection Port — Application-owned, Framework-neutral
- [x] **Chunk 157** — Strict Single Forecasting Failure Selector — Application-owned, Framework-neutral
- [x] **Chunk 158** — Forecasting Attempt-Number Source Contract — Application-owned, Framework-neutral
- [x] **Chunk 159** — Forecasting Failure-Policy Context Builder — Application-owned, Framework-neutral
- [x] **Chunk 160** — Forecasting Failure Context Resolution Service — Application-owned, Framework-neutral
- [x] **Chunk 161** — Forecasting Failure Context Preparation Service — Application-owned, Framework-neutral
- [x] **Chunk 162** — Initial Forecasting Attempt Number Source — Application-owned, Stateless, Framework-neutral
- [x] **Chunk 163** — Initial Forecasting Failure Policy — Application-owned, Stateless, Framework-neutral
- [x] **Chunk 164** — Forecasting Failure Decision Service — Application-owned, Framework-neutral
- [x] **Chunk 165** — Forecasting Failure Action Execution — Terminal FAIL Only
- [x] **Chunk 166** — Forecasting Failure Handling Service — Prepared Context to State
- [x] **Chunk 167** — Forecasting Failure Runtime Handling Service — Raw Exception Group to Terminal State
- [x] **Chunk 168** — LangGraph Forecasting Failure Capture and Terminal Routing
- [x] **Chunk 169** — DAM Price Forecast Explicit Inference Identity Contract
- [x] **Chunk 170** — DAM Price Forecast Previous-Day Persistence Baseline
- [x] **Chunk 171** — DAM Price Previous-Day Persistence Backtest Cases — ML-owned, Unwired
- [x] **Chunk 172** — DAM Price Previous-Day Persistence MAE Evaluation — ML-owned, Unwired
- [x] **Chunk 173** — DAM Price Exact 24-Hour Lag Feature Rows — ML-owned, Unwired
- [x] **Chunk 174** — DAM Price Chronological Feature Split — ML-owned, Unwired
- [x] **Chunk 175** — DAM Price Lag-24h Linear Regression Fit — ML-owned, Unwired
- [x] **Chunk 176** — DAM Price Lag-24h Linear Regression Prediction — ML-owned, Unwired
- [x] **Chunk 177** — DAM Price Lag-24h Linear Regression MAE Evaluation — ML-owned, Unwired
- [x] **Chunk 178** — DAM Price Persistence-vs-Trained OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 179** — DAM Price Exact 24-Hour + 168-Hour Lag Feature Rows — ML-owned, Unwired
- [x] **Chunk 180** — DAM Price 24h+168h Chronological Feature Split — ML-owned, Unwired
- [x] **Chunk 181** — DAM Price 24h+168h Linear Regression Fit — ML-owned, Unwired
- [x] **Chunk 182** — DAM Price 24h+168h Linear Regression Prediction — ML-owned, Unwired
- [x] **Chunk 183** — DAM Price 24h+168h Linear Regression MAE Evaluation — ML-owned, Unwired
- [x] **Chunk 184** — DAM Price One-Feature OLS vs Two-Feature OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 185** — DAM Price Persistence vs Two-Feature OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 186** — DAM Price Three-Way Persistence vs One-Feature vs Two-Feature OLS Aligned MAE Comparison — ML-owned, Unwired
- [x] **Chunk 187** — DAM Price 24h+168h OLS Candidate Live Adapter — ML-owned, Unwired
- [x] **Chunk 188** — Forecasting Execution Composition from Injected Model Ports — API-owned, Unwired
- [x] **Chunk 189** — Forecasting Workflow Step Composition from Injected Ports — API-owned, Unwired
- [x] **Chunk 190** — Forecasting Stack Composition from Injected Model and Context Ports — API-owned, Unwired
- [x] **Chunk 191** — Forecasting Failure Runtime Composition from Injected Policy Ports — API-owned, Unwired
- [x] **Chunk 192** — Offline Phase-3 Forecasting Vertical Slice — Integration Verification, No Production Wiring
- [x] **Chunk 193** — Forecasting Success Read Port — Application-owned, Unwired
- [x] **Chunk 194** — In-Memory Forecasting Success Snapshot Reader — Infrastructure-owned, Unwired
- [x] **Chunk 195** — In-Memory Forecasting Read-After-Write Context — Infrastructure-owned, Unwired
- [x] **Chunk 196** — Offline Forecasting Graph Read-After-Write Integration Verification — Test-only, No Production Wiring
- [ ] Shared ML utilities (`ml/common`)
- [ ] Load feature pipeline + model training/inference path
- [ ] Price feature pipeline + model training/inference path
- [ ] Consumer Load Forecast Agent (ML-backed)
- [ ] DAM Price Forecast Agent (ML-backed)
- [ ] LightGBM/XGBoost
- [ ] Generic ML framework
- [ ] DAM ML adapters
- [ ] Phase-3 runtime execution

## Phase 7 — Risk + trading

- [x] **Chunk 197** — Portfolio & Risk Assessment Request and Port Boundary — Application-owned, Unwired (published at `58b61091dbf18948c0e746f4d3181b9ddfb21640`, tag `chunk-197`)
- [x] **Chunk 198** — Portfolio & Risk Agent — Typed Assessment-Port Delegation, Application-owned, Unwired (published at `9df9913d2b4ec4e3eeaaf70dc9dc4561d9c12e11`, tag `chunk-198`)
- [x] **Chunk 199** — Portfolio & Risk Forecast-to-Assessment Execution Service — Application-owned, Unwired (published at `8fb8bf163f8789b7268e1aa00ddff0fb9089aa28`, tag `chunk-199`)
- [x] **Chunk 200** — Offline Forecasting-to-Portfolio Risk Handoff Vertical Slice — Integration Verification, No Production Wiring (published at `25efd7688e25ee8690a9e734f504be7d0af332fb`, tag `chunk-200`)
- [x] **Chunk 201** — Portfolio & Risk Execution Composition Builder — API-owned, Caller-supplied Ports, Unwired (published at `33a143c54265d7b4535ea1f948d8bb05fd33be51`, tag `chunk-201`)
- [x] **Chunk 202** — Trading Strategy Bid Proposal Request and Port Boundary — Application-owned, Unwired (published at `7ca2c3688b39ae3a245740b3231eafef58c35a3e`, tag `chunk-202`)
- [x] **Chunk 203** — Trading Strategy Agent — Typed Bid-Port Delegation, Application-owned, Unwired (published at `ff23382d95193f9cabc8f92649b3bef07f46d5cb`, tag `chunk-203`)
- [x] **Chunk 204** — Trading Strategy Bid Proposal Execution Service — Application-owned, Explicit Inputs, Unwired (published at `4d9a2540d728d45057adbd26b364aa151d1ed8bf`, tag `chunk-204`)
- [x] **Chunk 205** — Offline Forecasting-to-Trading Strategy Vertical Slice — Real Graph and Application Services, Test-only Decision Ports (published at `0941bec11e01259bcd828775631e22a4b758ed05`, tag `chunk-205`)
- [x] **Chunk 206** — Trading Strategy Execution Composition Builder — API-owned, Caller-supplied Bid Port, Unwired (published at `d6b98148f51322f43cfaf655d0598ee00950afd5`, tag `chunk-206`)
- [x] **Chunk 207** — Risk & Bid Proposal Handoff Result Contract — Immutable, Application-owned, Unwired (published at `d04fdf4dbc14ad5b9072100dd2837bc46a1eda13`, tag `chunk-207`)
- [x] **Chunk 208** — Trading Strategy Proposal Handoff Execution Service — Explicit Upstream Results, Unwired (published at `8c71a22f0e1513c8981583170c2ce9026cbeecd8`, tag `chunk-208`)
- [x] **Chunk 209** — Trading Strategy Proposal Handoff Composition Builder — API-owned, Reuses Existing Stack, Unwired (published at `926c0dd2d2632433cc94b4db8076a8d5ca04cda3`, tag `chunk-209`)
- [x] **Chunk 210** — Offline Forecasting-to-Risk-and-Bid Proposal Handoff Integration Verification — Test-only, No Production Wiring (local, unpublished)
- [ ] Portfolio & Risk Agent (parent capability; Chunk 198 adds only the thin delegate Chunk 199 only the unwired forecast-read-to-agent use case, Chunk 200 only offline test-only handoff evidence with a deterministic assessment fake, Chunk 201 only an API-owned, construction-only builder over caller-supplied ports, Chunk 205 only offline test-only forecast-to-risk-to-bid handoff evidence, Chunk 210 only offline test-only forecast-to-risk-to-proposal-handoff evidence, and Chunk 207 only an immutable, unwired `RiskAndBidProposalHandoff` record that can carry an already-obtained `RiskAssessment` without implying approval — a real assessment implementation and Phase 4 integration remain absent)
- [ ] Trading Strategy Agent (parent capability; Chunk 202 adds only the application-owned, unwired bid proposal request/port boundary, Chunk 203 only the thin, unwired `TradingStrategyAgent` delegate over that port, Chunk 204 only the unwired `TradingStrategyExecutionService` request-assembly and delegation use case over explicit caller-supplied inputs, Chunk 205 only offline test-only forecast-to-risk-to-bid handoff evidence with a deterministic bid fake, and Chunk 206 only an API-owned, unwired, construction-only `build_trading_strategy_execution_service` over one caller-supplied bid port that selects no bid engine or market policy, and Chunk 207 only the immutable, unwired `RiskAndBidProposalHandoff` data record over the forecasting result, risk assessment, and `tuple[MarketBid, ...]` proposals with no coordinator, approval, eligibility, or submission semantics, and Chunk 208 only the unwired `TradingStrategyProposalHandoffService` that awaits the published execution service once and wraps its exact proposals in one `RiskAndBidProposalHandoff` from caller-supplied forecasting and risk results, with no forecast retrieval, risk calculation, coordinator, approval, eligibility, or submission semantics, and Chunk 209 only an API-owned, unwired, construction-only `build_trading_strategy_proposal_handoff_service` that reuses the Chunk 206 builder and wraps its execution service in one `TradingStrategyProposalHandoffService` without executing anything, and Chunk 210 only offline test-only evidence that test-sequenced real Portfolio Risk and proposal handoff stacks return the published `RiskAndBidProposalHandoff` with deterministic assessment and bid fakes — automatic Risk & Bid orchestration, forecast snapshot consistency across stages, a concrete bid-generation port implementation, bidding algorithms, risk-approval and bid-eligibility policy, full Risk & Bid execution, production execution, actual bid formation, quantitative risk, market gateway, settlement, and production graph integration remain absent)
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

- **Completed:** Chunks 0–210 implemented locally
- **Latest published checkpoint:** Chunk 209 / `926c0dd2d2632433cc94b4db8076a8d5ca04cda3` (short `926c0dd`, tag `chunk-209`)
- **Next:** Chunks 0–210 implemented locally. Latest published checkpoint: Chunk 209 / `926c0dd2d2632433cc94b4db8076a8d5ca04cda3` (short `926c0dd`, tag `chunk-209`, subject `feat: add chunk 209 trading strategy proposal handoff composition builder`). Chunk 210 (Offline Forecasting-to-Risk-and-Bid Proposal Handoff Integration Verification — Test-only, No Production Wiring) implemented/validated locally but unpublished. Next chunk is not selected. Chunk 211 is not authorized. Published Chunk 209 baseline: 5706 passed, 38 skipped, 1 known warning (Starlette BlockingPortal deprecation); architecture suite 1983 passed; Ruff passed; format 731 files already formatted; mypy 255 source files clean; uv lock check passed; diff check passed. Local unpublished Chunk 210 validation: 5717 passed, 38 skipped, 1 known warning (Starlette BlockingPortal deprecation); architecture suite 1983 passed (unchanged; no architecture test added or amended); Ruff passed; format 732 files already formatted; mypy 255 source files clean (production source unchanged); uv lock check passed; diff check passed; targeted Chunk 210 test module 11 passed (mypy clean); Chunk 205 vertical slice 8 passed; Chunk 201 Portfolio Risk stack 11 passed; Chunk 209 proposal handoff stack 19 passed; Chunk 208 proposal handoff service 19 passed; Chunk 196 graph read-after-write 9 passed; Chunk 192 Phase 3 vertical slice 13 passed; Chunk 200 forecasting-to-Portfolio Risk vertical slice 6 passed. Superseded Chunk 209 local validation (now published): 5706 passed, 38 skipped, 1 known warning (Starlette BlockingPortal deprecation); architecture suite 1983 passed (1967 baseline + 12 new Chunk 209 proposal-handoff-stack-boundary tests + 1 new positive test in each of the four amended historical modules `tests/architecture/test_trading_strategy_bid_boundary.py`, `tests/architecture/test_trading_strategy_proposal_handoff_boundary.py`, `tests/architecture/test_trading_strategy_stack_boundary.py`, and `tests/architecture/test_trading_strategy_execution_boundary.py`); Ruff passed; format 731 files already formatted; mypy 255 source files clean; uv lock check passed; diff check passed; targeted Chunk 209 unit 19 passed; targeted Chunk 209 architecture 12 passed; amended `test_trading_strategy_bid_boundary.py` 16 passed, `test_trading_strategy_proposal_handoff_boundary.py` 16 passed, `test_trading_strategy_stack_boundary.py` 16 passed, and `test_trading_strategy_execution_boundary.py` 19 passed; Chunk 202 bid request 43 unit passed; Chunk 203 agent 13 unit passed; Chunk 204 execution 23 unit passed; Chunk 205 vertical slice 8 passed; Chunk 206 stack 12 unit passed; Chunk 207 handoff 46 unit + 15 architecture passed; Chunk 208 proposal handoff 19 unit passed; `test_orchestration_state_boundary.py` 6 passed; both new test modules and the four amended test modules mypy clean. The parent Risk & Bid workflow, quantitative risk, bidding algorithms, eligibility, submission, and settlement remain incomplete.

---

## Project Completion Targets / Planning Horizon

These figures are **estimates**, **planning targets**, and **subject to revision**. They are not guarantees or architecture invariants. `chunk-240` is not a mandatory stopping point; the project ends when required engineering goals are actually complete.

Approximate milestone bands (planning estimates; later chunks must not be forced to match these bands):

- **~Chunk 120–150** — the system should begin looking like a real integrated platform
- **~Chunk 170–200** — large portions of the 13-agent end-to-end flow should be runnable
- **~Chunk 220+** — experiments, hardening, observability, edge cases, production quality

Do not create checkboxes for all numbers through 240.

The first 80+ chunks established reusable patterns (ports, canonical DTOs, error contracts, async conventions, composition roots, provider adapters, settings patterns, lifespan patterns, architecture tests, publication discipline). Some later agents/features may therefore implement faster. Velocity will still vary and will slow in empirical areas: ML experiments, real datasets, feature engineering, backtesting, market validation, live integrations, edge cases, and production hardening. Do not assume linear acceleration.

**Engineering/platform completion** (planning target: roughly first half / middle of October 2026) is distinct from **Armenia-specific live trading validation**. The latter requires authoritative real data and market validation; its date cannot honestly be predicted until those sources are available. Future status wording may be: `Armenia-specific model calibration and live-market validation pending authoritative data access.`

Lack of authoritative Armenian market data must not stop unrelated platform engineering. Preserve the ACL: API / Excel / CSV / manual file / scraper / public dataset / synthetic dataset → source-specific Adapter / ACL → canonical internal model → rest of platform. Source schemas remain replaceable.

Three planning data levels (not implemented by this chunk):

1. **Level 1 — Synthetic / fixture data** validates engineering (ingestion, forecast pipelines, risk, trading, settlement, orchestration). It may include realistic seasonality, hourly peaks, weather influence, noise, missing intervals, anomalies, and price volatility. Synthetic data proves that the engineering system works. It does **not** prove that the model performs well on the real Armenian market.
2. **Level 2 — Public / proxy datasets** may validate ML engineering, backtesting infrastructure, and general forecasting behavior. They are not Armenia-specific model-quality evidence.
3. **Level 3 — File-first future integration** of authoritative data through messy Excel, CSV, API, manual files, or scraped sources must enter via source-specific adapters/ACL. Unreadable/unmappable inputs follow existing diagnostic/DLQ policy.
