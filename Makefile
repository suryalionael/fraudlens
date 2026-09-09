.PHONY: install test lint format typecheck dbt-parse dbt-test dbt-build \
       api dashboard docker-build docker-up docker-down docker-logs \
       clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──

install: ## Install dependencies
	pip install -r requirements.txt

# ── Testing ──

test: ## Run Python tests
	PYTHONPATH=src python -m pytest tests/ -v --tb=short

test-fast: ## Run Python tests (no verbose)
	PYTHONPATH=src python -m pytest tests/ --tb=no -q

# ── Linting ──

lint: ## Run linter (ruff)
	python -m ruff check src/ tests/ --no-fix

format: ## Format code (ruff)
	python -m ruff format src/ tests/
	python -m ruff check src/ tests/ --fix

typecheck: ## Run type checker (mypy)
	python -m mypy src/fraudlens/ --ignore-missing-imports

# ── dbt ──

dbt-parse: ## Parse dbt project
	cd dbt/fraudlens && dbt parse

dbt-test: ## Run dbt tests
	cd dbt/fraudlens && dbt test

dbt-build: ## Build dbt models
	cd dbt/fraudlens && dbt build

# ── Application ──

api: ## Run API server
	PYTHONPATH=src python -m uvicorn fraudlens.api.app:app --reload --host 127.0.0.1 --port 8000

dashboard: ## Run Streamlit dashboard
	PYTHONPATH=src streamlit run src/fraudlens/dashboard/app.py

# ── Docker ──

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all services
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## View service logs
	docker compose logs -f

# ── Cleanup ──

clean: ## Clean build artifacts
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf *.egg-info dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
