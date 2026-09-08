# Architecture Decisions

This document records significant architectural decisions made during FraudLens development.

The purpose is to preserve the reasoning behind the system rather than only documenting the final implementation.

---

# ADR-001 — Build FraudLens as a layered platform

## Status

Accepted

## Decision

FraudLens will be implemented as a layered system:

```text
Ingestion
↓
Storage
↓
Transformation
↓
Features
↓
ML + Rules
↓
Risk
↓
Investigation
↓
API / BI
```

## Rationale

A layered architecture demonstrates realistic separation between data engineering, analytics, machine learning, and application concerns.

It also allows individual components to be tested independently.

---

# ADR-002 — Use PostgreSQL as the primary database

## Status

Accepted

## Decision

PostgreSQL will be the primary relational database for the MVP.

## Rationale

PostgreSQL provides:

* relational modeling;
* SQL analytics;
* constraints;
* indexing;
* mature tooling;
* realistic industry relevance.

---

# ADR-003 — Use dbt for analytical transformations

## Status

Accepted

## Decision

dbt will manage the transformation layer.

## Rationale

dbt provides:

* modular SQL;
* testing;
* documentation;
* lineage;
* reproducibility.

This also allows the project to demonstrate analytics engineering practices.

---

# ADR-004 — Evaluate fraud models using PR-AUC and ranking metrics

## Status

Accepted

## Decision

Accuracy will not be the primary evaluation metric.

Primary evaluation will consider:

* PR-AUC;
* precision;
* recall;
* precision@K;
* recall@K.

## Rationale

Fraud detection is typically highly imbalanced, making raw accuracy potentially misleading.

Investigation capacity also makes ranking performance operationally important.

---

# ADR-005 — Treat fraud detection as an investigation prioritization problem

## Status

Accepted

## Decision

FraudLens will prioritize transactions for investigation rather than simply outputting binary fraud predictions.

## Rationale

A real fraud operation may have limited analyst capacity.

The system therefore needs to answer:

> Which transactions should be reviewed first?

This creates a more realistic business objective.

---

# ADR-006 — Combine rules with machine learning

## Status

Accepted

## Decision

FraudLens will support both deterministic rules and ML predictions.

## Rationale

Rules provide:

* transparency;
* controllability;
* straightforward business interpretation.

ML provides:

* pattern recognition;
* nonlinear relationships;
* scalable risk estimation.

Combining them demonstrates a more realistic risk-engineering architecture.

---

# ADR-007 — Avoid premature distributed infrastructure

## Status

Accepted

## Decision

Kafka, Spark, Airflow, AWS, and Terraform will not be required for the initial MVP.

## Rationale

The project should first prove the core data-to-risk workflow.

Distributed infrastructure will only be introduced if it solves a demonstrated scalability or deployment problem.

---

# ADR-008 — Preserve raw data

## Status

Accepted

## Decision

Raw source data will remain immutable.

## Rationale

This improves:

* reproducibility;
* debugging;
* auditing;
* pipeline reprocessing.

---

# ADR-009 — Prevent temporal leakage

## Status

Accepted

## Decision

Behavioral features must use only information available before the transaction being scored.

## Rationale

Using future transaction information would produce unrealistic model performance and invalidate the evaluation.

---

# ADR-010 — Never fabricate project metrics

## Status

Accepted

## Decision

All reported performance metrics must come from actual experiments.

## Rationale

FraudLens is intended to demonstrate real engineering and analytical ability.

Fabricated metrics undermine the credibility of the project.
