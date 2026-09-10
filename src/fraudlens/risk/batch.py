"""Batch scoring utility for FraudLens.

Scores existing transactions from raw.transactions through the full pipeline
(prep features → ML model → risk engine → persist) and stores results in
risk.transaction_scores.

Performance: uses vectorized pre-computation to avoid O(n²) per-row scanning.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import psycopg2

from fraudlens.ingestion.postgres_loader import DBConfig
from fraudlens.logging_config import configure_logging
from fraudlens.models.explainer import explain_prediction, format_explanation_for_api
from fraudlens.models.serving import (
    load_model_artifact,
)
from fraudlens.risk.engine import RiskEngine
from fraudlens.risk.storage import RiskScoreStore

logger = logging.getLogger(__name__)


def _load_raw_transactions(
    config: DBConfig,
    limit: int | None = None,
) -> pd.DataFrame:
    """Load raw transactions from PostgreSQL."""
    conn = psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
    )
    query = "SELECT * FROM raw.transactions ORDER BY timestamp"
    if limit:
        query += f" LIMIT {limit}"
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def _precompute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute all behavioral features using vectorized operations.

    Instead of scanning the full DataFrame per row (O(n²)), this uses
    groupby + cumulative operations to compute features in O(n log n).
    """
    df = df.sort_values("timestamp").reset_index(drop=True)

    # ── Sender-level cumulative features ──
    # Number of prior transactions by this sender (before current row)
    df["_sender_cumcount"] = df.groupby("sender_account").cumcount()

    # Running mean/std/max of amount by sender (using expanding window)
    # We need cumulative stats EXCLUDING current row
    sender_groups = df.groupby("sender_account")["amount_ngn"]

    # Use shift(1) to exclude current row from cumulative stats
    shifted_amount = sender_groups.shift(1)
    df["_sender_cum_sum"] = shifted_amount.groupby(df["sender_account"]).cumsum()
    df["_sender_cum_count"] = shifted_amount.groupby(df["sender_account"]).count()
    df["_sender_cum_max"] = shifted_amount.groupby(df["sender_account"]).cummax()

    # Customer features
    df["customer_transaction_count_prior"] = (
        df["_sender_cum_count"].fillna(0).astype(int)
    )
    df["customer_avg_amount_prior"] = (
        df["_sender_cum_sum"] / df["_sender_cum_count"].replace(0, np.nan)
    ).fillna(0.0)
    df["customer_max_amount_prior"] = df["_sender_cum_max"].fillna(0.0)

    # Std requires expanding window — compute via cumulative sum of squares
    amount_sq = (shifted_amount**2).fillna(0)
    cum_sq = amount_sq.groupby(df["sender_account"]).cumsum()
    n = df["_sender_cum_count"].replace(0, np.nan)
    mean = df["_sender_cum_sum"] / n
    df["customer_std_amount_prior"] = np.sqrt((cum_sq / n) - (mean**2)).fillna(0.0)

    # Amount ratio
    df["amount_ratio_to_avg"] = np.where(
        df["customer_avg_amount_prior"] > 0,
        df["amount_ngn"] / df["customer_avg_amount_prior"],
        1.0,
    )

    # Amount z-score
    std = df["customer_std_amount_prior"].replace(0, np.nan)
    df["amount_zscore"] = (
        (df["amount_ngn"] - df["customer_avg_amount_prior"]) / std
    ).fillna(0.0)

    # ── Merchant-level cumulative features ──
    merchant_groups = df.groupby("merchant_category")
    shifted_merchant = merchant_groups["is_fraud"].shift(1)
    df["merchant_transaction_count_prior"] = (
        shifted_merchant.groupby(df["merchant_category"]).count().fillna(0).astype(int)
    )
    merchant_fraud_cumsum = (
        shifted_merchant.fillna(0).groupby(df["merchant_category"]).cumsum()
    )
    merchant_count = df["merchant_transaction_count_prior"].replace(0, np.nan)
    df["merchant_fraud_rate_prior"] = (merchant_fraud_cumsum / merchant_count).fillna(
        0.0
    )

    # ── Location-level cumulative features ──
    location_groups = df.groupby("location")
    shifted_location = location_groups["is_fraud"].shift(1)
    df["location_transaction_count_prior"] = (
        shifted_location.groupby(df["location"]).count().fillna(0).astype(int)
    )
    location_fraud_cumsum = shifted_location.fillna(0).groupby(df["location"]).cumsum()
    location_count = df["location_transaction_count_prior"].replace(0, np.nan)
    df["location_fraud_rate_prior"] = (location_fraud_cumsum / location_count).fillna(
        0.0
    )

    # ── Device-level cumulative features ──
    # Device transaction count prior
    device_groups = df.groupby("device_hash")
    shifted_device = device_groups.cumcount()
    df["device_transaction_count_prior"] = shifted_device

    # Device first seen: first occurrence per (sender, device) pair
    df["_sender_device_key"] = df["sender_account"] + "||" + df["device_hash"]
    df["device_first_seen"] = ~df.duplicated(
        subset=["_sender_device_key"], keep="first"
    )

    # ── Temporal features ──
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # ── Velocity features (not available from raw data) ──
    df["transactions_last_10m"] = 0
    df["transactions_last_60m"] = 0
    df["transactions_last_1440m"] = 0

    # ── Amount zscore from source (untrusted) ──
    df["amount_zscore_source"] = df.get(
        "spending_deviation_score", pd.Series(0, index=df.index)
    ).fillna(0)

    # Cleanup temporary columns
    temp_cols = [c for c in df.columns if c.startswith("_")]
    df = df.drop(columns=temp_cols, errors="ignore")

    return df


def _row_to_transaction(row: pd.Series) -> dict[str, Any]:
    """Convert a database row to a transaction dictionary for the risk engine."""
    return {
        "transaction_id": row["transaction_id"],
        "sender_account": row["sender_account"],
        "receiver_account": row["receiver_account"],
        "transaction_type": row["transaction_type"],
        "merchant_category": row["merchant_category"],
        "location": row["location"],
        "device_used": row["device_used"],
        "amount_ngn": float(row["amount_ngn"]),
        "payment_channel": row["payment_channel"],
        "ip_address": row.get("ip_address", ""),
        "device_hash": row.get("device_hash", ""),
        "sender_persona": row.get("sender_persona", ""),
        "is_fraud": bool(row["is_fraud"]) if row["is_fraud"] is not None else False,
        "timestamp": row["timestamp"].isoformat()
        if hasattr(row["timestamp"], "isoformat")
        else str(row["timestamp"]),
        "amount_zscore": float(row.get("amount_zscore", 0)),
        "amount_ratio_to_avg": float(row.get("amount_ratio_to_avg", 1.0)),
        "customer_transaction_count_prior": int(
            row.get("customer_transaction_count_prior", 0)
        ),
        "customer_avg_amount_prior": float(row.get("customer_avg_amount_prior", 0)),
        "device_first_seen": bool(row.get("device_first_seen", False)),
        "merchant_fraud_rate_prior": float(row.get("merchant_fraud_rate_prior", 0)),
        "location_fraud_rate_prior": float(row.get("location_fraud_rate_prior", 0)),
        "transactions_last_1h": int(row.get("transactions_last_60m", 0)),
        "customer_transactions_per_day": 0.0,
    }


def _features_for_model(row: pd.Series, feature_columns: list[str]) -> dict[str, float]:
    """Extract model features from pre-computed row."""
    features = {}
    for col in feature_columns:
        if col == "device_first_seen_int":
            features[col] = float(int(row.get("device_first_seen", False)))
        else:
            val = row.get(col, 0)
            if val is None:
                features[col] = 0.0
            else:
                try:
                    features[col] = float(val)
                except (TypeError, ValueError):
                    features[col] = 0.0
    return features


def batch_score_transactions(
    config: DBConfig | None = None,
    model_path: str | None = None,
    limit: int | None = None,
    batch_size: int = 1000,
) -> dict[str, Any]:
    """Score all raw transactions and persist results.

    Uses vectorized feature pre-computation (O(n log n)) instead of
    per-row DataFrame scanning (O(n²)).

    Args:
        config: Database configuration. If None, uses env vars.
        model_path: Path to model artifact. If None, uses default.
        limit: Maximum transactions to score. None = all.
        batch_size: How many scores to persist at once.

    Returns:
        Summary dictionary with counts and timing.
    """
    config = config or DBConfig.from_env()

    # Configure logging
    configure_logging()

    # Load model
    from fraudlens.api.app import DEFAULT_MODEL_PATH

    resolved_path = model_path or DEFAULT_MODEL_PATH
    artifact = load_model_artifact(resolved_path)
    logger.info("Loaded model: %s", artifact.model_version)

    # Initialize risk engine and storage
    risk_engine = RiskEngine()
    store = RiskScoreStore(config)
    store.create_schema()

    # Load raw transactions
    logger.info("Loading raw transactions (limit=%s)...", limit)
    df = _load_raw_transactions(config, limit=limit)
    logger.info("Loaded %d transactions", len(df))

    # Pre-compute ALL features vectorized (O(n log n))
    logger.info("Pre-computing features...")
    precompute_start = datetime.now(tz=timezone.utc)
    df = _precompute_features(df)
    precompute_elapsed = (
        datetime.now(tz=timezone.utc) - precompute_start
    ).total_seconds()
    logger.info("Feature pre-computation took %.1fs", precompute_elapsed)

    # Score in batches
    total_scored = 0
    start_time = datetime.now(tz=timezone.utc)
    feature_columns = artifact.feature_columns

    for batch_start in range(0, len(df), batch_size):
        batch_end = min(batch_start + batch_size, len(df))
        batch_df = df.iloc[batch_start:batch_end]

        # Vectorized model prediction for the batch
        batch_model_features = []
        for _, row in batch_df.iterrows():
            mf = _features_for_model(row, feature_columns)
            batch_model_features.append(mf)

        # Build feature matrix for batch prediction
        X_batch = pd.DataFrame(batch_model_features, columns=feature_columns)
        if artifact.scaler is not None:
            X_batch = pd.DataFrame(
                artifact.scaler.transform(X_batch),
                columns=feature_columns,
            )
        probs = artifact.model.predict_proba(X_batch)[:, 1]

        # Process each row for risk assessment and persistence
        scores = []
        for i, (_, row) in enumerate(batch_df.iterrows()):
            try:
                fraud_prob = float(probs[i])
                transaction = _row_to_transaction(row)
                risk_result = risk_engine.assess_transaction(transaction, fraud_prob)

                # SHAP explanation (per-row, but only top_k=3 for batch efficiency)
                X_single = pd.DataFrame(
                    [batch_model_features[i]], columns=feature_columns
                )
                explanations = explain_prediction(
                    artifact.model, feature_columns, X_single, top_k=3
                )
                shap_factors = format_explanation_for_api(explanations)

                score = {
                    "transaction_id": row["transaction_id"],
                    "timestamp": row["timestamp"],
                    "sender_account": row["sender_account"],
                    "receiver_account": row["receiver_account"],
                    "transaction_type": row["transaction_type"],
                    "merchant_category": row["merchant_category"],
                    "location": row["location"],
                    "device_used": row["device_used"],
                    "payment_channel": row["payment_channel"],
                    "amount_ngn": float(row["amount_ngn"]),
                    "is_fraud": bool(row["is_fraud"])
                    if row["is_fraud"] is not None
                    else False,
                    "fraud_probability": round(fraud_prob, 4),
                    "risk_score": risk_result.risk_score,
                    "risk_level": risk_result.risk_level,
                    "recommended_action": risk_result.recommended_action,
                    "rule_score": risk_result.rule_score,
                    "ml_score": risk_result.ml_score,
                    "risk_factors": risk_result.risk_factors + shap_factors,
                    "rule_signals": risk_result.rule_signals,
                    "model_version": artifact.model_version,
                    "risk_engine_version": "001",
                    "scored_at": datetime.now(tz=timezone.utc),
                }
                scores.append(score)

            except (ValueError, TypeError, KeyError) as e:
                logger.warning(
                    "Failed to score %s: %s", row.get("transaction_id", "?"), e
                )
                continue

        # Persist batch
        if scores:
            store.upsert_batch(scores)
            total_scored += len(scores)

        if total_scored % 10000 == 0:
            logger.info("Scored %d / %d transactions...", total_scored, len(df))

    elapsed = (datetime.now(tz=timezone.utc) - start_time).total_seconds()
    store.close()

    result = {
        "total_transactions": len(df),
        "total_scored": total_scored,
        "elapsed_seconds": round(elapsed, 1),
        "precompute_seconds": round(precompute_elapsed, 1),
        "scoring_seconds": round(elapsed - precompute_elapsed, 1),
        "model_version": artifact.model_version,
        "scores_per_second": round(total_scored / elapsed, 1) if elapsed > 0 else 0,
    }

    logger.info("Batch scoring complete: %s", result)
    return result
