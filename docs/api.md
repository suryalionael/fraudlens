# FraudLens API

## 1. Purpose

The API provides programmatic access to FraudLens risk scoring.

Built with FastAPI. Uses the trained ML model (not heuristics) for fraud probability estimation.

---

## 2. Endpoints

### `POST /score-transaction`

Scores a transaction using the trained ML model and risk engine.

The request must include all behavioral features needed by the model.

### `GET /health`

Returns health status including whether the model is loaded.

### `GET /docs`

Interactive OpenAPI documentation.

---

## 3. Request Schema

```json
{
  "transaction_id": "T123456",
  "sender_account": "ACC001",
  "receiver_account": "ACC002",
  "transaction_type": "transfer",
  "merchant_category": "electronics",
  "location": "Lagos",
  "device_used": "mobile",
  "amount_ngn": 50000.00,
  "payment_channel": "Bank Transfer",
  "ip_address": "192.168.1.1",
  "device_hash": "D1234567",
  "sender_persona": "Trader",
  "customer_transaction_count_prior": 10,
  "customer_avg_amount_prior": 45000.0,
  "amount_zscore": 2.5,
  "device_first_seen": true,
  "transactions_last_10m": 5
}
```

Required fields: `transaction_id`, `sender_account`, `receiver_account`, `transaction_type`, `merchant_category`, `location`, `device_used`, `amount_ngn`, `payment_channel`, `ip_address`, `device_hash`, `sender_persona`.

Optional behavioral features default to 0 if not provided.

---

## 4. Response Schema

```json
{
  "transaction_id": "T123456",
  "fraud_probability": 0.85,
  "risk_score": 78.5,
  "risk_level": "high",
  "recommended_action": "review",
  "risk_factors": [
    "Transaction from a new device",
    "Feature 'amount_zscore' increases risk (contribution: 0.2341)"
  ],
  "model_version": "fraudlens-rf-v001",
  "risk_engine_version": "001",
  "scored_at": "2024-01-01T00:00:00"
}
```

`fraud_probability` comes from the actual trained ML model.
`risk_score` combines ML probability (70%) with rule engine (30%).
`risk_factors` combine rule-based signals with SHAP explanations.

---

## 5. Health Response

```json
{
  "status": "ok",
  "version": "0.1.0",
  "model_loaded": true,
  "model_version": "fraudlens-rf-v001",
  "scored_at": "2024-01-01T00:00:00"
}
```

`status` is `"ok"` when model is loaded, `"degraded"` when not.

---

## 6. Error Codes

| Code | Meaning |
| --- | --- |
| 422 | Invalid request (validation error) |
| 503 | Model not loaded (train a model first) |
| 500 | Internal scoring error |

---

## 7. Model Loading

The API loads a trained model artifact at startup from:

```text
FRAUDLENS_MODEL_PATH env var
  or
models/random_forest.artifact.pkl (default)
```

If no model is found, the API starts in degraded mode (health returns `"degraded"`, scoring returns 503).

To train a model:

```python
from fraudlens.models.serving import train_and_persist_model
train_and_persist_model(df, output_dir="models/", model_name="random_forest")
```

---

## 8. Explainability

Responses include SHAP-based feature explanations showing which features contributed most to the prediction.

---

## 9. API Testing

Tests cover:

* valid request with real model
* missing required fields (422)
* invalid values (422)
* model unavailable (503)
* health endpoint (ok/degraded)
* OpenAPI schema
* end-to-end scoring
