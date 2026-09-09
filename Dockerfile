FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY dbt/ dbt/
COPY tests/ tests/
COPY conftest.py .
COPY docs/ docs/
COPY .env.example .

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# ── API service ──
FROM base AS api
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "fraudlens.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Dashboard service ──
FROM base AS dashboard
EXPOSE 8501
CMD ["streamlit", "run", "src/fraudlens/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
