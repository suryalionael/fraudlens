# Data Pipeline

## 1. Objective

The FraudLens data pipeline converts the selected source dataset into validated, analytics-ready transaction data.

The pipeline must be reproducible and deterministic where possible.

---

## 2. Pipeline

```text
Source Dataset (CSV)
       ↓
Schema Validation
       ↓
Chunked CSV Reading
       ↓
PostgreSQL COPY (bulk load)
       ↓
raw.transactions
       ↓
Ingestion Metadata
       ↓
[Phase 2: dbt Transformation]
```

---

## 3. Phase 1 — Raw Ingestion (Implemented)

### Source

* **Dataset:** Nigerian Financial Transactions and Fraud Detection Dataset V1
* **File:** `V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv`
* **Size:** ~924 MB, 5,000,000 rows, 21 columns
* **SHA256:** `ed7753fbd7da6d775ce1cd0a339c15abdcc304dae6f668643d15f7e9427cbe09`

### Architecture

```text
src/fraudlens/ingestion/
├── __init__.py          # Package exports
├── __main__.py          # python -m fraudlens.ingestion
├── cli.py               # Command-line interface
├── schema.py            # Source schema definition + validation
├── csv_reader.py        # Chunked CSV reader with SHA-256
├── postgres_loader.py   # PostgreSQL DDL + bulk COPY loader
└── pipeline.py          # Orchestration: validate → load → verify
```

### How to Run

```bash
# Set DATABASE_URL or individual env vars
export DATABASE_URL=postgresql://localhost:5432/fraudlens

# Run full ingestion
PYTHONPATH=src python -m fraudlens.ingestion \
  --input data/raw/V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv

# Dry run (validate only)
PYTHONPATH=src python -m fraudlens.ingestion \
  --input data/raw/V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv \
  --dry-run
```

### Idempotency

Running the pipeline twice with `--replace` (default) truncates `raw.transactions` and reloads.

Running with `--no-replace` refuses to load if the table already has data.

### Performance

Full 5M-row ingestion completes in approximately 75 seconds using PostgreSQL COPY.

Chunk size: 50,000 rows (configurable via `--chunk-size`).

### Verification

After ingestion, the pipeline verifies:

* row count matches source
* ingestion run metadata is recorded
* SHA-256 checksum is stored

---

## 4. Raw Data

Raw source data in `data/raw/` is immutable.

The raw CSV is NOT committed to Git (924 MB).

Required metadata:

```text
source_name
source_url
dataset_version
download_date
license
checksum
```

Stored in `data/dataset_metadata.yml`.

---

## 5. Validation

Schema validation checks:

* required columns present (21 expected)
* no duplicate column names
* file exists and is readable

Data quality checks (post-ingestion):

* row count = 5,000,000
* fraud count = 179,553
* fraud rate ≈ 3.5911%
* 0 exact duplicate rows
* 0 timestamp parse failures

---

## 6. Database Schema

### raw.transactions

The raw table preserves all 21 source columns faithfully.

```text
transaction_id              TEXT PRIMARY KEY
timestamp                   TIMESTAMP NOT NULL
sender_account              TEXT NOT NULL
receiver_account            TEXT NOT NULL
transaction_type            TEXT NOT NULL
merchant_category           TEXT NOT NULL
location                    TEXT NOT NULL
device_used                 TEXT NOT NULL
is_fraud                    BOOLEAN NOT NULL
fraud_type                  TEXT
time_since_last_transaction NUMERIC
spending_deviation_score    NUMERIC
velocity_score              INTEGER
geo_anomaly_score           NUMERIC
payment_channel             TEXT NOT NULL
ip_address                  TEXT NOT NULL
device_hash                 TEXT NOT NULL
amount_ngn                  NUMERIC NOT NULL
bvn_linked                  BOOLEAN NOT NULL
new_device_transaction      BOOLEAN NOT NULL
sender_persona              TEXT NOT NULL
```

### raw.ingestion_runs

Tracks every ingestion execution for reproducibility.

```text
ingestion_run_id    SERIAL PRIMARY KEY
source_name         TEXT NOT NULL
source_version      TEXT
source_file         TEXT NOT NULL
source_sha256       TEXT
started_at          TIMESTAMP
completed_at        TIMESTAMP
rows_read           BIGINT
rows_loaded         BIGINT
fraud_count         BIGINT
fraud_rate          NUMERIC
status              TEXT
notes               TEXT
```

---

## 7. dbt Transformation (Phase 2 — Not Started)

Future dbt models will create:

```text
stg_transactions
stg_customers
stg_merchants
stg_devices
```

Intermediate models may calculate:

```text
customer_transaction_history
merchant_behavior
device_behavior
transaction_context
```

Marts should support:

```text
fraud monitoring
risk modeling
investigation
BI
```

---

## 8. Data Quality

Data quality tests should cover:

* primary key uniqueness;
* non-null keys;
* referential integrity;
* valid fraud labels;
* valid amounts;
* valid timestamps;
* accepted categorical values.

---

## 9. Observability

The ingestion run metadata table tracks:

```text
rows_received
rows_loaded
fraud_count
fraud_rate
pipeline_duration
status
```

---

## 10. Reproducibility

A new developer can reproduce the pipeline with:

1. Download the dataset (see `data/README.md`)
2. Configure PostgreSQL (see `.env.example`)
3. Run `PYTHONPATH=src python -m fraudlens.ingestion --input <path>`

The SHA-256 checksum ensures the exact same source file is used.

---

## 11. Known Limitations

* Pre-computed features (`new_device_transaction`, `time_since_last_transaction`, etc.) are ingested but NOT trusted — see `data/dataset_metadata.yml` for the leakage audit
* All behavioral features must be computed from raw fields in later phases
* The dataset is synthetic — fraud rates are suspiciously uniform across dimensions
