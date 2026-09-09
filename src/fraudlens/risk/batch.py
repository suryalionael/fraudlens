"""Batch scoring utility for FraudLens.

Scores existing transactions from raw.transactions through the full pipeline
(prep features → ML model → risk engine → persist) and stores results in
risk.transaction_scores.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd
import psycopg2

from fraudlens.features.preparation import (
    MODEL_FEATURES,
    prepare_features_from_transaction,
)
from fraudlens.ingestion.postgres_loader import DBConfig
from fraudlens.models.explainer import explain_prediction, format_explanation_for_api
from fraudlens.models.serving import ModelArtifact, load_model_artifact, predict_probability
from fraudlens.risk.engine import RiskEngine
from fraudlens.risk.storage import RiskScoreStore

logger = logging.getLogger(__name__)


def _load_raw_transactions(
    config: DBConfig,
    limit: int | None = None,
) -> pd.DataFrame:
    """Load raw transactions from PostgreSQL.

    Args:
        config: Database configuration.
        limit: Maximum rows to load. None = all.

    Returns:
        DataFrame with raw transaction data.
    """
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
        "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
    }


def _compute_simple_features(
    row: pd.Series,
    all_rows: pd.DataFrame,
) -> dict[str, Any]:
    """Compute simple features for a transaction using historical data.

    For batch scoring, we compute simplified features that don't require
    the full FeatureEngineer (which is O(n²) per sender). Instead, we use
    pre-computed dbt features or simple aggregations.
    """
    features: dict[str, Any] = {}

    # Amount features
    features["amount_ngn"] = float(row["amount_ngn"])

    # Pre-computed source fields (untrusted but ingested)
    features["amount_zscore"] = float(row.get("spending_deviation_score", 0) or 0)
    features["transactions_last_10m"] = 0  # Not available from raw data
    features["transactions_last_60m"] = 0
    features["transactions_last_1440m"] = 0

    # Customer features (simplified: use global averages as defaults)
    sender = row["sender_account"]
    sender_mask = all_rows["sender_account"] == sender
    sender_rows = all_rows[sender_mask]
    prior_rows = sender_rows[sender_rows["timestamp"] < row["timestamp"]]

    if len(prior_rows) > 0:
        features["customer_transaction_count_prior"] = len(prior_rows)
        features["customer_avg_amount_prior"] = float(prior_rows["amount_ngn"].mean())
        features["customer_std_amount_prior"] = float(prior_rows["amount_ngn"].std() or 0)
        features["customer_max_amount_prior"] = float(prior_rows["amount_ngn"].max())
        avg = features["customer_avg_amount_prior"]
        features["amount_ratio_to_avg"] = float(row["amount_ngn"]) / avg if avg > 0 else 1.0
    else:
        features["customer_transaction_count_prior"] = 0
        features["customer_avg_amount_prior"] = 0.0
        features["customer_std_amount_prior"] = 0.0
        features["customer_max_amount_prior"] = 0.0
        features["amount_ratio_to_avg"] = 1.0

    # Merchant features
    merchant = row["merchant_category"]
    merchant_mask = all_rows["merchant_category"] == merchant
    merchant_rows = all_rows[merchant_mask]
    merchant_prior = merchant_rows[merchant_rows["timestamp"] < row["timestamp"]]
    features["merchant_transaction_count_prior"] = len(merchant_prior)
    if len(merchant_prior) > 0:
        features["merchant_fraud_rate_prior"] = float(
            merchant_prior["is_fraud"].sum() / len(merchant_prior)
        )
    else:
        features["merchant_fraud_rate_prior"] = 0.0

    # Location features
    location = row["location"]
    location_mask = all_rows["location"] == location
    location_rows = all_rows[location_mask]
    location_prior = location_rows[location_rows["timestamp"] < row["timestamp"]]
    features["location_transaction_count_prior"] = len(location_prior)
    if len(location_prior) > 0:
        features["location_fraud_rate_prior"] = float(
            location_prior["is_fraud"].sum() / len(location_prior)
        )
    else:
        features["location_fraud_rate_prior"] = 0.0

    # Device features
    device = row.get("device_hash", "")
    device_mask = all_rows["device_hash"] == device if device else pd.Series(False, index=all_rows.index)
    device_rows = all_rows[device_mask]
    device_prior = device_rows[device_rows["timestamp"] < row["timestamp"]]
    features["device_transaction_count_prior"] = len(device_prior)

    # Device first seen: check if this sender has used this device before
    sender_device_prior = device_prior[device_prior["sender_account"] == sender]
    features["device_first_seen"] = len(sender_device_prior) == 0

    # Temporal features
    ts = row["timestamp"]
    if hasattr(ts, "hour"):
        features["hour_of_day"] = ts.hour
        features["day_of_week"] = ts.dayofweek
        features["is_weekend"] = 1 if ts.dayofweek >= 5 else 0
    else:
        features["hour_of_day"] = 0
        features["day_of_week"] = 0
        features["is_weekend"] = 0

    return features


def batch_score_transactions(
    config: DBConfig | None = None,
    model_path: str | None = None,
    limit: int | None = None,
    batch_size: int = 500,
) -> dict[str, Any]:
    """Score all raw transactions and persist results.

    Args:
        config: Database configuration. If None, uses env vars.
        model_path: Path to model artifact. If None, uses default.
        limit: Maximum transactions to score. None = all.
        batch_size: How many scores to persist at once.

    Returns:
        Summary dictionary with counts and timing.
    """
    config = config or DBConfig.from_env()

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

    # Score in batches
    total_scored = 0
    start_time = datetime.now()

    for batch_start in range(0, len(df), batch_size):
        batch_end = min(batch_start + batch_size, len(df))
        batch_df = df.iloc[batch_start:batch_end]

        scores = []
        for _, row in batch_df.iterrows():
            try:
                # Compute features
                features = _compute_simple_features(row, df)

                # Prepare for model
                model_features = prepare_features_from_transaction(
                    features, artifact.feature_columns
                )

                # Get fraud probability
                fraud_prob = predict_probability(artifact, model_features)

                # Get risk assessment
                transaction = _row_to_transaction(row)
                risk_result = risk_engine.assess_transaction(transaction, fraud_prob)

                # Generate explanations
                import pandas as pd
                X = pd.DataFrame([model_features], columns=artifact.feature_columns)
                explanations = explain_prediction(
                    artifact.model, artifact.feature_columns, X, top_k=5
                )
                shap_factors = format_explanation_for_api(explanations)

                # Build score record
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
                    "is_fraud": bool(row["is_fraud"]) if row["is_fraud"] is not None else False,
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
                    "scored_at": datetime.now(),
                }
                scores.append(score)

            except Exception as e:
                logger.warning("Failed to score %s: %s", row.get("transaction_id", "?"), e)
                continue

        # Persist batch
        if scores:
            store.upsert_batch(scores)
            total_scored += len(scores)

        if total_scored % 5000 == 0:
            logger.info("Scored %d / %d transactions...", total_scored, len(df))

    elapsed = (datetime.now() - start_time).total_seconds()
    store.close()

    result = {
        "total_transactions": len(df),
        "total_scored": total_scored,
        "elapsed_seconds": round(elapsed, 1),
        "model_version": artifact.model_version,
        "scores_per_second": round(total_scored / elapsed, 1) if elapsed > 0 else 0,
    }

    logger.info("Batch scoring complete: %s", result)
    return result
