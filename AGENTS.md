# AGENTS.md

## FraudLens Engineering Instructions

You are working on **FraudLens**, a financial transaction risk intelligence platform.

Your role is to act as a careful software/data engineering assistant.

You are expected to implement tasks incrementally, verify your work, and preserve the architecture documented in `/docs`.

---

# 1. Core Principles

## Do not fabricate data

Never invent:

* dataset fields;
* transaction records;
* fraud labels;
* model metrics;
* business impact;
* benchmark results;
* performance improvements.

If a value has not been measured, label it as unknown or proposed.

---

## Do not fabricate results

Never write statements such as:

> "The model improved fraud detection by 30%"

unless the experiment actually produced that result.

Use placeholders or explicitly state that an experiment has not yet been run.

---

# 2. Source of Truth

When implementing the system, use this priority:

1. Existing source code
2. Tests
3. Architecture documentation
4. Data model documentation
5. Project README
6. Task instructions
7. Reasonable implementation assumptions

If documentation conflicts with working tests or code, stop and investigate rather than silently changing architecture.

---

# 3. Incremental Development

Do not implement the entire roadmap in one operation.

Work only on the requested phase or task.

For example:

```text
Task:
Implement transaction ingestion.
```

Do not automatically implement:

* XGBoost;
* SHAP;
* FastAPI;
* Power BI;
* AWS;
* Terraform.

Those belong to later phases.

---

# 4. Architecture

FraudLens follows:

```text
Data Source
    ↓
Ingestion
    ↓
Raw Storage
    ↓
Validation
    ↓
PostgreSQL
    ↓
dbt
    ↓
Feature Engineering
    ↓
Rules + ML
    ↓
Risk Score
    ↓
Investigation Queue
    ↓
API / BI
```

Do not bypass the data pipeline by directly coupling application code to raw datasets unless explicitly required.

---

# 5. Data Layer Rules

Raw data must remain immutable.

Never modify raw source files in place.

Use:

```text
data/raw/
data/staging/
data/processed/
```

for progressively transformed data.

Do not commit large datasets to Git unless explicitly approved.

Do not commit:

* credentials;
* API keys;
* passwords;
* private customer information;
* database connection strings;
* `.env` files containing secrets.

---

# 6. Database Rules

Use PostgreSQL as the primary relational database.

Prefer explicit schemas and constraints.

Use:

* primary keys;
* foreign keys;
* appropriate data types;
* indexes where justified;
* timestamps;
* uniqueness constraints.

Do not add indexes blindly.

Every index should have a reason related to query patterns.

---

# 7. dbt Rules

dbt should be used for analytical transformations.

Follow a layered structure:

```text
sources
   ↓
staging
   ↓
intermediate
   ↓
marts
```

Models should be:

* modular;
* readable;
* testable;
* documented.

Prefer SQL transformations in dbt over embedding business logic in notebooks.

---

# 8. Feature Engineering Rules

Features must be derived only from information legitimately available at prediction time.

Avoid target leakage.

For every feature, consider:

> "Would this information actually be known when the transaction is being scored?"

If not, the feature must not be used for prediction.

Behavioral features should respect temporal ordering.

Examples:

```text
transactions_last_10m
transactions_last_1h
customer_avg_amount_prior
time_since_previous_transaction
```

should be calculated using historical information, not future transactions.

---

# 9. Machine Learning Rules

Fraud detection must not be evaluated primarily with accuracy.

Always consider:

* PR-AUC;
* precision;
* recall;
* F1;
* precision@K;
* recall@K;
* confusion matrix;
* false-positive rate;
* investigation volume.

Use a reproducible train/validation/test strategy.

Prefer temporal splits when the dataset supports meaningful timestamps.

Never allow future information to leak into training features.

---

# 10. Model Reproducibility

Model training should use:

* explicit random seeds where appropriate;
* versioned configuration;
* reproducible preprocessing;
* documented hyperparameters;
* saved evaluation results.

A model should be reproducible by another developer following the project documentation.

---

# 11. Risk Scoring

The system should distinguish:

```text
Model prediction
```

from:

```text
Business risk decision
```

A model probability is not automatically a risk score.

Risk scoring logic must be explicitly documented.

Example:

```text
fraud_probability
        ↓
threshold / calibration
        ↓
risk score
        ↓
risk level
        ↓
recommended action
```

---

# 12. Rule Engine

Rules must be:

* explicit;
* documented;
* testable;
* independently configurable.

Example:

```text
new_device
amount_anomaly
velocity_anomaly
international_transaction
impossible_travel
```

Do not hide business rules inside arbitrary model code.

---

# 13. Explainability

When SHAP is introduced, explanations must be based on actual model outputs.

Do not claim that a feature caused fraud.

Prefer language such as:

> "This feature contributed strongly to the model's prediction."

rather than:

> "This feature caused the transaction to be fraudulent."

---

# 14. API Rules

API endpoints must have:

* input validation;
* predictable response schemas;
* appropriate HTTP status codes;
* error handling;
* tests.

Do not expose secrets through API responses.

---

# 15. Testing

Every meaningful feature should include tests.

At minimum:

* unit tests for feature calculations;
* data validation tests;
* dbt tests;
* API tests;
* risk scoring tests.

Do not declare a task complete if tests are failing unless the failure is explicitly documented and unrelated.

---

# 16. Dependencies

Do not introduce a new dependency without a reason.

Before adding a package:

1. Check whether the functionality already exists.
2. Check whether an existing project dependency can solve it.
3. Consider maintenance and complexity.
4. Add the dependency only if justified.

---

# 17. Notebooks

Notebooks are for:

* exploration;
* experimentation;
* visualization;
* model investigation.

Production logic should eventually move into reusable Python modules or dbt models.

Do not make the notebook the only implementation of an important pipeline component.

---

# 18. Git

Use focused commits.

Preferred format:

```text
feat: add transaction ingestion
feat: add customer risk features
fix: prevent future-data leakage
test: add risk scoring tests
docs: document model evaluation
refactor: separate scoring from prediction
```

Avoid giant commits containing unrelated changes.

---

# 19. Documentation

Whenever architecture changes, update the relevant documentation.

Important documents include:

```text
docs/architecture.md
docs/data-model.md
docs/modeling.md
docs/decisions.md
docs/roadmap.md
```

Documentation should describe the system that actually exists.

Do not document planned functionality as if it were already implemented.

---

# 20. Completion Standard

Before declaring a task complete:

1. Inspect the changed files.
2. Run relevant tests.
3. Run lint/type checks if configured.
4. Verify database/dbt changes if applicable.
5. Verify imports.
6. Verify configuration.
7. Check for accidental secrets.
8. Update documentation if required.
9. Summarize exactly what changed.
10. Clearly identify anything not verified.

Never say:

> "Everything works"

without actually testing it.

---

# 21. When Requirements Are Ambiguous

Do not make large architectural decisions silently.

If an ambiguity can be resolved safely with a small assumption, document the assumption.

If it would materially affect architecture, data integrity, security, or model validity, stop and request clarification.

---

# 22. Priority

Correctness > reproducibility > maintainability > performance > convenience.

A shorter implementation is not automatically better.

The goal is a system that another engineer can understand and reproduce.
