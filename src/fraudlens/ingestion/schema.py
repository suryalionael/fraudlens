"""Source dataset schema definition and validation."""

from __future__ import annotations

import csv
from pathlib import Path

# Expected columns from the validated V1 dataset (21 columns).
# See data/dataset_metadata.yml for the authoritative field list.
EXPECTED_COLUMNS: list[str] = [
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
]

# Columns that the raw ingestion preserves but are NOT trusted features.
# They are ingested faithfully for provenance but must not be used as-is
# for modeling.  See data/dataset_metadata.yml for the leakage audit.
UNTRUSTED_COLUMNS: list[str] = [
    "new_device_transaction",  # leakage — 100% fraud correlation
    "time_since_last_transaction",  # broken — 41 % negative values
    "velocity_score",  # no predictive signal
    "geo_anomaly_score",  # no predictive signal
    "spending_deviation_score",  # very weak / no signal
]


def validate_source_schema(path: Path) -> tuple[bool, list[str]]:
    """Validate that a CSV file has the expected schema.

    Returns (is_valid, errors) where errors is a list of human-readable
    problem descriptions.  An empty list means the schema is valid.
    """
    errors: list[str] = []

    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            header = next(reader)
    except FileNotFoundError:
        return False, [f"File not found: {path}"]
    except csv.Error as exc:
        return False, [f"Failed to read CSV header: {exc}"]

    # Strip whitespace and compare case-sensitively
    header_clean = [h.strip() for h in header]

    missing = set(EXPECTED_COLUMNS) - set(header_clean)
    if missing:
        errors.append(f"Missing columns: {sorted(missing)}")

    extra = set(header_clean) - set(EXPECTED_COLUMNS)
    if extra:
        errors.append(f"Unexpected columns (preserved but flagged): {sorted(extra)}")

    if len(header_clean) != len(set(header_clean)):
        dupes = [c for c in header_clean if header_clean.count(c) > 1]
        errors.append(f"Duplicate column names: {sorted(set(dupes))}")

    return len(errors) == 0, errors
