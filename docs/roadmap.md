# FraudLens Roadmap

## Overview

FraudLens will be developed incrementally.

The goal is to reach a functioning MVP before adding production infrastructure.

---

# Phase 0 — Foundation

### Objective

Create the project foundation.

### Deliverables

* repository structure;
* AGENTS.md;
* documentation;
* Python environment;
* configuration;
* PostgreSQL connection;
* testing foundation.

### Exit Criteria

A new developer can clone the repository and understand how the project is structured.

---

# Phase 1 — Dataset and Ingestion

### Objective

Establish a trustworthy source dataset.

### Deliverables

* dataset selected;
* license documented;
* source documented;
* raw data stored;
* ingestion script;
* schema validation;
* data profiling.

### Exit Criteria

The dataset can be reproducibly loaded and validated.

---

# Phase 2 — Data Modeling

### Status

✅ COMPLETE

### Objective

Create the analytical data foundation.

### Deliverables

* PostgreSQL schema;
* staging tables;
* dbt models;
* analytical marts;
* data quality tests;
* data dictionary.

### Implementation

* dbt project initialized at `dbt/fraudlens/`
* Source definitions: `raw.transactions`, `raw.ingestion_runs`
* Staging models: `stg_transactions`, `stg_ingestion_runs`
* Intermediate models: `int_transaction_enriched`
* Marts: `fct_transactions_analytics`, `rpt_fraud_summary`
* 48 data quality tests (unique, not_null, accepted_values)

### Exit Criteria

✅ Transaction data can be queried through clean analytical models.

---

# Phase 3 — Behavioral Features

### Status

✅ COMPLETE

### Objective

Capture transaction behavior and anomalies.

### Deliverables

* velocity features;
* customer behavior;
* amount anomalies;
* device behavior;
* geographic behavior;
* merchant behavior.

### Implementation

* Python module: `src/fraudlens/features/engineering.py`
* Feature tester: `src/fraudlens/features/tester.py`
* dbt model: `dbt/fraudlens/models/intermediate/int_features_temporal.sql`
* 13 Python unit tests (all passing)
* 14 dbt data tests (all passing)

### Features Implemented

**Temporal Features:**
- `hour_of_day`, `day_of_week`, `is_weekend`, `month`, `day_of_month`

**Velocity Features (Python):**
- `transactions_last_10m`, `transactions_last_60m`, `transactions_last_1440m`

**Amount Features:**
- `amount_ratio_to_avg`, `amount_zscore`, `customer_avg_amount_prior`, `customer_std_amount_prior`, `customer_max_amount_prior`

**Customer Features:**
- `customer_transaction_count_prior`, `customer_days_active`, `customer_transactions_per_day`

**Device Features:**
- `device_transaction_count_prior`, `device_first_seen`

**Merchant Features:**
- `merchant_transaction_count_prior`, `merchant_fraud_rate_prior`

**Location Features:**
- `location_transaction_count_prior`, `location_fraud_rate_prior`

### Temporal Leakage Prevention

All features are computed using only historical information. For each transaction, features are calculated from transactions that occurred BEFORE the current transaction.

### Performance Note

Velocity features (time-windowed counts) are computed in Python due to PostgreSQL performance constraints at 5M row scale. Cumulative stats are computed in dbt using window functions.

### Exit Criteria

✅ Feature generation is reproducible and leakage-safe.

---

# Phase 4 — Machine Learning

### Status

✅ COMPLETE

### Objective

Develop and evaluate fraud models.

### Deliverables

* baseline model;
* Random Forest;
* XGBoost;
* class imbalance strategy;
* temporal evaluation;
* PR-AUC;
* precision/recall;
* Precision@K;
* Recall@K.

### Implementation

* Python module: `src/fraudlens/models/trainer.py`
* Evaluator: `src/fraudlens/models/evaluator.py`
* 13 unit tests (all passing)

### Models Implemented

| Model | Type | Class Imbalance |
| --- | --- | --- |
| Logistic Regression | Baseline | Balanced weights |
| Random Forest | Ensemble | Balanced weights |
| XGBoost | Gradient Boosting | scale_pos_weight |

### Evaluation Metrics

* PR-AUC (primary)
* ROC-AUC
* Precision / Recall / F1
* Precision@K (K=100, 500, 1000, 5000)
* Recall@K
* Confusion matrix
* Threshold analysis
* Optimal threshold selection (F1-maximizing)

### Class Imbalance Strategy

* Logistic Regression: `class_weight='balanced'`
* Random Forest: `class_weight='balanced'`
* XGBoost: `scale_pos_weight = n_negative / n_positive`

### Exit Criteria

✅ A defensible model selection decision can be made.

---

# Phase 5 — Risk Intelligence

### Status

✅ COMPLETE

### Objective

Turn predictions into operational risk decisions.

### Deliverables

* risk score;
* risk levels;
* rules engine;
* investigation queue;
* SHAP explanations;
* threshold analysis.

### Implementation

* Python module: `src/fraudlens/risk/engine.py`
* Rules engine: `src/fraudlens/risk/rules.py`
* 18 unit tests (all passing)

### Risk Scoring

* Risk score: 0-100 (ML 70% + Rules 30%)
* Risk levels: Low (0-29), Medium (30-59), High (60-79), Critical (80-100)
* Actions: allow, monitor, review, urgent_review

### Rules Implemented

| Rule | Severity | Score |
| --- | --- | --- |
| new_device | high | 20 |
| amount_anomaly | high | 25 |
| high_amount_ratio | medium | 15 |
| velocity_anomaly | high | 20 |
| high_risk_merchant | medium | 15 |
| high_risk_location | medium | 15 |
| first_transaction | low | 10 |
| high_frequency_sender | medium | 10 |

### Investigation Queue

Transactions are ranked by risk score for investigation prioritization.

### Exit Criteria

✅ A transaction can be ranked and explained.

---

# Phase 6 — API

### Status

✅ COMPLETE

### Objective

Make risk scoring programmatically accessible.

### Deliverables

* FastAPI;
* `/score-transaction`;
* `/health`;
* request validation;
* response schemas;
* API tests.

### Implementation

* Python module: `src/fraudlens/api/app.py`
* 8 API tests (all passing)

### Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/health` | GET | Health check |
| `/score-transaction` | POST | Score a transaction for fraud risk |
| `/docs` | GET | OpenAPI documentation |
| `/redoc` | GET | ReDoc documentation |

### Request Schema

```json
{
  "transaction_id": "T123456",
  "sender_account": "ACC001",
  "receiver_account": "ACC002",
  "transaction_type": "transfer",
  "merchant_category": "electronics",
  "location": "Lagos",
  "device_used": "mobile",
  "amount_ngn": 50000.00,
  "payment_channel": "Bank Transfer",
  "ip_address": "192.168.1.1",
  "device_hash": "D1234567",
  "sender_persona": "Trader"
}
```

### Response Schema

```json
{
  "transaction_id": "T123456",
  "fraud_probability": 0.85,
  "risk_score": 78.5,
  "risk_level": "high",
  "recommended_action": "review",
  "risk_factors": ["amount_anomaly", "new_device"],
  "model_version": "fraudlens-lr-v001",
  "risk_engine_version": "001",
  "scored_at": "2024-01-01T00:00:00"
}
```

### Exit Criteria

✅ A transaction can be submitted to the API and receive a validated risk response.

---

# Phase 7 — Business Intelligence

### Objective

Build a decision-oriented dashboard.

### Deliverables

* executive overview;
* risk monitoring;
* investigation queue;
* fraud analysis;
* model performance.

### Exit Criteria

A stakeholder can use the dashboard to understand current risk patterns.

---

# Phase 8 — Production Engineering

### Objective

Improve reliability and reproducibility.

### Deliverables

* Docker;
* CI;
* automated tests;
* model artifact management;
* logging;
* configuration management.

### Exit Criteria

The system can be built and tested automatically.

---

# Phase 9 — Cloud

### Objective

Deploy the system to a cloud environment if justified.

Potential components:

* AWS;
* Terraform;
* managed PostgreSQL;
* container deployment.

### Exit Criteria

The deployed system is reproducible and documented.

---

# Phase 10 — Advanced Extensions

Potential future work:

* streaming transactions;
* Kafka;
* Spark;
* Airflow;
* real-time feature computation;
* model monitoring;
* drift detection;
* graph-based fraud detection;
* analyst feedback loops.

These are optional.

The project is already considered successful without them if the core platform is robust.
