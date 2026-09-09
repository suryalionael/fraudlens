# FraudLens Dashboard

## 1. Purpose

The Streamlit dashboard translates transaction and risk data into actionable business intelligence.

All pages use real data from PostgreSQL/dbt marts. No fabricated or random data is used.

---

## 2. Data Architecture

```text
PostgreSQL (raw.transactions)
    ↓
dbt (fct_transactions_analytics, rpt_fraud_summary)
    ↓
Dashboard Data Access Layer (dashboard/data/)
    ↓
Streamlit Pages

Risk Scoring Pipeline:
raw.transactions → Feature preparation → ML model → Risk engine → risk.transaction_scores
    ↓
Dashboard Risk Monitoring / Investigation Queue
```

### Data Access Layer

```text
dashboard/data/
├── __init__.py
├── connection.py      — PostgreSQL connection utility
├── executive.py       — Executive Overview queries
├── risk.py            — Risk Monitoring queries
├── investigations.py  — Investigation Queue queries
└── fraud.py           — Fraud Analysis queries
```

All queries use parameterized SQL. No raw user input in queries.

---

## 3. Dashboard Pages

### Page 1 — Executive Overview

Data sources: `raw.transactions`

KPIs:
- Total Transactions
- Fraudulent Transactions
- Fraud Rate
- Total Transaction Value
- Fraudulent Transaction Value
- Average Transaction Amount

Charts:
- Fraud Volume & Rate Over Time
- Fraud by Merchant Category
- Fraud by Location
- Fraud by Transaction Type

### Page 2 — Risk Monitoring

Data sources: `risk.transaction_scores`

KPIs:
- Transactions Scored
- High Risk / Critical Risk counts
- High/Critical %
- Average Risk Score
- Requiring Investigation

Visuals:
- Risk Level Distribution
- Risk Score Trend
- Risk by Merchant Category

Requires: batch scoring to have been run first.

### Page 3 — Investigation Queue

Data sources: `risk.transaction_scores`

Features:
- Filterable by risk level
- Adjustable result limit
- Sorted by risk score DESC
- Shows transaction details, risk factors, recommended action

Requires: batch scoring to have been run first.

### Page 4 — Fraud Analysis

Data sources: `raw.transactions`

Tabs:
- Merchant analysis (volume, fraud count, fraud rate)
- Geography analysis
- Transaction Type analysis
- Payment Channel analysis

Additional: Fraud Volume vs Rate bubble data.

### Page 5 — Model Performance

Data sources: `models/*.metadata.json` files

Features:
- Real model metrics from training runs
- Model version, training timestamp
- PR-AUC, F1, feature count
- Expandable detail per model

---

## 4. Risk Score Persistence

Risk scores are stored in `risk.transaction_scores`:

```text
transaction_id (PK)
timestamp
sender_account, receiver_account
transaction_type, merchant_category, location, device_used, payment_channel
amount_ngn
is_fraud

fraud_probability
risk_score
risk_level
recommended_action
rule_score, ml_score
risk_factors (JSONB)
rule_signals (JSONB)

model_version
risk_engine_version
scored_at
```

### Populating Risk Scores

```python
from fraudlens.risk.batch import batch_score_transactions
batch_score_transactions(limit=10000)  # Score first 10K transactions
```

This scores raw transactions through the full pipeline and persists results.

---

## 5. Running the Dashboard

```bash
# Ensure PostgreSQL is running and data is ingested
export DATABASE_URL=postgresql://localhost:5432/fraudlens

# Run dashboard
python -m fraudlens.dashboard

# Or with Streamlit directly
streamlit run src/fraudlens/dashboard/app.py
```

### Model Performance Page

Set `FRAUDLENS_MODEL_DIR` to the directory containing trained model metadata:

```bash
export FRAUDLENS_MODEL_DIR=models/
```

---

## 6. Empty States

Each page handles missing data gracefully:

- Database unavailable → warning message
- No transactions → info message
- No risk scores → warning with instructions
- No model metadata → info message

---

## 7. Design Principles

1. Decision usefulness
2. Clarity
3. Consistency
4. Minimal visual clutter
5. Correct interpretation
6. Real data only — no fabricated metrics
