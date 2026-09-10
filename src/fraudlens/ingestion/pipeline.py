"""Ingestion pipeline — orchestrates CSV reading, validation, and PostgreSQL loading."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from fraudlens.ingestion.csv_reader import read_csv
from fraudlens.ingestion.postgres_loader import DBConfig, PostgresLoader
from fraudlens.ingestion.schema import validate_source_schema


@dataclass
class IngestionReport:
    """Summary of a completed ingestion run."""

    source_file: str = ""
    source_sha256: str = ""
    rows_read: int = 0
    rows_loaded: int = 0
    fraud_count: int = 0
    fraud_rate: float = 0.0
    timestamp_errors: int = 0
    duplicate_rows: int = 0
    elapsed_seconds: float = 0.0
    status: str = "pending"
    ingestion_run_id: int | None = None
    errors: list[str] = field(default_factory=list)

    def format(self) -> str:
        """Return a human-readable report string."""
        lines = [
            "",
            "FraudLens Data Ingestion",
            "\u2500" * 40,
            "",
            f"Source: {self.source_file}",
            "",
            f"Rows read:       {self.rows_read:>12,}",
            f"Rows loaded:     {self.rows_loaded:>12,}",
            f"Fraud rows:      {self.fraud_count:>12,}",
            f"Fraud rate:      {self.fraud_rate:>11.4f}%",
            "",
            f"Timestamp errors: {self.timestamp_errors:>11,}",
            f"Duplicate rows:   {self.duplicate_rows:>11,}",
            "",
            f"Elapsed:         {self.elapsed_seconds:>11.1f}s",
            f"Status:          {self.status:>11}",
        ]
        if self.errors:
            lines.append("")
            lines.append("Errors:")
            for e in self.errors:
                lines.append(f"  - {e}")
        lines.append("")
        return "\n".join(lines)


class IngestionPipeline:
    """End-to-end ingestion: validate source, create run, load chunks, finalize."""

    def __init__(
        self,
        db_config: DBConfig | None = None,
        chunk_size: int = 50_000,
    ) -> None:
        self.loader = PostgresLoader(db_config)
        self.chunk_size = chunk_size

    def run(
        self,
        input_path: str | Path,
        replace: bool = True,
    ) -> IngestionReport:
        """Execute the full ingestion pipeline.

        Args:
            input_path: Path to the source CSV file.
            replace: If True, truncate raw.transactions before loading.
                     If False and the table already has rows, the pipeline
                     will refuse to run (idempotency guard).

        Returns:
            IngestionReport with all statistics.
        """
        report = IngestionReport()
        input_path = Path(input_path)
        report.source_file = str(input_path)
        start = time.time()

        # --- Step 1: Validate source schema ---
        print("Step 1/5: Validating source schema...")
        is_valid, errors = validate_source_schema(input_path)
        if not is_valid:
            report.errors.extend(errors)
            report.status = "FAILED_SCHEMA"
            report.elapsed_seconds = time.time() - start
            return report

        # --- Step 2: Create schema and tables ---
        print("Step 2/5: Creating database schema...")
        self.loader.create_schema_and_tables()

        # --- Step 3: Handle idempotency ---
        existing_count = self.loader.count_transactions()
        if existing_count > 0 and not replace:
            report.status = "FAILED_IDEMPOTENCY"
            report.errors.append(
                f"Table raw.transactions has {existing_count:,} rows. "
                "Use replace=True to truncate and re-ingest."
            )
            report.elapsed_seconds = time.time() - start
            return report

        if existing_count > 0 and replace:
            print(f"  Truncating existing data ({existing_count:,} rows)...")
            self.loader.truncate_transactions()

        # --- Step 4: Create ingestion run and load chunks ---
        print("Step 3/5: Computing SHA-256 checksum...")
        # Compute SHA-256 first (streaming, doesn't load full file)
        from fraudlens.ingestion.csv_reader import compute_sha256

        sha256 = compute_sha256(input_path)
        report.source_sha256 = sha256

        print("Step 4/5: Loading data chunks...")
        run_id = self.loader.insert_ingestion_run(
            source_name="Nigerian Financial Transactions and Fraud Detection Dataset",
            source_version="V1",
            source_file=str(input_path),
            source_sha256=sha256,
        )
        report.ingestion_run_id = run_id

        total_loaded = 0
        for result, rows in read_csv(input_path, chunk_size=self.chunk_size):
            if rows:
                loaded = self.loader.bulk_insert(
                    header=[
                        "transaction_id",
                        "timestamp",
                        "sender_account",
                        "receiver_account",
                        "transaction_type",
                        "merchant_category",
                        "location",
                        "device_used",
                        "is_fraud",
                        "fraud_type",
                        "time_since_last_transaction",
                        "spending_deviation_score",
                        "velocity_score",
                        "geo_anomaly_score",
                        "payment_channel",
                        "ip_address",
                        "device_hash",
                        "amount_ngn",
                        "bvn_linked",
                        "new_device_transaction",
                        "sender_persona",
                    ],
                    rows=rows,
                )
                total_loaded += loaded
                # Print progress every 10 chunks
                if (total_loaded // self.chunk_size) % 10 == 0:
                    print(f"  Loaded {total_loaded:,} rows...")

            # Update report from latest result
            report.rows_read = result.rows_read
            report.fraud_count = result.fraud_count
            report.timestamp_errors = result.timestamp_errors
            report.duplicate_rows = result.duplicate_rows
            report.source_sha256 = result.sha256 or report.source_sha256

        report.rows_loaded = total_loaded
        if report.rows_read > 0:
            report.fraud_rate = (report.fraud_count / report.rows_read) * 100

        # --- Step 5: Finalize ingestion run ---
        print("Step 5/5: Finalizing ingestion run...")
        self.loader.update_ingestion_run(
            run_id,
            rows_read=report.rows_read,
            rows_loaded=report.rows_loaded,
            fraud_count=report.fraud_count,
            fraud_rate=report.fraud_rate,
            status="SUCCESS",
        )

        # Verify loaded count
        actual_count = self.loader.count_transactions()
        if actual_count != report.rows_loaded:
            report.errors.append(
                f"Row count mismatch: loaded {report.rows_loaded:,} "
                f"but DB has {actual_count:,}"
            )
            report.status = "PARTIAL"
        else:
            report.status = "SUCCESS"

        report.elapsed_seconds = time.time() - start
        return report
