"""FastAPI application for FraudLens risk scoring.

This module provides the REST API for transaction risk scoring.
The API uses a trained ML model (not heuristics) for fraud probability estimation.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fraudlens.features.preparation import (
    MODEL_FEATURES,
    prepare_features_from_transaction,
)
from fraudlens.logging_config import configure_logging
from fraudlens.models.explainer import explain_prediction, format_explanation_for_api
from fraudlens.models.serving import ModelArtifact, load_model_artifact, predict_probability
from fraudlens.risk.engine import RiskEngine

logger = logging.getLogger(__name__)

# Model artifact path — supports local paths and S3 URIs
DEFAULT_MODEL_PATH = os.environ.get(
    "FRAUDLENS_MODEL_PATH", "models/random_forest.artifact.pkl"
)

# S3 model loading (alternative to local path)
MODEL_S3_BUCKET = os.environ.get("FRAUDLENS_MODEL_S3_BUCKET", "")
MODEL_S3_KEY = os.environ.get("FRAUDLENS_MODEL_S3_KEY", "")


def _resolve_model_path() -> str:
    """Resolve model path from environment variables."""
    # Prefer explicit FRAUDLENS_MODEL_PATH if set
    explicit = os.environ.get("FRAUDLENS_MODEL_PATH", "")
    if explicit:
        return explicit

    # Check S3 configuration
    if MODEL_S3_BUCKET and MODEL_S3_KEY:
        return f"s3://{MODEL_S3_BUCKET}/{MODEL_S3_KEY}"

    return DEFAULT_MODEL_PATH


# Request/Response schemas
class TransactionRequest(BaseModel):
    """Request schema for transaction scoring."""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    sender_account: str = Field(..., description="Sender account identifier")
    receiver_account: str = Field(..., description="Receiver account identifier")
    transaction_type: str = Field(..., description="Transaction type")
    merchant_category: str = Field(..., description="Merchant category")
    location: str = Field(..., description="Transaction location")
    device_used: str = Field(..., description="Device type used")
    amount_ngn: float = Field(..., gt=0, description="Transaction amount in NGN")
    payment_channel: str = Field(..., description="Payment channel")
    ip_address: str = Field(..., description="IP address")
    device_hash: str = Field(..., description="Device hash")
    sender_persona: str = Field(..., description="Sender persona type")

    # Behavioral features (computed by feature pipeline, provided at scoring time)
    customer_transaction_count_prior: int = Field(0, ge=0)
    customer_avg_amount_prior: float = Field(0.0, ge=0)
    customer_std_amount_prior: float = Field(0.0, ge=0)
    customer_max_amount_prior: float = Field(0.0, ge=0)
    amount_ratio_to_avg: float = Field(1.0, ge=0)
    amount_zscore: float = Field(0.0)
    merchant_transaction_count_prior: int = Field(0, ge=0)
    merchant_fraud_rate_prior: float = Field(0.0, ge=0, le=1)
    location_transaction_count_prior: int = Field(0, ge=0)
    location_fraud_rate_prior: float = Field(0.0, ge=0, le=1)
    device_transaction_count_prior: int = Field(0, ge=0)
    device_first_seen: bool = Field(False)
    transactions_last_10m: int = Field(0, ge=0)
    transactions_last_60m: int = Field(0, ge=0)
    transactions_last_1440m: int = Field(0, ge=0)
    hour_of_day: int = Field(0, ge=0, le=23)
    day_of_week: int = Field(0, ge=0, le=6)
    is_weekend: int = Field(0, ge=0, le=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "T123456",
                "sender_account": "ACC001",
                "receiver_account": "ACC002",
                "transaction_type": "transfer",
                "merchant_category": "electronics",
                "location": "Lagos",
                "device_used": "mobile",
                "amount_ngn": 50000.00,
                "payment_channel": "Bank Transfer",
                "ip_address": "192.168.1.1",
                "device_hash": "D1234567",
                "sender_persona": "Trader",
            }
        }
    }


class ExplanationItem(BaseModel):
    """Single feature explanation."""

    feature: str
    shap_value: float
    direction: str
    magnitude: float


class TransactionResponse(BaseModel):
    """Response schema for transaction scoring."""

    transaction_id: str
    fraud_probability: float = Field(..., ge=0, le=1)
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern="^(low|medium|high|critical)$")
    recommended_action: str = Field(..., pattern="^(allow|monitor|review|urgent_review)$")
    risk_factors: list[str]
    model_version: str
    risk_engine_version: str
    scored_at: str


class HealthResponse(BaseModel):
    """Response schema for health check."""

    status: str
    version: str
    model_loaded: bool
    model_version: str
    timestamp: str


class ReadyResponse(BaseModel):
    """Response schema for readiness check."""

    status: str
    model_loaded: bool
    database_reachable: bool
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: str


def create_app(
    model_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        model_path: Path to the trained model artifact. If None, uses env var or default.
        config: Optional configuration dictionary.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title="FraudLens API",
        description="Financial Transaction Risk Intelligence Platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure logging
    configure_logging()

    # Load model artifact
    resolved_path = _resolve_model_path() if model_path is None else str(model_path)
    artifact: ModelArtifact | None = None
    model_loaded = False

    is_s3 = resolved_path.startswith("s3://")
    path_exists = is_s3 or Path(resolved_path).exists()

    if path_exists:
        try:
            artifact = load_model_artifact(resolved_path)
            model_loaded = True
            logger.info("Loaded model: %s from %s", artifact.model_version, resolved_path)
        except Exception as e:
            logger.error("Failed to load model from %s: %s", resolved_path, e)
    else:
        logger.warning("Model artifact not found at %s. API will return 503.", resolved_path)

    # Initialize risk engine
    risk_engine = RiskEngine()
    RISK_ENGINE_VERSION = "001"

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Liveness check — is the process alive?"""
        return HealthResponse(
            status="ok" if model_loaded else "degraded",
            version="0.1.0",
            model_loaded=model_loaded,
            model_version=artifact.model_version if artifact else "none",
            timestamp=datetime.now().isoformat(),
        )

    @app.get("/ready", response_model=ReadyResponse)
    async def readiness_check() -> ReadyResponse:
        """Readiness check — can the API serve requests?"""
        # Check database connectivity
        db_reachable = False
        try:
            from fraudlens.dashboard.data.connection import get_connection
            conn = get_connection()
            conn.close()
            db_reachable = True
        except Exception:
            pass

        ready = model_loaded and db_reachable
        return ReadyResponse(
            status="ready" if ready else "not_ready",
            model_loaded=model_loaded,
            database_reachable=db_reachable,
            timestamp=datetime.now().isoformat(),
        )

    @app.post(
        "/score-transaction",
        response_model=TransactionResponse,
        responses={
            400: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def score_transaction(request: TransactionRequest) -> TransactionResponse:
        """Score a transaction for fraud risk.

        This endpoint accepts transaction details and returns a risk assessment
        including fraud probability, risk score, risk level, and recommended action.
        """
        if not model_loaded or artifact is None:
            raise HTTPException(
                status_code=503,
                detail="Model not loaded. Train a model first.",
            )

        try:
            # Convert request to dictionary
            transaction = request.model_dump()

            # Prepare features using shared preparation (ensures parity with training)
            features = prepare_features_from_transaction(transaction, artifact.feature_columns)

            # Get fraud probability from the ACTUAL trained model
            fraud_probability = predict_probability(artifact, features)

            # Generate SHAP explanations
            import pandas as pd

            X_explain = pd.DataFrame([features], columns=artifact.feature_columns)
            explanations = explain_prediction(
                artifact.model, artifact.feature_columns, X_explain, top_k=5
            )

            # Assess risk using real model probability + rules
            risk_result = risk_engine.assess_transaction(transaction, fraud_probability)

            # Combine rule-based factors with SHAP explanations
            shap_factors = format_explanation_for_api(explanations)
            all_risk_factors = risk_result.risk_factors + shap_factors

            return TransactionResponse(
                transaction_id=risk_result.transaction_id,
                fraud_probability=round(fraud_probability, 4),
                risk_score=risk_result.risk_score,
                risk_level=risk_result.risk_level,
                recommended_action=risk_result.recommended_action,
                risk_factors=all_risk_factors,
                model_version=artifact.model_version,
                risk_engine_version=RISK_ENGINE_VERSION,
                scored_at=datetime.now().isoformat(),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Risk scoring failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Risk scoring failed: {type(e).__name__}",
            )

    return app


# Create default app instance
app = create_app()
