"""Command-line interface for FraudLens data ingestion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fraudlens.ingestion.pipeline import IngestionPipeline, IngestionReport
from fraudlens.ingestion.postgres_loader import DBConfig


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fraudlens-ingest",
        description="FraudLens Phase 1 — Raw data ingestion into PostgreSQL.",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the source CSV file.",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="PostgreSQL connection URL. Falls back to DATABASE_URL env var.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50_000,
        help="Number of rows per ingestion chunk (default: 50000).",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        default=True,
        help="Truncate and re-ingest if table already has data (default: True).",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Refuse to ingest if table already has data.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate schema and print info without loading data.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ingestion CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        return 1

    # Build DB config
    db_config: DBConfig | None = None
    if args.database_url:
        from urllib.parse import urlparse

        parsed = urlparse(args.database_url)
        db_config = DBConfig(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            dbname=(parsed.path or "/fraudlens").lstrip("/"),
            user=parsed.username or "",
            password=parsed.password or "",
        )

    replace = not args.no_replace

    if args.dry_run:
        from fraudlens.ingestion.schema import validate_source_schema

        is_valid, errors = validate_source_schema(input_path)
        if is_valid:
            print("Schema validation: PASS")
            print(f"File: {input_path}")
            print(f"Size: {input_path.stat().st_size / (1024 * 1024):.1f} MB")
        else:
            print("Schema validation: FAIL")
            for e in errors:
                print(f"  - {e}")
            return 1
        return 0

    pipeline = IngestionPipeline(db_config=db_config, chunk_size=args.chunk_size)
    report: IngestionReport = pipeline.run(input_path, replace=replace)
    print(report.format())
    return 0 if report.status == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
