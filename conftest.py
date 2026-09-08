"""Pytest configuration — add src/ to sys.path so tests can import fraudlens."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to the Python path so `import fraudlens` works in tests.
sys.path.insert(0, str(Path(__file__).parent / "src"))
