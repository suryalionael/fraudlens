# FraudLens API

## 1. Purpose

The API provides programmatic access to FraudLens risk scoring.

The initial API will use FastAPI.

---

## 2. Endpoint

### `POST /score-transaction`

Scores a transaction using the currently configured model and risk engine.

---

## 3. Example Request

```json
{
  "customer_id": "C182",
  "amount": 4921.00,
  "merchant_category": "electronics",
  "country": "JP",
  "device_id": "D9182"
}
```

The exact request schema depends on the finalized feature set.

---

## 4. Example Response

```json
{
  "risk_score": 91,
  "risk_level": "critical",
  "fraud_probability": 0.91,
  "recommended_action": "urgent_review",
  "risk_factors": [
    "new_device",
    "amount_anomaly",
    "international_transaction"
  ],
  "model_version": "xgb-v001",
  "risk_engine_version": "001"
}
```

The example is illustrative only.

Actual values must come from the deployed model.

---

## 5. Health Endpoint

### `GET /health`

Expected response:

```json
{
  "status": "ok"
}
```

---

## 6. Model Metadata

A future endpoint may expose:

```text
model version
feature version
training timestamp
```

without exposing sensitive implementation details.

---

## 7. Validation

Requests must validate:

* required fields;
* types;
* valid numeric ranges;
* categorical values where applicable.

---

## 8. Error Handling

The API should return appropriate HTTP status codes.

Examples:

```text
400 / 422
Invalid request

404
Resource not found

500
Unexpected server error
```

Errors should not expose secrets or internal credentials.

---

## 9. API Testing

Tests should cover:

* valid request;
* invalid request;
* missing fields;
* invalid values;
* model unavailable;
* risk engine failure;
* health endpoint.
