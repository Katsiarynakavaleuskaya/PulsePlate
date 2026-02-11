"""Deterministic guards for dependency vulnerability floor versions."""

from __future__ import annotations

from pathlib import Path
import re

from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
CRYPTOGRAPHY_MIN_SAFE = Version("46.0.5")


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _extract_version_from_line(content: str, pattern: str, relpath: str) -> Version:
    match = re.search(pattern, content, flags=re.MULTILINE)
    assert match, (
        f"Could not find cryptography version declaration in {relpath}.\n"
        "Fix: keep an explicit cryptography constraint/version in this file."
    )
    return Version(match.group("version"))


def test_cryptography_pinned_files_are_not_vulnerable() -> None:
    """Pinned requirement files must not use vulnerable cryptography versions."""
    pinned_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-lock.txt",
    ]
    pattern = r"^cryptography==(?P<version>[0-9]+\.[0-9]+\.[0-9]+)\s*$"

    violations: list[str] = []
    for relpath in pinned_files:
        current = _extract_version_from_line(_read(relpath), pattern, relpath)
        if current < CRYPTOGRAPHY_MIN_SAFE:
            violations.append(f"{relpath}: cryptography=={current} < {CRYPTOGRAPHY_MIN_SAFE}")

    assert not violations, (
        "Vulnerable cryptography pin detected (CVE-2026-26007 floor).\n"
        + "\n".join(f"- {v}" for v in violations)
        + f"\nFix: bump to cryptography>={CRYPTOGRAPHY_MIN_SAFE} in pinned files."
    )


def test_cryptography_min_constraints_are_not_vulnerable() -> None:
    """Constraint/input files must enforce non-vulnerable minimum versions."""
    min_constraint_files = [
        ("requirements.in", r"^cryptography>=(?P<version>[0-9]+\.[0-9]+\.[0-9]+),<47\.0\.0\s*$"),
        ("constraints.txt", r"^cryptography>=(?P<version>[0-9]+\.[0-9]+\.[0-9]+)\s*$"),
    ]

    violations: list[str] = []
    for relpath, pattern in min_constraint_files:
        current = _extract_version_from_line(_read(relpath), pattern, relpath)
        if current < CRYPTOGRAPHY_MIN_SAFE:
            violations.append(f"{relpath}: cryptography>={current} < {CRYPTOGRAPHY_MIN_SAFE}")

    assert not violations, (
        "Vulnerable cryptography lower-bound detected.\n"
        + "\n".join(f"- {v}" for v in violations)
        + f"\nFix: set lower bound to cryptography>={CRYPTOGRAPHY_MIN_SAFE}."
    )
