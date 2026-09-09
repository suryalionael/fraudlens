"""Database connection for the FraudLens dashboard.

Provides a simple function to get a PostgreSQL connection using
the same configuration as the rest of the project.
"""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


def get_connection():
    """Get a PostgreSQL connection for dashboard queries.

    Returns:
        psycopg2 connection object.

    Raises:
        psycopg2.OperationalError: If connection fails.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url:
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        return psycopg2.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            dbname=(parsed.path or "/fraudlens").lstrip("/"),
            user=parsed.username or "",
            password=parsed.password or "",
        )

    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "fraudlens"),
        user=os.environ.get("POSTGRES_USER", ""),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )


def query_df(sql: str, params: tuple | None = None):
    """Execute a SQL query and return a pandas DataFrame.

    Args:
        sql: SQL query string.
        params: Optional query parameters.

    Returns:
        pandas DataFrame with query results.
    """
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    finally:
        conn.close()


def query_scalar(sql: str, params: tuple | None = None):
    """Execute a SQL query and return a single scalar value.

    Args:
        sql: SQL query returning a single value.
        params: Optional query parameters.

    Returns:
        The scalar value, or None if no results.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()
