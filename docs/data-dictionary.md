# Data Dictionary

## Purpose

This document defines the meaning, type, grain, and provenance of important FraudLens fields.

The dictionary must be updated when the selected dataset is finalized.

---

## Field Documentation Standard

Every important field should document:

| Attribute      | Description                          |
| -------------- | ------------------------------------ |
| Field          | Column name                          |
| Type           | Data type                            |
| Grain          | Record-level meaning                 |
| Source         | Original or derived                  |
| Description    | Business meaning                     |
| Allowed Values | When applicable                      |
| Nullable       | Whether null is valid                |
| Leakage Risk   | Whether temporal leakage is possible |

---

## Raw Transaction Fields (raw.transactions)

| Field                          | Type      | Source   | Description                           | Leakage Risk |
| ------------------------------ | --------- | -------- | ------------------------------------- | ------------ |
| `transaction_id`               | TEXT      | Original | Unique transaction identifier         | No           |
| `timestamp`                    | TIMESTAMP | Original | Transaction timestamp                 | No           |
| `sender_account`               | TEXT      | Original | Sender account identifier             | No           |
| `receiver_account`             | TEXT      | Original | Receiver account identifier           | No           |
| `transaction_type`             | TEXT      | Original | Type (deposit/withdrawal/transfer/payment) | No    |
| `merchant_category`            | TEXT      | Original | Merchant classification               | No           |
| `location`                     | TEXT      | Original | Transaction location                  | No           |
| `device_used`                  | TEXT      | Original | Device type used                      | No           |
| `is_fraud`                     | BOOLEAN   | Original | Ground-truth fraud indicator          | No           |
| `fraud_type`                   | TEXT      | Original | Type of fraud if applicable           | No           |
| `time_since_last_transaction`  | NUMERIC   | Precomputed | Time since last transaction       | YES — NOT TRUSTED |
| `spending_deviation_score`     | NUMERIC   | Precomputed | Spending deviation score          | YES — NOT TRUSTED |
| `velocity_score`               | INTEGER   | Precomputed | Velocity score                   | YES — NOT TRUSTED |
| `geo_anomaly_score`            | NUMERIC   | Precomputed | Geographic anomaly score         | YES — NOT TRUSTED |
| `payment_channel`              | TEXT      | Original | Payment channel used                  | No           |
| `ip_address`                   | TEXT      | Original | IP address of transaction             | No           |
| `device_hash`                  | TEXT      | Original | Device hash identifier                | No           |
| `amount_ngn`                   | NUMERIC   | Original | Transaction amount in NGN             | No           |
| `bvn_linked`                   | BOOLEAN   | Original | Whether BVN is linked                 | No           |
| `new_device_transaction`       | BOOLEAN   | Original | Whether this is a new device          | YES — NOT TRUSTED |
| `sender_persona`               | TEXT      | Original | Sender persona type                   | No           |

---

## Staging Model Fields (stg_transactions)

Same as raw.transactions. No transformations applied.

---

## Intermediate Model Fields (int_transaction_enriched)

Inherits all raw.transaction fields plus:

| Field                        | Type    | Source    | Description                          | Leakage Risk |
| ---------------------------- | ------- | --------- | ------------------------------------ | ------------ |
| `sender_total_transactions`  | INTEGER | Derived   | Total transactions by sender         | Potential    |
| `sender_fraud_count`         | INTEGER | Derived   | Fraud count by sender                | Potential    |
| `sender_fraud_rate`          | NUMERIC | Derived   | Fraud rate by sender                 | Potential    |
| `sender_avg_amount`          | NUMERIC | Derived   | Average amount by sender             | Potential    |
| `sender_std_amount`          | NUMERIC | Derived   | Std dev of amount by sender          | Potential    |
| `merchant_total_transactions`| INTEGER | Derived   | Total transactions by merchant       | Potential    |
| `merchant_fraud_count`       | INTEGER | Derived   | Fraud count by merchant              | Potential    |
| `merchant_fraud_rate`        | NUMERIC | Derived   | Fraud rate by merchant               | Potential    |
| `merchant_avg_amount`        | NUMERIC | Derived   | Average amount by merchant           | Potential    |
| `location_total_transactions`| INTEGER | Derived   | Total transactions by location       | Potential    |
| `location_fraud_count`       | INTEGER | Derived   | Fraud count by location              | Potential    |
| `location_fraud_rate`        | NUMERIC | Derived   | Fraud rate by location               | Potential    |
| `device_total_transactions`  | INTEGER | Derived   | Total transactions by device         | Potential    |
| `device_fraud_count`         | INTEGER | Derived   | Fraud count by device                | Potential    |
| `device_fraud_rate`          | NUMERIC | Derived   | Fraud rate by device                 | Potential    |

**Note:** Phase 2 intermediate models compute full-dataset aggregates. Phase 3 will implement temporal-only aggregates to prevent leakage.

---

## Mart Model Fields (fct_transactions_analytics)

Inherits all int_transaction_enriched fields plus:

| Field                        | Type    | Source    | Description                          | Leakage Risk |
| ---------------------------- | ------- | --------- | ------------------------------------ | ------------ |
| `amount_zscore`              | NUMERIC | Derived   | Amount z-score relative to sender    | Potential    |
| `sender_total_transactions_freq` | INTEGER | Derived | Transaction count by sender       | Potential    |
| `sender_days_active`         | INTEGER | Derived   | Days active for sender               | Potential    |
| `sender_transactions_per_day`| NUMERIC | Derived   | Transactions per day by sender       | Potential    |
| `sender_risk_level`          | TEXT    | Derived   | HIGH/MEDIUM/LOW risk level           | No           |
| `merchant_risk_level`        | TEXT    | Derived   | HIGH/MEDIUM/LOW risk level           | No           |
| `location_risk_level`        | TEXT    | Derived   | HIGH/MEDIUM/LOW risk level           | No           |

---

## Derived Feature Fields (Phase 3 — Planned)

| Feature                              | Meaning                                                 |
| ------------------------------------ | ------------------------------------------------------- |
| `transactions_last_10m`              | Number of prior transactions in the previous 10 minutes |
| `transactions_last_1h`               | Number of prior transactions in the previous hour       |
| `customer_avg_amount_prior`          | Historical average transaction amount                   |
| `amount_ratio_to_customer_avg`       | Current amount relative to historical average           |
| `time_since_previous_transaction`    | Time since prior transaction                            |
| `new_device_flag`                    | Whether the device is new to the customer               |
| `merchant_risk_rate`                 | Historical merchant fraud rate where valid              |
| `distance_from_previous_transaction` | Geographic distance from previous transaction           |

All behavioral features must be calculated without using future information.

---

## Data Provenance

Each derived feature should identify:

```text
source table
transformation
calculation logic
prediction-time availability
```

---

## Important Rule

If a field does not exist in the source dataset, it must not be presented as an observed field.

It may only be introduced as:

1. an explicitly engineered feature;
2. a generated/synthetic field;
3. a future enhancement.
