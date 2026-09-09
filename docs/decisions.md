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

---

# ADR-011 — Use pickle for model artifact serialization

## Status

Accepted

## Decision

Model artifacts (model + scaler + metadata) are serialized using Python pickle via a `ModelArtifact` dataclass.

## Alternatives Considered

* joblib — similar to pickle, no meaningful advantage for this use case
* XGBoost native format — only works for XGBoost, not RF/LR
* ONNX — adds dependency, unnecessary for portfolio project
* JSON-only metadata + separate model file — more complex, no benefit

## Rationale

Pickle is already a dependency (via scikit-learn). It handles arbitrary Python objects including sklearn models and scalers. The `ModelArtifact` dataclass bundles model, scaler, feature list, and metadata into a single file.

## Consequences

* Artifact is Python-specific (not portable to non-Python runtimes)
* Security: never load untrusted pickle files
* Artifact includes metadata JSON sidecar for easy inspection

---

# ADR-012 — Centralize feature preparation for training/inference parity

## Status

Accepted

## Decision

Feature preparation is centralized in `src/fraudlens/features/preparation.py`.

Training uses `prepare_features_from_dataframe()`.
Inference uses `prepare_features_from_transaction()`.
Both share the canonical `MODEL_FEATURES` list.

## Rationale

Training/inference feature mismatch is one of the most common and hardest-to-diagnose ML bugs. A shared feature contract prevents this.

## Consequences

* Single source of truth for feature names and transformations
* Both paths produce identical feature vectors for the same input
* Adding a new feature requires updating one list

---

# ADR-013 — Use SHAP for model explainability

## Status

Accepted

## Decision

SHAP (TreeExplainer for tree models, coefficient-based for linear models) provides feature-level explanations for individual predictions.

## Rationale

SHAP is the industry standard for local model explanations. It provides theoretically grounded feature attributions. The risk_factors in the API response combine rule-based signals with SHAP explanations.

## Consequences

* SHAP is an additional dependency (already installed)
* Explanations describe feature contributions, not causal evidence
* Fallback to feature importances if SHAP fails

---

# ADR-014 — API uses trained model, not heuristic probability

## Status

Accepted

## Decision

The `/score-transaction` endpoint uses the actual trained ML model for fraud probability estimation. No heuristic fallback in the primary scoring path.

## Rationale

A heuristic masquerading as ML output is worse than no model. The trained model provides genuinely learned patterns. If no model is loaded, the API returns 503 rather than fake scores.

## Consequences

* API requires a trained model artifact to be present
* Health endpoint reports `"degraded"` when no model is loaded
* Scoring returns 503 when no model is available
