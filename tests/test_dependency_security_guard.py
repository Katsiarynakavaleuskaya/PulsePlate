"""Deterministic guards for dependency vulnerability floor versions (schema SSOT)."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from fnmatch import fnmatch
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional

import pytest
from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement
from packaging.specifiers import InvalidSpecifier
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "tests" / "fixtures" / "dependency_security_schema.json"
ADMISSION_DOC_PATH = REPO_ROOT / "docs" / "security" / "CRYPTOGRAPHY_50_0_0_ADVISORY_CLUSTER.md"
SNAPSHOT_START = "<!-- dependency-remediation-admission-v1-snapshot:start -->"
SNAPSHOT_END = "<!-- dependency-remediation-admission-v1-snapshot:end -->"
SNAPSHOT_ALLOWLIST_LINE = "<!-- pragma: allowlist nextline secret -->"
SNAPSHOT_KIND = "dependency-remediation-admission-v1-evidence"
SNAPSHOT_CUTOFF = "2026-08-04T10:18:11Z"
SNAPSHOT_TARGET = "50.0.0"

REQUIREMENT_SURFACES = (
    REPO_ROOT / "requirements.in",
    REPO_ROOT / "requirements-docker-runtime.in",
    REPO_ROOT / "requirements-ci-lite.in",
    REPO_ROOT / "requirements-dev.in",
    REPO_ROOT / "requirements.txt",
    REPO_ROOT / "requirements-docker-runtime.txt",
    REPO_ROOT / "requirements-dev.txt",
    REPO_ROOT / "requirements-lock.txt",
    REPO_ROOT / "requirements-ci-lite.txt",
    REPO_ROOT / "constraints.txt",
)

CRYPTOGRAPHY_REMEDIATION_BASE = (
    "643eb78d01476835523a3e800f1e88cb36f0aa8f"  # pragma: allowlist secret
)
CRYPTOGRAPHY_REMEDIATION_REPLAY_WITNESS = (
    "5383a5bfe5c81eb5b9f07699dd67983d09118882"  # pragma: allowlist secret
)
CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES = (
    "requirements.in",
    "requirements-docker-runtime.in",
    "requirements-ci-lite.in",
    "requirements-dev.in",
    "constraints.txt",
    "requirements.txt",
    "requirements-docker-runtime.txt",
    "requirements-ci-lite.txt",
    "requirements-dev.txt",
    "requirements-lock.txt",
)
CRYPTOGRAPHY_INTENT_SURFACES = frozenset(CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES[:5])
CRYPTOGRAPHY_COMPILED_SURFACES = frozenset(CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES[5:])
CRYPTOGRAPHY_F_CUTOFF = {
    "GHSA-m2h6-j472-rp4c": ">=0,<49.0.0",
    "GHSA-g6cj-pr64-35w5": ">=44.0.0,<50.0.0",
    "GHSA-jwv3-5hgf-82ww": ">=0,<49.0.0",
}

CURRENT_ENFORCED_RUNTIME_FLOORS = {
    "click": "8.3.3",
    "cryptography": "50.0.0",
    "pillow": "12.3.0",
    "python-multipart": "0.0.31",
    "setuptools": "83.0.0",
    "starlette": "1.3.1",
}

CURRENT_BLOCKED_VERSION_SPECIFIERS = {
    "python-multipart": "<0.0.31",
    "setuptools": "<83.0.0",
}

PIP_DIRECTIVE_PREFIXES = (
    "-i ",
    "--index-url ",
    "--extra-index-url ",
    "-f ",
    "--find-links ",
    "-r ",
    "--requirement ",
    "-c ",
    "--constraint ",
)

URL_VCS_EDITABLE_PREFIXES = (
    "-e ",
    "--editable ",
    "git+",
    "hg+",
    "svn+",
    "bzr+",
)
PIP_DIRECTIVE_SEMANTIC_CARRIER = "__pip_directive__"


def _is_constraint_style(path: Path) -> bool:
    """Constraint-style (>=) by filename for source/constraint requirement surfaces."""
    return path.name in {
        "requirements.in",
        "requirements-ci-lite.in",
        "requirements-docker-runtime.in",
        "requirements-dev.in",
    } or path.name.startswith("constraints")


def _normalized_package_name(package_name: str) -> str:
    """PEP 503-style canonical package names keep guard comparisons stable."""
    return canonicalize_name(package_name)


def _is_pip_directive_line(line: str) -> bool:
    """Return True for pip option lines that are not package requirements."""
    return line.startswith(PIP_DIRECTIVE_PREFIXES)


def _is_url_vcs_editable_requirement(line: str) -> bool:
    """Return True for direct URL, VCS, or editable requirement entries."""
    return "://" in line or line.startswith(URL_VCS_EDITABLE_PREFIXES)


def _load_schema(path: Path) -> dict:
    if not path.exists():
        pytest.fail(f"Missing dependency security schema file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        pytest.fail(f"Invalid JSON in dependency security schema {path}: {e}")
    if not isinstance(data, dict):
        pytest.fail("Schema root must be a JSON object.")
    min_versions = data.get("min_versions")
    if not isinstance(min_versions, dict) or not min_versions:
        pytest.fail("Schema must contain non-empty object: { 'min_versions': { ... } }")
    for pkg, v_str in min_versions.items():
        if not isinstance(v_str, str) or not v_str.strip():
            pytest.fail(f"Schema: {pkg!r} has invalid version string: {v_str!r}")
        try:
            Version(v_str)
        except InvalidVersion as e:
            pytest.fail(f"Schema: {pkg!r} has unparseable version {v_str!r}: {e}")
    # Validate optional blocked_packages field
    _validate_blocked_packages(data)
    # Validate optional blocked_versions field
    _validate_blocked_versions(data)
    return data


def _validate_blocked_packages(data: dict) -> None:
    """Validate blocked_packages is list[str] if present."""
    blocked_packages = data.get("blocked_packages")
    if blocked_packages is None:
        return
    if not isinstance(blocked_packages, list):
        pytest.fail("Schema: 'blocked_packages' must be a list.")
    for i, pkg in enumerate(blocked_packages):
        if not isinstance(pkg, str) or not pkg.strip():
            pytest.fail(f"Schema: blocked_packages[{i}] must be a non-empty string.")


def _validate_blocked_versions(data: dict) -> None:
    """Validate blocked_versions is dict[str, list[str]] with parseable specifiers."""
    blocked_versions = data.get("blocked_versions")
    if blocked_versions is None:
        return
    if not isinstance(blocked_versions, dict):
        pytest.fail("Schema: 'blocked_versions' must be a dict.")
    for pkg, specifiers in blocked_versions.items():
        if not isinstance(pkg, str) or not pkg.strip():
            pytest.fail(f"Schema: blocked_versions key must be a non-empty string: {pkg!r}")
        if not isinstance(specifiers, list):
            pytest.fail(f"Schema: blocked_versions[{pkg!r}] must be a list of specifiers.")
        for i, spec_str in enumerate(specifiers):
            if not isinstance(spec_str, str) or not spec_str.strip():
                pytest.fail(f"Schema: blocked_versions[{pkg!r}][{i}] must be a non-empty string.")
            try:
                SpecifierSet(spec_str)
            except InvalidSpecifier as e:
                pytest.fail(
                    f"Schema: blocked_versions[{pkg!r}][{i}] has unparseable specifier "
                    f"{spec_str!r}: {e}"
                )


def _iter_requirement_lines(path: Path) -> Iterable[str]:
    if not path.exists():
        pytest.fail(f"Missing requirement surface file: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        # Keep trailing-comment requirements valid: `pkg>=1.2.3  # note`
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if _is_pip_directive_line(line):
            continue
        yield line


def _parse_requirement(line: str, path: Optional[Path] = None) -> Optional[Requirement]:
    """
    Return parsed Requirement, or None for non-requirement lines.
    If path is given and line looks like a requirement but fails to parse, fail-fast.
    Inline comments are stripped in _iter_requirement_lines before lines are yielded.
    """
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if _is_pip_directive_line(s):
        return None
    if _is_url_vcs_editable_requirement(s):
        if path is not None:
            pytest.fail(
                f"{path.name}: URL/VCS/editable requirement entries are not allowed in "
                "dependency guard surfaces. Use pinned/constraint package specifiers instead."
            )
        return None
    try:
        return Requirement(s)
    except (InvalidRequirement, InvalidSpecifier) as e:
        if path is not None:
            pytest.fail(f"{path.name}: Invalid requirement syntax: {line!r}\nError: {e}")
        return None


def _min_version_for_pkg(req: Requirement, pkg: str, *, pinned: bool) -> Optional[str]:
    if _normalized_package_name(req.name) != _normalized_package_name(pkg):
        return None
    if pinned:
        equals = [sp.version for sp in req.specifier if sp.operator == "=="]
        return min(equals, key=lambda v: Version(v)) if equals else None
    floors = [sp.version for sp in req.specifier if sp.operator in (">=", "==")]
    if not floors:
        return None
    return min(floors, key=lambda v: Version(v))


def _effective_min_version_in_file(path: Path, package: str) -> Optional[Version]:
    """
    Return the effective minimum version for `package` in this file.
    Pinned surfaces: min of == pins. Constraint surfaces: min of >= and ==.
    """
    pinned = not _is_constraint_style(path)
    versions: list[Version] = []
    for line in _iter_requirement_lines(path):
        req = _parse_requirement(line, path)
        if req is None:
            continue
        v_str = _min_version_for_pkg(req, package, pinned=pinned)
        if v_str is not None:
            versions.append(Version(v_str))
    return min(versions) if versions else None


def _requirement_evidence_per_package(
    path: Path,
) -> tuple[dict[str, Version], dict[str, tuple[Requirement, ...]]]:
    """Parse once; return effective minima and every complete requirement carrier."""
    pinned = not _is_constraint_style(path)
    by_pkg: dict[str, list[Version]] = {}
    carriers: dict[str, list[Requirement]] = {}
    for line in _iter_requirement_lines(path):
        req = _parse_requirement(line, path)
        if req is None:
            continue
        normalized_name = _normalized_package_name(req.name)
        carriers.setdefault(normalized_name, []).append(req)
        v_str = _min_version_for_pkg(req, req.name, pinned=pinned)
        if v_str is not None:
            by_pkg.setdefault(normalized_name, []).append(Version(v_str))
    minima = {pkg: min(versions) for pkg, versions in by_pkg.items()}
    return minima, {pkg: tuple(requirements) for pkg, requirements in carriers.items()}


def _effective_min_versions_per_package(path: Path) -> dict[str, Version]:
    """Return normalized package name -> effective min version."""
    minima, _carriers = _requirement_evidence_per_package(path)
    return minima


def _pinned_versions_per_package(path: Path) -> dict[str, set[Version]]:
    """Parse file once; return every pinned version by normalized package name."""
    by_pkg: dict[str, set[Version]] = {}
    for line in _iter_requirement_lines(path):
        req = _parse_requirement(line, path)
        if req is None:
            continue
        pins = {Version(sp.version) for sp in req.specifier if sp.operator == "=="}
        if pins:
            by_pkg.setdefault(_normalized_package_name(req.name), set()).update(pins)
    return by_pkg


def _packages_present_in_file(path: Path) -> set[str]:
    """Parse file once; return normalized package names present in this surface."""
    packages: set[str] = set()
    for line in _iter_requirement_lines(path):
        req = _parse_requirement(line, path)
        if req is None:
            continue
        packages.add(_normalized_package_name(req.name))
    return packages


def _git_command(arguments: list[str]) -> str:
    """Run git through its resolved absolute executable for finite admission evidence."""
    git = shutil.which("git")
    if git is None:
        pytest.fail("dependency-remediation admission requires an available git executable")
    result = subprocess.run(
        [git, *arguments],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        pytest.fail(
            f"dependency-remediation admission git command failed: {' '.join(arguments)}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout


def _snapshot_introduction_revision() -> str:
    """Locate the unique reachable commit that introduced the owner snapshot marker."""
    owner_path = ADMISSION_DOC_PATH.relative_to(REPO_ROOT).as_posix()
    revisions = [
        line
        for line in _git_command(
            [
                "log",
                f"-S{SNAPSHOT_START}",
                "--format=%H",
                f"{CRYPTOGRAPHY_REMEDIATION_BASE}..HEAD",
                "--",
                owner_path,
            ]
        ).splitlines()
        if line
    ]
    assert (
        len(revisions) == 1
    ), "snapshot marker must have exactly one reachable introduction revision"
    revision = revisions[0]
    assert len(revision) == 40 and all(
        character in "0123456789abcdef" for character in revision
    ), "snapshot introduction revision must be a lowercase 40-hex Git object"
    return revision


def _discover_cryptography_surfaces(revision: str) -> dict[str, str]:
    """Mechanically discover every top-level tracked requirement surface with cryptography."""
    candidates = _git_command(["ls-tree", "-r", "--name-only", revision]).splitlines()
    discovered: dict[str, str] = {}
    for name in candidates:
        if Path(name).parent != Path(".") or not (
            fnmatch(name, "requirements*.in")
            or fnmatch(name, "requirements*.txt")
            or name == "constraints.txt"
        ):
            continue
        text = _git_command(["show", f"{revision}:{name}"])
        occurrences = _cryptography_versions_from_text(name, text)
        if not occurrences:
            continue
        assert len(occurrences) == 1, f"{name}: duplicate cryptography occurrences are forbidden"
        discovered[name] = text
    assert discovered, f"{revision}: no tracked cryptography requirement surfaces discovered"
    return discovered


def _cryptography_versions_from_text(surface_name: str, text: str) -> list[Version]:
    """Return every cryptography floor/pin so absence and duplication stay distinct."""
    path = REPO_ROOT / surface_name
    versions: list[Version] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or _is_pip_directive_line(line):
            continue
        req = _parse_requirement(line, path)
        if req is None or _normalized_package_name(req.name) != "cryptography":
            continue
        version = _min_version_for_pkg(req, "cryptography", pinned=not _is_constraint_style(path))
        assert (
            version is not None
        ), f"{surface_name}: cryptography occurrence must declare a comparable >= or == version"
        versions.append(Version(version))
    return versions


def _cryptography_version_from_text(surface_name: str, text: str) -> Version:
    """Return the one governed cryptography floor/pin for a surface snapshot."""
    versions = _cryptography_versions_from_text(surface_name, text)
    assert len(versions) == 1, f"{surface_name}: expected exactly one cryptography occurrence"
    return versions[0]


def _semantic_requirements(text: str, path: Path) -> dict[str, tuple[str, ...]]:
    """Compare requirement/directive meaning, ignoring comments and lockfile relocation."""
    parsed: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if _is_pip_directive_line(line):
            parsed.setdefault(PIP_DIRECTIVE_SEMANTIC_CARRIER, []).append(line)
            continue
        req = _parse_requirement(line, path)
        if req is not None:
            extras = ",".join(sorted(canonicalize_name(extra) for extra in req.extras))
            marker = str(req.marker) if req.marker is not None else ""
            parsed.setdefault(_normalized_package_name(req.name), []).append(
                "|".join((extras, str(req.specifier), marker, req.url or ""))
            )
    return {name: tuple(sorted(specifiers)) for name, specifiers in parsed.items()}


def _semantic_sha256(text: str, path: Path) -> str:
    """Hash normalized requirement meaning, independent of line relocation."""
    canonical = json.dumps(
        _semantic_requirements(text, path),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_selected_target(
    surface_name: str,
    surface_class: str,
    requirement_text: str,
    target_text: str,
) -> Version:
    """Validate the package, full target membership, and compiled exact pin."""
    requirement = Requirement(requirement_text)
    assert (
        _normalized_package_name(requirement.name) == "cryptography"
    ), f"{surface_name}: snapshot requirement must name cryptography"
    assert not requirement.extras, f"{surface_name}: snapshot requirement must not declare extras"
    assert requirement.marker is None, f"{surface_name}: snapshot requirement must not use a marker"
    assert (
        requirement.url is None
    ), f"{surface_name}: snapshot requirement must not use a direct URL"
    target = Version(target_text)
    assert (
        target in requirement.specifier
    ), f"{surface_name}: selected target {target} must be contained by recorded requirement"
    specifiers = tuple(requirement.specifier)
    if surface_class == "I_R":
        expected_operators = {">="} if surface_name == "constraints.txt" else {">=", "<"}
        assert (
            len(specifiers) == len(expected_operators)
            and {specifier.operator for specifier in specifiers} == expected_operators
        ), f"{surface_name}: intent snapshot must preserve the canonical range operation kind"
    elif surface_class == "C_R":
        assert (
            len(specifiers) == 1
            and specifiers[0].operator == "=="
            and specifiers[0].version == target_text
        ), f"{surface_name}: compiled snapshot must contain exactly one =={target} pin"
    return target


def _is_lowercase_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _load_admission_snapshot(document: str) -> dict:
    assert document.count(SNAPSHOT_START) == 1, "snapshot must have exactly one start marker"
    assert document.count(SNAPSHOT_END) == 1, "snapshot must have exactly one end marker"
    start = document.index(SNAPSHOT_START)
    end = document.index(SNAPSHOT_END)
    assert start < end, "snapshot markers must appear in start/end order"
    payload_lines = document[start + len(SNAPSHOT_START) : end].strip().splitlines()
    assert (
        len(payload_lines) == 2 and payload_lines[0] == SNAPSHOT_ALLOWLIST_LINE
    ), "snapshot markers must contain exactly one allowlist line and one JSON object line"
    try:
        snapshot = json.loads(payload_lines[1])
    except json.JSONDecodeError as exc:
        pytest.fail(f"invalid dependency-remediation admission snapshot: {exc}")
    assert isinstance(snapshot, dict), "snapshot JSON root must be an object"
    assert set(snapshot) == {
        "advisories",
        "base",
        "cutoff",
        "snapshot_kind",
        "surfaces",
        "target",
    }, "snapshot top-level keys must match the v1 contract exactly"
    assert snapshot["snapshot_kind"] == SNAPSHOT_KIND
    assert snapshot["base"] == CRYPTOGRAPHY_REMEDIATION_BASE
    assert snapshot["cutoff"] == SNAPSHOT_CUTOFF
    assert snapshot["target"] == SNAPSHOT_TARGET
    assert snapshot["advisories"] == CRYPTOGRAPHY_F_CUTOFF
    surfaces = snapshot["surfaces"]
    assert isinstance(surfaces, dict), "snapshot surfaces must be an object"
    assert set(surfaces) == set(
        CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES
    ), "snapshot must contain exactly the ten governed surfaces"
    for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES:
        record = surfaces[name]
        assert isinstance(record, dict), f"{name}: snapshot record must be an object"
        expected_record_keys = {
            "class",
            "requirement",
            "semantic_sha256",
        }
        expected_class = "I_R" if name in CRYPTOGRAPHY_INTENT_SURFACES else "C_R"
        if expected_class == "C_R":
            expected_record_keys.add("file_sha256")
        assert (
            set(record) == expected_record_keys
        ), f"{name}: snapshot record keys must match its v1 class exactly"
        assert record["class"] == expected_class, f"{name}: snapshot class mismatch"
        assert (
            isinstance(record["requirement"], str) and record["requirement"].strip()
        ), f"{name}: snapshot requirement must be non-empty"
        _validate_selected_target(
            name,
            expected_class,
            record["requirement"],
            snapshot["target"],
        )
        assert _is_lowercase_sha256(
            record["semantic_sha256"]
        ), f"{name}: semantic_sha256 must be a lowercase 64-hex digest"
        if expected_class == "C_R":
            assert _is_lowercase_sha256(
                record["file_sha256"]
            ), f"{name}: file_sha256 must be a lowercase 64-hex digest"
    return snapshot


def _historical_snapshot_evidence() -> tuple[dict, dict[str, str], dict[str, str]]:
    snapshot_revision = _snapshot_introduction_revision()
    owner_path = ADMISSION_DOC_PATH.relative_to(REPO_ROOT).as_posix()
    snapshot_document = _git_command(["show", f"{snapshot_revision}:{owner_path}"])
    snapshot = _load_admission_snapshot(snapshot_document)
    base_texts = _discover_cryptography_surfaces(CRYPTOGRAPHY_REMEDIATION_BASE)
    head_texts = _discover_cryptography_surfaces(snapshot_revision)
    return snapshot, base_texts, head_texts


def _immutable_replay_witness_evidence() -> tuple[str, str, dict[str, str]]:
    """Open the immutable replay commit and its current-head reachability proof."""
    parent_record = _git_command(
        ["rev-list", "--parents", "-n", "1", CRYPTOGRAPHY_REMEDIATION_REPLAY_WITNESS]
    ).strip()
    merge_base = _git_command(
        ["merge-base", CRYPTOGRAPHY_REMEDIATION_REPLAY_WITNESS, "HEAD"]
    ).strip()
    replay_texts = _discover_cryptography_surfaces(CRYPTOGRAPHY_REMEDIATION_REPLAY_WITNESS)
    return parent_record, merge_base, replay_texts


def _derive_material_transitions(
    base_texts: dict[str, str], head_texts: dict[str, str]
) -> dict[str, str]:
    """Classify actual semantic transitions; only the floor may change."""
    assert set(base_texts) == set(head_texts), "base/head surface union must reconcile exactly"
    transitions: dict[str, str] = {}
    for name in sorted(base_texts):
        base_semantics = _semantic_requirements(base_texts[name], REPO_ROOT / name)
        head_semantics = _semantic_requirements(head_texts[name], REPO_ROOT / name)
        changed = {
            package
            for package in set(base_semantics) | set(head_semantics)
            if base_semantics.get(package) != head_semantics.get(package)
        }
        assert changed == {"cryptography"}, f"{name}: unrelated semantic transition: {changed}"
        transitions[name] = "I_R" if name in CRYPTOGRAPHY_INTENT_SURFACES else "C_R"
    return transitions


def _assert_immutable_replay_witness(
    *,
    parent_record: str,
    merge_base: str,
    base_texts: dict[str, str],
    replay_texts: dict[str, str],
    frozen_head_texts: dict[str, str],
) -> None:
    """Fail closed unless replay proves the exact I_R/C_R remediation transition."""
    assert parent_record.split() == [
        CRYPTOGRAPHY_REMEDIATION_REPLAY_WITNESS,
        CRYPTOGRAPHY_REMEDIATION_BASE,
    ], "immutable replay witness must have the exact remediation base as its sole parent"
    assert (
        merge_base == CRYPTOGRAPHY_REMEDIATION_REPLAY_WITNESS
    ), "immutable replay witness must remain an ancestor of HEAD"

    expected_classes = {
        **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
        **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
    }
    assert CRYPTOGRAPHY_INTENT_SURFACES.isdisjoint(
        CRYPTOGRAPHY_COMPILED_SURFACES
    ), "I_R and C_R must remain a disjoint partition"
    assert set(expected_classes) == set(
        CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES
    ), "I_R/C_R partition must equal the ten governed surfaces"
    for evidence_class, surface_texts in (
        ("S_base", base_texts),
        ("S_replay", replay_texts),
        ("S_head", frozen_head_texts),
    ):
        assert set(surface_texts) == set(
            expected_classes
        ), f"{evidence_class} must mechanically enumerate all ten governed surfaces"

    transitions = _derive_material_transitions(base_texts, replay_texts)
    assert (
        transitions == expected_classes
    ), "base/replay transitions must preserve the exact I_R/C_R partition"

    for name in sorted(CRYPTOGRAPHY_INTENT_SURFACES):
        replay_carrier = _semantic_requirements(replay_texts[name], REPO_ROOT / name).get(
            "cryptography"
        )
        frozen_head_carrier = _semantic_requirements(frozen_head_texts[name], REPO_ROOT / name).get(
            "cryptography"
        )
        assert replay_carrier is not None, f"{name}: replay cryptography carrier is missing"
        assert (
            replay_carrier == frozen_head_carrier
        ), f"{name}: replay I_R carrier differs from frozen S_head"

    for name in sorted(CRYPTOGRAPHY_COMPILED_SURFACES):
        replay_bytes = replay_texts[name].encode("utf-8")
        frozen_head_bytes = frozen_head_texts[name].encode("utf-8")
        assert (
            replay_bytes == frozen_head_bytes
        ), f"{name}: replay C_R lock bytes differ from frozen S_head"


def _assert_snapshot_receipts(snapshot: dict, head_texts: dict[str, str]) -> None:
    """Bind independent S_head inventory, meaning, and C_R bytes to its snapshot."""
    declared_surfaces = CRYPTOGRAPHY_INTENT_SURFACES | CRYPTOGRAPHY_COMPILED_SURFACES
    assert CRYPTOGRAPHY_INTENT_SURFACES.isdisjoint(
        CRYPTOGRAPHY_COMPILED_SURFACES
    ), "I_R and C_R must remain a disjoint partition"
    snapshot_surfaces = set(snapshot["surfaces"])
    assert (
        snapshot_surfaces == declared_surfaces
    ), "snapshot inventory must equal the declared I_R/C_R partition"
    assert (
        set(head_texts) == snapshot_surfaces
    ), "independently discovered S_head inventory must equal the owner snapshot"
    for name in sorted(snapshot_surfaces):
        text = head_texts[name]
        record = snapshot["surfaces"][name]
        surface_path = REPO_ROOT / name
        actual_carrier = _semantic_requirements(text, surface_path).get("cryptography")
        recorded_carrier = _semantic_requirements(record["requirement"], surface_path).get(
            "cryptography"
        )
        assert (
            actual_carrier == recorded_carrier
        ), f"{name}: cryptography carrier semantics mismatch"
        semantic_hash = _semantic_sha256(text, surface_path)
        assert (
            semantic_hash == record["semantic_sha256"]
        ), f"{name}: snapshot semantic receipt mismatch"
        if record["class"] == "C_R":
            file_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            assert file_hash == record["file_sha256"], f"{name}: compiled replay receipt mismatch"


def _historical_admission_inputs() -> tuple[
    dict,
    dict[str, Version],
    dict[str, Version],
    dict[str, str],
]:
    """Build immutable admission inputs without reading live requirement surfaces."""
    historical_snapshot, base_texts, head_texts = _historical_snapshot_evidence()
    snapshot = _load_admission_snapshot(ADMISSION_DOC_PATH.read_text(encoding="utf-8"))
    assert (
        snapshot == historical_snapshot
    ), "current owner snapshot must equal its immutable introduction evidence"
    declared_surfaces = CRYPTOGRAPHY_INTENT_SURFACES | CRYPTOGRAPHY_COMPILED_SURFACES
    base_surfaces = set(base_texts)
    head_surfaces = set(head_texts)
    assert base_surfaces | head_surfaces == declared_surfaces, "S_base/S_head union drifted"
    assert not base_surfaces ^ head_surfaces, "S_base/S_head topology deltas are forbidden"
    _assert_snapshot_receipts(snapshot, head_texts)
    parent_record, merge_base, replay_texts = _immutable_replay_witness_evidence()
    _assert_immutable_replay_witness(
        parent_record=parent_record,
        merge_base=merge_base,
        base_texts=base_texts,
        replay_texts=replay_texts,
        frozen_head_texts=head_texts,
    )
    base_occurrences = {
        name: _cryptography_version_from_text(name, text) for name, text in base_texts.items()
    }
    head_occurrences = {
        name: _cryptography_version_from_text(name, text) for name, text in head_texts.items()
    }
    transitions = _derive_material_transitions(base_texts, head_texts)
    return snapshot, base_occurrences, head_occurrences, transitions


def _assert_cryptography_remediation_admission(
    *,
    base_occurrences: dict[str, Version],
    head_occurrences: dict[str, Version],
    advisories: dict[str, str],
    material_transitions: dict[str, str],
) -> None:
    """Fail closed unless the finite remediation evidence has an exact partition."""
    expected_surfaces = set(CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES)
    assert (
        set(base_occurrences) == expected_surfaces
    ), "S_base must enumerate every governed surface"
    assert (
        set(head_occurrences) == expected_surfaces
    ), "S_head must enumerate every governed surface"
    assert set(advisories) == set(
        CRYPTOGRAPHY_F_CUTOFF
    ), "F_cutoff advisory set drifted or is incomplete"
    assert all(
        version == Version("48.0.1") for version in base_occurrences.values()
    ), "S_base witnesses must all report the pre-remediation 48.0.1 version"
    affected = {
        advisory
        for advisory, affected_range in advisories.items()
        if any(
            str(version) in SpecifierSet(affected_range) for version in base_occurrences.values()
        )
    }
    assert affected == set(
        CRYPTOGRAPHY_F_CUTOFF
    ), "A must contain every advisory with an affected OSV/pip-audit base witness"
    assert all(
        version >= Version("50.0.0") for version in head_occurrences.values()
    ), "P requires every head witness to meet the 50.0.0 floor"
    assert all(
        str(version) not in SpecifierSet(affected_range)
        for version in head_occurrences.values()
        for affected_range in advisories.values()
    ), "P requires every head witness to clear every frozen advisory"
    expected_transitions = {
        **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
        **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
    }
    assert (
        material_transitions == expected_transitions
    ), "material transitions must partition into I_R or C_R"


def _validate_live_cryptography_intent_carrier(
    surface: Path,
    carriers: tuple[Requirement, ...],
    required_min: Version,
) -> None:
    """Keep live I_R in one schema-derived operation class."""
    if len(carriers) != 1:
        pytest.fail(f"{surface.name}: cryptography I_R must contain exactly one carrier")
    requirement = carriers[0]
    if requirement.extras:
        pytest.fail(f"{surface.name}: cryptography I_R must not declare extras")
    if requirement.url is not None:
        pytest.fail(f"{surface.name}: cryptography I_R must not use a direct URL")

    expected_specifiers = {(">=", required_min)}
    if surface.name != "constraints.txt":
        expected_specifiers.add(("<", Version(f"{required_min.major + 1}.0.0")))
    specifiers = tuple(requirement.specifier)
    actual_specifiers = {
        (specifier.operator, Version(specifier.version)) for specifier in specifiers
    }
    if len(specifiers) != len(expected_specifiers) or actual_specifiers != expected_specifiers:
        pytest.fail(
            f"{surface.name}: cryptography I_R must preserve the canonical " "schema-driven range"
        )


@pytest.mark.parametrize("surface", REQUIREMENT_SURFACES)
def test_dependency_security_guard_enforces_min_versions(surface: Path) -> None:
    """
    Guard: Every requirement surface must pin/constrain each package in schema
    to a version >= the schema minimum. Parses each file once (O(1) reads).
    """
    schema = _load_schema(SCHEMA_PATH)
    min_versions = schema["min_versions"]
    pinned = not _is_constraint_style(surface)
    all_reqs, carriers = _requirement_evidence_per_package(surface)

    for pkg, min_v_str in min_versions.items():
        required_min = Version(str(min_v_str))
        normalized_name = _normalized_package_name(pkg)
        effective = all_reqs.get(normalized_name)
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
        if normalized_name not in CURRENT_ENFORCED_RUNTIME_FLOORS:
            continue
        package_carriers = carriers[normalized_name]
        if pinned and len(package_carriers) != 1:
            pytest.fail(
                f"{surface.name}: {pkg} security-floor lock must contain exactly one carrier."
            )
        for requirement in package_carriers:
            if requirement.marker is not None:
                pytest.fail(
                    f"{surface.name}: {pkg} security-floor requirement must be unconditional; "
                    f"marker {requirement.marker!s} is not allowed."
                )
            version_to_check = required_min
            version_label = "required safe floor"
            if pinned:
                specifiers = tuple(requirement.specifier)
                if len(specifiers) != 1 or specifiers[0].operator != "==":
                    pytest.fail(
                        f"{surface.name}: {pkg} security-floor lock carrier must contain "
                        "exactly one == pin."
                    )
                version_to_check = Version(specifiers[0].version)
                version_label = "pinned version"
            if not requirement.specifier.contains(str(version_to_check), prereleases=True):
                pytest.fail(
                    f"{surface.name}: {pkg} requirement {requirement.specifier!s} excludes "
                    f"{version_label} {version_to_check}."
                )

    if surface.name in CRYPTOGRAPHY_INTENT_SURFACES:
        _validate_live_cryptography_intent_carrier(
            surface,
            carriers.get("cryptography", ()),
            Version(str(min_versions["cryptography"])),
        )


def test_constraint_surface_effective_min_includes_pins(tmp_path: Path) -> None:
    """
    Regression: constraint-style surface effective min must include both >= and ==.
    A file with both cryptography>=50.0.0 and cryptography==3.4.8 must yield
    effective min 3.4.8 so the guard fails (low pin cannot bypass).
    """
    fake_constraints = tmp_path / "constraints.txt"
    fake_constraints.write_text(
        "cryptography>=50.0.0\ncryptography==3.4.8\n",
        encoding="utf-8",
    )
    effective = _effective_min_version_in_file(fake_constraints, "cryptography")
    assert effective is not None
    assert effective == Version(
        "3.4.8"
    ), "Constraint surface must take min over all lines; lower == must not be ignored."
    required_min = Version("50.0.0")
    assert effective < required_min, "Guard should fail when a lower pin exists."


def test_dependency_security_guard_rejects_former_cryptography_floor(
    tmp_path: Path,
) -> None:
    """The actual all-min guard rejects a complete surface still pinned to 48.0.1."""

    schema = _load_schema(SCHEMA_PATH)
    former_surface = tmp_path / "requirements.txt"
    former_surface.write_text(
        "\n".join(
            f"{package}=={'48.0.1' if package == 'cryptography' else version}"
            for package, version in schema["min_versions"].items()
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        pytest.fail.Exception,
        match=(
            r"requirements\.txt: cryptography has 48\.0\.1, but minimum safe "
            r"version is 50\.0\.0"
        ),
    ):
        test_dependency_security_guard_enforces_min_versions(former_surface)


@pytest.mark.parametrize(
    ("cryptography_carriers", "expected_error"),
    [
        (
            ("cryptography>=50.0.0,!=50.0.0,<51.0.0",),
            r"cryptography requirement .* excludes required safe floor 50\.0\.0",
        ),
        (
            ('cryptography>=50.0.0; python_version < "0"',),
            r"cryptography security-floor requirement must be unconditional",
        ),
        (
            ("cryptography==50.0.0",),
            r"cryptography I_R must preserve the canonical schema-driven range",
        ),
        (
            ("cryptography[ssh]>=50.0.0,<51.0.0",),
            r"cryptography I_R must not declare extras",
        ),
        (
            (
                "cryptography>=50.0.0,<51.0.0",
                "cryptography>=50.0.0,<51.0.0",
            ),
            r"cryptography I_R must contain exactly one carrier",
        ),
        (
            ("cryptography>=50.0.0,<52.0.0",),
            r"cryptography I_R must preserve the canonical schema-driven range",
        ),
    ],
    ids=[
        "selected-floor-excluded",
        "inactive-marker",
        "exact-pin-is-not-source-intent",
        "extra-is-not-source-intent",
        "duplicate-canonical-carriers",
        "non-next-major-upper-bound",
    ],
)
def test_dependency_security_guard_rejects_noncanonical_live_floor_carrier(
    tmp_path: Path,
    cryptography_carriers: tuple[str, ...],
    expected_error: str,
) -> None:
    """The live all-surfaces path validates the complete floor carrier."""

    schema = _load_schema(SCHEMA_PATH)
    source_surface = tmp_path / "requirements.in"
    source_surface.write_text(
        "\n".join(
            [
                f"{package}>={version}"
                for package, version in schema["min_versions"].items()
                if package != "cryptography"
            ]
            + list(cryptography_carriers)
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(pytest.fail.Exception, match=expected_error):
        test_dependency_security_guard_enforces_min_versions(source_surface)


@pytest.mark.parametrize(
    ("surface_name", "cryptography_carrier"),
    (
        ("requirements.in", "cryptography>=50.0.1,<51.0.0"),
        ("constraints.txt", "cryptography>=50.0.1"),
    ),
)
def test_dependency_security_guard_allows_schema_driven_live_floor_rotation(
    surface_name: str,
    cryptography_carrier: str,
) -> None:
    """Live carrier truth may rotate without rewriting historical admission evidence."""
    _validate_live_cryptography_intent_carrier(
        Path(surface_name),
        (Requirement(cryptography_carrier),),
        Version("50.0.1"),
    )


@pytest.mark.parametrize(
    ("cryptography_carriers", "expected_error"),
    [
        (("cryptography==50.0.1",), None),
        (
            ("cryptography>=50.0.0,==50.0.1",),
            r"cryptography security-floor lock carrier must contain exactly one == pin",
        ),
        (
            ("cryptography==50.0.1", "cryptography==50.0.2"),
            r"cryptography security-floor lock must contain exactly one carrier",
        ),
    ],
    ids=["above-floor-pin", "hybrid-carrier", "conflicting-duplicate-pins"],
)
def test_dependency_security_guard_enforces_live_lock_carrier_class(
    tmp_path: Path,
    cryptography_carriers: tuple[str, ...],
    expected_error: str | None,
) -> None:
    """Live C_R permits a higher pin but rejects hybrid or conflicting carriers."""
    schema = _load_schema(SCHEMA_PATH)
    lock_surface = tmp_path / "requirements.txt"
    lock_surface.write_text(
        "\n".join(
            [
                f"{package}=={version}"
                for package, version in schema["min_versions"].items()
                if package != "cryptography"
            ]
            + list(cryptography_carriers)
        )
        + "\n",
        encoding="utf-8",
    )

    if expected_error is None:
        test_dependency_security_guard_enforces_min_versions(lock_surface)
    else:
        with pytest.raises(pytest.fail.Exception, match=expected_error):
            test_dependency_security_guard_enforces_min_versions(lock_surface)


def test_cryptography_50_dependency_remediation_admission_is_exact_and_replayable() -> None:
    """Admission v1 closes the base/head/advisory transition proof over ten surfaces."""
    _git_command(["merge-base", "--is-ancestor", CRYPTOGRAPHY_REMEDIATION_BASE, "HEAD"])
    snapshot, base_occurrences, head_occurrences, transitions = _historical_admission_inputs()
    _assert_cryptography_remediation_admission(
        base_occurrences=base_occurrences,
        head_occurrences=head_occurrences,
        advisories=snapshot["advisories"],
        material_transitions=transitions,
    )

    assert base_occurrences == {
        name: Version("48.0.1") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES
    }
    assert head_occurrences == {
        name: Version("50.0.0") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES
    }
    owner_document = ADMISSION_DOC_PATH.read_text(encoding="utf-8")
    for receipt in (
        CRYPTOGRAPHY_REMEDIATION_BASE,
        SNAPSHOT_CUTOFF,
        "5383a5bfe5c81eb5b9f07699dd67983d09118882",  # pragma: allowlist secret
        "GHSA-m2h6-j472-rp4c",
        "GHSA-g6cj-pr64-35w5",
        "GHSA-jwv3-5hgf-82ww",
        ">=0,<49.0.0",
        ">=44.0.0,<50.0.0",
        "I_R={requirements.in",
        "C_R={requirements.txt",
    ):
        assert receipt in owner_document, f"owner evidence receipt missing: {receipt}"


def test_cryptography_50_admission_rejects_duplicate_surface_occurrence() -> None:
    with pytest.raises(AssertionError, match="expected exactly one cryptography occurrence"):
        _cryptography_version_from_text(
            "requirements.txt", "cryptography==50.0.0\ncryptography==50.0.0\n"
        )


def test_cryptography_50_admission_rejects_unversioned_surface_occurrence() -> None:
    with pytest.raises(AssertionError, match="must declare a comparable"):
        _cryptography_versions_from_text("requirements.in", "cryptography\n")


def test_cryptography_50_admission_rejects_unrelated_semantic_transition() -> None:
    _, base_texts, head_texts = _historical_snapshot_evidence()
    head_texts["requirements.txt"] = head_texts["requirements.txt"].replace(
        "click==8.3.3", "click==8.3.4", 1
    )
    with pytest.raises(AssertionError, match="unrelated semantic transition"):
        _derive_material_transitions(base_texts, head_texts)


@pytest.mark.parametrize(
    "directive",
    (
        "--extra-index-url https://pypi.org/simple",
        "--find-links https://example.invalid/wheels",
    ),
)
def test_cryptography_50_admission_rejects_changed_pip_directive(directive: str) -> None:
    _, base_texts, head_texts = _historical_snapshot_evidence()
    head_texts["requirements.in"] = f"{head_texts['requirements.in']}\n{directive}\n"
    with pytest.raises(AssertionError, match="unrelated semantic transition"):
        _derive_material_transitions(base_texts, head_texts)


@pytest.mark.parametrize(
    ("before", "after"),
    (
        ("psycopg[binary]>=3.2.3", "psycopg>=3.2.3"),
        ('click>=8.3.3; python_version >= "3.12"', 'click>=8.3.3; python_version < "3.12"'),
    ),
)
def test_cryptography_50_admission_rejects_changed_requirement_semantics(
    before: str, after: str
) -> None:
    _, base_texts, head_texts = _historical_snapshot_evidence()
    head_texts["requirements.in"] = f"{head_texts['requirements.in']}\n{after}\n"
    base_texts["requirements.in"] = f"{base_texts['requirements.in']}\n{before}\n"
    with pytest.raises(AssertionError, match="unrelated semantic transition"):
        _derive_material_transitions(base_texts, head_texts)


def test_cryptography_50_admission_rejects_unreplayable_compiled_lock() -> None:
    loaded_snapshot, _, head_texts = _historical_snapshot_evidence()
    snapshot = deepcopy(loaded_snapshot)
    snapshot["surfaces"]["requirements.txt"]["file_sha256"] = "0" * 64
    with pytest.raises(AssertionError, match="compiled replay receipt mismatch"):
        _assert_snapshot_receipts(snapshot, head_texts)


def test_cryptography_50_admission_rejects_current_owner_snapshot_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical_snapshot, base_texts, head_texts = _historical_snapshot_evidence()
    owner_document = ADMISSION_DOC_PATH.read_text(encoding="utf-8")
    recorded_hash = historical_snapshot["surfaces"]["requirements.txt"]["file_sha256"]
    drifted_owner = tmp_path / ADMISSION_DOC_PATH.name
    drifted_owner.write_text(owner_document.replace(recorded_hash, "0" * 64, 1), encoding="utf-8")
    monkeypatch.setitem(
        _historical_admission_inputs.__globals__,
        "_historical_snapshot_evidence",
        lambda: (historical_snapshot, base_texts, head_texts),
    )
    monkeypatch.setitem(
        _historical_admission_inputs.__globals__,
        "ADMISSION_DOC_PATH",
        drifted_owner,
    )

    with pytest.raises(AssertionError, match="current owner snapshot must equal"):
        _historical_admission_inputs()


def test_cryptography_50_admission_rejects_snapshot_head_inventory_drift() -> None:
    snapshot, _, head_texts = _historical_snapshot_evidence()
    renamed_head_texts = dict(head_texts)
    renamed_head_texts["renamed-requirements.txt"] = renamed_head_texts.pop("requirements.txt")
    with pytest.raises(AssertionError, match="independently discovered S_head inventory"):
        _assert_snapshot_receipts(snapshot, renamed_head_texts)


@pytest.mark.parametrize(
    ("surface_name", "surface_class", "replacement"),
    (
        (
            "requirements.in",
            "I_R",
            'cryptography>=50.0.0,<51.0.0; python_version >= "0"',
        ),
        (
            "requirements.txt",
            "C_R",
            "cryptography[ssh]==50.0.0",
        ),
    ),
)
def test_cryptography_50_admission_rejects_carrier_semantics_mismatch(
    surface_name: str,
    surface_class: str,
    replacement: str,
) -> None:
    loaded_snapshot, _, loaded_head_texts = _historical_snapshot_evidence()
    snapshot = deepcopy(loaded_snapshot)
    head_texts = dict(loaded_head_texts)
    record = snapshot["surfaces"][surface_name]
    assert record["class"] == surface_class
    assert head_texts[surface_name].count(record["requirement"]) == 1
    head_texts[surface_name] = head_texts[surface_name].replace(
        record["requirement"], replacement, 1
    )
    record["semantic_sha256"] = _semantic_sha256(head_texts[surface_name], REPO_ROOT / surface_name)
    if surface_class == "C_R":
        record["file_sha256"] = hashlib.sha256(head_texts[surface_name].encode("utf-8")).hexdigest()
    with pytest.raises(AssertionError, match="cryptography carrier semantics mismatch"):
        _assert_snapshot_receipts(snapshot, head_texts)


@pytest.mark.parametrize(
    ("failure_mode", "expected_message"),
    (
        ("parent", "exact remediation base as its sole parent"),
        ("reachability", "must remain an ancestor of HEAD"),
        ("transition", "unrelated semantic transition"),
        ("lock_bytes", "replay C_R lock bytes differ from frozen S_head"),
    ),
)
def test_cryptography_50_immutable_replay_witness_fails_closed(
    failure_mode: str,
    expected_message: str,
) -> None:
    _, base_texts, frozen_head_texts = _historical_snapshot_evidence()
    parent_record, merge_base, loaded_replay_texts = _immutable_replay_witness_evidence()
    replay_texts = dict(loaded_replay_texts)

    if failure_mode == "parent":
        parent_record = f"{parent_record} {'0' * 40}"
    elif failure_mode == "reachability":
        merge_base = CRYPTOGRAPHY_REMEDIATION_BASE
    elif failure_mode == "transition":
        replay_texts["requirements.in"] = replay_texts["requirements.in"].replace(
            "click>=8.3.3,<9.0.0", "click>=8.3.4,<9.0.0", 1
        )
    elif failure_mode == "lock_bytes":
        replay_texts["requirements.txt"] += "# replay-byte-drift\n"
    else:
        raise AssertionError(f"unsupported replay-witness failure mode: {failure_mode}")

    with pytest.raises(AssertionError, match=expected_message):
        _assert_immutable_replay_witness(
            parent_record=parent_record,
            merge_base=merge_base,
            base_texts=base_texts,
            replay_texts=replay_texts,
            frozen_head_texts=frozen_head_texts,
        )


def test_cryptography_50_admission_reports_noncanonical_base_witness() -> None:
    base_occurrences = {name: Version("48.0.1") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES}
    base_occurrences["requirements.txt"] = Version("48.0.0")
    head_occurrences = {name: Version("50.0.0") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES}
    transitions = {
        **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
        **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
    }
    with pytest.raises(
        AssertionError,
        match="S_base witnesses must all report the pre-remediation 48.0.1 version",
    ):
        _assert_cryptography_remediation_admission(
            base_occurrences=base_occurrences,
            head_occurrences=head_occurrences,
            advisories=CRYPTOGRAPHY_F_CUTOFF,
            material_transitions=transitions,
        )


@pytest.mark.parametrize(
    "requirement_text",
    (
        "cryptography>=50.0.0,<50.0.0",
        "cryptography>=50.0.0,!=50.0.0,<51.0.0",
    ),
)
def test_cryptography_50_admission_rejects_selected_target_exclusion(
    requirement_text: str,
) -> None:
    with pytest.raises(
        AssertionError,
        match="selected target 50.0.0 must be contained by recorded requirement",
    ):
        _validate_selected_target(
            "requirements.in",
            "I_R",
            requirement_text,
            "50.0.0",
        )


def test_cryptography_50_admission_rejects_pinned_intent_operation() -> None:
    with pytest.raises(AssertionError, match="canonical range operation kind"):
        _validate_selected_target(
            "requirements.in",
            "I_R",
            "cryptography==50.0.0",
            "50.0.0",
        )


def test_cryptography_50_admission_rejects_nonexact_compiled_target_pin() -> None:
    with pytest.raises(AssertionError, match="must contain exactly one ==50.0.0 pin"):
        _validate_selected_target(
            "requirements.txt",
            "C_R",
            "cryptography>=50.0.0,<51.0.0",
            "50.0.0",
        )


@pytest.mark.parametrize(
    ("surface_class", "requirement_text", "message"),
    (
        (
            "I_R",
            'cryptography>=50.0.0,<51.0.0; python_version < "0"',
            "must not use a marker",
        ),
        (
            "C_R",
            'cryptography==50.0.0; python_version < "0"',
            "must not use a marker",
        ),
        (
            "I_R",
            "cryptography @ https://example.invalid/cryptography-50.0.0.whl",
            "must not use a direct URL",
        ),
        (
            "I_R",
            "cryptography[ssh]>=50.0.0,<51.0.0",
            "must not declare extras",
        ),
    ),
)
def test_cryptography_50_admission_rejects_noncanonical_requirement_carrier(
    surface_class: str,
    requirement_text: str,
    message: str,
) -> None:
    with pytest.raises(AssertionError, match=message):
        _validate_selected_target(
            "requirements.in",
            surface_class,
            requirement_text,
            "50.0.0",
        )


def test_cryptography_50_historical_snapshot_is_independent_of_future_live_rotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(CURRENT_ENFORCED_RUNTIME_FLOORS, "cryptography", "50.0.1")
    assert CURRENT_ENFORCED_RUNTIME_FLOORS["cryptography"] == "50.0.1"
    snapshot, base_occurrences, head_occurrences, transitions = _historical_admission_inputs()
    assert snapshot["target"] == "50.0.0"
    assert all(version == Version("50.0.0") for version in head_occurrences.values())
    assert all(
        version < Version(CURRENT_ENFORCED_RUNTIME_FLOORS["cryptography"])
        for version in head_occurrences.values()
    )
    assert transitions == {
        **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
        **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
    }
    _assert_cryptography_remediation_admission(
        base_occurrences=base_occurrences,
        head_occurrences=head_occurrences,
        advisories=snapshot["advisories"],
        material_transitions=transitions,
    )


@pytest.mark.parametrize(
    ("base_occurrences", "head_occurrences", "advisories", "transitions", "message"),
    [
        (
            {name: Version("48.0.1") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES[1:]},
            {name: Version("50.0.0") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES},
            CRYPTOGRAPHY_F_CUTOFF,
            {
                **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
                **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
            },
            "S_base",
        ),
        (
            {name: Version("48.0.1") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES},
            {name: Version("50.0.0") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES},
            {"GHSA-g6cj-pr64-35w5": ">=44.0.0,<50.0.0"},
            {
                **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
                **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
            },
            "F_cutoff",
        ),
        (
            {name: Version("48.0.1") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES},
            {name: Version("48.0.1") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES},
            CRYPTOGRAPHY_F_CUTOFF,
            {
                **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
                **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
            },
            "P requires",
        ),
        (
            {name: Version("48.0.1") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES},
            {name: Version("50.0.0") for name in CRYPTOGRAPHY_GOVERNED_SURFACE_NAMES},
            CRYPTOGRAPHY_F_CUTOFF,
            {
                **{name: "I_R" for name in CRYPTOGRAPHY_INTENT_SURFACES},
                **{name: "C_R" for name in CRYPTOGRAPHY_COMPILED_SURFACES},
                "manual.txt": "manual",
            },
            "partition",
        ),
    ],
)
def test_cryptography_50_admission_rejects_incomplete_or_unsafe_evidence(
    base_occurrences: dict[str, Version],
    head_occurrences: dict[str, Version],
    advisories: dict[str, str],
    transitions: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(AssertionError, match=message):
        _assert_cryptography_remediation_admission(
            base_occurrences=base_occurrences,
            head_occurrences=head_occurrences,
            advisories=advisories,
            material_transitions=transitions,
        )


def test_load_schema_fails_on_invalid_version(tmp_path: Path) -> None:
    """Schema loader must fail if a version string is unparseable."""
    bad_schema = tmp_path / "schema.json"
    bad_schema.write_text(
        '{"min_versions": {"cryptography": "46..0.5"}}',
        encoding="utf-8",
    )
    with pytest.raises(BaseException, match="unparseable version"):
        _load_schema(bad_schema)


def test_parse_requirement_fails_on_invalid_syntax(tmp_path: Path) -> None:
    """Guard must fail-fast if a requirements file has invalid requirement syntax."""
    bad_req = tmp_path / "requirements.txt"
    bad_req.write_text("cryptography==46..0.5\n", encoding="utf-8")
    with pytest.raises(BaseException, match="Invalid requirement syntax"):
        _effective_min_versions_per_package(bad_req)


@pytest.mark.parametrize(
    "requirement_line",
    [
        "cryptography @ https://example.com/cryptography-3.4.8-py3-none-any.whl",
        "git+https://example.com/acme/cryptography.git",
        "-e git+https://example.com/acme/cryptography.git#egg=cryptography",
        "--editable git+https://example.com/acme/cryptography.git#egg=cryptography",
    ],
)
def test_parse_requirement_fails_on_url_vcs_or_editable_requirement(
    tmp_path: Path, requirement_line: str
) -> None:
    """Guard must fail-fast if a requirements file contains URL/VCS/editable entry."""
    bad_req = tmp_path / "requirements.txt"
    bad_req.write_text(
        f"{requirement_line}\n",
        encoding="utf-8",
    )
    with pytest.raises(
        pytest.fail.Exception,
        match=r"requirements\.txt: URL/VCS/editable requirement entries are not allowed",
    ):
        _effective_min_versions_per_package(bad_req)


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
    # Validate blocked_packages is sorted (if present)
    blocked_packages = schema.get("blocked_packages", [])
    if blocked_packages:
        if blocked_packages != sorted(blocked_packages, key=lambda s: s.lower()):
            pytest.fail(
                "Schema blocked_packages must be sorted (case-insensitive) to keep diffs clean."
            )
    # Validate blocked_versions keys are sorted (if present)
    blocked_versions = schema.get("blocked_versions", {})
    if blocked_versions:
        bv_keys = list(blocked_versions.keys())
        if bv_keys != sorted(bv_keys, key=lambda s: s.lower()):
            pytest.fail(
                "Schema blocked_versions keys must be sorted (case-insensitive) "
                "to keep diffs clean."
            )
        # Validate each blocked_versions value list is sorted
        for pkg, specifiers in blocked_versions.items():
            if specifiers != sorted(specifiers):
                pytest.fail(
                    f"Schema blocked_versions[{pkg!r}] specifiers must be sorted "
                    "to keep diffs clean."
                )


def test_dependency_security_schema_tracks_current_enforced_runtime_floors() -> None:
    """Guard current security-floor rotations in one intentionally updated map."""
    schema = _load_schema(SCHEMA_PATH)

    for package, floor in CURRENT_ENFORCED_RUNTIME_FLOORS.items():
        assert schema["min_versions"][package] == floor
    for package, specifier in CURRENT_BLOCKED_VERSION_SPECIFIERS.items():
        assert specifier in schema["blocked_versions"][package]


@pytest.mark.parametrize("surface", REQUIREMENT_SURFACES)
def test_dependency_security_guard_enforces_blocked_packages(surface: Path) -> None:
    """
    Guard: No requirement surface may contain packages listed in
    schema["blocked_packages"]. Entirely forbidden dependencies.
    """
    schema = _load_schema(SCHEMA_PATH)
    blocked_packages = schema.get("blocked_packages", [])
    if not blocked_packages:
        pytest.skip("No blocked packages defined in schema.")
    all_reqs = _packages_present_in_file(surface)
    for pkg in blocked_packages:
        if _normalized_package_name(pkg) in all_reqs:
            pytest.fail(
                f"{surface.name}: package {pkg!r} is blocked by security policy. "
                f"Remove it from this surface."
            )


def test_blocked_packages_detects_unpinned_requirements(tmp_path: Path) -> None:
    """Blocked package detection must include bare package names without specifiers."""
    req = tmp_path / "requirements.txt"
    req.write_text("unsafe-pkg\n", encoding="utf-8")
    assert "unsafe-pkg" in _packages_present_in_file(req)


def test_blocked_packages_detects_pinned_requirements(tmp_path: Path) -> None:
    """Blocked package detection must still catch pinned package requirements."""
    req = tmp_path / "requirements.txt"
    req.write_text("unsafe-pkg==1.2.3\n", encoding="utf-8")
    assert "unsafe-pkg" in _packages_present_in_file(req)


def test_blocked_packages_canonicalize_equivalent_package_names(tmp_path: Path) -> None:
    """Equivalent _, ., and - package spellings must match the same blocked package."""
    req = tmp_path / "requirements.txt"
    req.write_text("unsafe_pkg==1.2.3\nunsafe.pkg\n", encoding="utf-8")
    all_reqs = _packages_present_in_file(req)
    assert "unsafe-pkg" in all_reqs
    assert _normalized_package_name("unsafe_pkg") in all_reqs
    assert _normalized_package_name("unsafe.pkg") in all_reqs


def test_min_versions_lookup_uses_canonical_package_names(tmp_path: Path) -> None:
    """Schema names using - must match requirement names using _ or . spellings."""
    req = tmp_path / "requirements.txt"
    req.write_text("unsafe_pkg==1.2.3\n", encoding="utf-8")

    all_reqs = _effective_min_versions_per_package(req)
    effective = all_reqs.get(_normalized_package_name("unsafe-pkg"))

    assert effective == Version("1.2.3")


def test_parse_requirement_skips_short_form_pip_flags(tmp_path: Path) -> None:
    """Short-form pip directives must not be parsed as package requirements."""
    req = tmp_path / "requirements.txt"
    req.write_text(
        "-i https://example.com/simple\n"
        "--index-url https://example.com/simple\n"
        "--extra-index-url https://example.com/extra\n"
        "-f https://example.com/wheels\n"
        "--find-links https://example.com/wheels\n"
        "-r base-requirements.txt\n"
        "--requirement base-requirements.txt\n"
        "-c constraints.txt\n"
        "--constraint constraints.txt\n",
        encoding="utf-8",
    )
    assert _packages_present_in_file(req) == set()


@pytest.mark.parametrize("surface", REQUIREMENT_SURFACES)
def test_dependency_security_guard_enforces_blocked_versions(surface: Path) -> None:
    """
    Guard: Packages with blocked version ranges must not match any
    blocked specifier in schema["blocked_versions"].
    Only checks pinned (==) versions; constraint-style ranges are not failed.
    """
    schema = _load_schema(SCHEMA_PATH)
    blocked_versions = schema.get("blocked_versions", {})
    if not blocked_versions:
        pytest.skip("No blocked versions defined in schema.")
    # Only check pinned surfaces (==) to avoid false positives on ranges
    if _is_constraint_style(surface):
        pytest.skip(
            f"{surface.name} is constraint-style; blocked versions check skipped "
            "(only pinned surfaces checked)."
        )
    pinned_versions = _pinned_versions_per_package(surface)
    for pkg, specifiers in blocked_versions.items():
        versions = pinned_versions.get(_normalized_package_name(pkg))
        if not versions:
            continue  # Package not in this surface
        for spec_str in specifiers:
            spec = SpecifierSet(spec_str)
            for effective in sorted(versions):
                if str(effective) in spec:
                    pytest.fail(
                        f"{surface.name}: {pkg}=={effective} matches blocked specifier "
                        f"{spec_str!r}. Update to a safe version."
                    )


def test_blocked_versions_lookup_uses_canonical_package_names(tmp_path: Path) -> None:
    """Blocked version schema names must match equivalent requirement spellings."""
    req = tmp_path / "requirements.txt"
    req.write_text("unsafe_pkg==2.0.3\n", encoding="utf-8")

    pinned_versions = _pinned_versions_per_package(req)
    versions = pinned_versions.get(_normalized_package_name("unsafe-pkg"))

    assert versions == {Version("2.0.3")}
    assert any(str(version) in SpecifierSet(">=2.0.0,<2.1.0") for version in versions)


def test_blocked_versions_check_all_pinned_versions(tmp_path: Path) -> None:
    """Blocked-version guard must not collapse marker-split pins to one version."""
    req = tmp_path / "requirements.txt"
    req.write_text(
        'some-pkg==2.0.3; python_version < "3.13"\n' 'some_pkg==3.0.0; python_version >= "3.13"\n',
        encoding="utf-8",
    )

    versions = _pinned_versions_per_package(req).get(_normalized_package_name("some-pkg"))

    assert versions == {Version("2.0.3"), Version("3.0.0")}
    assert any(str(version) in SpecifierSet(">=2.0.0,<2.1.0") for version in versions)


def test_validate_blocked_packages_fails_on_invalid_type(tmp_path: Path) -> None:
    """blocked_packages must be a list."""
    bad_schema = tmp_path / "schema.json"
    bad_schema.write_text(
        '{"min_versions": {"cryptography": "46.0.5"}, "blocked_packages": "not-a-list"}',
        encoding="utf-8",
    )
    with pytest.raises(BaseException, match="must be a list"):
        _load_schema(bad_schema)


def test_validate_blocked_packages_fails_on_invalid_entry(tmp_path: Path) -> None:
    """blocked_packages entries must be non-empty strings."""
    bad_schema = tmp_path / "schema.json"
    bad_schema.write_text(
        '{"min_versions": {"cryptography": "46.0.5"}, "blocked_packages": [""]}',
        encoding="utf-8",
    )
    with pytest.raises(BaseException, match="must be a non-empty string"):
        _load_schema(bad_schema)


def test_validate_blocked_versions_fails_on_invalid_type(tmp_path: Path) -> None:
    """blocked_versions must be a dict."""
    bad_schema = tmp_path / "schema.json"
    bad_schema.write_text(
        '{"min_versions": {"cryptography": "46.0.5"}, "blocked_versions": "not-a-dict"}',
        encoding="utf-8",
    )
    with pytest.raises(BaseException, match="must be a dict"):
        _load_schema(bad_schema)


def test_validate_blocked_versions_fails_on_invalid_specifier(tmp_path: Path) -> None:
    """blocked_versions specifiers must be parseable."""
    bad_schema = tmp_path / "schema.json"
    bad_schema.write_text(
        '{"min_versions": {"cryptography": "46.0.5"}, '
        '"blocked_versions": {"pkg": [">=1.0.0,<=invalid"]}}',
        encoding="utf-8",
    )
    with pytest.raises(BaseException, match="unparseable specifier"):
        _load_schema(bad_schema)


def test_blocked_package_enforcement_with_fake_surface(tmp_path: Path) -> None:
    """Regression: blocked package in surface should be detected."""
    fake_req = tmp_path / "requirements.txt"
    fake_req.write_text("unsafe-pkg==1.0.0\nsome-other==2.0.0\n", encoding="utf-8")
    all_reqs = _packages_present_in_file(fake_req)
    blocked_packages = ["unsafe-pkg"]
    # Simulate the guard check
    violations = [pkg for pkg in blocked_packages if _normalized_package_name(pkg) in all_reqs]
    assert violations == ["unsafe-pkg"], "Blocked package should be detected."


def test_blocked_version_enforcement_with_fake_surface(tmp_path: Path) -> None:
    """Regression: blocked version match in surface should be detected."""
    fake_req = tmp_path / "requirements.txt"
    fake_req.write_text("some-pkg==2.0.3\n", encoding="utf-8")
    pinned_versions = _pinned_versions_per_package(fake_req)
    blocked_versions = {"some-pkg": [">=2.0.0,<2.1.0"]}
    # Simulate the guard check
    violations = []
    for pkg, specifiers in blocked_versions.items():
        versions = pinned_versions.get(_normalized_package_name(pkg))
        if not versions:
            continue
        for spec_str in specifiers:
            spec = SpecifierSet(spec_str)
            for effective in sorted(versions):
                if str(effective) in spec:
                    violations.append((pkg, str(effective), spec_str))
    assert violations == [
        ("some-pkg", "2.0.3", ">=2.0.0,<2.1.0")
    ], "Blocked version match should be detected."


def test_repo_managed_lock_surfaces_do_not_pin_pip() -> None:
    """Guard: repo-managed lock surfaces must not pin pip as an unsafe package.

    pip-compile --allow-unsafe may reintroduce pip==... entries; the repo
    security policy (GHSA-58qw-9mgm-455v-pip.md) requires these entries to
    be absent.  This guard prevents future drift regardless of the specific
    pip version.
    """
    pinned_surfaces = [
        surface for surface in REQUIREMENT_SURFACES if not _is_constraint_style(surface)
    ]

    offenders: list[str] = []
    for surface in pinned_surfaces:
        if not surface.exists():
            continue
        pins = _pinned_versions_per_package(surface).get(
            _normalized_package_name("pip"),
        )
        if pins:
            versions = ", ".join(str(v) for v in sorted(pins))
            offenders.append(f"{surface.name}: pip=={versions}")

    assert not offenders, (
        "Repo-managed lock surfaces must not pin pip as an unsafe package. "
        "Remove pip==... entries instead of repinning pip. "
        "See docs/security/GHSA-58qw-9mgm-455v-pip.md. Offenders: " + "; ".join(offenders)
    )
