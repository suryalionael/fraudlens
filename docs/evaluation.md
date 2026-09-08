# Model Evaluation

## 1. Objective

FraudLens evaluates models from both a machine-learning and operational perspective.

---

## 2. Primary Metric

### PR-AUC

Precision-Recall Area Under the Curve is the primary model-ranking metric because fraud is expected to be highly imbalanced.

---

## 3. Secondary Metrics

### Precision

Of transactions flagged as fraud, how many were actually fraudulent?

```text
Precision = TP / (TP + FP)
```

---

### Recall

Of actual fraudulent transactions, how many were detected?

```text
Recall = TP / (TP + FN)
```

---

### F1

Harmonic mean of precision and recall.

```text
F1 = 2 × Precision × Recall / (Precision + Recall)
```

---

### Precision@K

Among the top K highest-risk transactions, what proportion are fraudulent?

This is especially relevant to investigation teams with limited capacity.

---

### Recall@K

What percentage of all fraud is captured within the top K transactions?

---

## 4. Business Metrics

The project should also report:

```text
transactions reviewed
fraud detected
fraud capture rate
false positives
investigation rate
```

Where the dataset provides enough information, potential financial impact may also be estimated.

Such estimates must clearly state their assumptions.

---

## 5. Threshold Analysis

Instead of selecting an arbitrary probability threshold, evaluate multiple operating points.

Example:

```text
Threshold
    ↓
Flagged transactions
    ↓
Precision
    ↓
Recall
    ↓
Investigation workload
```

---

## 6. Investigation Capacity

Evaluate scenarios such as:

```text
Top 100
Top 500
Top 1,000
Top 5,000
```

The goal is to understand the trade-off between:

```text
analyst workload
        vs.
fraud captured
```

---

## 7. Confusion Matrix

Report:

```text
True Positives
False Positives
True Negatives
False Negatives
```

---

## 8. Model Comparison

All models must be evaluated on the same test set.

Example structure:

| Model               | PR-AUC | Precision | Recall |  F1 |
| ------------------- | -----: | --------: | -----: | --: |
| Logistic Regression |    TBD |       TBD |    TBD | TBD |
| Random Forest       |    TBD |       TBD |    TBD | TBD |
| XGBoost             |    TBD |       TBD |    TBD | TBD |

`TBD` values must be replaced only after experiments are actually run.

---

## 9. Evaluation Integrity

Never:

* tune directly on the test set;
* report validation performance as test performance;
* mix future information into training;
* claim business impact without assumptions;
* optimize solely for accuracy.
