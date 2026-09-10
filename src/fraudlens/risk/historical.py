"""Historical context service for real-time fraud scoring.

Provides leakage-safe feature queries against PostgreSQL.
All queries use strict temporal cutoffs: only transactions BEFORE
the current transaction timestamp are included.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import psycopg2

from fraudlens.ingestion.postgres_loader import DBConfig

logger = logging.getLogger(__name__)


class HistoricalContextService:
    """Retrieve historical context for real-time feature generation.

    All queries enforce temporal leakage protection:
    WHERE timestamp < :transaction_timestamp
    """

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

    def get_customer_context(
        self,
        sender_account: str,
        as_of: datetime,
    ) -> dict[str, Any]:
        """Get customer-level historical aggregates.

        Args:
            sender_account: The sender's account identifier.
            as_of: Temporal cutoff — only transactions before this time.

        Returns:
            Dictionary with customer aggregates.
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) as transaction_count,
                    COALESCE(AVG(amount_ngn), 0) as avg_amount,
                    COALESCE(STDDEV(amount_ngn), 0) as std_amount,
                    COALESCE(MAX(amount_ngn), 0) as max_amount,
                    COUNT(CASE WHEN is_fraud THEN 1 END) as fraud_count
                FROM raw.transactions
                WHERE sender_account = %s
                  AND timestamp < %s
            """,
                (sender_account, as_of),
            )
            row = cur.fetchone()

        count = row[0] or 0
        avg = float(row[1] or 0)
        std = float(row[2] or 0)
        max_amt = float(row[3] or 0)
        fraud_count = row[4] or 0

        return {
            "customer_transaction_count": count,
            "customer_avg_amount": avg,
            "customer_std_amount": std,
            "customer_max_amount": max_amt,
            "customer_fraud_rate": fraud_count / count if count > 0 else 0.0,
        }

    def get_velocity_context(
        self,
        sender_account: str,
        as_of: datetime,
    ) -> dict[str, int]:
        """Get transaction velocity (count in recent time windows).

        Args:
            sender_account: The sender's account identifier.
            as_of: Temporal cutoff.

        Returns:
            Dictionary with velocity counts.
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(CASE WHEN timestamp >= %s - interval '10 minutes'
                               AND timestamp < %s THEN 1 END) as last_10m,
                    COUNT(CASE WHEN timestamp >= %s - interval '1 hour'
                               AND timestamp < %s THEN 1 END) as last_1h,
                    COUNT(CASE WHEN timestamp >= %s - interval '24 hours'
                               AND timestamp < %s THEN 1 END) as last_24h
                FROM raw.transactions
                WHERE sender_account = %s
            """,
                (
                    as_of,
                    as_of,
                    as_of,
                    as_of,
                    as_of,
                    as_of,
                    sender_account,
                ),
            )
            row = cur.fetchone()

        return {
            "transactions_last_10m": row[0] or 0,
            "transactions_last_60m": row[1] or 0,
            "transactions_last_1440m": row[2] or 0,
        }

    def get_merchant_context(
        self,
        merchant_category: str,
        as_of: datetime,
    ) -> dict[str, Any]:
        """Get merchant-level historical aggregates.

        Args:
            merchant_category: The merchant category.
            as_of: Temporal cutoff.

        Returns:
            Dictionary with merchant aggregates.
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) as transaction_count,
                    COUNT(CASE WHEN is_fraud THEN 1 END) as fraud_count
                FROM raw.transactions
                WHERE merchant_category = %s
                  AND timestamp < %s
            """,
                (merchant_category, as_of),
            )
            row = cur.fetchone()

        count = row[0] or 0
        fraud_count = row[1] or 0

        return {
            "merchant_transaction_count": count,
            "merchant_fraud_rate": fraud_count / count if count > 0 else 0.0,
        }

    def get_location_context(
        self,
        location: str,
        as_of: datetime,
    ) -> dict[str, Any]:
        """Get location-level historical aggregates.

        Args:
            location: The transaction location.
            as_of: Temporal cutoff.

        Returns:
            Dictionary with location aggregates.
        """
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) as transaction_count,
                    COUNT(CASE WHEN is_fraud THEN 1 END) as fraud_count
                FROM raw.transactions
                WHERE location = %s
                  AND timestamp < %s
            """,
                (location, as_of),
            )
            row = cur.fetchone()

        count = row[0] or 0
        fraud_count = row[1] or 0

        return {
            "location_transaction_count": count,
            "location_fraud_rate": fraud_count / count if count > 0 else 0.0,
        }

    def get_device_context(
        self,
        device_hash: str,
        sender_account: str,
        as_of: datetime,
    ) -> dict[str, Any]:
        """Get device-level historical aggregates.

        Args:
            device_hash: The device identifier.
            sender_account: The sender's account (for first-seen check).
            as_of: Temporal cutoff.

        Returns:
            Dictionary with device aggregates.
        """
        conn = self.connect()
        with conn.cursor() as cur:
            # Total device transactions before this time
            cur.execute(
                """
                SELECT COUNT(*)
                FROM raw.transactions
                WHERE device_hash = %s
                  AND timestamp < %s
            """,
                (device_hash, as_of),
            )
            device_count = cur.fetchone()[0] or 0

            # Device first seen by this sender
            cur.execute(
                """
                SELECT COUNT(*)
                FROM raw.transactions
                WHERE device_hash = %s
                  AND sender_account = %s
                  AND timestamp < %s
            """,
                (device_hash, sender_account, as_of),
            )
            sender_device_count = cur.fetchone()[0] or 0

        return {
            "device_transaction_count": device_count,
            "device_first_seen": sender_device_count == 0,
        }

    def get_all_context(
        self,
        sender_account: str,
        merchant_category: str,
        location: str,
        device_hash: str,
        as_of: datetime,
    ) -> dict[str, Any]:
        """Get all historical context in a single call.

        Args:
            sender_account: Sender account identifier.
            merchant_category: Merchant category.
            location: Transaction location.
            device_hash: Device identifier.
            as_of: Temporal cutoff.

        Returns:
            Combined dictionary of all historical context.
        """
        customer = self.get_customer_context(sender_account, as_of)
        velocity = self.get_velocity_context(sender_account, as_of)
        merchant = self.get_merchant_context(merchant_category, as_of)
        location_ctx = self.get_location_context(location, as_of)
        device = self.get_device_context(device_hash, sender_account, as_of)

        return {
            **customer,
            **velocity,
            **merchant,
            **location_ctx,
            **device,
        }
