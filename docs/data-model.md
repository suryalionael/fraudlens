# FraudLens Data Model

## 1. Purpose

The database separates transactional entities from analytical and risk outputs.

The exact fields depend on the selected dataset.

No fields should be invented merely to make the architecture appear complete.

---

## 2. Conceptual Model

```text
Customer
   |
   | 1:N
   v
Transaction
   |
   +---- Merchant
   |
   +---- Device
   |
   +---- Location
```

---

## 3. Core Entities

### Customers

Represents the customer/account entity if customer identifiers are available.

Potential attributes:

```text
customer_id
customer_created_at
customer_segment
home_location
```

Only fields present or legitimately derived from the dataset should be included.

---

### Transactions

Central fact table.

Potential attributes:

```text
transaction_id
customer_id
timestamp
amount
merchant_id
device_id
location_id
payment_method
fraud_label
```

---

### Merchants

Merchant-level reference data.

Potential attributes:

```text
merchant_id
merchant_category
merchant_location
```

---

### Devices

Device-level information where available.

Potential attributes:

```text
device_id
device_type
device_first_seen
```

---

### Locations

Geographic information where available.

Potential attributes:

```text
location_id
country
region
latitude
longitude
```

---

## 4. Implemented Models (Phase 2)

### Staging Models

```text
stg_transactions          — Raw transaction data (view)
stg_ingestion_runs        — Ingestion run metadata (view)
```

### Intermediate Models

```text
int_transaction_enriched  — Transactions with sender, merchant, location, device statistics (view)
```

### Mart Models

```text
fct_transactions_analytics — Enriched fact table with analytics features (table)
rpt_fraud_summary          — Fraud summary report by dimensions (table)
```

### Schema Hierarchy

```text
raw (source)
  ↓
staging (views)
  ↓
intermediate (views)
  ↓
marts (tables)
```

### Future Analytical Models

Planned for later phases:

```text
fct_transaction_risk
fct_fraud_events
fct_investigations
```

---

## 5. Risk Model Output

A transaction risk record may contain:

```text
transaction_id
model_version
fraud_probability
risk_score
risk_level
rule_score
recommended_action
scored_at
```

---

## 6. Investigation Queue

Potential fields:

```text
investigation_id
transaction_id
risk_score
risk_level
priority
risk_factors
recommended_action
status
created_at
```

---

## 7. Data Modeling Principles

* Avoid unnecessary duplication.
* Preserve transaction grain.
* Clearly define table grain.
* Use explicit keys.
* Document derived fields.
* Separate raw data from analytical outputs.
* Prevent leakage between historical and future information.
