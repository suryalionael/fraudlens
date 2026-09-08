# Data Pipeline

## 1. Objective

The FraudLens data pipeline converts the selected source dataset into validated, analytics-ready transaction data.

The pipeline must be reproducible and deterministic where possible.

---

## 2. Pipeline

```text
Source Dataset
      ↓
Ingestion
      ↓
Raw Data
      ↓
Schema Validation
      ↓
Cleaning
      ↓
PostgreSQL
      ↓
dbt Staging
      ↓
dbt Intermediate
      ↓
dbt Marts
      ↓
Feature Engineering
```

---

## 3. Raw Data

Raw source data should remain unchanged.

Required metadata:

```text
source_name
source_url
dataset_version
download_date
license
checksum
```

if available.

---

## 4. Validation

Validation should check:

* required columns;
* data types;
* null rates;
* duplicate records;
* invalid timestamps;
* invalid transaction amounts;
* unexpected categorical values;
* label validity.

Failures should be explicit.

The pipeline must not silently discard unexpected records.

---

## 5. Cleaning

Cleaning may include:

* type conversion;
* timestamp normalization;
* categorical normalization;
* duplicate handling;
* missing-value handling.

Every destructive transformation must be documented.

---

## 6. Database Loading

Data should be loaded into PostgreSQL using an idempotent or safely repeatable process where practical.

The pipeline should avoid creating duplicate records during repeated execution.

---

## 7. dbt Transformation

dbt should create:

```text
stg_transactions
stg_customers
stg_merchants
stg_devices
```

where applicable.

Intermediate models may calculate:

```text
customer_transaction_history
merchant_behavior
device_behavior
transaction_context
```

Marts should support:

```text
fraud monitoring
risk modeling
investigation
BI
```

---

## 8. Data Quality

Data quality tests should cover:

* primary key uniqueness;
* non-null keys;
* referential integrity;
* valid fraud labels;
* valid amounts;
* valid timestamps;
* accepted categorical values.

---

## 9. Observability

Future versions may track:

```text
records_received
records_loaded
records_rejected
duplicates_detected
validation_failures
pipeline_duration
```

---

## 10. Reproducibility

A new developer should be able to reproduce the pipeline using documented setup instructions.

The pipeline must not depend on undocumented manual transformations.
