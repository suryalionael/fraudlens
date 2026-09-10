"""Real-time scoring service for FraudLens.

Orchestrates the complete scoring pipeline:
request validation → historical context → feature preparation →
ML model → SHAP → risk engine → persistence → response.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

import pandas as pd

from fraudlens.features.preparation import (
    prepare_features_from_transaction,
)
from fraudlens.ingestion.postgres_loader import DBConfig
from fraudlens.models.explainer import explain_prediction, format_explanation_for_api
from fraudlens.models.serving import ModelArtifact, predict_probability
from fraudlens.risk.engine import RiskEngine, RiskResult
from fraudlens.risk.historical import HistoricalContextService
from fraudlens.risk.storage import RiskScoreStore

logger = logging.getLogger(__name__)


class ScoringResult:
    """Result of a real-time scoring operation."""

    def __init__(
        self,
        transaction_id: str,
        fraud_probability: float,
        risk_result: RiskResult,
        shap_factors: list[str],
        model_version: str,
        risk_engine_version: str,
        latency_ms: float,
        persisted: bool,
    ) -> None:
        self.transaction_id = transaction_id
        self.fraud_probability = fraud_probability
        self.risk_result = risk_result
        self.shap_factors = shap_factors
        self.model_version = model_version
        self.risk_engine_version = risk_engine_version
        self.latency_ms = latency_ms
        self.persisted = persisted


class RealtimeScoringService:
    """Orchestrate real-time transaction scoring.

    Flow:
    request → historical context → features → model → SHAP → risk → persist
    """

    def __init__(
        self,
        artifact: ModelArtifact,
        db_config: DBConfig | None = None,
    ) -> None:
        self.artifact = artifact
        self.db_config = db_config or DBConfig.from_env()
        self.risk_engine = RiskEngine()
        self.historical_service = HistoricalContextService(self.db_config)
        self.risk_store = RiskScoreStore(self.db_config)
        self.risk_store.create_schema()

    def score_transaction(
        self,
        transaction: dict[str, Any],
        persist: bool = True,
    ) -> ScoringResult:
        """Score a single transaction through the complete pipeline.

        Args:
            transaction: Raw transaction dictionary from the API request.
            persist: Whether to persist the result to PostgreSQL.

        Returns:
            ScoringResult with all scoring outputs.
        """
        start_time = time.time()
        transaction_id = transaction.get("transaction_id", "unknown")

        # 1. Parse transaction timestamp
        ts_str = transaction.get("timestamp", "")
        if isinstance(ts_str, str):
            transaction_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        else:
            transaction_ts = ts_str

        # 2. Retrieve historical context from PostgreSQL
        logger.info("Retrieving historical context for %s", transaction_id)
        historical = self.historical_service.get_all_context(
            sender_account=transaction["sender_account"],
            merchant_category=transaction["merchant_category"],
            location=transaction["location"],
            device_hash=transaction["device_hash"],
            as_of=transaction_ts,
        )

        # 3. Merge raw transaction with historical context for feature preparation
        enriched = {
            "transaction_id": transaction_id,
            "amount_ngn": transaction["amount_ngn"],
            # Customer features from historical context
            "customer_transaction_count_prior": historical[
                "customer_transaction_count"
            ],
            "customer_avg_amount_prior": historical["customer_avg_amount"],
            "customer_std_amount_prior": historical["customer_std_amount"],
            "customer_max_amount_prior": historical["customer_max_amount"],
            # Velocity features
            "transactions_last_10m": historical["transactions_last_10m"],
            "transactions_last_60m": historical["transactions_last_60m"],
            "transactions_last_1440m": historical["transactions_last_1440m"],
            # Merchant features
            "merchant_transaction_count_prior": historical[
                "merchant_transaction_count"
            ],
            "merchant_fraud_rate_prior": historical["merchant_fraud_rate"],
            # Location features
            "location_transaction_count_prior": historical[
                "location_transaction_count"
            ],
            "location_fraud_rate_prior": historical["location_fraud_rate"],
            # Device features
            "device_transaction_count_prior": historical["device_transaction_count"],
            "device_first_seen": historical["device_first_seen"],
        }

        # 4. Derive amount features
        avg = enriched["customer_avg_amount_prior"]
        std = enriched["customer_std_amount_prior"]
        enriched["amount_ratio_to_avg"] = (
            transaction["amount_ngn"] / avg if avg > 0 else 1.0
        )
        enriched["amount_zscore"] = (
            (transaction["amount_ngn"] - avg) / std if std > 0 else 0.0
        )

        # 5. Temporal features
        enriched["hour_of_day"] = transaction_ts.hour
        enriched["day_of_week"] = transaction_ts.weekday()
        enriched["is_weekend"] = 1 if transaction_ts.weekday() >= 5 else 0

        # 6. Prepare model features (ensures training/inference parity)
        model_features = prepare_features_from_transaction(
            enriched, self.artifact.feature_columns
        )

        # 7. Model inference
        fraud_probability = predict_probability(self.artifact, model_features)

        # 8. SHAP explanation
        X_explain = pd.DataFrame(
            [model_features], columns=self.artifact.feature_columns
        )
        explanations = explain_prediction(
            self.artifact.model,
            self.artifact.feature_columns,
            X_explain,
            top_k=5,
        )
        shap_factors = format_explanation_for_api(explanations)

        # 9. Risk engine
        # Merge enriched data back into transaction for risk engine rules
        risk_input = {
            **enriched,
            "transaction_id": transaction_id,
        }
        risk_result = self.risk_engine.assess_transaction(risk_input, fraud_probability)

        # 10. Combine risk factors
        all_risk_factors = risk_result.risk_factors + shap_factors

        # 11. Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # 12. Persist if requested
        persisted = False
        if persist:
            try:
                self._persist_score(
                    transaction=transaction,
                    fraud_probability=fraud_probability,
                    risk_result=risk_result,
                    all_risk_factors=all_risk_factors,
                )
                persisted = True
            except Exception as e:
                logger.error(
                    "Failed to persist risk score for %s: %s", transaction_id, e
                )
                raise

        logger.info(
            "Scored %s: probability=%.4f, risk=%.1f, level=%s, latency=%.1fms, persisted=%s",
            transaction_id,
            fraud_probability,
            risk_result.risk_score,
            risk_result.risk_level,
            latency_ms,
            persisted,
        )

        return ScoringResult(
            transaction_id=transaction_id,
            fraud_probability=fraud_probability,
            risk_result=risk_result,
            shap_factors=shap_factors,
            model_version=self.artifact.model_version,
            risk_engine_version="001",
            latency_ms=round(latency_ms, 1),
            persisted=persisted,
        )

    def _persist_score(
        self,
        transaction: dict[str, Any],
        fraud_probability: float,
        risk_result: RiskResult,
        all_risk_factors: list[str],
    ) -> None:
        """Persist the scoring result to PostgreSQL."""
        score = {
            "transaction_id": transaction["transaction_id"],
            "timestamp": transaction.get("timestamp"),
            "sender_account": transaction.get("sender_account"),
            "receiver_account": transaction.get("receiver_account"),
            "transaction_type": transaction.get("transaction_type"),
            "merchant_category": transaction.get("merchant_category"),
            "location": transaction.get("location"),
            "device_used": transaction.get("device_used"),
            "payment_channel": transaction.get("payment_channel"),
            "amount_ngn": float(transaction["amount_ngn"]),
            "is_fraud": None,
            "fraud_probability": round(fraud_probability, 4),
            "risk_score": risk_result.risk_score,
            "risk_level": risk_result.risk_level,
            "recommended_action": risk_result.recommended_action,
            "rule_score": risk_result.rule_score,
            "ml_score": risk_result.ml_score,
            "risk_factors": all_risk_factors,
            "rule_signals": risk_result.rule_signals,
            "model_version": self.artifact.model_version,
            "risk_engine_version": "001",
            "scored_at": datetime.now().isoformat(),
        }
        self.risk_store.upsert_score(score)

    def check_existing_score(self, transaction_id: str) -> dict[str, Any] | None:
        """Check if a transaction has already been scored.

        Args:
            transaction_id: The transaction identifier.

        Returns:
            Existing score record if found, None otherwise.
        """
        conn = self.historical_service.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT transaction_id, fraud_probability, risk_score, "
                "risk_level, recommended_action, risk_factors, model_version, scored_at "
                "FROM risk.transaction_scores WHERE transaction_id = %s",
                (transaction_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        return {
            "transaction_id": row[0],
            "fraud_probability": float(row[1]),
            "risk_score": float(row[2]),
            "risk_level": row[3],
            "recommended_action": row[4],
            "risk_factors": json.loads(row[5]) if isinstance(row[5], str) else row[5],
            "model_version": row[6],
            "scored_at": row[7].isoformat() if row[7] else None,
        }

    def close(self) -> None:
        """Close database connections."""
        self.historical_service.close()
        self.risk_store.close()
