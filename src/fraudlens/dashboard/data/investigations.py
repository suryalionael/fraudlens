"""Investigation Queue queries — real data from risk.transaction_scores."""

from __future__ import annotations

import json

import pandas as pd

from fraudlens.dashboard.data.connection import query_df, query_scalar


def get_investigation_queue(
    risk_level: str | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Get prioritized investigation queue from scored transactions.

    Args:
        risk_level: Filter by risk level (None = all).
        limit: Maximum rows to return.
    """
    where_clauses = []
    params: list = []

    if risk_level:
        where_clauses.append("risk_level = %s")
        params.append(risk_level)

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    return query_df(f"""
        SELECT
            transaction_id,
            timestamp,
            sender_account,
            merchant_category,
            location,
            payment_channel,
            amount_ngn,
            fraud_probability,
            risk_score,
            risk_level,
            risk_factors,
            recommended_action,
            model_version,
            scored_at
        FROM risk.transaction_scores
        {where_sql}
        ORDER BY risk_score DESC, timestamp DESC
        LIMIT %s
    """, params=tuple(params + [limit]))


def get_investigation_stats() -> dict:
    """Get investigation queue statistics."""
    total = query_scalar("SELECT COUNT(*) FROM risk.transaction_scores")
    high_critical = query_scalar(
        "SELECT COUNT(*) FROM risk.transaction_scores WHERE risk_level IN ('high', 'critical')"
    )
    needs_review = query_scalar(
        "SELECT COUNT(*) FROM risk.transaction_scores WHERE recommended_action IN ('review', 'urgent_review')"
    )

    return {
        "total_scored": total or 0,
        "high_critical_count": high_critical or 0,
        "needs_review_count": needs_review or 0,
    }


def get_transaction_detail(transaction_id: str) -> dict | None:
    """Get detailed information for a single transaction."""
    df = query_df(
        "SELECT * FROM risk.transaction_scores WHERE transaction_id = %s",
        params=(transaction_id,),
    )
    if df.empty:
        return None

    row = df.iloc[0]
    result = row.to_dict()

    # Parse JSON fields
    for field in ["risk_factors", "rule_signals"]:
        if isinstance(result.get(field), str):
            try:
                result[field] = json.loads(result[field])
            except (json.JSONDecodeError, TypeError):
                pass

    return result
