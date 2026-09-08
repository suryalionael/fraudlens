# FraudLens

## Financial Transaction Risk Intelligence Platform

> From transaction data to explainable fraud-risk decisions.

FraudLens is a production-oriented financial risk analytics platform that analyzes transaction behavior, generates explainable risk scores, and prioritizes transactions for fraud investigation.

The project is designed to demonstrate the intersection of:

* Data Engineering
* Analytics Engineering
* Data Science
* Machine Learning
* Risk Analytics
* Business Intelligence
* API Development
* Production Software Engineering

Rather than treating fraud detection as a simple binary classification problem, FraudLens focuses on the operational question:

> **Which transactions should a fraud analyst investigate, and why?**

---

## Problem

Financial institutions process large volumes of transactions every day. Only a small fraction may be fraudulent, creating a highly imbalanced classification problem.

A system that simply maximizes classification accuracy can be misleading.

For example, if 99.5% of transactions are legitimate, a model that predicts every transaction as legitimate could achieve 99.5% accuracy while detecting zero fraud.

FraudLens therefore evaluates models using metrics and business constraints that better reflect real-world fraud operations.

The platform focuses on:

* Fraud detection
* Risk ranking
* Investigation prioritization
* Explainability
* False-positive management
* Analyst workload
* Fraud capture
* Business trade-offs

---

## Core Concept

```text
Raw Transactions
       |
       v
Data Ingestion
       |
       v
Data Validation
       |
       v
PostgreSQL
       |
       v
dbt Transformation
       |
       v
Behavioral Features
       |
       +----------------+
       |                |
       v                v
 Rule Engine       ML Model
       |                |
       +-------+--------+
               |
               v
          Risk Scoring
               |
               v
       Explainability
               |
               v
      Investigation Queue
          /          \
         v            v
      FastAPI      Power BI
```

---

## Project Goals

FraudLens aims to demonstrate the ability to:

1. Ingest and validate transaction data.
2. Design a relational data model.
3. Build reproducible data transformations.
4. Engineer behavioral risk features.
5. Handle highly imbalanced classification.
6. Train and evaluate fraud models.
7. Generate interpretable risk scores.
8. Combine machine learning with deterministic risk rules.
9. Prioritize transactions for human investigation.
10. expose model predictions through an API.
11. Build business-facing risk analytics.
12. Apply software engineering practices to a data science project.

---

## Non-Goals

FraudLens is a portfolio and educational project.

It is **not** intended to:

* process real financial transactions;
* make real financial decisions;
* replace human fraud investigators;
* provide banking or financial advice;
* claim production regulatory compliance;
* use personally identifiable financial information;
* guarantee fraud detection.

All datasets and examples must be appropriately licensed and safe for public demonstration.

---

## Project Philosophy

FraudLens follows five principles.

### 1. Data before models

The quality and structure of the data pipeline matter as much as the model.

### 2. Decisions before predictions

A prediction is only useful if it supports an operational decision.

### 3. Ranking before classification

Fraud teams often have limited investigation capacity.

The system therefore prioritizes transactions rather than simply returning `fraud` or `not fraud`.

### 4. Explainability matters

Risk analysts should be able to understand why a transaction received a high score.

### 5. Never fabricate results

All reported metrics, benchmarks, performance numbers, and business impact estimates must come from actual experiments.

---

## Planned Technology Stack

The exact stack may evolve as the project develops.

### Data

* Python
* pandas
* PostgreSQL

### Transformation

* dbt

### Machine Learning

* scikit-learn
* XGBoost
* SHAP

### API

* FastAPI

### Analytics

* Power BI

### Engineering

* Docker
* pytest
* GitHub Actions

### Potential Future Infrastructure

* AWS
* Terraform
* Apache Airflow
* Spark
* Kafka

Future technologies will only be introduced when they solve a demonstrated problem.

---

## Project Status

Current stage:

> **Phase 0 — Foundation / Dataset Validation**

| Phase | Status |
| --- | --- |
| Phase 0 — Foundation | COMPLETE |
| Phase 0 — Dataset Validation | COMPLETE |
| Phase 1 — Ingestion | NOT STARTED |
| Phase 2 — Data Modeling | NOT STARTED |
| Phase 3 — Feature Engineering | NOT STARTED |
| Phase 4 — Modeling | NOT STARTED |
| Phase 5 — Risk Engine | NOT STARTED |
| Phase 6 — API | NOT STARTED |
| Phase 7 — Dashboard | NOT STARTED |

### Dataset

FraudLens uses the **Nigerian Financial Transactions and Fraud Detection Dataset** (V1).

* **Source:** [HuggingFace](https://huggingface.co/datasets/electricsheepafrica/Nigerian-Financial-Transactions-and-Fraud-Detection-Dataset)
* **Type:** Synthetic
* **Rows:** 5,000,000
* **Columns:** 21
* **Observed fraud rate:** 3.5911% (179,553 fraud transactions)
* **File size:** ~924 MB

The raw dataset is intentionally excluded from Git. See [`data/README.md`](data/README.md) for download instructions.

**Critical validation findings:**

* `new_device_transaction` is a **leakage feature** — 100% of fraud cases have it=True
* `time_since_last_transaction` is **broken** — 41% negative values, no correlation with actual
* `velocity_score` and `geo_anomaly_score` have **no predictive signal**
* All behavioral features must be computed from raw fields

See [`docs/dataset-selection.md`](docs/dataset-selection.md) for the full validation report.

---

## Repository Structure

```text
fraudlens/
├── README.md
├── AGENTS.md
├── LICENSE
├── .gitignore
├── .env.example
│
├── data/
│   ├── README.md
│   ├── dataset_metadata.yml
│   ├── raw/            (not tracked — too large)
│   ├── staging/
│   └── processed/
│
├── docs/
│   ├── architecture.md
│   ├── data-pipeline.md
│   ├── data-model.md
│   ├── data-dictionary.md
│   ├── dataset-selection.md
│   ├── feature-engineering.md
│   ├── modeling.md
│   ├── evaluation.md
│   ├── risk-engine.md
│   ├── api.md
│   ├── dashboard.md
│   ├── development.md
│   ├── testing.md
│   ├── deployment.md
│   ├── security.md
│   ├── decisions.md
│   └── roadmap.md
│
├── src/
│   └── fraudlens/
│       └── __init__.py
│
├── tests/
└── notebooks/
```

---

## Roadmap

### Phase 0 — Foundation

* Repository structure
* Development environment
* Documentation
* Configuration
* Database connection
* Testing foundation

### Phase 1 — Data Ingestion

* Dataset selection
* Raw data ingestion
* Schema validation
* Data profiling

### Phase 2 — Data Modeling

* PostgreSQL schema
* Normalized entities
* dbt staging models
* dbt analytical models
* Data quality tests

### Phase 3 — Feature Engineering

* Transaction velocity
* Amount anomalies
* Customer behavior
* Device behavior
* Geographic behavior
* Merchant behavior

### Phase 4 — Baseline ML

* Train/validation/test strategy
* Logistic regression
* Random forest
* XGBoost
* Class imbalance handling

### Phase 5 — Risk Intelligence

* Risk scoring
* Threshold optimization
* Rule engine
* Investigation queue
* SHAP explanations

### Phase 6 — API

* FastAPI
* Transaction scoring endpoint
* Health endpoint
* Model metadata
* API validation

### Phase 7 — BI

* Executive dashboard
* Risk monitoring
* Investigation queue
* Model performance

### Phase 8 — Production Engineering

* Docker
* CI/CD
* Automated tests
* Model artifact management
* Observability

### Phase 9 — Cloud

Potentially:

* AWS
* Terraform
* Managed PostgreSQL
* Cloud deployment

---

## Success Criteria

FraudLens is considered MVP-complete when a user can:

1. Load the selected dataset.
2. Run the data pipeline.
3. Generate validated analytical data.
4. Generate transaction-level risk features.
5. Train the selected model.
6. Evaluate the model using appropriate metrics.
7. Generate a risk score.
8. Explain the primary risk factors.
9. Produce an investigation queue.

---

## Disclaimer

FraudLens is a portfolio project using public or appropriately generated data.

It does not represent a real financial institution or production fraud detection system.
