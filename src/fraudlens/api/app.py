"""FastAPI application for FraudLens real-time risk scoring.

Phase 10: Synchronous real-time transaction scoring with:
- strict request validation
- historical context from PostgreSQL (leakage-safe)
- real ML model inference
- SHAP explanations
- risk engine
- persistence to risk.transaction_scores
- idempotent behavior
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from fraudlens.features.preparation import MODEL_FEATURES
from fraudlens.logging_config import configure_logging
from fraudlens.models.serving import ModelArtifact, load_model_artifact
from fraudlens.risk.engine import RiskEngine

logger = logging.getLogger(__name__)

# Model artifact path
DEFAULT_MODEL_PATH = os.environ.get(
    "FRAUDLENS_MODEL_PATH", "models/random_forest.artifact.pkl"
)
MODEL_S3_BUCKET = os.environ.get("FRAUDLENS_MODEL_S3_BUCKET", "")
MODEL_S3_KEY = os.environ.get("FRAUDLENS_MODEL_S3_KEY", "")

FORBIDDEN_FIELDS = {
    "new_device_transaction",
    "time_since_last_transaction",
    "velocity_score",
    "geo_anomaly_score",
    "spending_deviation_score",
}


def _resolve_model_path() -> str:
    """Resolve model path from environment variables."""
    explicit = os.environ.get("FRAUDLENS_MODEL_PATH", "")
    if explicit:
        return explicit
    if MODEL_S3_BUCKET and MODEL_S3_KEY:
        return f"s3://{MODEL_S3_BUCKET}/{MODEL_S3_KEY}"
    return DEFAULT_MODEL_PATH


# ── Request Schema (Phase 10 hardened) ──

class TransactionRequest(BaseModel):
    """Request schema for real-time transaction scoring.

    Only raw transaction attributes are accepted.
    Behavioral features are generated server-side from historical context.
    Precomputed features from the source dataset are forbidden.
    """

    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(
        ..., min_length=1, max_length=128,
        description="Unique transaction identifier",
    )
    timestamp: str = Field(
        ..., description="ISO 8601 transaction timestamp"
    )
    amount_ngn: float = Field(
        ..., gt=0, description="Transaction amount in NGN"
    )
    transaction_type: str = Field(
        ..., min_length=1, max_length=50,
        description="Transaction type",
    )
    merchant_category: str = Field(
        ..., min_length=1, max_length=100,
        description="Merchant category",
    )
    location: str = Field(
        ..., min_length=1, max_length=100,
        description="Transaction location",
    )
    device_used: str = Field(
        ..., min_length=1, max_length=50,
        description="Device type used",
    )
    payment_channel: str = Field(
        ..., min_length=1, max_length=50,
        description="Payment channel",
    )
    ip_address: str = Field(
        ..., min_length=1, max_length=45,
        description="IP address",
    )
    device_hash: str = Field(
        ..., min_length=1, max_length=256,
        description="Device hash identifier",
    )
    bvn_linked: bool = Field(
        ..., description="Whether BVN is linked"
    )
    sender_persona: str = Field(
        ..., min_length=1, max_length=50,
        description="Sender persona type",
    )
    sender_account: str = Field(
        ..., min_length=1, max_length=128,
        description="Sender account identifier",
    )
    receiver_account: str = Field(
        ..., min_length=1, max_length=128,
        description="Receiver account identifier",
    )

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("transaction_id must not be whitespace-only")
        return v.strip()

    @field_validator("amount_ngn")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v != v:  # NaN check
            raise ValueError("amount_ngn must not be NaN")
        if v == float("inf") or v == float("-inf"):
            raise ValueError("amount_ngn must be finite")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            ts = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {e}")
        if ts.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware")
        return v


# ── Response Schema ──

class RiskFactor(BaseModel):
    """A single risk factor with explanation."""

    feature: str
    impact: float
    direction: str


class TransactionResponse(BaseModel):
    """Response schema for real-time transaction scoring."""

    transaction_id: str
    fraud_probability: float = Field(..., ge=0, le=1)
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern="^(low|medium|high|critical)$")
    recommended_action: str = Field(
        ..., pattern="^(allow|monitor|review|urgent_review)$"
    )
    risk_factors: list[RiskFactor]
    model_version: str
    risk_engine_version: str
    scored_at: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    message: str
    details: list[dict[str, Any]] = []
    request_id: str


class HealthResponse(BaseModel):
    """Liveness check response."""

    status: str
    version: str
    model_loaded: bool
    model_version: str
    timestamp: str


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str
    model_loaded: bool
    database_reachable: bool
    timestamp: str


# ── Application Factory ──

def create_app(
    model_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="FraudLens API",
        description="Real-time Financial Transaction Risk Intelligence",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    configure_logging()

    # Load model
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
        logger.warning("Model artifact not found at %s.", resolved_path)

    risk_engine = RiskEngine()

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="ok" if model_loaded else "degraded",
            version="0.2.0",
            model_loaded=model_loaded,
            model_version=artifact.model_version if artifact else "none",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @app.get("/ready", response_model=ReadyResponse)
    async def readiness_check() -> ReadyResponse:
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
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @app.post(
        "/score-transaction",
        response_model=TransactionResponse,
        responses={
            400: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def score_transaction(
        request: TransactionRequest,
        raw_request: Request,
    ) -> TransactionResponse:
        """Score a transaction for fraud risk (Phase 10: real-time synchronous)."""
        request_id = raw_request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        transaction_id = request.transaction_id

        # 1. Model check
        if not model_loaded or artifact is None:
            raise HTTPException(
                status_code=503,
                detail="Scoring unavailable: model not loaded.",
            )

        # 2. Timestamp validation (no future timestamps)
        try:
            ts = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format.")

        now = datetime.now(timezone.utc)
        if ts > now:
            raise HTTPException(
                status_code=400,
                detail="Future timestamps are not allowed.",
            )

        # 3. Idempotency check
        try:
            from fraudlens.risk.scoring import RealtimeScoringService
            scoring_service = RealtimeScoringService(artifact)

            existing = scoring_service.check_existing_score(transaction_id)
            if existing is not None:
                return TransactionResponse(
                    transaction_id=existing["transaction_id"],
                    fraud_probability=existing["fraud_probability"],
                    risk_score=existing["risk_score"],
                    risk_level=existing["risk_level"],
                    recommended_action=existing["recommended_action"],
                    risk_factors=[
                        RiskFactor(
                            feature=f.get("feature", "unknown") if isinstance(f, dict) else "unknown",
                            impact=f.get("impact", 0) if isinstance(f, dict) else 0,
                            direction=f.get("direction", "unknown") if isinstance(f, dict) else "unknown",
                        )
                        for f in (existing.get("risk_factors") or [])
                    ],
                    model_version=existing["model_version"],
                    risk_engine_version="001",
                    scored_at=existing["scored_at"] or now.isoformat(),
                )

            # 4. Score through full pipeline
            transaction = request.model_dump()
            result = scoring_service.score_transaction(transaction, persist=True)

            # 5. Build response
            risk_factors = []
            for f in result.risk_result.risk_factors:
                risk_factors.append(RiskFactor(
                    feature=f[:200] if isinstance(f, str) else "unknown",
                    impact=0.0,
                    direction="HIGHER_RISK",
                ))
            for f in result.shap_factors:
                risk_factors.append(RiskFactor(
                    feature=f[:200] if isinstance(f, str) else "unknown",
                    impact=0.0,
                    direction="HIGHER_RISK",
                ))

            return TransactionResponse(
                transaction_id=result.transaction_id,
                fraud_probability=round(result.fraud_probability, 4),
                risk_score=result.risk_result.risk_score,
                risk_level=result.risk_result.risk_level,
                recommended_action=result.risk_result.recommended_action,
                risk_factors=risk_factors,
                model_version=result.model_version,
                risk_engine_version=result.risk_engine_version,
                scored_at=now.isoformat(),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Scoring failed for %s: %s", transaction_id, e, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal scoring error: {type(e).__name__}",
            )

    return app


app = create_app()
