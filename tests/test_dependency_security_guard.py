"""Deterministic guards for dependency vulnerability floor versions."""

from __future__ import annotations

from pathlib import Path
import re

from packaging.requirements import Requirement
from packaging.version import InvalidVersion
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
CRYPTOGRAPHY_MIN_SAFE = Version("46.0.5")


def _read(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _iter_cryptography_requirements(content: str, relpath: str) -> list[tuple[int, Requirement]]:
    """Return all parsable cryptography requirements found in file content."""
    requirements: list[tuple[int, Requirement]] = []
    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        # Support inline comments and requirement markers while ignoring blank/comment lines.
        line = re.sub(r"\s+#.*$", "", raw_line).strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "--", "-c ")):
            continue
        try:
            requirement = Requirement(line)
        except Exception:
            continue
        if requirement.name.lower() == "cryptography":
            requirements.append((line_no, requirement))

    assert requirements, (
        f"Could not find cryptography requirement declaration(s) in {relpath}.\n"
        "Fix: keep explicit cryptography constraint/version entries in this file."
    )
    return requirements


def _specifier_versions(
    requirement: Requirement,
    operator: str,
    relpath: str,
    line_no: int,
) -> list[Version]:
    """Extract typed versions for specifiers with a given operator."""
    versions: list[Version] = []
    for specifier in requirement.specifier:
        if specifier.operator != operator:
            continue
        try:
            versions.append(Version(specifier.version))
        except InvalidVersion:
            continue
    assert versions, (
        f"{relpath}:{line_no} has cryptography without '{operator}' specifier.\n"
        f"Found: {requirement}\n"
        "Fix: declare explicit, parseable version bounds for cryptography."
    )
    return versions


def test_cryptography_pinned_files_are_not_vulnerable() -> None:
    """Pinned requirement files must not use vulnerable cryptography versions."""
    pinned_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-lock.txt",
    ]
    violations: list[str] = []
    for relpath in pinned_files:
        for line_no, requirement in _iter_cryptography_requirements(_read(relpath), relpath):
            for current in _specifier_versions(requirement, "==", relpath, line_no):
                if current < CRYPTOGRAPHY_MIN_SAFE:
                    violations.append(
                        f"{relpath}:{line_no}: cryptography=={current} < {CRYPTOGRAPHY_MIN_SAFE}"
                    )

    assert not violations, (
        "Vulnerable cryptography pin detected (CVE-2026-26007 floor).\n"
        + "\n".join(f"- {v}" for v in violations)
        + f"\nFix: bump to cryptography>={CRYPTOGRAPHY_MIN_SAFE} in pinned files."
    )


def test_cryptography_min_constraints_are_not_vulnerable() -> None:
    """Constraint/input files must enforce non-vulnerable minimum versions."""
    min_constraint_files = [
        "requirements.in",
        "constraints.txt",
    ]

    violations: list[str] = []
    for relpath in min_constraint_files:
        for line_no, requirement in _iter_cryptography_requirements(_read(relpath), relpath):
            for current in _specifier_versions(requirement, ">=", relpath, line_no):
                if current < CRYPTOGRAPHY_MIN_SAFE:
                    violations.append(
                        f"{relpath}:{line_no}: cryptography>={current} < {CRYPTOGRAPHY_MIN_SAFE}"
                    )

    assert not violations, (
        "Vulnerable cryptography lower-bound detected.\n"
        + "\n".join(f"- {v}" for v in violations)
        + f"\nFix: set lower bound to cryptography>={CRYPTOGRAPHY_MIN_SAFE}."
    )
