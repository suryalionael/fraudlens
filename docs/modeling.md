# Machine Learning Modeling

## 1. Objective

The objective of the ML component is to estimate the likelihood that a transaction is fraudulent and provide a useful ranking for investigation prioritization.

The model is not intended to make an irreversible financial decision.

---

## 2. Modeling Problem

Primary formulation:

```text
Input:
Transaction + historical behavioral features

Output:
P(fraud | transaction context)
```

The output should be a probability or calibrated score rather than an arbitrary binary label.

---

## 3. Baseline

The first model should be simple and interpretable.

Recommended baseline:

```text
Logistic Regression
```

Purpose:

* establish a benchmark;
* identify basic signal;
* provide interpretable coefficients;
* validate the feature pipeline.

---

## 4. Candidate Models

Potential progression:

```text
Logistic Regression
        ↓
Random Forest
        ↓
XGBoost
```

More complex models should only be adopted if they provide meaningful improvement.

---

## 5. Class Imbalance

Fraud is expected to represent a minority class.

Potential techniques:

* class weighting;
* threshold adjustment;
* undersampling;
* oversampling;
* SMOTE where appropriate.

The chosen approach must be documented.

---

## 6. Train / Validation / Test

Where timestamps permit, prefer temporal evaluation.

Example:

```text
Historical period
       ↓
Training

Later period
       ↓
Validation

Most recent period
       ↓
Test
```

Random splitting should not be used automatically when it would create unrealistic temporal leakage.

---

## 7. Hyperparameter Tuning

Hyperparameter tuning should optimize an appropriate validation metric.

Avoid optimizing purely for accuracy.

Potential objective:

```text
PR-AUC
```

or a business-oriented ranking metric.

---

## 8. Calibration

If the model probability is used directly for risk scoring, probability calibration should be evaluated.

Potential methods:

* Platt scaling;
* isotonic regression.

Calibration should only be added when supported by the data and evaluation.

---

## 9. Model Versioning

Every trained model should have a version identifier.

Example:

```text
fraudlens-xgb-v001
```

Model metadata should include:

```text
model_version
training_data_version
feature_version
training_timestamp
hyperparameters
evaluation_results
```

---

## 10. Model Selection

The best model is not necessarily the model with the highest PR-AUC.

Selection should consider:

* predictive performance;
* precision/recall trade-off;
* calibration;
* explainability;
* computational cost;
* operational usefulness;
* stability.

---

## 11. Leakage Prevention

The modeling pipeline must ensure:

```text
Training features
        ↓
Historical information only
```

No future transaction information may influence the model.
