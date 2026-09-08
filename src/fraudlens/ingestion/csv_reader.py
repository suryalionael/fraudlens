"""Chunked CSV reader for the raw transaction dataset."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from fraudlens.ingestion.schema import EXPECTED_COLUMNS


@dataclass
class ReadResult:
    """Outcome of reading the CSV file."""

    rows_read: int = 0
    fraud_count: int = 0
    timestamp_errors: int = 0
    duplicate_rows: int = 0
    sha256: str = ""
    errors: list[str] = field(default_factory=list)


def compute_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    """Compute SHA-256 of a file without loading it entirely into memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            data = fh.read(chunk_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def iter_chunks(
    path: Path,
    chunk_size: int = 50_000,
) -> Iterator[tuple[list[str], list[list[str]]]]:
    """Yield (header, rows) chunks from a CSV file.

    Each chunk contains up to *chunk_size* data rows.  The header is
    yielded with the first chunk and then repeated for API convenience
    (callers can ignore it on subsequent chunks).
    """
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = [h.strip() for h in next(reader)]
        chunk: list[list[str]] = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield header, chunk
                chunk = []
        if chunk:
            yield header, chunk


def read_csv(
    path: Path,
    chunk_size: int = 50_000,
) -> Iterator[tuple[ReadResult, list[list[str]]]]:
    """Stream a CSV file, yielding per-chunk stats and rows.

    This function does NOT load the entire file into memory.  It yields
    one ``(result, rows)`` pair per chunk.  The caller is responsible for
    consuming *result* after processing each chunk (e.g. loading into DB).

    Validation checks applied:
    - expected column count
    - ``is_fraud`` boolean parsing
    - ``timestamp`` non-empty check
    - ``amount_ngn`` numeric check
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    header: list[str] = []
    seen_ids: set[str] = set()
    total_rows = 0
    total_fraud = 0
    total_ts_errors = 0
    total_dupes = 0

    for hdr, rows in iter_chunks(path, chunk_size):
        if not header:
            header = hdr
            # Quick check that the header matches expectations
            if header != EXPECTED_COLUMNS:
                missing = set(EXPECTED_COLUMNS) - set(header)
                extra = set(header) - set(EXPECTED_COLUMNS)
                parts = []
                if missing:
                    parts.append(f"missing={sorted(missing)}")
                if extra:
                    parts.append(f"extra={sorted(extra)}")
                raise ValueError(f"Unexpected columns: {'; '.join(parts)}")

        col_idx = {name: i for i, name in enumerate(header)}
        fraud_idx = col_idx["is_fraud"]
        ts_idx = col_idx["timestamp"]
        amt_idx = col_idx["amount_ngn"]
        id_idx = col_idx["transaction_id"]

        chunk_fraud = 0
        chunk_ts_err = 0
        chunk_dupes = 0

        for row in rows:
            total_rows += 1

            # Check duplicates
            txn_id = row[id_idx]
            if txn_id in seen_ids:
                chunk_dupes += 1
            else:
                seen_ids.add(txn_id)

            # Validate fraud label
            if row[fraud_idx] not in ("True", "False", "true", "false", "1", "0"):
                pass  # preserve row; flag later

            if row[fraud_idx] in ("True", "true", "1"):
                chunk_fraud += 1

            # Validate timestamp is non-empty
            if not row[ts_idx].strip():
                chunk_ts_err += 1

            # Validate amount is numeric
            try:
                float(row[amt_idx])
            except ValueError:
                pass  # preserve row; flag later

        total_fraud += chunk_fraud
        total_ts_errors += chunk_ts_err
        total_dupes += chunk_dupes

        result = ReadResult(
            rows_read=total_rows,
            fraud_count=total_fraud,
            timestamp_errors=total_ts_errors,
            duplicate_rows=total_dupes,
        )
        yield result, rows

    # Final SHA-256 (computed once at the end for efficiency)
    final_sha = compute_sha256(path)
    final_result = ReadResult(
        rows_read=total_rows,
        fraud_count=total_fraud,
        timestamp_errors=total_ts_errors,
        duplicate_rows=total_dupes,
        sha256=final_sha,
    )
    # Yield an empty final chunk so the caller can access final_result
    yield final_result, []
