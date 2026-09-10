"""Risk Monitoring queries — real data from risk.transaction_scores."""

from __future__ import annotations

import pandas as pd

from fraudlens.dashboard.data.connection import query_df, query_scalar


def get_risk_kpi_summary() -> dict:
    """Get risk monitoring KPI summary."""
    total_scored = query_scalar("SELECT COUNT(*) FROM risk.transaction_scores")
    high_risk = query_scalar(
        "SELECT COUNT(*) FROM risk.transaction_scores WHERE risk_level IN ('high', 'critical')"
    )
    critical_risk = query_scalar(
        "SELECT COUNT(*) FROM risk.transaction_scores WHERE risk_level = 'critical'"
    )
    avg_score = query_scalar(
        "SELECT ROUND(AVG(risk_score), 2) FROM risk.transaction_scores"
    )
    review_count = query_scalar(
        "SELECT COUNT(*) FROM risk.transaction_scores WHERE recommended_action IN ('review', 'urgent_review')"
    )

    high_risk_pct = (
        (high_risk / total_scored * 100) if total_scored and total_scored > 0 else 0
    )

    return {
        "total_scored": total_scored or 0,
        "high_risk": high_risk or 0,
        "critical_risk": critical_risk or 0,
        "high_risk_pct": round(high_risk_pct, 2),
        "avg_risk_score": float(avg_score or 0),
        "review_count": review_count or 0,
    }


def get_risk_distribution() -> pd.DataFrame:
    """Get risk level distribution with counts and values."""
    return query_df("""
        SELECT
            risk_level,
            COUNT(*) as count,
            ROUND(SUM(amount_ngn), 2) as total_amount,
            ROUND(AVG(risk_score), 2) as avg_score,
            ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM risk.transaction_scores), 2) as percentage
        FROM risk.transaction_scores
        GROUP BY risk_level
        ORDER BY
            CASE risk_level
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END
    """)


def get_risk_trend() -> pd.DataFrame:
    """Get risk score trend over time."""
    return query_df("""
        SELECT
            DATE(scored_at) as date,
            COUNT(*) as total_scored,
            ROUND(AVG(risk_score), 2) as avg_risk_score,
            SUM(CASE WHEN risk_level IN ('high', 'critical') THEN 1 ELSE 0 END) as high_risk_count,
            ROUND(100.0 * SUM(CASE WHEN risk_level IN ('high', 'critical') THEN 1 ELSE 0 END) / COUNT(*), 2) as high_risk_pct
        FROM risk.transaction_scores
        GROUP BY DATE(scored_at)
        ORDER BY date
    """)


def get_risk_by_dimension(dimension: str) -> pd.DataFrame:
    """Get average risk score by a specified dimension."""
    allowed = {"merchant_category", "location", "transaction_type", "payment_channel"}
    if dimension not in allowed:
        raise ValueError(f"Dimension must be one of {allowed}")

    return query_df(f"""
        SELECT
            {dimension} as category,
            COUNT(*) as count,
            ROUND(AVG(risk_score), 2) as avg_risk_score,
            SUM(CASE WHEN risk_level IN ('high', 'critical') THEN 1 ELSE 0 END) as high_risk_count
        FROM risk.transaction_scores
        GROUP BY {dimension}
        ORDER BY avg_risk_score DESC
    """)
