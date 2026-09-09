# FraudLens

**Real-time financial transaction risk scoring with explainable ML, leakage-safe feature engineering, and production AWS deployment.**

FraudLens receives an incoming transaction, validates it, generates behavioral features from historical context using only data available before the transaction timestamp, scores it with a trained ML model, explains the prediction via SHAP, calculates a risk decision combining ML and deterministic rules, persists the result to PostgreSQL, and returns a structured response — all synchronously.

> **Which transactions should a fraud analyst investigate, and why?**

---

## Architecture

### Real-Time Scoring Path

```text
Incoming Transaction
        │
        ▼
   FastAPI (validation)
        │
        ▼
   Historical Context ──────────────────────┐
   (PostgreSQL, strict temporal cutoff)     │
        │                                   │
        ▼                                   │
   Leakage-Safe Feature Engineering        │
   (server-side, from raw fields)           │
        │                                   │
        ▼                                   │
   ML Model (Random Forest)                │
        │                                   │
        ├──▶ SHAP Explanation               │
        │                                   │
        ▼                                   │
   Risk Engine                             │
   (ML 70% + Rules 30%)                    │
        │                                   │
        ▼                                   │
   PostgreSQL ──────────────────────────────┘
   (risk.transaction_scores)
        │
        ├──▶ API Response
        │
        └──▶ Investigation Queue (Streamlit)
```

### Cloud Architecture

```text
                    GitHub Actions
                    ┌──────┴──────┐
                    │             │
               Docker Build   Terraform
                    │             │
                    ▼             ▼
                   ECR          AWS
                    │
              ┌─────┴─────┐
              │           │
         FastAPI     Streamlit
              │           │
              └─────┬─────┘
                    │
                    ▼
              RDS PostgreSQL

                 S3
            ┌──────┴──────┐
            │              │
       Model Artifacts   Dataset
```

---

## End-to-End Transaction Flow

```text
1. POST /score-transaction
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

2. Server generates features from PostgreSQL historical context
   (strictly: timestamp < transaction_timestamp — no future leakage)

3. ML model predicts fraud probability

4. SHAP explains which features contributed to the prediction

5. Risk engine combines ML + rules into risk score and action

6. Result persisted to PostgreSQL

7. Response:
   {
     "transaction_id": "TXN-001",
     "fraud_probability": 0.87,
     "risk_score": 84,
     "risk_level": "high",
     "recommended_action": "review",
     "risk_factors": [...],
     "model_version": "fraudlens-rf-v001",
     "scored_at": "2026-09-09T15:42:32Z"
   }
```

---

## Key Engineering Decisions

| Decision | Rationale |
| --- | --- |
| **Server-side feature generation** | Prevents training/inference mismatch; client cannot inject fabricated features |
| **Strict temporal cutoff (`< T`)** | Ensures no future data influences current transaction scoring |
| **Forbidden precomputed fields** | Dataset fields with leakage/broken signal are rejected at API validation |
| **ML + Rules hybrid** | ML provides pattern recognition; rules provide transparency and controllability |
| **Idempotent scoring** | Duplicate transaction_id returns existing result, no duplicate investigation records |
| **Persistence before response** | API returns 500 if database write fails — never returns fake success |
| **SHAP explanations** | TreeExplainer for RF/XGBoost; feature contributions, not causal claims |

---

## What This Project Demonstrates

### Data Engineering
- PostgreSQL data architecture with 5M-row dataset
- dbt analytics layer (staging → intermediate → marts)
- Ingestion pipeline with schema validation and checksums
- Data quality tests

### Machine Learning
- Random Forest / Logistic Regression / XGBoost
- Class imbalance handling (balanced weights, scale_pos_weight)
- Temporal train/test split (no future leakage)
- PR-AUC, precision, recall, F1, Precision@K evaluation

### Feature Engineering
- Leakage-safe behavioral features computed server-side from PostgreSQL
- Historical context: velocity, customer behavior, merchant/location risk
- Training/inference parity via shared `MODEL_FEATURES` contract

### Explainability
- SHAP TreeExplainer for tree-based models
- Feature contribution explanations in API response

### Risk Intelligence
- ML probability + deterministic rules → risk score (0–100)
- Risk levels: Low / Medium / High / Critical
- Actions: allow / monitor / review / urgent_review
- Investigation queue prioritized by risk score

### API / Backend
- FastAPI with strict Pydantic validation
- `extra="forbid"` rejects unknown fields
- Forbidden precomputed features rejected
- Idempotent scoring via PostgreSQL upsert
- Health/readiness endpoints

### Dashboard
- Streamlit with 5 pages (Executive, Risk, Investigation, Fraud, Model Performance)
- All data from PostgreSQL — no fabricated metrics

### Cloud / DevOps
- Docker multi-stage build (non-root containers)
- AWS ECS Fargate deployment
- RDS PostgreSQL, S3 for model artifacts
- Terraform infrastructure as code
- GitHub Actions CI/CD with OIDC

### Testing
- 139 Python tests (unit, integration, API, temporal leakage, idempotency)
- dbt data quality tests

---

## Technology Stack

| Layer | Technology |
| --- | --- |
| Data | PostgreSQL, dbt |
| ML | scikit-learn, XGBoost, SHAP |
| API | FastAPI, Pydantic |
| Dashboard | Streamlit |
| Infrastructure | Docker, AWS ECS Fargate, RDS, S3, ECR, ALB |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Testing | pytest |

---

## Testing

```bash
make test          # Run all 139 Python tests
make dbt-test      # Run dbt data quality tests
make lint          # Check code style
```

---

## Local Development

```bash
# Docker
cp .env.example .env
make docker-up

# Or manual
make install
make api           # Terminal 1
make dashboard     # Terminal 2
```

---

## Cloud Deployment

```bash
# Infrastructure
cd terraform && terraform apply

# Application (via GitHub Actions on push to main)
git push origin main
```

---

## Repository Structure

```text
fraudlens/
├── src/fraudlens/
│   ├── api/              FastAPI endpoints
│   ├── features/         Feature preparation (training/inference parity)
│   ├── models/           ML training, serving, SHAP
│   ├── risk/             Risk engine, rules, persistence, scoring
│   ├── ingestion/        PostgreSQL ingestion pipeline
│   └── dashboard/        Streamlit dashboard + data access layer
├── dbt/fraudlens/        dbt analytics models
├── tests/                139 Python tests
├── terraform/            AWS infrastructure as code
├── docs/                 Architecture, API, decisions, deployment
└── .github/workflows/    CI/CD pipelines
```

---

## Known Limitations

- **Synthetic dataset** — Fraud patterns are synthetic, not real financial data
- **Latency not comprehensively benchmarked** — Real-time scoring latency measured but not stress-tested at scale
- **No model monitoring** — Drift detection and automated retraining are not implemented
- **No authentication** — API is unauthenticated (portfolio project)
- **Single-region AWS deployment** — No multi-AZ or disaster recovery

---

## License

MIT
