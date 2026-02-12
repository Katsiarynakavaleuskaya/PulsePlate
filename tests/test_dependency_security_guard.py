"""Deterministic guards for dependency vulnerability floor versions (schema SSOT)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

import pytest
from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement
from packaging.specifiers import InvalidSpecifier
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

# Constraint-style (>=) surfaces; derived from REQUIREMENT_SURFACES (no duplicate list).
CONSTRAINT_STYLE_NAMES = frozenset({"requirements.in", "constraints.txt"})
CONSTRAINT_STYLE_SURFACES = frozenset(
    s for s in REQUIREMENT_SURFACES if s.name in CONSTRAINT_STYLE_NAMES
)


def _load_schema(path: Path) -> dict:
    if not path.exists():
        pytest.fail(f"Missing dependency security schema file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        pytest.fail(f"Invalid JSON in dependency security schema {path}: {e}")
    min_versions = data.get("min_versions")
    if not isinstance(min_versions, dict) or not min_versions:
        pytest.fail("Schema must contain non-empty object: { 'min_versions': { ... } }")
    return data


def _iter_requirement_lines(path: Path) -> Iterable[str]:
    if not path.exists():
        pytest.fail(f"Missing requirement surface file: {path}")
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


def _parse_requirement(line: str) -> Optional[Requirement]:
    """
    Return parsed Requirement, or None for non-requirement lines.
    Intentionally ignore editable/URL/VCS installs for this guard.
    """
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if s.startswith(("-r ", "--requirement", "-c ", "--constraint")):
        return None
    if "://" in s or s.startswith(("-e ", "--editable", "git+", "hg+", "svn+", "bzr+")):
        return None
    try:
        return Requirement(s)
    except (InvalidRequirement, InvalidSpecifier):
        return None


def _min_version_for_pkg(req: Requirement, pkg: str, *, pinned: bool) -> Optional[str]:
    if req.name.lower() != pkg.lower():
        return None
    if pinned:
        equals = [sp.version for sp in req.specifier if sp.operator == "=="]
        return equals[0] if equals else None
    floors = [sp.version for sp in req.specifier if sp.operator in (">=", "==")]
    if not floors:
        return None
    return min(floors, key=lambda v: Version(v))


def _effective_min_version_in_file(path: Path, package: str) -> Optional[Version]:
    """
    Return the effective minimum version for `package` in this file:
    - Pinned surfaces: min of all == pins.
    - Constraint surfaces: min of all >= (or == if present).
    """
    pinned = path not in CONSTRAINT_STYLE_SURFACES
    versions: list[Version] = []
    for line in _iter_requirement_lines(path):
        req = _parse_requirement(line)
        if req is None:
            continue
        v_str = _min_version_for_pkg(req, package, pinned=pinned)
        if v_str is not None:
            versions.append(Version(v_str))
    return min(versions) if versions else None


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
        if effective is None:
            pytest.fail(
                f"{surface.name}: expected {pkg} to be pinned (==) or constrained (>=) "
                f"(required min {required_min}), but no version was found."
            )
        if effective < required_min:
            pytest.fail(
                f"{surface.name}: {pkg} has {effective}, but minimum safe version is {required_min}. "
                f"Update this surface to at least {required_min}."
            )


def test_constraint_surface_effective_min_includes_pins(tmp_path: Path) -> None:
    """
    Regression: constraint-style surface effective min must include both >= and ==.
    A file with both cryptography>=46.0.5 and cryptography==3.4.8 must yield
    effective min 3.4.8 so the guard fails (low pin cannot bypass).
    """
    fake_constraints = tmp_path / "constraints.txt"
    fake_constraints.write_text(
        "cryptography>=46.0.5\ncryptography==3.4.8\n",
        encoding="utf-8",
    )
    effective = _effective_min_version_in_file(fake_constraints, "cryptography")
    assert effective is not None
    assert effective == Version(
        "3.4.8"
    ), "Constraint surface must take min over all lines; lower == must not be ignored."
    required_min = Version("46.0.5")
    assert effective < required_min, "Guard should fail when a lower pin exists."


def test_dependency_security_schema_is_stable_and_sorted() -> None:
    """Schema must be stable (string keys/values) and keys sorted (diff hygiene)."""
    schema = _load_schema(SCHEMA_PATH)
    min_versions = schema["min_versions"]
    if not all(isinstance(k, str) and k.strip() for k in min_versions.keys()):
        pytest.fail("Schema min_versions keys must be non-empty strings.")
    if not all(isinstance(v, str) and v.strip() for v in min_versions.values()):
        pytest.fail("Schema min_versions values must be non-empty strings.")
    keys = list(min_versions.keys())
    if keys != sorted(keys, key=lambda s: s.lower()):
        pytest.fail(
            "Schema min_versions keys must be sorted (case-insensitive) to keep diffs clean."
        )
