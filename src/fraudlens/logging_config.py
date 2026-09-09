"""Structured logging configuration for FraudLens.

Provides consistent logging across all modules.
Configurable via FRAUDLENS_LOG_LEVEL environment variable.
"""

from __future__ import annotations

import logging
import os
import sys


def configure_logging(level: str | None = None) -> None:
    """Configure FraudLens logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR). If None, uses env var.
    """
    if level is None:
        level = os.environ.get("FRAUDLENS_LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, level, logging.INFO)

    # Root logger for the project
    root_logger = logging.getLogger("fraudlens")
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler with structured format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Propagate to child loggers
    root_logger.propagate = False

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("psycopg2").setLevel(logging.WARNING)
    logging.getLogger("streamlit").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a FraudLens module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
