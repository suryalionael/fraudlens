"""Executive Overview queries — real data from PostgreSQL/dbt marts."""

from __future__ import annotations

import pandas as pd

from fraudlens.dashboard.data.connection import query_df, query_scalar


def get_kpi_summary() -> dict:
    """Get executive KPI summary from raw transactions."""
    total = query_scalar("SELECT COUNT(*) FROM raw.transactions")
    fraud_count = query_scalar(
        "SELECT COUNT(*) FROM raw.transactions WHERE is_fraud = true"
    )
    total_value = query_scalar("SELECT ROUND(SUM(amount_ngn), 2) FROM raw.transactions")
    fraud_value = query_scalar(
        "SELECT ROUND(SUM(amount_ngn), 2) FROM raw.transactions WHERE is_fraud = true"
    )
    avg_amount = query_scalar("SELECT ROUND(AVG(amount_ngn), 2) FROM raw.transactions")

    fraud_rate = (fraud_count / total * 100) if total and total > 0 else 0

    return {
        "total_transactions": total or 0,
        "fraud_count": fraud_count or 0,
        "fraud_rate": round(fraud_rate, 4),
        "total_value": float(total_value or 0),
        "fraud_value": float(fraud_value or 0),
        "avg_amount": float(avg_amount or 0),
    }


def get_fraud_trend() -> pd.DataFrame:
    """Get daily fraud volume and rate over time."""
    return query_df("""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as total_transactions,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 4) as fraud_rate,
            ROUND(SUM(amount_ngn), 2) as total_amount,
            ROUND(SUM(CASE WHEN is_fraud THEN amount_ngn ELSE 0 END), 2) as fraud_amount
        FROM raw.transactions
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)


def get_fraud_by_dimension(dimension: str) -> pd.DataFrame:
    """Get fraud rate by a specified dimension.

    Args:
        dimension: Column name (merchant_category, location, transaction_type, payment_channel).
    """
    allowed = {
        "merchant_category",
        "location",
        "transaction_type",
        "payment_channel",
        "device_used",
    }
    if dimension not in allowed:
        raise ValueError(f"Dimension must be one of {allowed}")

    return query_df(f"""
        SELECT
            {dimension} as category,
            COUNT(*) as total_transactions,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_rate,
            ROUND(SUM(amount_ngn), 2) as total_amount
        FROM raw.transactions
        GROUP BY {dimension}
        ORDER BY fraud_rate DESC
    """)
