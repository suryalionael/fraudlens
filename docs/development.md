# Development Guide

## 1. Prerequisites

* Python 3.12+
* PostgreSQL 16+
* Git
* Docker (optional, for containerized development)

---

## 2. Quick Start

### Option A: Docker (recommended)

```bash
# Clone and configure
cp .env.example .env

# Start all services
make docker-up

# API available at http://localhost:8000
# Dashboard available at http://localhost:8501
```

### Option B: Local development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
make install

# Configure database
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run tests
make test

# Run API
make api

# Run dashboard (separate terminal)
make dashboard
```

---

## 3. Configuration

All configuration uses environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | — | PostgreSQL connection URL |
| `POSTGRES_HOST` | localhost | Database host |
| `POSTGRES_PORT` | 5432 | Database port |
| `POSTGRES_DB` | fraudlens | Database name |
| `POSTGRES_USER` | — | Database user |
| `POSTGRES_PASSWORD` | — | Database password |
| `FRAUDLENS_MODEL_PATH` | models/random_forest.artifact.pkl | Model artifact path |
| `FRAUDLENS_MODEL_DIR` | models/ | Model metadata directory |
| `FRAUDLENS_LOG_LEVEL` | INFO | Logging level |

Never commit `.env` files. Use `.env.example` as a template.

---

## 4. Project Workflow

```text
1. Ingest data       → python -m fraudlens.ingestion --input <csv>
2. Run dbt           → cd dbt/fraudlens && dbt build
3. Train model       → python -c "from fraudlens.models.serving import ..."
4. Score transactions → python -c "from fraudlens.risk.batch import ..."
5. Run API           → make api
6. Run dashboard     → make dashboard
```

---

## 5. Makefile Commands

```bash
make help           # Show all commands
make install        # Install dependencies
make test           # Run Python tests
make test-fast      # Run tests (quiet)
make lint           # Check code style
make format         # Auto-format code
make typecheck      # Run type checks
make dbt-build      # Build dbt models
make dbt-test       # Run dbt tests
make api            # Start API server
make dashboard      # Start Streamlit dashboard
make docker-up      # Start Docker services
make docker-down    # Stop Docker services
```

---

## 6. Code Style

* Readability over cleverness
* Explicit typing where useful
* Small, focused functions
* Meaningful names
* No unnecessary abstraction

---

## 7. Git Workflow

Before committing:

```text
tests pass
code is formatted
no secrets present
documentation updated
```

Use focused commit messages:

```text
feat: add feature
fix: resolve bug
test: add coverage
docs: update documentation
chore: maintenance
```
