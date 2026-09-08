# FraudLens Architecture

## 1. Overview

FraudLens is designed as a layered financial risk analytics platform.

The system transforms transaction data into explainable risk decisions.

```text
                 DATA SOURCES
                      |
                      v
                INGESTION LAYER
                      |
                      v
                 RAW STORAGE
                      |
                      v
               DATA VALIDATION
                      |
                      v
                 POSTGRESQL
                      |
                      v
                    dbt
                      |
             +--------+--------+
             |                 |
             v                 v
      Feature Engineering   Analytics Marts
             |
       +-----+------+
       |            |
       v            v
  Rule Engine    ML Models
       |            |
       +-----+------+
             |
             v
        Risk Scoring
             |
             v
       Explainability
             |
             v
    Investigation Queue
         /         \
        v           v
     FastAPI     Power BI
```

---

## 2. Architectural Layers

### Layer 1 — Data Source

The project begins with a public or appropriately generated transaction dataset.

The source dataset must be documented.

Important metadata includes:

* source;
* license;
* acquisition method;
* dataset version;
* known limitations;
* available fields;
* target definition.

---

### Layer 2 — Ingestion

The ingestion layer loads source data into the project.

Responsibilities:

* reading source data;
* schema validation;
* basic type normalization;
* ingestion logging;
* duplicate detection;
* load status reporting.

---

### Layer 3 — Raw Storage

Raw data is preserved without destructive transformation.

Purpose:

* reproducibility;
* auditing;
* debugging;
* reprocessing.

---

### Layer 4 — PostgreSQL

PostgreSQL acts as the primary relational data platform.

It stores structured transaction, customer, merchant, device, and analytical data.

---

### Layer 5 — dbt

dbt provides the transformation layer.

Expected layers:

```text
source
  ↓
staging
  ↓
intermediate
  ↓
marts
```

dbt is responsible for repeatable analytical transformations and data quality tests.

---

### Layer 6 — Feature Engineering

The feature layer converts transactional history into behavioral signals.

Examples:

* transaction velocity;
* amount deviation;
* customer spending behavior;
* device novelty;
* geographic behavior;
* merchant behavior.

---

### Layer 7 — Risk Engine

The risk engine combines:

* machine-learning predictions;
* deterministic rules;
* contextual signals.

The output is a standardized risk representation.

---

### Layer 8 — Investigation Queue

Transactions are ranked according to risk.

The queue should contain enough information for an analyst to understand:

* what happened;
* how risky it is;
* why it was flagged;
* what action is recommended.

---

### Layer 9 — API

FastAPI exposes scoring functionality.

Potential endpoint:

```text
POST /score-transaction
```

---

### Layer 10 — BI

Power BI consumes analytical outputs to provide:

* executive monitoring;
* risk trends;
* fraud analysis;
* investigation prioritization;
* model performance.

---

## 3. Architectural Principles

### Separation of concerns

Each layer should have a clear responsibility.

### Reproducibility

The pipeline should be rerunnable.

### Testability

Critical transformations and decisions must be testable.

### Explainability

Risk decisions should provide interpretable reasons.

### Extensibility

The architecture should support future streaming and cloud deployment without requiring a complete rewrite.

---

## 4. MVP Architecture

The initial MVP intentionally excludes:

* Kafka;
* Spark;
* Airflow;
* AWS;
* Terraform.

The MVP should first prove that:

```text
transaction
    ↓
features
    ↓
model
    ↓
risk
    ↓
investigation
```

works correctly.

Advanced infrastructure will be introduced only after the core workflow is stable.
