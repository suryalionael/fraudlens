"""Risk score persistence for FraudLens.

This module provides PostgreSQL storage for risk scoring outputs,
enabling the dashboard to query historical risk assessments.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg2
import psycopg2.extras

from fraudlens.ingestion.postgres_loader import DBConfig

logger = logging.getLogger(__name__)

# DDL for risk score storage
RISK_SCORES_DDL = """
CREATE SCHEMA IF NOT EXISTS risk;

CREATE TABLE IF NOT EXISTS risk.transaction_scores (
    transaction_id      TEXT PRIMARY KEY,
    timestamp           TIMESTAMP,
    sender_account      TEXT,
    receiver_account    TEXT,
    transaction_type    TEXT,
    merchant_category   TEXT,
    location            TEXT,
    device_used         TEXT,
    payment_channel     TEXT,
    amount_ngn          NUMERIC NOT NULL,
    is_fraud            BOOLEAN,

    fraud_probability   NUMERIC NOT NULL,
    risk_score          NUMERIC NOT NULL,
    risk_level          TEXT NOT NULL,
    recommended_action  TEXT NOT NULL,
    rule_score          NUMERIC,
    ml_score            NUMERIC,
    risk_factors        JSONB,
    rule_signals        JSONB,

    model_version       TEXT,
    risk_engine_version TEXT,
    scored_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Dashboard query indexes
CREATE INDEX IF NOT EXISTS idx_transaction_scores_risk_level
    ON risk.transaction_scores (risk_level);
CREATE INDEX IF NOT EXISTS idx_transaction_scores_risk_score
    ON risk.transaction_scores (risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_transaction_scores_scored_at
    ON risk.transaction_scores (scored_at);
CREATE INDEX IF NOT EXISTS idx_transaction_scores_merchant
    ON risk.transaction_scores (merchant_category);
CREATE INDEX IF NOT EXISTS idx_transaction_scores_location
    ON risk.transaction_scores (location);

-- Real-time scoring indexes (raw.transactions)
-- Note: These are created separately via migration SQL below
"""

# Indexes for raw.transactions to support real-time historical queries
RAW_TRANSACTIONS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_raw_tx_sender_timestamp
    ON raw.transactions (sender_account, timestamp);

CREATE INDEX IF NOT EXISTS idx_raw_tx_device_hash
    ON raw.transactions (device_hash, timestamp);

CREATE INDEX IF NOT EXISTS idx_raw_tx_merchant_timestamp
    ON raw.transactions (merchant_category, timestamp);

CREATE INDEX IF NOT EXISTS idx_raw_tx_location_timestamp
    ON raw.transactions (location, timestamp);
"""


class RiskScoreStore:
    """Persist and query risk scoring outputs in PostgreSQL."""

    def __init__(self, config: DBConfig | None = None) -> None:
        self.config = config or DBConfig.from_env()
        self._conn: psycopg2.extensions.connection | None = None

    def connect(self) -> psycopg2.extensions.connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                dbname=self.config.dbname,
                user=self.config.user,
                password=self.config.password,
            )
        return self._conn

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None

    def create_schema(self) -> None:
        """Create the risk schema, tables, and indexes."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(RISK_SCORES_DDL)
        conn.commit()

    def create_raw_indexes(self) -> None:
        """Create indexes on raw.transactions for real-time queries."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(RAW_TRANSACTIONS_INDEXES)
        conn.commit()

    def upsert_score(self, score: dict[str, Any]) -> None:
        """Insert or update a single risk score record.

        Args:
            score: Dictionary with score fields. Must include transaction_id.
        """
        conn = self.connect()
        sql = """
            INSERT INTO risk.transaction_scores (
                transaction_id, timestamp, sender_account, receiver_account,
                transaction_type, merchant_category, location, device_used,
                payment_channel, amount_ngn, is_fraud,
                fraud_probability, risk_score, risk_level, recommended_action,
                rule_score, ml_score, risk_factors, rule_signals,
                model_version, risk_engine_version, scored_at
            ) VALUES (
                %(transaction_id)s, %(timestamp)s, %(sender_account)s, %(receiver_account)s,
                %(transaction_type)s, %(merchant_category)s, %(location)s, %(device_used)s,
                %(payment_channel)s, %(amount_ngn)s, %(is_fraud)s,
                %(fraud_probability)s, %(risk_score)s, %(risk_level)s, %(recommended_action)s,
                %(rule_score)s, %(ml_score)s, %(risk_factors)s, %(rule_signals)s,
                %(model_version)s, %(risk_engine_version)s, %(scored_at)s
            )
            ON CONFLICT (transaction_id) DO UPDATE SET
                fraud_probability = EXCLUDED.fraud_probability,
                risk_score = EXCLUDED.risk_score,
                risk_level = EXCLUDED.risk_level,
                recommended_action = EXCLUDED.recommended_action,
                rule_score = EXCLUDED.rule_score,
                ml_score = EXCLUDED.ml_score,
                risk_factors = EXCLUDED.risk_factors,
                rule_signals = EXCLUDED.rule_signals,
                model_version = EXCLUDED.model_version,
                scored_at = EXCLUDED.scored_at
        """
        # Serialize lists to JSON
        params = dict(score)
        if isinstance(params.get("risk_factors"), list):
            params["risk_factors"] = json.dumps(params["risk_factors"])
        if isinstance(params.get("rule_signals"), list):
            params["rule_signals"] = json.dumps(params["rule_signals"])

        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()

    def upsert_batch(self, scores: list[dict[str, Any]]) -> int:
        """Insert or update a batch of risk score records.

        Args:
            scores: List of score dictionaries.

        Returns:
            Number of records upserted.
        """
        if not scores:
            return 0

        conn = self.connect()
        sql = """
            INSERT INTO risk.transaction_scores (
                transaction_id, timestamp, sender_account, receiver_account,
                transaction_type, merchant_category, location, device_used,
                payment_channel, amount_ngn, is_fraud,
                fraud_probability, risk_score, risk_level, recommended_action,
                rule_score, ml_score, risk_factors, rule_signals,
                model_version, risk_engine_version, scored_at
            ) VALUES (
                %(transaction_id)s, %(timestamp)s, %(sender_account)s, %(receiver_account)s,
                %(transaction_type)s, %(merchant_category)s, %(location)s, %(device_used)s,
                %(payment_channel)s, %(amount_ngn)s, %(is_fraud)s,
                %(fraud_probability)s, %(risk_score)s, %(risk_level)s, %(recommended_action)s,
                %(rule_score)s, %(ml_score)s, %(risk_factors)s, %(rule_signals)s,
                %(model_version)s, %(risk_engine_version)s, %(scored_at)s
            )
            ON CONFLICT (transaction_id) DO UPDATE SET
                fraud_probability = EXCLUDED.fraud_probability,
                risk_score = EXCLUDED.risk_score,
                risk_level = EXCLUDED.risk_level,
                recommended_action = EXCLUDED.recommended_action,
                rule_score = EXCLUDED.rule_score,
                ml_score = EXCLUDED.ml_score,
                risk_factors = EXCLUDED.risk_factors,
                rule_signals = EXCLUDED.rule_signals,
                model_version = EXCLUDED.model_version,
                scored_at = EXCLUDED.scored_at
        """

        # Process all scores
        processed = []
        for score in scores:
            params = dict(score)
            if isinstance(params.get("risk_factors"), list):
                params["risk_factors"] = json.dumps(params["risk_factors"])
            if isinstance(params.get("rule_signals"), list):
                params["rule_signals"] = json.dumps(params["rule_signals"])
            processed.append(params)

        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, processed, page_size=500)
        conn.commit()

        logger.info("Upserted %d risk scores", len(processed))
        return len(processed)

    def count_scores(self) -> int:
        """Return total number of scored transactions."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM risk.transaction_scores")
            return cur.fetchone()[0]

    def get_risk_distribution(self) -> dict[str, Any]:
        """Get risk level distribution from actual data."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    risk_level,
                    COUNT(*) as count,
                    ROUND(SUM(amount_ngn), 2) as total_amount,
                    ROUND(AVG(risk_score), 2) as avg_score
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
            rows = cur.fetchall()
            return {
                row[0]: {
                    "count": row[1],
                    "total_amount": float(row[2]),
                    "avg_score": float(row[3]),
                }
                for row in rows
            }
