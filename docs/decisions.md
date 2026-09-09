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

---

# ADR-015 — Dashboard analytics query PostgreSQL directly

## Status

Accepted

## Decision

The Streamlit dashboard queries PostgreSQL directly for historical analytics rather than routing through FastAPI.

## Rationale

* Historical analytics (fraud rates, trends, aggregations) are read-heavy analytical queries
* FastAPI is designed for operational scoring, not analytics
* PostgreSQL handles analytical queries efficiently with appropriate indexes
* dbt marts provide pre-aggregated data for common queries
* Adding an analytics API layer would be unnecessary indirection

## Consequences

* Dashboard requires database connectivity
* Dashboard data access is isolated in `dashboard/data/` package
* API remains focused on operational scoring endpoints

---

# ADR-016 — Persist risk scores in PostgreSQL

## Status

Accepted

## Decision

Risk scoring outputs are persisted in `risk.transaction_scores` table in PostgreSQL.

## Rationale

* Risk scores computed during API calls are transient by default
* Dashboard needs historical risk data for monitoring and investigation
* PostgreSQL provides reliable storage with query capabilities
* The `risk.transaction_scores` table is the single source of truth for scored transactions

## Consequences

* Batch scoring populates the table from raw.transactions
* Dashboard reads from the same table the API could write to
* Risk persistence is optional — dashboard gracefully handles missing data
* Upsert semantics allow re-scoring without duplicates

---

# ADR-017 — Dashboard data access layer

## Status

Accepted

## Decision

Dashboard data access is isolated in `dashboard/data/` package with page-specific query modules.

## Rationale

* Keeps SQL queries out of Streamlit rendering code
* Enables unit testing of query logic without database
* Provides a clear contract between data and presentation
* Each page has a dedicated query module with focused responsibilities

## Consequences

* `dashboard/data/connection.py` — shared PostgreSQL connection
* `dashboard/data/executive.py` — executive overview queries
* `dashboard/data/risk.py` — risk monitoring queries
* `dashboard/data/investigations.py` — investigation queue queries
* `dashboard/data/fraud.py` — fraud analysis queries

---

# ADR-018 — ECS Fargate for container compute

## Status

Accepted

## Decision

FraudLens deploys on AWS ECS Fargate rather than EC2 instances or Lambda.

## Rationale

* Fargate eliminates instance management
* Pay-per-use matches portfolio cost requirements
* Containers provide consistent runtime between local and cloud
* ECS is simpler than EKS for this scale
* Lambda would require rewriting the application

## Consequences

* No SSH access to containers (use CloudWatch for debugging)
* Cold start time ~30s (acceptable for this use case)
* Resource limits are softer than EC2

---

# ADR-019 — S3 for model artifact storage

## Status

Accepted

## Decision

Model artifacts are stored in S3 and loaded by ECS containers at startup.

## Rationale

* S3 provides durable, versioned object storage
* Model artifacts are ~10MB (pickle files)
* ECS containers load from S3 at startup (acceptable cold start)
* Avoids baking models into Docker images
* Enables model versioning without image rebuilds

## Consequences

* API startup time includes S3 download (~2-5s)
* ECS task role needs S3 read access
* Model artifacts must be uploaded separately from deployment

---

# ADR-020 — GitHub Actions OIDC for AWS authentication

## Status

Accepted

## Decision

GitHub Actions authenticates to AWS using OIDC federation instead of static credentials.

## Rationale

* No long-lived AWS credentials stored in GitHub
* Automatic credential rotation
* Least-privilege access per workflow
* Industry best practice for CI/CD

## Consequences

* Requires one-time setup of OIDC provider in AWS
* IAM roles must be configured with correct trust policies
* Each workflow needs appropriate role ARN

---

# ADR-021 — Terraform for infrastructure as code

## Status

Accepted

## Decision

All AWS infrastructure is managed by Terraform.

## Rationale

* Reproducible infrastructure
* Version-controlled infrastructure changes
* Plan before apply
* Clear resource ownership
* Standard tool for AWS infrastructure

## Consequences

* Requires Terraform knowledge
* State management needed (S3 backend)
* Infrastructure changes go through PR review
