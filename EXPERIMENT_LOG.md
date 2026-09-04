# Experiment Log

Engineering notebook for ML and related empirical work.

**Status:** No ML experiments have been run yet. There are no datasets versioned in this repository and no trained artifacts.

Use a new heading per run. Copy the template below.

---

## Template

```markdown
### Date
YYYY-MM-DD

### Experiment ID
EXP-YYYYMMDD-NN

### Objective
One paragraph: hypothesis or question.

### Dataset / version
Name, grain (interval), date range, row counts, fixture or storage path. Do not commit large raw dumps.

### Features
Canonical contracts used (e.g. ConsumptionRecord, WeatherRecord) and derived features.

### Model
Family and library (XGBoost / LightGBM / Prophet / other). Not an LLM.

### Hyperparameters
Explicit list or reference to a committed config file.

### Train / validation strategy
Walk-forward, holdout dates, purge/embargo. Timezone of splits.

### Metrics
Named metrics with units (MW error, price error in stated currency). Include baseline.

### Result
Pass/fail vs objective. Numbers.

### Failure / lesson
What broke or misled. Include data-quality issues routed via ACL/DLQ.

### Artifact location
Path or URI. Trained weights should remain gitignored unless a chunk explicitly versions a tiny fixture model.
```

---

## Runs

_(none)_
