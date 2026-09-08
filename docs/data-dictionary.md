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

## Transaction Fields

The following are examples of expected fields.

They are **not guaranteed to exist** in the final dataset.

| Field               | Description                   |
| ------------------- | ----------------------------- |
| `transaction_id`    | Unique transaction identifier |
| `customer_id`       | Customer/account identifier   |
| `timestamp`         | Transaction timestamp         |
| `amount`            | Transaction monetary amount   |
| `merchant_id`       | Merchant identifier           |
| `merchant_category` | Merchant classification       |
| `device_id`         | Device identifier             |
| `country`           | Transaction country           |
| `fraud_label`       | Ground-truth fraud indicator  |

---

## Derived Feature Fields

Potential examples:

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
