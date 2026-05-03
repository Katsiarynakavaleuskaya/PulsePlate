"""Shared conftest for tests/evals/.

RU: Путь к корню репо для импорта scripts/evals/*.
EN: Adds repo root to sys.path so scripts.evals.* is importable.

conftest.py is in the import-hygiene allowlist for sys.path.insert.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
