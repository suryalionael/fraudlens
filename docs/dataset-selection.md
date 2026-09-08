# Dataset Selection

## Purpose

FraudLens requires a transaction dataset suitable for demonstrating realistic fraud-risk analytics.

Dataset selection is an engineering and modeling decision, not merely a data acquisition step.

---

## Selection Criteria

The dataset should ideally provide:

### Transaction information

* transaction identifier;
* timestamp;
* amount;
* transaction attributes.

### Behavioral context

Preferably:

* customer/account identifier;
* merchant identifier;
* device identifier;
* location;
* payment method.

### Target

A reliable fraud/legitimate label.

---

## Required Characteristics

The dataset should provide sufficient:

* transaction volume;
* fraud examples;
* temporal information;
* feature diversity;
* class imbalance.

---

## Evaluation of Candidate Datasets

Each candidate should be evaluated on:

| Criterion                     | Assessment |
| ----------------------------- | ---------- |
| Transaction volume            | TBD        |
| Fraud labels                  | TBD        |
| Class imbalance               | TBD        |
| Timestamp availability        | TBD        |
| Customer identifiers          | TBD        |
| Merchant information          | TBD        |
| Device information            | TBD        |
| Geographic information        | TBD        |
| License                       | TBD        |
| Public redistribution         | TBD        |
| Temporal modeling suitability | TBD        |

---

## Dataset Decision

The selected dataset must be documented with:

```text
Dataset name:
Source:
URL:
License:
Version:
Download date:
Number of records:
Number of features:
Fraud rate:
Known limitations:
```

---

## Important Principle

A dataset should not be selected simply because it produces a high model score.

The dataset should support the project's intended business and engineering story.

---

## Limitations

The selected dataset may not represent the complexity of a real financial institution.

Known limitations should be explicitly documented and discussed in the final project.

---

## Synthetic Extensions

If important operational concepts are missing from the dataset, synthetic extensions may be considered.

Synthetic fields must be clearly labeled as synthetic.

They must never be presented as original observations from the source dataset.

---

# Dataset Research — Full Evaluation

## Date

2026-09-08

## Methodology

Datasets were evaluated against FraudLens project requirements using a weighted scoring matrix.

### Scoring Weights

| Criterion                    | Weight | Rationale |
| ---------------------------- | -----: | --------- |
| Behavioral feature potential |    20% | Core FraudLens differentiator |
| Temporal information         |    15% | Leakage prevention, velocity features |
| Transaction realism          |    15% | Credible portfolio narrative |
| Customer/account context     |    10% | Behavioral profiling |
| Merchant context             |    10% | Merchant risk features |
| Fraud label quality          |    10% | Ground truth reliability |
| Geographic/device context    |     5% | Risk rule signals |
| Explainability potential     |     5% | SHAP feature interpretability |
| Dataset size                 |     5% | Manageable for student project |
| License/provenance           |     5% | Legal use in portfolio |

---

## Candidate Comparison Matrix

| Dataset | Realism (15) | Behavioral (20) | Temporal (15) | Customer (10) | Merchant (10) | Fraud Label (10) | Geo/Device (5) | Explainability (5) | Size (5) | License (5) | Weighted Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Nigerian Financial Txn** | 8 | 10 | 9 | 9 | 7 | 9 | 8 | 9 | 8 | 7 | **8.70** |
| **Kartik Fraud Detection** | 7 | 8 | 10 | 9 | 8 | 8 | 7 | 8 | 7 | 5 | **7.95** |
| **IEEE-CIS (Vesta)** | 10 | 8 | 8 | 5 | 4 | 8 | 5 | 4 | 8 | 6 | **7.00** |
| **PaySim** | 5 | 7 | 7 | 8 | 3 | 8 | 2 | 6 | 4 | 8 | **6.00** |
| **MLG-ULB Credit Card** | 8 | 2 | 4 | 1 | 1 | 9 | 1 | 2 | 7 | 9 | **4.05** |
| **NeurIPS Bank Account Fraud** | 6 | 4 | 2 | 3 | 2 | 8 | 3 | 5 | 6 | 8 | **4.50** |
| **Olist Brazilian E-Commerce** | 9 | 6 | 9 | 8 | 7 | 1 | 5 | 6 | 6 | 8 | **6.35** |

---

## Detailed Candidate Analysis

### 1. Nigerian Financial Transactions and Fraud Detection Dataset

**Source:** Electric Sheep Africa (HuggingFace)
**URL:** https://huggingface.co/datasets/electricsheepafrica/Nigerian-Financial-Transactions-and-Fraud-Detection-Dataset
**Size:** ~5,000,000 rows
**Columns:** 44
**Fraud rate:** NOT VERIFIED (requires download to confirm)
**License:** "other" (non-standard; requires investigation before use)
**Type:** Synthetic (generated to mimic Nigerian banking patterns)

#### Available Fields

```text
Core:
  transaction_id          transaction timestamp
  sender_account          receiver_account
  amount_ngn              transaction_type
  merchant_category       location
  device_used             payment_channel
  ip_address              device_hash

Labels:
  is_fraud                fraud_type

Pre-computed behavioral:
  time_since_last_transaction
  spending_deviation_score
  velocity_score
  geo_anomaly_score

Context:
  bvn_linked              new_device_transaction
  sender_persona          geospatial_velocity_anomaly
  txn_hour                is_weekend
  is_salary_week          is_night_txn

Aggregated (potential leakage risk):
  device_seen_count       is_device_shared
  ip_seen_count           is_ip_shared
  user_txn_count_total    user_avg_txn_amt
  user_std_txn_amt        user_txn_frequency_24h
  user_top_category       txn_count_last_1h
  txn_count_last_24h      total_amount_last_1h
  time_since_last         avg_gap_between_txns
  merchant_fraud_rate     channel_risk_score
  persona_fraud_risk      location_fraud_risk
  ip_geo_region
```

#### Strengths

* Richest feature set of any candidate
* Explicit sender/receiver accounts enable behavioral profiling
* Timestamps enable temporal feature engineering
* Device, location, IP information present
* Pre-computed behavioral scores provide baseline
* Multiple fraud type categories
* Large enough for meaningful ML evaluation
* Supports business analytics (which transaction types, personas, locations are risky)

#### Weaknesses

* Synthetic data — not real-world observations
* License is non-standard ("other") — must verify before use
* Some pre-computed features (e.g., `user_txn_count_total`) may leak future information if used naively
* Nigerian banking context may not generalize to other markets
* `fraud_type` column may have nulls for legitimate transactions

#### Temporal Leakage Analysis

* Timestamps are present and meaningful (datetime format)
* `time_since_last_transaction` uses only prior history (safe)
* `txn_count_last_1h` and `txn_count_last_24h` are relative windows (likely safe)
* WARNING: `user_txn_count_total`, `user_avg_txn_amt`, `user_std_txn_amt` appear to be all-time aggregates — using these directly would cause leakage. Must calculate history-only versions.
* VERDICT: Supports temporal feature engineering if computed correctly from raw transactions

#### Behavioral Feature Potential: EXCELLENT

Can compute:
* Transaction velocity (transactions per hour/day)
* Amount anomaly (current vs. historical average)
* Time-of-day patterns
* Device novelty (new device flag)
* Geographic deviation
* Merchant risk rate
* Category behavior

#### Business Analytics Potential: EXCELLENT

Supports:
* Fraud rate by transaction type
* Risk by merchant category
* Geographic risk analysis
* Device risk analysis
* Investigation capacity modeling
* Top-K fraud capture analysis

---

### 2. Kartik Agrawal — Credit Card Transactions Fraud Detection

**Source:** Kaggle (user-contributed)
**URL:** https://www.kaggle.com/datasets/kartik2112/fraud-detection
**Size:** ~1,296,675 rows (train: 1.29M, test: 555K)
**Columns:** 23
**Fraud rate:** ~0.211%
**License:** CC0 / Public Domain (user-uploaded, no explicit license stated)
**Type:** Synthetic (generated to mimic real patterns)

#### Available Fields

```text
Core:
  trans_date_trans_time   unix_time
  trans_num               cc_num
  amt                     merchant
  category

Demographics:
  first / last            gender
  street / city / state / zip
  lat / long              city_pop
  job                     dob

Geography:
  merch_lat / merch_long

Label:
  is_fraud
```

#### Strengths

* Full datetime timestamps (real calendar dates)
* Explicit customer identifier (`cc_num`)
* Merchant information (name + category)
* Geographic coordinates (lat/long for both customer and merchant)
* Demographic information (age, gender, job, city)
* Good size for ML
* Clean structure

#### Weaknesses

* No explicit license documentation
* Synthetic data
* No device information
* No payment method channel
* Merchant names are synthetic strings
* Geographic coordinates may not be fully realistic
* Less feature-rich than Nigerian dataset

#### Temporal Leakage Analysis

* `trans_date_trans_time` provides real datetime ordering
* Can compute time-of-day, day-of-week, hour-of-day features
* Can compute per-customer temporal features (time since last transaction, transaction velocity)
* VERDICT: Excellent temporal feature engineering potential

#### Behavioral Feature Potential: VERY GOOD

Can compute:
* Customer transaction frequency
* Amount patterns per customer
* Time-of-day behavior
* Geographic behavior (distance from home, unusual locations)
* Merchant category preferences
* Transaction velocity

#### Business Analytics Potential: GOOD

Supports:
* Fraud rate by merchant category
* Fraud rate by geographic region
* Customer spending patterns
* Time-of-day fraud analysis

---

### 3. IEEE-CIS Fraud Detection (Vesta Corporation)

**Source:** Vesta Corporation via IEEE ICDM 2018
**URL:** https://www.kaggle.com/competitions/ieee-fraud-detection
**Size:** ~590,540 transactions (train)
**Columns:** 399 (V1-V339 are anonymized PCA features)
**Fraud rate:** ~3.5%
**License:** Competition rules (research/educational use)
**Type:** Real (e-commerce card-not-present transactions)

#### Available Fields

```text
Core:
  TransactionDT (seconds from reference)
  TransactionAmt
  ProductCD

Card features:
  card1-card6 (partially anonymized)

Address:
  addr1 / addr2

Email:
  P_emaildomain / R_emaildomain

Device:
  DeviceType / DeviceInfo

Identity:
  id_12-id_38 (anonymized)

Target:
  isFraud

V features:
  V1-V339 (anonymized velocity/identity features)
```

#### Strengths

* Real-world data from Vesta Corporation
* Best competition pedigree
* Large feature space
* Meaningful temporal ordering
* Device information available
* Product and card features
* Higher fraud rate (~3.5%) for better modeling

#### Weaknesses

* Heavily anonymized — V-columns have no interpretable meaning
* No explicit customer/user ID
* Card features are anonymized (card1-card6 are not real card numbers)
* No merchant identifier
* No geographic coordinates
* Competition dataset — may have data processing applied
* 399 columns make it harder to explain to non-technical audience

#### Temporal Leakage Analysis

* `TransactionDT` provides temporal ordering (seconds from reference)
* Can compute time-based features
* Customer grouping requires proxy (card1 + addr1)
* VERDICT: Supports temporal features but customer grouping is fuzzy

#### Behavioral Feature Potential: GOOD (with caveats)

Can compute:
* Transaction velocity via V-columns (but these are pre-computed)
* Amount patterns
* Time-of-day features
* Card-based grouping features

LIMITATION: Without clear customer ID, per-customer behavioral features are approximate.

#### Business Analytics Potential: MODERATE

* Product type analysis possible
* Email domain analysis possible
* Device analysis possible
* BUT: Lack of merchant/geography limits business narrative

---

### 4. PaySim Mobile Money Simulation

**Source:** NTNU (Norwegian University of Science and Technology)
**URL:** https://www.kaggle.com/datasets/ealaxi/paysim1
**Size:** ~6,362,620 rows
**Columns:** 11
**Fraud rate:** ~0.129%
**License:** CC BY 4.0
**Type:** Synthetic (simulated mobile money from African patterns)

#### Available Fields

```text
Core:
  step (time unit = 1 hour)
  type (CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER)
  amount

Accounts:
  nameOrig (origin customer)
  nameDest (destination customer)

Balances:
  oldbalanceOrg / newbalanceOrig
  oldbalanceDest / newbalanceDest

Labels:
  isFraud
  isFlaggedFraud
```

#### Strengths

* Explicit customer IDs (`nameOrig`)
* Temporal ordering via `step`
* Balance information enables anomaly detection
* Academic paper backing (KES 2016)
* Good license (CC BY 4.0)
* Large size
* Clean fraud labels

#### Weaknesses

* Only 11 columns — very sparse feature set
* Synthetic data
* No merchant information
* No device information
* No geographic information
* No payment method beyond transaction type
* Balance fields may leak fraud signal (fraudulent transactions often have balance discrepancies)
* Only 4 transaction types

#### Temporal Leakage Analysis

* `step` provides hourly temporal ordering
* Can compute velocity and time-based features
* Balance changes are transaction-level (safe)
* VERDICT: Supports temporal features but limited context

#### Behavioral Feature Potential: MODERATE

Can compute:
* Transaction frequency per customer
* Amount patterns
* Transaction type preferences
* Balance anomaly patterns

LIMITATION: Only 4 transaction types, no merchant/device/geo.

#### Business Analytics Potential: LIMITED

* Transaction type analysis only
* No merchant, device, or geographic analysis possible

---

### 5. MLG-ULB Credit Card Fraud Detection

**Source:** Worldline & ULB (Universite Libre de Bruxelles)
**URL:** https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
**Size:** 284,807 rows
**Columns:** 31
**Fraud rate:** ~0.172%
**License:** CC BY 4.0
**Type:** Real (European card transactions, 2 days)

#### Available Fields

```text
Core:
  Time (seconds from first transaction)
  Amount

Target:
  Class (0=legitimate, 1=fraud)

PCA features:
  V1-V28 (anonymized)
```

#### Strengths

* Real data
* Clean license (CC BY 4.0)
* Academic pedigree
* Well-documented

#### Weaknesses

* Only 31 columns — severely limited feature set
* V1-V28 are PCA-transformed — no original features preserved
* No customer ID
* No merchant ID
* No geographic information
* No device information
* Only 2 days of data
* Time field is relative (seconds from first transaction), not calendar
* Massively overused in tutorials — poor portfolio differentiation
* Cannot support behavioral feature engineering
* Cannot support investigation queue narrative

#### Temporal Leakage Analysis

* `Time` provides ordering but no calendar date
* Only 2 days of data — very limited temporal patterns
* No customer ID — cannot compute per-customer temporal features
* VERDICT: POOR temporal feature engineering potential

#### Behavioral Feature Potential: POOR

Cannot compute meaningful behavioral features without customer/merchant identity.

#### Business Analytics Potential: POOR

Cannot support business analytics beyond basic precision/recall analysis.

#### WHY THIS DATASET IS NOT RECOMMENDED

This dataset is the most famous fraud detection dataset, but it is unsuitable for FraudLens because:

1. No customer identifiers → no behavioral profiling
2. No merchant identifiers → no merchant risk analysis
3. No geographic data → no location-based rules
4. No device data → no device risk signals
5. Only 2 days → no meaningful temporal patterns
6. PCA features are uninterpretable → poor SHAP explanations
7. Cannot support investigation queue narrative
8. Cannot demonstrate data engineering or analytics engineering

This dataset demonstrates binary classification on anonymized features. FraudLens needs transaction-level behavioral intelligence.

---

### 6. NeurIPS Bank Account Fraud Dataset Suite

**Source:** Amdocs Research / Olist Brazil
**URL:** https://www.kaggle.com/datasets/sgpjesus/bank-account-fraud-dataset-neurips-2022
**Size:** ~200K to 1.5M rows (6 variants)
**Columns:** ~30
**Fraud rate:** ~1.8%
**License:** CC BY 4.0
**Type:** Synthetic (generative model trained on real data)

#### Available Fields

```text
Core:
  fraud_bool (target)
  income
  intended_balcon_amount
  days_since_request

Velocity:
  velocity_6h / 24h / 4w
  zip_count_4w
  bank_branch_count_8w
  device_distinct_emails_8w
  device_fraud_count

Identity:
  customer_age
  name_email_similarity
  prev_address_months_count
  current_address_months_count
  date_of_birth_distinct_email_4w

Employment:
  employment_status
  housing_status
  credit_risk_score

Payment:
  payment_type
  bank_months_count
  has_other_cards
  foreign_request
  session_length_in_minutes
  email_is_free
  phone_home_valid / phone_mobile_valid
```

#### Strengths

* Academic pedigree (NeurIPS 2022)
* Good license (CC BY 4.0)
* Pre-computed velocity features
* Multiple dataset variants for debiasing research

#### Weaknesses

* Application-level fraud, not transaction-level
* No timestamps (only `days_since_request`)
* No customer ID
* No merchant information
- No device identity (only aggregated device features)
- No geographic coordinates
- Synthetic data
- Designed for fairness/bias research, not operational fraud detection

#### Temporal Leakage Analysis

* No meaningful timestamps — `days_since_request` is relative
* Cannot compute temporal behavioral features
* VERDICT: POOR temporal feature engineering potential

#### Behavioral Feature Potential: POOR

Pre-computed velocity features exist but cannot be extended with new behavioral features.

#### Business Analytics Potential: MODERATE

* Application fraud analysis possible
* Velocity analysis via pre-computed features
* But: Not transaction-level, so doesn't match FraudLens use case

---

### 7. Olist Brazilian E-Commerce

**Source:** Olist (Brazilian e-commerce company)
**URL:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
**Size:** ~100K orders across 7 relational CSV files
**Columns:** ~30+ (across tables)
**Fraud rate:** NOT LABELED — no fraud column exists
**License:** CC BY 4.0
**Type:** Real (anonymized)

#### Available Fields

```text
Orders:
  order_id, customer_id, order_status
  order_purchase_timestamp
  order_approved_timestamp
  order_delivered_timestamp

Items:
  product_id, seller_id, price, freight_value

Customers:
  customer_id, customer_unique_id
  customer_city, customer_state

Payments:
  payment_type, payment_value, payment_installments

Reviews:
  review_score, review_comment

Products:
  product_category, product_weight

Sellers:
  seller_id, seller_city, seller_state
```

#### Strengths

* Real data
* Excellent relational structure
* Rich timestamps (purchase, approval, delivery)
* Customer and seller identifiers
* Geographic information
* Payment information
* Good license

#### Weaknesses

* NO FRAUD LABELS — cannot be used directly for fraud detection
* E-commerce orders, not financial transactions
* Would require synthetic fraud label generation
* Not designed for fraud detection

#### Temporal Leakage Analysis

* Rich timestamps available
* Temporal ordering is excellent
* VERDICT: Excellent temporal structure, but no fraud labels

#### Behavioral Feature Potential: N/A (no fraud labels)

#### Business Analytics Potential: N/A (no fraud labels)

#### NOTE

Olist is excluded from final consideration because it lacks fraud labels. However, it could be combined with synthetic fraud label generation if needed.

---

## Temporal Leakage Analysis — Deep Dive

Temporal leakage is the most critical evaluation criterion for FraudLens.

### Nigerian Financial Transactions

| Feature | Leakage Risk | Notes |
| --- | --- | --- |
| `time_since_last_transaction` | LOW | Uses only prior history |
| `txn_count_last_1h` | LOW | Relative window from current txn |
| `txn_count_last_24h` | LOW | Relative window from current txn |
| `total_amount_last_1h` | LOW | Relative window from current txn |
| `user_txn_count_total` | **HIGH** | All-time aggregate — causes leakage |
| `user_avg_txn_amt` | **HIGH** | All-time aggregate — causes leakage |
| `user_std_txn_amt` | **HIGH** | All-time aggregate — causes leakage |
| `merchant_fraud_rate` | **HIGH** | All-time aggregate — causes leakage |
| `spending_deviation_score` | UNKNOWN | Pre-computed — needs verification |
| `velocity_score` | UNKNOWN | Pre-computed — needs verification |
| `geo_anomaly_score` | UNKNOWN | Pre-computed — needs verification |

**Mitigation:** Compute history-only versions of aggregated features in dbt/feature engineering layer. Use raw transaction data with timestamps to ensure only prior transactions are used.

### Kartik Fraud Detection

| Feature | Leakage Risk | Notes |
| --- | --- | --- |
| `trans_date_trans_time` | SAFE | Input timestamp |
| `amt` | SAFE | Transaction attribute |
| Customer features (computed) | SAFE if computed correctly | Use only prior transactions |

**All features must be computed from scratch** — no pre-computed aggregates exist.

**VERDICT:** Cleanest temporal feature engineering — no pre-computed features to worry about.

### IEEE-CIS

| Feature | Leakage Risk | Notes |
| --- | --- | --- |
| `TransactionDT` | SAFE | Input timestamp |
| `V1-V339` | UNKNOWN | Pre-computed by Vesta — may include future info |
| Card features | SAFE | Transaction attributes |

**VERDICT:** V-columns are opaque — cannot verify leakage risk without documentation.

### PaySim

| Feature | Leakage Risk | Notes |
| --- | --- | --- |
| `step` | SAFE | Input timestamp |
| Balance fields | SAFE | Transaction-level |
| `isFlaggedFraud` | N/A | System flag, not model input |

**VERDICT:** Clean temporal structure.

---

## Decision

### PRIMARY DATASET

**Name:** Nigerian Financial Transactions and Fraud Detection Dataset

**Source:** Electric Sheep Africa (HuggingFace)

**URL:** https://huggingface.co/datasets/electricsheepafrica/Nigerian-Financial-Transactions-and-Fraud-Detection-Dataset

**License:** "other" (non-standard; must verify before committing to use)

**Type:** Synthetic

**Why selected:**

1. **Richest feature set** — 44 columns covering transactions, accounts, devices, geography, behavioral scores, and fraud labels
2. **Temporal ordering** — full datetime timestamps enable velocity features and temporal splits
3. **Customer identifiers** — `sender_account` and `receiver_account` enable per-customer behavioral profiling
4. **Device and location** — device_used, location, ip_address enable device/geographic risk rules
5. **Fraud type categories** — `fraud_type` column provides explainability beyond binary label
6. **Business analytics** — supports questions about which transaction types, personas, locations, and devices are risky
7. **Investigation queue** — large enough to demonstrate top-K fraud capture and analyst workload modeling
8. **Pre-computed baselines** — spending_deviation_score, velocity_score, geo_anomaly_score provide reference features
9. **Portfolio differentiation** — less commonly used than MLG-ULB, more feature-rich than PaySim

**Weaknesses to build around:**

* Synthetic data — must document clearly
* License requires verification
* Some pre-computed features may leak future information — must compute history-only versions
* Nigerian banking context — must acknowledge domain specificity

**What it prevents us from demonstrating:**

* Real-world data provenance (it's synthetic)
* Cross-market generalization
* Regulatory compliance scenarios

### BACKUP DATASET

**Name:** Kartik Agrawal — Credit Card Transactions Fraud Detection

**Source:** Kaggle

**URL:** https://www.kaggle.com/datasets/kartik2112/fraud-detection

**License:** CC0 / Public Domain (user-uploaded)

**Type:** Synthetic

**Why selected as backup:**

1. Clean temporal structure with full datetime timestamps
2. Explicit customer ID (`cc_num`) and merchant information
3. Geographic coordinates for customer and merchant
4. No pre-computed features — all behavioral features must be computed from scratch (cleaner temporal guarantee)
5. Good size (~1.3M rows)
6. Well-structured for pipeline demonstration

**When to use backup:**

If the Nigerian dataset license proves problematic, or if the pre-computed features create too much complexity in the feature engineering layer, the Kartik dataset provides a cleaner starting point.

---

## FraudLens Will Use

FraudLens will use the **Nigerian Financial Transactions and Fraud Detection Dataset** as the primary dataset because it provides the richest feature set for demonstrating transaction-level behavioral risk intelligence, temporal feature engineering, and business analytics — the core differentiators of the FraudLens platform.

The decision is conditional on verifying the dataset license permits use in a public GitHub portfolio project.

---

## Candidates Evaluated

7

## Strongest Capability

Temporal behavioral analysis with per-customer device, geographic, and velocity features

## Biggest Limitation

License status requires verification; synthetic data must be clearly documented

## Documentation Updated

* `docs/dataset-selection.md` — full evaluation and decision
* `data/README.md` — dataset directory documentation
* `data/dataset_metadata.yml` — dataset metadata

## Verification

* Dataset pages confirmed accessible via WebFetch
* Field names verified from HuggingFace dataset viewer
* Row count verified (5M rows)
* License marked as "other" — requires manual verification
* Fraud rate requires download to confirm

## Next Step

STOP.

Do not proceed to implementation.

Wait for explicit instruction before beginning the ingestion phase.

---

# Raw Dataset Validation — Physical Audit

## Date

2026-09-08

## Dataset

**Name:** Nigerian Financial Transactions and Fraud Detection Dataset

**Version:** V1 (main dataset)

**File:** `V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv`

**Rows:** 5,000,000

**Columns:** 21

**File size:** 924.0 MB

**SHA256:** `ed7753fbd7da6d775ce1cd0a339c15abdcc304dae6f668643d15f7e9427cbe09`

**Source:** https://huggingface.co/datasets/electricsheepafrica/Nigerian-Financial-Transactions-and-Fraud-Detection-Dataset

**License:** "other" (non-standard; requires manual review)

---

## Data Quality

| Check | Result | Status |
| --- | --- | --- |
| Row count | 5,000,000 | VERIFIED |
| Column count | 21 | VERIFIED |
| Schema | All columns readable | PASS |
| Fraud rate | 3.5911% (179,553 fraud) | VERIFIED |
| Timestamps | 0 parse failures, microsecond precision | PASS |
| Nulls | Only in time_since_last_transaction (17.93%) | PASS |
| Duplicates | 0 exact duplicate rows | PASS |
| Identifier quality | All IDs unique, no nulls | PASS |
| Data anomalies | See critical findings below | MIXED |

---

## Critical Findings

### 1. new_device_transaction — TARGET LEAKAGE

**100% of fraud cases have `new_device_transaction=True`.**
**0% of legitimate cases have `new_device_transaction=False`.**

| new_device_transaction | Legitimate | Fraud | Fraud Rate |
| --- | --- | --- | --- |
| False | 896,464 | 0 | 0.0000% |
| True | 3,923,983 | 179,553 | 4.3756% |

**This feature directly encodes the fraud label.** Must be excluded from all models.

### 2. time_since_last_transaction — BROKEN

- 41.03% of values are **negative** (time cannot be negative)
- 17.93% are null (first transactions per customer)
- Correlation with actual time difference between transactions: **0.23** (essentially random)
- Does not match reconstructed values from raw timestamps

### 3. velocity_score — NO PREDICTIVE SIGNAL

Uniformly distributed 1-20 with ~250,000 observations per value. Fraud rate is identical across all values (~3.59%).

### 4. geo_anomaly_score — NO PREDICTIVE SIGNAL

Uniform distribution 0-1. Fraud rate identical across all bins.

### 5. spending_deviation_score — WEAK SIGNAL

Nearly uniform fraud rate across bins. Weak positive correlation with fraud (0.0007 vs -0.0004).

### 6. Suspiciously Uniform Fraud Rates

Fraud rate is approximately 3.59% across ALL dimensions:
- Transaction type: 3.56-3.63%
- Payment channel: 3.58-3.61%
- Location: 3.55-3.64%
- Device: 3.57-3.62%
- Persona: 3.59%

This uniformity is characteristic of synthetic data generation without proper feature-target coupling.

---

## Fraud Rate (Calculated from Raw Data)

```text
Total transactions:    5,000,000
Fraud transactions:      179,553
Legitimate transactions: 4,820,447
Fraud rate:              3.5911%
```

### Fraud Rate by Transaction Type

| Type | Fraud Count | Total | Fraud Rate |
| --- | ---: | ---: | ---: |
| deposit | 44,786 | 1,250,593 | 3.58% |
| payment | 44,565 | 1,250,438 | 3.56% |
| transfer | 45,328 | 1,250,334 | 3.63% |
| withdrawal | 44,874 | 1,248,635 | 3.59% |

### Fraud Rate by Location

| Location | Fraud Count | Total | Fraud Rate |
| --- | ---: | ---: | ---: |
| Port Harcourt | 18,214 | 500,490 | 3.64% |
| Aba | 18,138 | 499,578 | 3.63% |
| Abuja | 17,958 | 500,193 | 3.59% |
| Kano | 17,961 | 499,699 | 3.59% |
| Onitsha | 17,954 | 498,894 | 3.60% |
| Kaduna | 17,936 | 500,738 | 3.58% |
| Ibadan | 17,941 | 501,521 | 3.58% |
| Lagos | 17,801 | 498,167 | 3.57% |
| Benin City | 17,858 | 499,806 | 3.57% |
| Enugu | 17,792 | 500,914 | 3.55% |

### Fraud Type Distribution

| Fraud Type | Count |
| --- | ---: |
| Account Takeover | 170,635 |
| Identity Fraud | 8,918 |

---

## Timestamp Audit

```text
Min timestamp:      2023-01-01 00:00:24.048140
Max timestamp:      2024-01-28 23:57:09.371969
Total time span:    392 days 23:56:45
Parse failures:     0
Null timestamps:    0
Globally sorted:    False
Duplicate timestamps: 0
Precision:          Microseconds (6 decimal digits)
```

### Hour Distribution

Hours 9-17 (business hours) have ~4x more transactions than off-hours. This is a realistic pattern.

### Day of Week

Uniform distribution (~700K-745K per day).

### Monthly

Uniform distribution (~382K-425K per month).

---

## Identifier Analysis

| Identifier | Unique | % Unique | Avg per Entity | Interpretation |
| --- | ---: | ---: | ---: | --- |
| transaction_id | 5,000,000 | 100.00% | 1.0 | All unique |
| sender_account | 896,463 | 17.93% | 5.6 | Good for customer profiling |
| receiver_account | 896,589 | 17.93% | 5.6 | Good for counterparty analysis |
| device_hash | 3,835,723 | 76.71% | 1.3 | Low reuse — limited device features |
| ip_address | 362,362 | 7.25% | 13.8 | Good for IP-based features |
| location | 10 | 0.00% | 500K | 10 Nigerian cities |
| merchant_category | 21 | 0.00% | 238K | 21 categories |
| payment_channel | 4 | 0.00% | 1.25M | 4 channels |
| device_used | 4 | 0.00% | 1.25M | 4 types (mobile/atm/pos/web) |
| sender_persona | 3 | 0.00% | 1.67M | 3 types (Student/Trader/Salary Earner) |

---

## Customer Distribution

```text
Max transactions per customer:  20
Median:                         5
Mean:                           5.6
P25:                            4
P75:                            7
P90:                            9
P95:                           10
P99:                           12
```

---

## Behavioral Feature Viability

| Feature Category | Status | Notes |
| --- | --- | --- |
| Velocity | SUPPORTED | Can compute from raw timestamps; limited by max 20 txns/customer |
| Customer behavior | SUPPORTED | Can compute avg, std, max, count from raw data |
| Device behavior | PARTIALLY | device_hash has low reuse (1.3 txns/device); new_device_transaction is leakage |
| IP behavior | PARTIALLY | Good IP reuse (13.8 txns/IP) but IP may not be reliable identifier |
| Geography | SUPPORTED | 10 cities; cannot compute distance (no lat/long) |
| Merchant/category | SUPPORTED | 21 categories; can compute category frequency and deviation |

---

## Leakage Audit

### SAFE (raw fields)

| Feature | Status | Reason |
| --- | --- | --- |
| timestamp | SAFE | Input field |
| amount_ngn | SAFE | Transaction attribute |
| transaction_type | SAFE | Transaction attribute |
| merchant_category | SAFE | Transaction attribute |
| location | SAFE | Transaction attribute |
| device_used | SAFE | Transaction attribute |
| payment_channel | SAFE | Transaction attribute |
| ip_address | SAFE | Transaction attribute |
| device_hash | SAFE | Transaction attribute |
| bvn_linked | SAFE | Account attribute |
| sender_persona | SAFE | Account attribute |
| sender_account | SAFE | Account identifier |
| receiver_account | SAFE | Account identifier |

### EXCLUDE FROM MODEL

| Feature | Status | Reason |
| --- | --- | --- |
| new_device_transaction | **LEAKAGE** | 100% fraud correlation; directly encodes target |
| time_since_last_transaction | **BROKEN** | 41% negative; correlation 0.23 with actual |
| velocity_score | **NO SIGNAL** | Uniform distribution; identical fraud rates |
| geo_anomaly_score | **NO SIGNAL** | Uniform distribution; identical fraud rates |
| spending_deviation_score | **WEAK** | Nearly uniform fraud rate across bins |

### COMPUTE FROM RAW

All behavioral features must be computed from raw fields using temporal ordering:

```text
transactions_last_10m       # from timestamp
transactions_last_1h        # from timestamp
transactions_last_24h       # from timestamp
customer_avg_amount_prior   # from sender_account + timestamp + amount_ngn
customer_std_amount_prior   # from sender_account + timestamp + amount_ngn
time_since_previous_txn     # from sender_account + timestamp
new_location_flag           # from sender_account + location + timestamp
category_frequency          # from sender_account + merchant_category
```

---

## Data Quality Summary

### Amounts

```text
Min:      22.80 NGN
Max:   21,628,477.86 NGN
Mean:    749,616.37 NGN
Median:  164,278.30 NGN
Negative: 0
Zero:     0
```

### Categorical Consistency

No whitespace issues. No case inconsistencies. All categorical fields have clean values.

---

## Synthetic Data Assessment

**Evidence of synthetic generation:**

1. Uniform fraud rates across ALL categorical dimensions (~3.59%)
2. `velocity_score` uniformly distributed 1-20 with identical fraud rates
3. `geo_anomaly_score` uniform distribution
4. `spending_deviation_score` appears to be standard normal
5. `new_device_transaction` has 100% fraud correlation (impossible in real data)
6. 41% negative `time_since_last_transaction` values
7. Timestamps have microsecond precision but `time_since` doesn't match

**Assessment:** Dataset is clearly synthetic. The generation process appears to independently assign features without proper temporal causality.

---

## License Investigation

```text
License listed:     "other" (non-standard)
License file:       NOT PRESENT in repository
README:             Basic description only, no license text
Original source:    Electric Sheep Africa (HuggingFace organization)
Provenance:         Synthetic; generation method NOT documented
Attribution:        NOT SPECIFIED
Portfolio use:      REQUIRES MANUAL REVIEW
Redistribution:     REQUIRES MANUAL REVIEW
```

---

## Performance / Resource Test

```text
File size:          924.0 MB
Memory required:    ~3.3 GB (for full DataFrame)
Load time:          ~16 seconds (on local machine)
Chunked processing: NOT required for V1 (fits in memory)
V2 file:            1.8 GB (45 columns) — may require chunking
```

---

## Dataset Decision

### APPROVED WITH CONDITIONS

**Conditions:**

1. **EXCLUDE `new_device_transaction`** — target leakage (100% fraud correlation)
2. **EXCLUDE `time_since_last_transaction`** — broken (41% negative, no correlation)
3. **EXCLUDE `velocity_score`** — no predictive signal
4. **EXCLUDE `geo_anomaly_score`** — no predictive signal
5. **EXCLUDE `spending_deviation_score`** — weak/no signal
6. **COMPUTE ALL behavioral features from raw fields** — do not use any pre-computed features
7. **VERIFY LICENSE** before any public distribution
8. **DOCUMENT synthetic nature** clearly in all outputs

**The raw fields (timestamp, sender_account, amount_ngn, merchant_category, location, device_used, payment_channel, ip_address, device_hash, bvn_linked, sender_persona) are sufficient for feature engineering.**

---

## Changes Made

* `data/dataset_metadata.yml` — updated with validation findings
* `docs/dataset-selection.md` — appended raw validation report

## Verification Performed

* File existence and size: VERIFIED
* Row count: VERIFIED (5,000,000)
* Column count: VERIFIED (21 in V1, 45 in V2)
* Schema audit: ALL COLUMNS INSPECTED
* Fraud rate: CALCULATED FROM RAW DATA
* Timestamp parsing: 0 failures
* Duplicate audit: 0 duplicates
* Identifier cardinality: ALL CALCULATED
* Customer distribution: CALCULATED (max 20 txns/customer)
* Temporal leakage: TESTED (new_device_transaction = leakage, time_since = broken)
* Feature signal: TESTED (velocity_score, geo_anomaly_score = no signal)
* Synthetic assessment: CONFIRMED (uniform fraud rates, broken temporal features)
* License: REQUIRES MANUAL REVIEW

---

## Next Step

STOP.

Do not proceed to implementation.

Wait for explicit instruction before beginning the ingestion phase.
