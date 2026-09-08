# FraudLens Power BI Dashboard

## 1. Purpose

The dashboard translates transaction and risk data into actionable business intelligence.

The primary audience is:

* fraud analysts;
* risk analysts;
* managers;
* business stakeholders.

---

# 2. Dashboard Pages

## Page 1 — Executive Overview

Potential KPIs:

```text
Total Transactions
Transaction Value
Fraud Rate
Fraudulent Transaction Count
High-Risk Transactions
Fraud Capture Rate
Investigation Volume
```

Visuals:

* fraud trend;
* risk distribution;
* fraud by category;
* fraud by geography.

---

## Page 2 — Risk Monitoring

Focus:

> Where is risk increasing?

Potential visuals:

* risk-score distribution;
* high-risk transaction trend;
* risk by merchant category;
* risk by geography;
* risk by time of day.

---

## Page 3 — Investigation Queue

Primary table:

```text
Transaction ID
Timestamp
Amount
Risk Score
Risk Level
Fraud Probability
Top Risk Factors
Recommended Action
Investigation Status
```

The queue should prioritize high-risk transactions.

---

## Page 4 — Fraud Analysis

Potential analysis:

* fraud rate by merchant category;
* fraud rate by customer segment;
* fraud over time;
* transaction amount distributions;
* device-related fraud;
* geographic patterns.

---

## Page 5 — Model Performance

Potential metrics:

```text
PR-AUC
Precision
Recall
F1
Precision@K
Recall@K
False-positive rate
```

---

## 3. Dashboard Design Principles

The dashboard should prioritize:

1. Decision usefulness
2. Clarity
3. Consistency
4. Minimal visual clutter
5. Correct interpretation

Avoid decorative charts that do not answer a business question.

---

## 4. Investigation Experience

The investigation page should allow an analyst to quickly answer:

> What happened?

> How risky is it?

> Why was it flagged?

> What should I investigate first?

---

## 5. Data Refresh

The dashboard should eventually use a repeatable refresh process.

Manual manipulation of exported CSV files should not be part of the final workflow.
