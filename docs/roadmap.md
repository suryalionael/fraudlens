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

### Exit Criteria

A defensible model selection decision can be made.

---

# Phase 5 — Risk Intelligence

### Objective

Turn predictions into operational risk decisions.

### Deliverables

* risk score;
* risk levels;
* rules engine;
* investigation queue;
* SHAP explanations;
* threshold analysis.

### Exit Criteria

A transaction can be ranked and explained.

---

# Phase 6 — API

### Objective

Make risk scoring programmatically accessible.

### Deliverables

* FastAPI;
* `/score-transaction`;
* `/health`;
* request validation;
* response schemas;
* API tests.

### Exit Criteria

A transaction can be submitted to the API and receive a validated risk response.

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
