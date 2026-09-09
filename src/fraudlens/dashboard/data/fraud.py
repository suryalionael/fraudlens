"""Fraud Analysis queries — real data from raw.transactions."""

from __future__ import annotations

import pandas as pd

from fraudlens.dashboard.data.connection import query_df, query_scalar


def get_fraud_by_merchant() -> pd.DataFrame:
    """Get fraud analysis by merchant category."""
    return query_df("""
        SELECT
            merchant_category,
            COUNT(*) as total_transactions,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_rate,
            ROUND(SUM(amount_ngn), 2) as total_amount,
            ROUND(SUM(CASE WHEN is_fraud THEN amount_ngn ELSE 0 END), 2) as fraud_amount
        FROM raw.transactions
        GROUP BY merchant_category
        ORDER BY fraud_rate DESC
    """)


def get_fraud_by_location() -> pd.DataFrame:
    """Get fraud analysis by location."""
    return query_df("""
        SELECT
            location,
            COUNT(*) as total_transactions,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_rate,
            ROUND(SUM(amount_ngn), 2) as total_amount
        FROM raw.transactions
        GROUP BY location
        ORDER BY fraud_rate DESC
    """)


def get_fraud_by_transaction_type() -> pd.DataFrame:
    """Get fraud analysis by transaction type."""
    return query_df("""
        SELECT
            transaction_type,
            COUNT(*) as total_transactions,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_rate,
            ROUND(SUM(amount_ngn), 2) as total_amount
        FROM raw.transactions
        GROUP BY transaction_type
        ORDER BY fraud_rate DESC
    """)


def get_fraud_by_payment_channel() -> pd.DataFrame:
    """Get fraud analysis by payment channel."""
    return query_df("""
        SELECT
            payment_channel,
            COUNT(*) as total_transactions,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_rate,
            ROUND(SUM(amount_ngn), 2) as total_amount
        FROM raw.transactions
        GROUP BY payment_channel
        ORDER BY fraud_rate DESC
    """)


def get_fraud_by_device() -> pd.DataFrame:
    """Get fraud analysis by device type."""
    return query_df("""
        SELECT
            device_used,
            COUNT(*) as total_transactions,
            SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_rate
        FROM raw.transactions
        GROUP BY device_used
        ORDER BY fraud_rate DESC
    """)


def get_fraud_volume_vs_rate() -> pd.DataFrame:
    """Get fraud rate vs transaction volume by merchant category.

    Used for the bubble chart visualization.
    """
    return query_df("""
        SELECT
            merchant_category,
            COUNT(*) as transaction_volume,
            ROUND(100.0 * SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) / COUNT(*), 2) as fraud_rate,
            ROUND(SUM(amount_ngn), 2) as total_value
        FROM raw.transactions
        GROUP BY merchant_category
    """)
