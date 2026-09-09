# FraudLens API

## 1. Purpose

Real-time synchronous fraud risk scoring for financial transactions.

Built with FastAPI. Uses trained ML model for fraud probability, SHAP for explanations, risk engine for decisions, and PostgreSQL for persistence.

---

## 2. Endpoints

### `POST /score-transaction`

Real-time synchronous scoring of a single transaction.

### `GET /health`

Liveness check — is the process alive?

### `GET /ready`

Readiness check — can the API serve requests? (verifies model + database)

---

## 3. Request Schema (`POST /score-transaction`)

Only raw transaction attributes are accepted. Behavioral features are generated server-side from historical context.

```json
{
  "transaction_id": "TXN-001",
  "timestamp": "2026-09-09T15:42:31Z",
  "amount_ngn": 185000.00,
  "transaction_type": "TRANSFER",
  "merchant_category": "Electronics",
  "location": "Lagos",
  "device_used": "mobile",
  "payment_channel": "mobile_app",
  "ip_address": "192.168.1.100",
  "device_hash": "device_abc123",
  "bvn_linked": true,
  "sender_persona": "individual",
  "sender_account": "ACC-12345",
  "receiver_account": "ACC-98765"
}
```

### Required Fields

| Field | Type | Validation |
| --- | --- | --- |
| `transaction_id` | string | 1-128 chars, not whitespace |
| `timestamp` | string | ISO 8601, timezone-aware, not future |
| `amount_ngn` | float | > 0, finite, not NaN |
| `transaction_type` | string | 1-50 chars |
| `merchant_category` | string | 1-100 chars |
| `location` | string | 1-100 chars |
| `device_used` | string | 1-50 chars |
| `payment_channel` | string | 1-50 chars |
| `ip_address` | string | 1-45 chars |
| `device_hash` | string | 1-256 chars |
| `bvn_linked` | bool | JSON boolean |
| `sender_persona` | string | 1-50 chars |
| `sender_account` | string | 1-128 chars |
| `receiver_account` | string | 1-128 chars |

### Forbidden Fields

The following fields are rejected with 422:

```text
new_device_transaction
time_since_last_transaction
velocity_score
geo_anomaly_score
spending_deviation_score
```

### Unknown Fields

Unknown fields are rejected with 422 (`extra="forbid"`).

---

## 4. Response Schema

```json
{
  "transaction_id": "TXN-001",
  "fraud_probability": 0.8734,
  "risk_score": 84,
  "risk_level": "high",
  "recommended_action": "review",
  "risk_factors": [
    {
      "feature": "amount_zscore",
      "impact": 0.31,
      "direction": "HIGHER_RISK"
    }
  ],
  "model_version": "fraudlens-rf-v001",
  "risk_engine_version": "001",
  "scored_at": "2026-09-09T15:42:32Z"
}
```

### Response Fields

| Field | Type | Range |
| --- | --- | --- |
| `fraud_probability` | float | 0-1 |
| `risk_score` | float | 0-100 |
| `risk_level` | string | low/medium/high/critical |
| `recommended_action` | string | allow/monitor/review/urgent_review |

---

## 5. Error Responses

### 422 — Validation Error

Missing fields, invalid types, unknown fields, forbidden precomputed features.

### 400 — Bad Request

Future timestamp, invalid timestamp format.

### 409 — Conflict

Same transaction_id with different payload (if detected).

### 503 — Scoring Unavailable

Model not loaded or database unreachable.

### 500 — Internal Error

Unexpected failures. Never exposes stack traces or secrets.

---

## 6. Feature Generation

Features are generated server-side using historical context from PostgreSQL:

```text
Incoming Transaction
        ↓
Historical Context (PostgreSQL, strict temporal cutoff < T)
        ↓
Behavioral Features
        ↓
MODEL_FEATURES
        ↓
ML Model
        ↓
SHAP
        ↓
Risk Engine
        ↓
Response
```

---

## 7. Idempotency

Repeated requests with the same `transaction_id` return the existing scoring result without creating duplicate records.

---

## 8. Persistence

Every successful scoring result is persisted to `risk.transaction_scores` before the response is returned. The Investigation Queue automatically reflects persisted results.

---

## 9. Running

```bash
# Local
make api

# Docker
docker compose up api

# Production (ECS)
# Automatically deployed via GitHub Actions
```
