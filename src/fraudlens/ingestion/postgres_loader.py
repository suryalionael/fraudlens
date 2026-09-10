"""PostgreSQL raw schema and bulk loader."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Optional

import psycopg2


# SQL for the raw transactions table.
RAW_TRANSACTIONS_DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.transactions (
    transaction_id              TEXT PRIMARY KEY,
    timestamp                   TIMESTAMP NOT NULL,
    sender_account              TEXT NOT NULL,
    receiver_account            TEXT NOT NULL,
    transaction_type            TEXT NOT NULL,
    merchant_category           TEXT NOT NULL,
    location                    TEXT NOT NULL,
    device_used                 TEXT NOT NULL,
    is_fraud                    BOOLEAN NOT NULL,
    fraud_type                  TEXT,
    time_since_last_transaction NUMERIC,
    spending_deviation_score    NUMERIC,
    velocity_score              INTEGER,
    geo_anomaly_score           NUMERIC,
    payment_channel             TEXT NOT NULL,
    ip_address                  TEXT NOT NULL,
    device_hash                 TEXT NOT NULL,
    amount_ngn                  NUMERIC NOT NULL,
    bvn_linked                  BOOLEAN NOT NULL,
    new_device_transaction      BOOLEAN NOT NULL,
    sender_persona              TEXT NOT NULL
);
"""

# SQL for the ingestion runs metadata table.
INGESTION_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS raw.ingestion_runs (
    ingestion_run_id    SERIAL PRIMARY KEY,
    source_name         TEXT NOT NULL,
    source_version      TEXT,
    source_file         TEXT NOT NULL,
    source_sha256       TEXT,
    started_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMP,
    rows_read           BIGINT,
    rows_loaded         BIGINT,
    fraud_count         BIGINT,
    fraud_rate          NUMERIC,
    status              TEXT NOT NULL DEFAULT 'running',
    notes               TEXT
);
"""

COLLECTION_DELIMITER = "\t"
NULL_STRING = "\\N"


@dataclass
class DBConfig:
    """Database connection configuration."""

    host: str = "localhost"
    port: int = 5432
    dbname: str = "fraudlens"
    user: str = ""
    password: str = ""

    @classmethod
    def from_env(cls) -> "DBConfig":
        url = os.environ.get("DATABASE_URL", "")
        if url:
            # Parse a simple postgresql:// URL
            # Format: postgresql://user:pass@host:port/dbname
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return cls(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                dbname=(parsed.path or "/fraudlens").lstrip("/"),
                user=parsed.username or "",
                password=parsed.password or "",
            )
        return cls(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", "5432")),
            dbname=os.environ.get("POSTGRES_DB", "fraudlens"),
            user=os.environ.get("POSTGRES_USER", ""),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
        )


class PostgresLoader:
    """Manages PostgreSQL raw schema and bulk data loading."""

    def __init__(self, config: Optional[DBConfig] = None) -> None:
        self.config = config or DBConfig.from_env()
        self._conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> psycopg2.extensions.connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                dbname=self.config.dbname,
                user=self.config.user,
                password=self.config.password,
            )
        return self._conn

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def create_schema_and_tables(self) -> None:
        """Create the raw schema and tables if they do not exist."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(RAW_TRANSACTIONS_DDL)
            cur.execute(INGESTION_RUNS_DDL)
        conn.commit()

    def truncate_transactions(self) -> None:
        """Truncate the raw.transactions table (for idempotent re-ingestion)."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("TRUNCATE raw.transactions RESTART IDENTITY CASCADE")
        conn.commit()

    def insert_ingestion_run(
        self,
        source_name: str,
        source_version: str,
        source_file: str,
        source_sha256: str,
    ) -> int:
        """Create an ingestion run record and return its ID."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw.ingestion_runs
                    (source_name, source_version, source_file, source_sha256)
                VALUES (%s, %s, %s, %s)
                RETURNING ingestion_run_id
                """,
                (source_name, source_version, source_file, source_sha256),
            )
            run_id = cur.fetchone()[0]
        conn.commit()
        return run_id

    def update_ingestion_run(
        self,
        run_id: int,
        *,
        rows_read: Optional[int] = None,
        rows_loaded: Optional[int] = None,
        fraud_count: Optional[int] = None,
        fraud_rate: Optional[float] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Update an ingestion run record."""
        conn = self.connect()
        sets: list[str] = []
        params: list = []
        if rows_read is not None:
            sets.append("rows_read = %s")
            params.append(rows_read)
        if rows_loaded is not None:
            sets.append("rows_loaded = %s")
            params.append(rows_loaded)
        if fraud_count is not None:
            sets.append("fraud_count = %s")
            params.append(fraud_count)
        if fraud_rate is not None:
            sets.append("fraud_rate = %s")
            params.append(fraud_rate)
        if status is not None:
            sets.append("status = %s")
            params.append(status)
        if notes is not None:
            sets.append("notes = %s")
            params.append(notes)
        if not sets:
            return
        sets.append("completed_at = NOW()")
        params.append(run_id)
        query = f"UPDATE raw.ingestion_runs SET {', '.join(sets)} WHERE ingestion_run_id = %s"
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()

    def bulk_insert(self, header: list[str], rows: list[list[str]]) -> int:
        """Insert a chunk of rows using PostgreSQL COPY for efficiency.

        Returns the number of rows inserted.
        """
        if not rows:
            return 0

        conn = self.connect()
        col_names = ", ".join(header)

        # Build a COPY-compatible text stream
        buf = io.StringIO()
        for row in rows:
            # Convert booleans from CSV string to PostgreSQL format
            cells = []
            for val in row:
                if val in ("True", "true"):
                    cells.append("t")
                elif val in ("False", "false"):
                    cells.append("f")
                elif val == "":
                    cells.append(NULL_STRING)
                else:
                    cells.append(val.replace("\t", " ").replace("\n", " "))
            buf.write(COLLECTION_DELIMITER.join(cells))
            buf.write("\n")
        buf.seek(0)

        with conn.cursor() as cur:
            cur.copy_expert(
                f"COPY raw.transactions ({col_names}) FROM STDIN WITH (FORMAT TEXT, DELIMITER E'\\t', NULL '{NULL_STRING}')",
                buf,
            )
        conn.commit()
        return len(rows)

    def count_transactions(self) -> int:
        """Return the current row count in raw.transactions."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM raw.transactions")
            return cur.fetchone()[0]

    def get_ingestion_runs(self) -> list[dict]:
        """Return all ingestion run records."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM raw.ingestion_runs ORDER BY ingestion_run_id DESC"
            )
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
