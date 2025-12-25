"""Guard test to prevent sys.path.insert from returning to tests.

This ensures import hygiene standards are maintained.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Allowed exceptions - tests that intentionally load non-package scripts
EXCEPTIONS = {
    "test_test_pro_access_coverage.py",  # tests standalone script test_pro_access.py
    "test_ensure_database_versions.py",  # tests scripts/ensure_database_versions.py
    "test_import_hygiene_guard.py",  # this guard test itself contains the pattern in strings
    "test_repo_policy_guards.py",  # guard test checks for patterns as strings
}


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_no_sys_path_insert_in_tests() -> None:
    """Ensure no test files use sys.path.insert except allowed exceptions."""
    offenders: list[str] = []
    tests_dir = Path(__file__).parent

    for p in tests_dir.rglob("*.py"):
        if p.name in EXCEPTIONS:
            continue
        try:
            content = p.read_text(encoding="utf-8")
            if "sys.path.insert" in content:
                offenders.append(str(p.relative_to(tests_dir)))
        except (OSError, UnicodeDecodeError):
            continue

    assert not offenders, (
        f"sys.path.insert found in {len(offenders)} files "
        "(use standard imports like 'import app.services.X as X'):\n"
        + "\n".join(f"  - {f}" for f in sorted(offenders))
    )
