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

- **Completed:** Chunk 0 through Chunk 162 locally
- **Latest published checkpoint:** Chunk 161 / `1ddcdf33f43808dc70ff5c4cd312f2044b149e82`
- **Next:** Chunk 162 implemented/validated locally but unpublished. Next chunk is not selected. Chunk 163 is not authorized. `ConsumerLoadForecastModelRequest` requires caller-supplied `forecast_run_id` and `generated_at` in addition to consumer, MW history, and targets. An ML-owned previous-day persistence baseline (`PreviousDayPersistenceConsumerLoadForecastModel`) now structurally implements `ConsumerLoadForecastModelPort` as exact `T - 24h` MW copy with fail-closed missing/duplicate lag and caller identity passthrough; it remains completely unwired. An ML-owned previous-day persistence backtest-case builder (`PreviousDayPersistenceBacktestCase`, `build_previous_day_persistence_backtest_cases`) now derives chronological exact `T` / `T - 24h` evaluation cases from canonical `ConsumptionRecord` history: missing pairs are skipped, mixed-consumer or duplicate-timestamp history fails closed, canonical MW is copied unchanged, and the builder does not calculate metrics; it remains completely unwired and does not change live-inference fail-closed lag policy. An ML-owned previous-day persistence MAE evaluator (`PreviousDayPersistenceMAEResult`, `evaluate_previous_day_persistence_mae`) now scores already-built cases as MW MAE only: empty input fails closed, RMSE/MSE/MAPE are not calculated, and no generic metrics framework is introduced; it remains completely unwired. An ML-owned exact 24-hour lag feature-row builder (`ConsumerLoadLag24hFeatureRow`, `build_consumer_load_lag_24h_feature_rows`) now derives chronological supervised rows from canonical `ConsumptionRecord` history: the only numerical feature is `lag_24h_mw`, the supervised target is `target_value_mw`, missing exact lags are skipped, mixed-consumer or duplicate-timestamp history fails closed, and no calendar/weather/weekly/rolling features or generic feature framework are introduced; it remains completely unwired and does not depend on Chunk 132–134 inference/backtest/evaluation artifacts. An ML-owned chronological feature-row split (`ConsumerLoadChronologicalFeatureSplit`, `split_consumer_load_feature_rows_chronologically`) now partitions those already-built rows at an explicit UTC cutoff: `training_rows` are `target_timestamp < cutoff`, `evaluation_rows` are `target_timestamp >= cutoff`, both partitions must be non-empty, malformed chronology and mixed consumers fail closed, and no ratio/random/generic dataset split is introduced; it remains completely unwired and does not train a model. An ML-owned lag-24h OLS fit (`ConsumerLoadLag24hLinearRegressionFit`, `fit_consumer_load_lag_24h_linear_regression`) now returns `slope` and signed `intercept_mw` from already-built training rows: one feature `lag_24h_mw`, one target `target_value_mw`, at least two rows, zero feature variance fails closed, mixed consumers and malformed chronology fail closed, and no metric comparison is introduced; it remains completely unwired. An ML-owned lag-24h OLS evaluation prediction (`ConsumerLoadLag24hLinearRegressionPrediction`, `predict_consumer_load_lag_24h_linear_regression`) now applies those already-fitted parameters to already-built evaluation rows: identity and actual target are preserved, negative finite predictions are not clamped, empty/mixed/malformed/non-finite inputs fail closed, and no MAE/RMSE/MAPE is calculated; it remains completely unwired. An ML-owned trained lag-24h OLS MAE evaluator (`ConsumerLoadLag24hLinearRegressionMAEResult`, `evaluate_consumer_load_lag_24h_linear_regression_mae`) now scores already-produced prediction artifacts as MW MAE only: empty input, mixed consumers, and malformed chronology fail closed, negative finite predictions are scored with ordinary absolute error, RMSE/MSE/MAPE and persistence comparison are not calculated, and no generic metrics framework is introduced; it remains completely unwired. An ML-owned aligned persistence-versus-trained OLS MAE comparison (`ConsumerLoadPersistenceVsTrainedOLSMAEComparison`, `compare_consumer_load_persistence_vs_trained_ols_mae`) now requires the same consumer, same target timestamps, same actual MW labels, and equal cohort size, then delegates scoring to the published persistence and trained OLS MAE evaluators: empty/unequal/mixed/mismatched/malformed inputs fail closed, no production-model choice or relative change is computed, and no generic comparison framework is introduced; it remains completely unwired. This comparison machinery does not constitute empirical Armenian-data evidence that either model is better. An ML-owned exact 24-hour plus 168-hour lag feature-row builder (`ConsumerLoadLag24h168hFeatureRow`, `build_consumer_load_lag_24h_168h_feature_rows`) now derives chronological supervised rows from canonical `ConsumptionRecord` history: both exact `T - 24h` and exact `T - 168h` observations are required, missing either lag omits that target, mixed-consumer or duplicate-timestamp history fails closed, canonical MW is copied unchanged, and no imputation, calendar/weather/rolling features, or generic feature framework are introduced; it remains completely unwired, does not modify the published Chunk 135 one-feature contract, and does not split, train, predict, score, or compare. An ML-owned chronological two-lag feature-row split (`ConsumerLoadLag24h168hChronologicalFeatureSplit`, `split_consumer_load_lag_24h_168h_feature_rows_chronologically`) now partitions those already-built Chunk 141 rows at an explicit UTC cutoff: `training_rows` are `target_timestamp < cutoff`, `evaluation_rows` are `target_timestamp >= cutoff`, both partitions must be non-empty, malformed chronology and mixed consumers fail closed, and no ratio/random/generic dataset split or feature rebuilding is introduced; it remains completely unwired, does not modify the published Chunk 136 one-feature splitter, and does not train a model. An ML-owned two-feature OLS fit (`ConsumerLoadLag24h168hLinearRegressionFit`, `fit_consumer_load_lag_24h_168h_linear_regression`) now returns signed `lag_24h_coefficient`, `lag_168h_coefficient`, and `intercept_mw` from already-built training rows: both exact lag features participate, at least three rows are required, a non-positive centered two-feature determinant fails closed, mixed consumers and malformed chronology fail closed, and no metric comparison is introduced; it remains completely unwired, does not modify the published Chunk 137 one-feature fitter, and does not import the Chunk 142 split type. An ML-owned two-feature OLS evaluation prediction (`ConsumerLoadLag24h168hLinearRegressionPrediction`, `predict_consumer_load_lag_24h_168h_linear_regression`) now applies those already-fitted parameters to already-built evaluation rows: identity and actual target are preserved, negative finite predictions are not clamped, empty/mixed/malformed/non-finite inputs fail closed, and no MAE/RMSE/MAPE is calculated; it remains completely unwired, does not modify the published Chunk 138 one-feature predictor, and does not import the Chunk 142 split type. An ML-owned two-feature OLS MAE evaluator (`ConsumerLoadLag24h168hLinearRegressionMAEResult`, `evaluate_consumer_load_lag_24h_168h_linear_regression_mae`) now scores already-produced Chunk 144 prediction artifacts as MW MAE only: empty input, mixed consumers, and malformed chronology fail closed, negative finite predictions are scored with ordinary absolute error, RMSE/MSE/MAPE and persistence or one-feature comparison are not calculated, and no generic metrics framework is introduced; it remains completely unwired, does not modify the published Chunk 139 one-feature evaluator, and does not select a production model. An ML-owned aligned one-feature-versus-two-feature OLS MAE comparison (`ConsumerLoadLag24hVsLag24h168hOLSMAEComparison`, `compare_consumer_load_lag_24h_vs_lag_24h_168h_ols_mae`) now requires the same consumer, same target timestamps, same actual MW labels, and equal cohort size, then delegates scoring to the published Chunk 139 and Chunk 145 MAE evaluators: empty/unequal/mixed/mismatched/malformed inputs fail closed, no production-model choice or relative change is computed, and no generic comparison framework is introduced; it remains completely unwired. This comparison machinery does not constitute empirical evidence that either model is better. An ML-owned aligned persistence-versus-two-feature OLS MAE comparison (`ConsumerLoadPersistenceVsLag24h168hOLSMAEComparison`, `compare_consumer_load_persistence_vs_lag_24h_168h_ols_mae`) now requires the same consumer, same target timestamps, same actual MW labels, and equal cohort size, then delegates scoring to the published Chunk 134 persistence and Chunk 145 two-feature MAE evaluators: empty/unequal/mixed/mismatched/malformed inputs fail closed, no production-model choice or relative change is computed, and no generic comparison framework is introduced; it remains completely unwired. This comparison machinery does not constitute empirical evidence that either model is better. An ML-owned aligned three-way persistence-versus-one-feature-versus-two-feature OLS MAE comparison (`ConsumerLoadPersistenceVsLag24hVsLag24h168hOLSMAEComparison`, `compare_consumer_load_persistence_vs_lag_24h_vs_lag_24h_168h_ols_mae`) now requires the same consumer, same target timestamps, same actual MW labels, and equal cohort size across all three cohorts, then delegates scoring to the published Chunk 134 persistence, Chunk 139 one-feature, and Chunk 145 two-feature MAE evaluators: empty/unequal/mixed/mismatched/malformed inputs fail closed, pairwise comparison functions are not reused, no production-model choice or relative change is computed, and no generic comparison framework is introduced; it remains completely unwired. This comparison machinery does not constitute empirical evidence that any of the three models is better. An ML-owned two-feature OLS candidate live adapter (`Lag24h168hOLSConsumerLoadForecastModel`) now structurally implements `ConsumerLoadForecastModelPort` from already-fitted Chunk 143 parameters and exact `T - 24h` / `T - 168h` history: missing or duplicate lags fail closed; negative finite live predictions fail closed because canonical `LoadForecastPoint.value_mw` remains `NonNegativeMW`; there is no clamping, persistence fallback, or production-model selection; Chunk 144 offline signed predictions remain unchanged; it remains completely unwired. Application now owns unwired `ForecastingPlan` composing the published Consumer Load and DAM Price forecast request DTOs, unwired `ForecastingSuccess` composing the existing canonical `LoadForecastPoint` and `PriceForecastPoint` tuples, unwired `ForecastingExecutionPort` as `async execute(*, plan: ForecastingPlan) -> ForecastingSuccess`, `ForecastingWorkflowContextPort` as `async resolve_plan(*, state: WorkflowState) -> ForecastingPlan` and `async record_success(*, state: WorkflowState, success: ForecastingSuccess) -> None`, and infrastructure `InMemoryForecastingWorkflowContext` as an unwired local/dev structural implementation of that port. Application-owned `ForecastingWorkflowStep` composes resolve → execute → record and returns the original `WorkflowState` unchanged, published `advance_after_forecasting` maps `forecasting`/`running` to `risk_and_bid`/`running` on a new seven-field `WorkflowState`, LangGraph injects that already-composed `ForecastingWorkflowStep` on `FORECASTING`/`RUNNING`, and LangGraph node `forecasting_success_transition` applies `advance_after_forecasting` so a successful Phase-3 graph run ends at `risk_and_bid`/`running` (`workflow_entry` → `forecasting` → `forecasting_success_transition` → `END`). None of those contracts execute agents or expand `WorkflowState`. Application-owned `ParallelForecastingExecutionService` now structurally implements `ForecastingExecutionPort` by running Consumer Load and DAM agents concurrently with `asyncio.TaskGroup` and attributing ordinary branch failures as `ForecastingAgentFailure`; it remains unwired from LangGraph/`create_app()` and does not own context. Application-owned `fail_after_forecasting` now maps `forecasting`/`running` to `forecasting`/`failed` on a new seven-field `WorkflowState` without mutating diagnostics, accepting exceptions, or wiring LangGraph. Application-owned `extract_forecasting_agent_failures` now extracts already-attributed `ForecastingAgentFailure` leaves from a possibly nested `BaseExceptionGroup` in depth-first left-to-right encounter order, preserves wrapper identity, retains duplicates, and fails closed on unattributed leaves; it remains unwired from LangGraph, the executor, and the workflow step. Application-owned `classify_forecasting_agent_failure` now classifies exactly one already-attributed `ForecastingAgentFailure` into frozen `ForecastingFailureFact` (`agent_name` + `error_code`); `ApplicationError` causes reuse `.code`; other causes collapse to `forecasting_unexpected_failure`; it remains unwired from LangGraph, the extractor, the executor, and the workflow step. Application-owned `classify_forecasting_agent_failures` now classifies `tuple[ForecastingAgentFailure, ...]` into `tuple[ForecastingFailureFact, ...]` by delegating each element independently to that one-leaf classifier; empty tuples, encounter order, cardinality, and duplicate agent identities are preserved; it does not inspect `__cause__` or map error codes and remains unwired from LangGraph, the extractor, the executor, the workflow step, and `fail_after_forecasting`. Application-owned `ForecastingFailureSelectionPort` now defines synchronous `select(facts: tuple[ForecastingFailureFact, ...]) -> ForecastingFailureFact` without a winner rule, ranking, or AgentName/error_code priority, and remains unwired from LangGraph, the extractor, classifiers, executor, workflow step, and `fail_after_forecasting`. Application-owned `StrictSingleForecastingFailureSelector` now structurally implements that port for the unambiguous one-fact case: exactly one fact is returned by identity; zero or multiple facts fail closed as the same sanitized `InvalidRequestError`; duplicates remain multiple; there is no ranking, sorting, first/last winner, or AgentName/error_code priority; it remains unwired from LangGraph, the extractor, classifiers, executor, workflow step, and `fail_after_forecasting`. Application-owned `ForecastingAttemptNumberPort` now defines async `get_attempt_number(self, workflow_id: str) -> int` as the Phase-3 read-only attempt-number contract over workflow identity; there is no increment/reset semantics on the port, and no LangGraph wiring. Application-owned `InitialForecastingAttemptNumberSource` now structurally implements that port for the current no-retry runtime by returning exactly `1`; it is not a tracker, has no increment/reset/persistence, and remains unwired from LangGraph. Application-owned `build_forecasting_failure_policy_context` now constructs existing `FailurePolicyContext` from already-sanitized keyword-only `phase`, `error_code`, `attempt_number`, and optional `agent_name`; it does not select failures, look up attempts, invoke policy, execute an action, or wire LangGraph. Application-owned `ForecastingFailureContextResolutionService` now composes selection, attempt lookup, and that builder into one `FailurePolicyContext` without policy decision, action execution, or LangGraph coupling. Application-owned `ForecastingFailureContextPreparationService` now composes extraction, tuple classification, and that resolution service into one `FailurePolicyContext` without policy decision, action execution, or LangGraph coupling. There is no production/durable forecasting context and no LangGraph wiring of the forecasting failure transition. A concrete forecasting attempt source now exists as unwired `InitialForecastingAttemptNumberSource`. Retry-capable attempt tracking, policy decision, action execution, runtime handling, LangGraph forecasting-failure routing, and retry/fallback remain incomplete. Shared ML utilities, wider feature pipelines, trained models, DAM model adapters, RMSE/MAPE, and production Phase 3 composition remain future work. Do not mark the parent Consumer Load Forecast capability complete. Do not mark the parent Regulatory Intelligence capability complete. Do not mark Pricing & Sales started. Do not mark the contract-phase graph complete: Chunk 117 wires a terminal Regulatory slice only, with no post-Regulatory commercial step and no CONTRACT→INGESTION transition. Do not mark generic production Qdrant collection provisioning complete. Document Vector Index collection provisioning now exists indirectly through the existing production lifespan → loaded runtime → managed runtime chain using ensure/create-if-missing. Regulatory collection readiness verification is now active indirectly through the existing production Regulatory lifespan → loaded runtime → managed runtime chain using verify-existing/fail-closed; a missing or incompatible Regulatory collection prevents query-service startup and is not created empty. Regulatory collection automatic provisioning, shared Regulatory/index collection identity, collection migration, recreate/update/delete, race retry/locking, aliases, payload indexes, schema versioning, and production distance defaults remain absent. An application-owned Regulatory workflow step now exists (`RegulatoryIntelligenceWorkflowStep`) over existing `AgentPort` and `RegulatoryIntelligenceQueryExecutionService`; LangGraph topology does not import or invoke it; `WorkflowState` was not expanded because it still has no typed agent-output slot. An application-owned Regulatory workflow-context Protocol now exists (`RegulatoryIntelligenceWorkflowContextPort`) that resolves a typed Chunk 114 request from `WorkflowState` and records the existing `RegulatoryIntelligenceResult` without embedding those values on the snapshot; there is no production context implementation and LangGraph does not import the context port. An application-owned Regulatory workflow-node adapter now exists (`RegulatoryIntelligenceWorkflowNodeAdapter`) that coordinates that context with the Chunk 114 step as resolve → step `run` → record and returns the original `WorkflowState` unchanged; LangGraph injects that already-constructed adapter on contract/running and then ends. Do not mark the parent Weather, Hydro, Generation Availability, News Intelligence, or Market Monitoring agent capabilities complete. Do not mark the parent Parallel Phase 2 join complete. Do not pre-authorize OCR, actual RAG workflow, verified Armenian DAM rule extraction, production/durable workflow-context implementation, general multi-failure selection, retry-capable attempt tracking, increment/reset semantics, retry/fallback execution, LangGraph wiring of lower-level failure internals, LangGraph/`create_app()` wiring of `ParallelForecastingExecutionService`, or API/composition graph wiring. Do not mark raw document ingestion or corpus automation complete merely because an unwired explicit one-shot PDF extraction-to-index execute function exists. Do not pre-authorize a numbered chunk after 162. Retry-capable attempt tracking, policy decision, action execution, runtime handling, LangGraph forecasting-failure routing, and retry/fallback remain future work and are not authorized by this chunk.

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
