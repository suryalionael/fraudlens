# Testing Strategy

## 1. Purpose

FraudLens must be tested as both a data system and a software system.

A model with good metrics is not sufficient if the underlying pipeline is incorrect.

---

## 2. Test Layers

```text
Unit Tests
    ↓
Data Tests
    ↓
dbt Tests
    ↓
Integration Tests
    ↓
API Tests
    ↓
Model Evaluation
```

---

## 3. Unit Tests

Test:

* feature calculations;
* risk-score calculations;
* risk-level assignment;
* rule triggering;
* utility functions.

---

## 4. Data Tests

Validate:

* schema;
* data types;
* null values;
* duplicate IDs;
* valid labels;
* valid amounts;
* valid timestamps.

---

## 5. dbt Tests

Expected tests include:

```text
unique
not_null
relationships
accepted_values
```

Additional custom tests may be added for business logic.

---

## 6. Feature Tests

Feature tests should verify temporal correctness.

Example:

A transaction at:

```text
10:00
```

must not use a transaction at:

```text
10:05
```

when calculating historical features for the 10:00 transaction.

---

## 7. Model Tests

Model tests should verify:

* expected feature columns;
* no missing required features;
* deterministic preprocessing;
* valid probability output;
* correct model artifact loading.

---

## 8. API Tests

Test:

* valid scoring;
* invalid inputs;
* missing fields;
* unavailable model;
* health endpoint;
* response schema.

---

## 9. Integration Tests

Eventually test:

```text
database
    ↓
feature pipeline
    ↓
model
    ↓
risk engine
    ↓
API
```

as an end-to-end workflow.

---

## 10. Test Philosophy

Tests should catch:

* incorrect assumptions;
* data leakage;
* broken transformations;
* schema changes;
* incorrect risk calculations;
* API regressions.

The goal is confidence, not maximizing the number of tests.
