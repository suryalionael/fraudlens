"""FastAPI application for FraudLens risk scoring.

This module provides the REST API for transaction risk scoring.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

from fraudlens.risk.engine import RiskEngine, RiskConfig


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

    # Feature fields (optional, will be computed if not provided)
    customer_transaction_count_prior: int = Field(0, ge=0)
    customer_avg_amount_prior: float = Field(0, ge=0)
    customer_std_amount_prior: float = Field(0, ge=0)
    customer_max_amount_prior: float = Field(0, ge=0)
    amount_ratio_to_avg: float = Field(1.0, ge=0)
    amount_zscore: float = Field(0.0)
    merchant_fraud_rate_prior: float = Field(0.0, ge=0, le=1)
    location_fraud_rate_prior: float = Field(0.0, ge=0, le=1)
    device_first_seen: bool = Field(False)
    transactions_last_1h: int = Field(0, ge=0)
    customer_transactions_per_day: float = Field(0, ge=0)

    class Config:
        json_schema_extra = {
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


class RiskFactor(BaseModel):
    """Risk factor in the response."""

    factor: str
    description: str


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
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: str


# Application
def create_app(config: dict[str, Any] | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
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

    # Initialize risk engine
    risk_engine = RiskEngine()

    # Model metadata (would be loaded from trained model in production)
    MODEL_VERSION = "fraudlens-lr-v001"
    RISK_ENGINE_VERSION = "001"

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(
            status="ok",
            version="0.1.0",
            timestamp=datetime.now().isoformat(),
        )

    @app.post(
        "/score-transaction",
        response_model=TransactionResponse,
        responses={
            400: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def score_transaction(request: TransactionRequest) -> TransactionResponse:
        """Score a transaction for fraud risk.

        This endpoint accepts transaction details and returns a risk assessment
        including fraud probability, risk score, risk level, and recommended action.
        """
        try:
            # Convert request to dictionary
            transaction = request.model_dump()

            # Use a simple heuristic for fraud probability
            # In production, this would use the trained ML model
            fraud_probability = _estimate_fraud_probability(transaction)

            # Assess risk
            result = risk_engine.assess_transaction(transaction, fraud_probability)

            return TransactionResponse(
                transaction_id=result.transaction_id,
                fraud_probability=round(result.fraud_probability, 4),
                risk_score=result.risk_score,
                risk_level=result.risk_level,
                recommended_action=result.recommended_action,
                risk_factors=result.risk_factors,
                model_version=MODEL_VERSION,
                risk_engine_version=RISK_ENGINE_VERSION,
                scored_at=datetime.now().isoformat(),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Risk scoring failed: {str(e)}",
            )

    return app


def _estimate_fraud_probability(transaction: dict[str, Any]) -> float:
    """Estimate fraud probability using heuristics.

    In production, this would use the trained ML model.
    This is a simplified version for demonstration.
    """
    score = 0.0

    # Amount-based signals
    amount = transaction.get("amount_ngn", 0)
    avg_amount = transaction.get("customer_avg_amount_prior", 0)
    if avg_amount > 0:
        amount_ratio = amount / avg_amount
        if amount_ratio > 3:
            score += 0.3
        elif amount_ratio > 2:
            score += 0.2
        elif amount_ratio > 1.5:
            score += 0.1

    # Z-score signal
    zscore = abs(transaction.get("amount_zscore", 0))
    if zscore > 3:
        score += 0.3
    elif zscore > 2:
        score += 0.2
    elif zscore > 1.5:
        score += 0.1

    # Device signal
    if transaction.get("device_first_seen", False):
        score += 0.2

    # Merchant risk
    merchant_fraud_rate = transaction.get("merchant_fraud_rate_prior", 0)
    if merchant_fraud_rate > 0.1:
        score += 0.2
    elif merchant_fraud_rate > 0.05:
        score += 0.1

    # Location risk
    location_fraud_rate = transaction.get("location_fraud_rate_prior", 0)
    if location_fraud_rate > 0.1:
        score += 0.2
    elif location_fraud_rate > 0.05:
        score += 0.1

    # Velocity signal
    velocity = transaction.get("transactions_last_1h", 0)
    if velocity > 10:
        score += 0.2
    elif velocity > 5:
        score += 0.1

    # Cap at 0.95
    return min(score, 0.95)


# Create default app instance
app = create_app()
