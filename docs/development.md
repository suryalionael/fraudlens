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

The exact commands will be added as implementation progresses.

Expected workflows:

```text
ingest data
run validation
run dbt
generate features
train model
evaluate model
run risk scoring
run API
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
