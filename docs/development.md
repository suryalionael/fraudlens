# Development Guide

## 1. Prerequisites

The project is expected to use:

* Python
* PostgreSQL
* Git
* dbt

Additional tooling will be introduced as required.

---

## 2. Environment

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it according to the operating system.

Install project dependencies using the project's configured package manager.

---

## 3. Configuration

Use environment variables for configuration.

Example:

```text
DATABASE_URL=
MODEL_PATH=
ENVIRONMENT=
```

Never commit secrets.

Provide:

```text
.env.example
```

with placeholder values.

---

## 4. Local Database

The development environment should provide a local PostgreSQL database.

Database configuration must be documented separately from application logic.

---

## 5. Running the Project

### Data Ingestion (Phase 1 — Implemented)

```bash
# Download the dataset (see data/README.md for details)
# Place CSV in data/raw/

# Set database connection
export DATABASE_URL=postgresql://localhost:5432/fraudlens

# Run full ingestion
PYTHONPATH=src python -m fraudlens.ingestion \
  --input data/raw/V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv

# Dry run (validate schema only)
PYTHONPATH=src python -m fraudlens.ingestion \
  --input data/raw/V1-nigerian-financial-transactions-and-fraud-detection-dataset.csv \
  --dry-run
```

### Tests

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

### Expected Workflow

```text
ingest data          ← Phase 1 (implemented)
run validation       ← Phase 1 (implemented)
run dbt              ← Phase 2 (not started)
generate features    ← Phase 3 (not started)
train model          ← Phase 4 (not started)
run risk scoring     ← Phase 5 (not started)
run API              ← Phase 6 (not started)
```

---

## 6. Code Style

Python code should prioritize:

* readability;
* explicit typing where useful;
* small functions;
* meaningful names;
* modularity;
* testability.

Avoid unnecessary abstraction.

---

## 7. Notebooks

Notebooks should be used for exploration and analysis.

Reusable logic should eventually move into:

```text
src/fraudlens/
```

---

## 8. Git Workflow

Use small, focused commits.

Before committing:

```text
tests pass
code is formatted
no secrets are present
documentation is updated where needed
```

---

## 9. Local Development Principle

The local development environment should reproduce the project's documented workflow as closely as practical.

Avoid undocumented manual steps.
