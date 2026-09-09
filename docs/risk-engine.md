# Risk Engine

## 1. Purpose

The risk engine converts transaction context and model outputs into an actionable risk assessment.

The goal is to produce:

```text
Risk Score
Risk Level
Risk Factors
Recommended Action
```

---

## 2. Conceptual Flow

```text
Transaction
     |
     +---- Behavioral Features
     |
     +---- ML Prediction
     |
     +---- Rule Signals
     |
     v
Risk Engine
     |
     v
Risk Score
     |
     v
Risk Level
     |
     v
Recommended Action
```

---

## 3. Risk Score

The initial score should be standardized to:

```text
0–100
```

The exact scoring formula must be documented and versioned.

---

## 4. Risk Levels

Initial proposal:

|  Score | Level    |
| -----: | -------- |
|   0–29 | Low      |
|  30–59 | Medium   |
|  60–79 | High     |
| 80–100 | Critical |

These boundaries are configurable and should eventually be validated against operational performance.

---

## 5. Rule Engine

Potential rule signals:

```text
new_device
amount_anomaly
velocity_anomaly
international_transaction
impossible_travel
high_risk_merchant
prior_customer_fraud
```

Rules should generate structured signals.

Example:

```json
{
  "rule": "amount_anomaly",
  "triggered": true,
  "severity": "high"
}
```

---

## 6. ML Contribution

The model produces:

```text
fraud_probability
```

The risk engine may transform this into a normalized contribution.

The model output must remain distinguishable from deterministic rules.

---

## 7. Explainability

The API response combines two types of risk factors:

1. **Rule-based signals** — deterministic rules that trigger on specific conditions
2. **SHAP explanations** — model-based feature contributions

Example:

```json
{
  "risk_factors": [
    "Transaction from a new device",
    "Transaction amount significantly deviates from sender's average",
    "Feature 'amount_zscore' increases risk (contribution: 0.2341)",
    "Feature 'device_first_seen_int' increases risk (contribution: 0.1892)"
  ]
}
```

SHAP explanations are generated using:
* `TreeExplainer` for tree-based models (Random Forest, XGBoost)
* Coefficient-based attribution for linear models (Logistic Regression)

Explanations describe features CONTRIBUTING to the model prediction, not causal evidence of fraud.

---

## 8. Recommended Actions

Potential actions:

```text
allow
monitor
review
urgent_review
```

These are analytical recommendations only.

They do not represent actual banking authorization logic.

---

## 9. Versioning

Risk logic should have a version.

Example:

```text
risk_engine_version = 001
```

Changes to:

* thresholds;
* weights;
* rules;
* scoring formulas

should produce a documented version change.

---

## 10. Testing

Test:

* boundary values;
* missing features;
* rule triggering;
* score ranges;
* risk-level assignment;
* deterministic behavior.
