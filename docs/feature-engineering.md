# Feature Engineering

## 1. Objective

FraudLens uses behavioral features to capture deviations from normal transaction behavior.

The goal is not simply to describe a transaction.

The goal is to describe:

> **How unusual is this transaction relative to the relevant historical context?**

---

## 2. Feature Categories

### Transaction Features

Examples:

```text
amount
hour
day_of_week
is_weekend
```

---

### Velocity Features

Examples:

```text
transactions_last_10m
transactions_last_1h
transactions_last_24h
amount_last_1h
```

These should use only transactions occurring before the transaction being scored.

---

### Customer Behavioral Features

Examples:

```text
customer_transaction_count_prior
customer_avg_amount_prior
customer_std_amount_prior
customer_max_amount_prior
amount_ratio_to_customer_avg
```

---

### Device Features

Examples:

```text
new_device_flag
device_transaction_count_prior
customer_device_count_prior
```

---

### Geographic Features

Potential features:

```text
international_transaction_flag
distance_from_previous_transaction
time_since_previous_transaction
impossible_travel_flag
```

---

### Merchant Features

Potential features:

```text
merchant_transaction_count_prior
merchant_fraud_rate_prior
merchant_category_risk
```

Merchant statistics must be calculated using historical information only.

---

## 3. Temporal Leakage

Temporal leakage is one of the most important risks in fraud modeling.

A feature must not use information that would not be available when the transaction is being evaluated.

Incorrect:

```text
merchant_fraud_rate = all-time merchant fraud rate
```

if that includes transactions occurring after the transaction being scored.

Preferred:

```text
merchant_fraud_rate_prior
```

calculated only from historical transactions.

---

## 4. Feature Selection

Features should be evaluated based on:

* predictive usefulness;
* availability at scoring time;
* leakage risk;
* interpretability;
* computational cost;
* stability.

---

## 5. Feature Documentation

Every production feature should have:

```text
name
definition
source
calculation
data type
prediction-time availability
leakage considerations
```

---

## 6. Feature Validation

Feature tests should verify:

* expected data types;
* expected ranges;
* no impossible values;
* correct temporal ordering;
* correct handling of first transactions;
* correct null behavior.

---

## 7. Future Enhancements

Potential future features:

* customer behavioral embeddings;
* graph-based transaction relationships;
* device-sharing networks;
* merchant anomaly scores;
* sequence-based features;
* streaming velocity features.
