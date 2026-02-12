"""Deterministic guards for dependency vulnerability floor versions (schema SSOT)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

import pytest
from packaging.version import InvalidVersion
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "tests" / "fixtures" / "dependency_security_schema.json"

REQUIREMENT_SURFACES = (
    REPO_ROOT / "requirements.in",
    REPO_ROOT / "requirements.txt",
    REPO_ROOT / "requirements-dev.txt",
    REPO_ROOT / "requirements-lock.txt",
    REPO_ROOT / "constraints.txt",
)

# Surfaces that use >= (constraint style); others must use == (pinned).
CONSTRAINT_STYLE_SURFACES = (REPO_ROOT / "requirements.in", REPO_ROOT / "constraints.txt")


def _load_schema(path: Path) -> dict:
    assert path.exists(), f"Missing dependency security schema: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Schema must be a JSON object"
    assert "min_versions" in data and isinstance(
        data["min_versions"], dict
    ), "Schema must contain `min_versions` object"
    return data


def _iter_requirement_lines(path: Path) -> Iterable[str]:
    assert path.exists(), f"Missing requirement surface: {path}"
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ", "-c ", "--constraint ")):
            continue
        if line.startswith(("--find-links", "--index-url", "--extra-index-url")):
            continue
        yield line


_PKG_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def _extract_pinned_version(line: str, package: str) -> Optional[Version]:
    """
    Return Version if this line pins `package` via `==`.
    Non-goals: ranges (>=, ~=) and VCS/URL installs are ignored here.
    """
    m = _PKG_RE.match(line)
    if not m:
        return None
    name = m.group(1)
    if name.lower() != package.lower():
        return None
    if "://" in line or line.startswith(("git+", "hg+", "svn+", "bzr+")):
        return None
    if "==" not in line:
        return None
    left = line.split(";", 1)[0].strip()
    parts = left.split("==", 1)
    if len(parts) != 2:
        return None
    rhs = parts[1].strip().split("#", 1)[0].strip()
    if not rhs:
        return None
    token = rhs.split()[0].strip().rstrip("\\")
    try:
        return Version(token)
    except (InvalidVersion, Exception):
        return None


def _extract_min_constraint_version(line: str, package: str) -> Optional[Version]:
    """Return Version from >= specifier if this line constrains `package` with >=."""
    m = _PKG_RE.match(line)
    if not m:
        return None
    name = m.group(1)
    if name.lower() != package.lower():
        return None
    if ">=" not in line:
        return None
    left = line.split(";", 1)[0].strip()
    # Match >= X (possibly followed by ,< or other)
    match = re.search(r">=\s*([A-Za-z0-9_.]+)", left)
    if not match:
        return None
    token = match.group(1).strip().rstrip(",")
    try:
        return Version(token)
    except (InvalidVersion, Exception):
        return None


def _effective_min_version_in_file(path: Path, package: str) -> Optional[Version]:
    """
    Return the effective minimum version for `package` in this file:
    - Pinned surfaces: min of all == pins.
    - Constraint surfaces: min of all >= (or == if present).
    """
    pinned: list[Version] = []
    constraint: list[Version] = []
    for line in _iter_requirement_lines(path):
        v = _extract_pinned_version(line, package)
        if v is not None:
            pinned.append(v)
        v = _extract_min_constraint_version(line, package)
        if v is not None:
            constraint.append(v)
    if path in CONSTRAINT_STYLE_SURFACES:
        # Constraint file: >= is sufficient; == also counts.
        use = constraint if constraint else pinned
    else:
        # Pinned file: must have ==.
        use = pinned
    if not use:
        return None
    return min(use)


@pytest.mark.parametrize("surface", REQUIREMENT_SURFACES)
def test_dependency_security_guard_enforces_min_versions(surface: Path) -> None:
    """
    Guard: Every requirement surface must pin/constrain each package in schema
    to a version >= the schema minimum.
    """
    schema = _load_schema(SCHEMA_PATH)
    min_versions = schema["min_versions"]

    for pkg, min_v_str in min_versions.items():
        required_min = Version(str(min_v_str))
        effective = _effective_min_version_in_file(surface, pkg)
        assert effective is not None, (
            f"{surface.name}: expected {pkg} to be pinned (==) or constrained (>=) "
            f"(required min {required_min}), but no version was found."
        )
        assert effective >= required_min, (
            f"{surface.name}: {pkg} has {effective}, but minimum safe version is {required_min}. "
            f"Update this surface to at least {required_min}."
        )


def test_dependency_security_schema_is_stable_and_sorted() -> None:
    """Schema must be stable (string keys/values) and keys sorted (diff hygiene)."""
    schema = _load_schema(SCHEMA_PATH)
    min_versions = schema["min_versions"]
    assert all(isinstance(k, str) and k.strip() for k in min_versions.keys())
    assert all(isinstance(v, str) and v.strip() for v in min_versions.values())
    keys = list(min_versions.keys())
    assert keys == sorted(
        keys, key=lambda s: s.lower()
    ), "Schema min_versions keys must be sorted (case-insensitive) to keep diffs clean."
