"""Allow running the ingestion module with ``python -m fraudlens.ingestion``."""

from fraudlens.ingestion.cli import main

raise SystemExit(main())
