#!/usr/bin/env python3
"""Validate the canonical Python dependency surface registry.

The registry in this file is executable policy. Docs mirror it for humans, but
the validator must stay offline and must not resolve packages.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CONTRACT_DOC = Path("docs/contracts/PYTHON_DEPENDENCY_SURFACES.md")
DEPENDENCY_DOC = Path("docs/DEPENDENCY_MANAGEMENT.md")
REQUIREMENTS_GUIDE = Path("REQUIREMENTS.md")
PYTHON_SETUP_ACTION = Path(".github/actions/python-setup/action.yml")
PIP_AUDIT_HELPER = Path("scripts/ci_pip_audit.sh")
DEPENDENCY_SUBMISSION_WORKFLOW = Path(".github/workflows/python-dependency-submission.yml")
INSTALLER_MODULE = "scripts.ci.install_locked_python_requirements"

FORBIDDEN_LOCK_TOKENS = (
    "PULSEPLATE_PYTHON_INDEX_URL",
    "/Users/",
    "file://",
    "git+",
    " @ ",
    "--find-links",
    "--editable",
    "\n-e ",
)
FORBIDDEN_SHARED_PROFILE_NAMES = (
    "rag-vector-cpu",
    "data",
    "evals",
)
PROFILE_CASE_RE = re.compile(
    r'case "\$selected_profile" in(?P<body>.*?)(?:^\s*\*\)|^\s*esac)',
    re.S | re.M,
)
CASE_ARM_RE = re.compile(r"(?m)^\s*(?P<label>[A-Za-z0-9_-]+)\)(?:\s|$)")
PIP_AUDIT_MANIFEST_RE = re.compile(r"^\s*manifests(?:\+)?=\((?P<body>.*)\)\s*(?:#.*)?$")
SHELL_QUOTED_LOCKFILE_RE = re.compile(
    r"(?P<quote>['\"])(?P<value>requirements[-A-Za-z0-9_]*\.txt)(?P=quote)"
)
WORKFLOW_PATH_ENTRY_RE = re.compile(
    r"^\s*-\s*[\"']?(?P<path>requirements[-A-Za-z0-9_]*\.(?:in|txt))[\"']?\s*$"
)
DEPENDENCY_SUBMISSION_TRIGGER_EVENTS = ("push", "pull_request")


@dataclass(frozen=True)
class DependencySurface:
    """Executable metadata for one managed Python dependency surface."""

    name: str
    source_file: str | None
    lockfile: str
    owner: str
    use_case: str
    install_authority: str
    shared_profiles: tuple[str, ...] = ()
    pip_audit_required: bool = False
    dependency_submission_required: bool = False
    allow_empty_lock: bool = False
    allow_lock_directives: tuple[str, ...] = ()
    noncanonical_install: bool = False


DEPENDENCY_SURFACES: tuple[DependencySurface, ...] = (
    DependencySurface(
        name="runtime",
        source_file="requirements.in",
        lockfile="requirements.txt",
        owner="Backend runtime",
        use_case="Application runtime dependencies",
        install_authority="runtime, runtime-dev, runtime-test, and rag-vector profiles",
        shared_profiles=("runtime", "runtime-dev", "runtime-test", "rag-vector"),
        pip_audit_required=True,
        dependency_submission_required=True,
    ),
    DependencySurface(
        name="docker-runtime",
        source_file="requirements-docker-runtime.in",
        lockfile="requirements-docker-runtime.txt",
        owner="Docker production image",
        use_case="Production Docker runtime without CI-only tooling",
        install_authority="Dockerfile and production image workflows",
        pip_audit_required=True,
        dependency_submission_required=True,
    ),
    DependencySurface(
        name="ci-lite",
        source_file="requirements-ci-lite.in",
        lockfile="requirements-ci-lite.txt",
        owner="CI control-plane",
        use_case="Lint, OpenAPI, diff coverage, and governance jobs",
        install_authority="ci-lite and ci-test profiles",
        shared_profiles=("ci-lite", "ci-test"),
        dependency_submission_required=True,
    ),
    DependencySurface(
        name="test",
        source_file="requirements-test.in",
        lockfile="requirements-test.txt",
        owner="Backend test lanes",
        use_case="Pytest, coverage, and postgres-vector test support",
        install_authority="runtime-test and ci-test profiles",
        shared_profiles=("runtime-test", "ci-test"),
        dependency_submission_required=True,
    ),
    DependencySurface(
        name="dev",
        source_file="requirements-dev.in",
        lockfile="requirements-dev.txt",
        owner="Local development tooling",
        use_case="Developer lint, typecheck, security, and hook tooling",
        install_authority="runtime-dev profile",
        shared_profiles=("runtime-dev",),
        dependency_submission_required=True,
    ),
    DependencySurface(
        name="rag-vector",
        source_file="requirements-rag-vector.in",
        lockfile="requirements-rag-vector.txt",
        owner="Optional vector runtime",
        use_case="Opt-in FastEmbed/RAG vector runtime with ML stack",
        install_authority="rag-vector profile",
        shared_profiles=("rag-vector",),
        pip_audit_required=True,
        dependency_submission_required=True,
    ),
    DependencySurface(
        name="rag-vector-cpu",
        source_file="requirements-rag-vector-cpu.in",
        lockfile="requirements-rag-vector-cpu.txt",
        owner="Local optional vector runtime",
        use_case="Local CPU-only vector runtime without shared CI install authority",
        install_authority="Manual local pip-sync only",
        pip_audit_required=True,
        dependency_submission_required=True,
        allow_lock_directives=("--extra-index-url https://download.pytorch.org/whl/cpu",),
    ),
    DependencySurface(
        name="data",
        source_file="requirements-data.in",
        lockfile="requirements-data.txt",
        owner="Offline data builders",
        use_case="Manual FoodDB/recipe snapshot build tooling",
        install_authority="Manual local pip-sync only",
        pip_audit_required=True,
        dependency_submission_required=True,
    ),
    DependencySurface(
        name="evals",
        source_file="requirements-evals.in",
        lockfile="requirements-evals.txt",
        owner="Offline eval companion",
        use_case="Manual eval tooling; native RAGAS deps remain disabled until patched",
        install_authority="Manual local pip-sync only",
        pip_audit_required=True,
        dependency_submission_required=True,
        allow_empty_lock=True,
    ),
    DependencySurface(
        name="dev-full-lock",
        source_file=None,
        lockfile="requirements-lock.txt",
        owner="Dependency graph reconciliation",
        use_case="Compiled aggregate for dev/full-lock scanner attribution",
        install_authority="Noncanonical; not a shared install profile",
        dependency_submission_required=True,
        noncanonical_install=True,
    ),
    DependencySurface(
        name="all-flexible",
        source_file=None,
        lockfile="requirements-all.txt",
        owner="Legacy local convenience",
        use_case="Flexible aggregate reference for manual local experimentation",
        install_authority="Noncanonical; not a lockfile or shared install profile",
        noncanonical_install=True,
    ),
)


def _relative(path: str) -> Path:
    return Path(path)


def _read_text(repo_root: Path, relative_path: str | Path) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8")


def _existing_requirement_surfaces(repo_root: Path) -> set[str]:
    surfaces: set[str] = set()
    for pattern in ("requirements*.in", "requirements*.txt"):
        surfaces.update(path.name for path in repo_root.glob(pattern))
    return surfaces


def _known_requirement_surfaces() -> set[str]:
    known: set[str] = set()
    for surface in DEPENDENCY_SURFACES:
        known.add(surface.lockfile)
        if surface.source_file is not None:
            known.add(surface.source_file)
    return known


def _load_installer_profiles() -> tuple[str, ...]:
    from scripts.ci.install_locked_python_requirements import REQUIREMENTS_PROFILES

    return tuple(REQUIREMENTS_PROFILES)


def _shared_profile_case_labels(action_text: str) -> set[str]:
    """Return exact requirements-profile case labels from the setup action."""
    match = PROFILE_CASE_RE.search(action_text)
    if match is None:
        return set()
    return {case_match.group("label") for case_match in CASE_ARM_RE.finditer(match.group("body"))}


def _is_requirement_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if stripped.startswith(("-", "--")):
        return False
    return True


def _pip_audit_manifest_entries(script_text: str) -> set[str]:
    """Return lockfiles listed in the pip-audit manifest array."""
    entries: set[str] = set()
    for raw_line in script_text.splitlines():
        match = PIP_AUDIT_MANIFEST_RE.match(raw_line)
        if match is None:
            continue
        entries.update(
            token_match.group("value")
            for token_match in SHELL_QUOTED_LOCKFILE_RE.finditer(match.group("body"))
        )
    return entries


def _dependency_submission_cp_entries(workflow_text: str) -> set[str]:
    """Return lockfiles copied into dependency-submission graph roots."""
    entries: set[str] = set()
    in_cp_block = False
    for raw_line in workflow_text.splitlines():
        stripped = raw_line.strip()
        if not in_cp_block and re.fullmatch(r"cp(?:\s+\\)?", stripped):
            in_cp_block = True
            continue
        if not in_cp_block:
            continue

        token = stripped.removesuffix("\\").strip().strip("'\"")
        if token.startswith("${") or token.startswith("$"):
            in_cp_block = stripped.endswith("\\")
            continue
        if re.fullmatch(r"requirements[-A-Za-z0-9_]*\.txt", token):
            entries.add(token)
        if not stripped.endswith("\\"):
            in_cp_block = False
    return entries


def _dependency_submission_trigger_paths(workflow_text: str) -> dict[str, set[str]]:
    """Return dependency-submission workflow path-filter entries by trigger event."""
    paths_by_event: dict[str, set[str]] = {
        event: set() for event in DEPENDENCY_SUBMISSION_TRIGGER_EVENTS
    }
    in_on_section = False
    current_event: str | None = None
    in_paths = False

    for raw_line in workflow_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if indent == 0:
            in_on_section = stripped == "on:"
            current_event = None
            in_paths = False
            continue
        if not in_on_section:
            continue

        if indent == 2:
            key = stripped.split(":", 1)[0]
            current_event = key if key in paths_by_event else None
            in_paths = False
            continue
        if current_event is None:
            continue

        if indent == 4:
            in_paths = stripped == "paths:"
            continue
        if not in_paths or indent < 6:
            continue

        match = WORKFLOW_PATH_ENTRY_RE.match(raw_line)
        if match is not None:
            paths_by_event[current_event].add(match.group("path"))

    return paths_by_event


def _require_exact_lock_entries(
    *,
    repo_root: Path,
    surface: DependencySurface,
    errors: list[str],
) -> None:
    lock_path = _relative(surface.lockfile)
    lock_text = _read_text(repo_root, lock_path)
    if surface.lockfile == "requirements-all.txt":
        if "-r requirements.txt" not in lock_text:
            errors.append("requirements-all.txt must remain a reference to requirements.txt.")
        return

    if "# This file is autogenerated by pip-compile" not in lock_text:
        errors.append(f"{surface.lockfile}: missing pip-compile generated header.")
    if f"--output-file={surface.lockfile}" not in lock_text:
        errors.append(f"{surface.lockfile}: header must name --output-file={surface.lockfile}.")
    expected_sources = (
        ("requirements-dev.in", "requirements.in")
        if surface.lockfile == "requirements-lock.txt"
        else ((surface.source_file,) if surface.source_file is not None else ())
    )
    for source_file in expected_sources:
        if source_file not in lock_text:
            errors.append(f"{surface.lockfile}: generated header must reference {source_file}.")

    for token in FORBIDDEN_LOCK_TOKENS:
        if token in lock_text:
            errors.append(f"{surface.lockfile}: forbidden token in compiled surface: {token!r}.")
    for raw_line in lock_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-", "--")):
            if line not in surface.allow_lock_directives:
                errors.append(f"{surface.lockfile}: unexpected resolver directive {line!r}.")
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            errors.append(f"{surface.lockfile}: invalid requirement line {raw_line!r}: {exc}.")
            continue
        if "==" not in str(requirement.specifier):
            errors.append(f"{surface.lockfile}: compiled entry must be exact-pinned: {line!r}.")

    has_requirements = any(_is_requirement_line(line) for line in lock_text.splitlines())
    if not has_requirements and not surface.allow_empty_lock:
        errors.append(f"{surface.lockfile}: compiled lockfile must contain at least one pin.")


def _validate_shared_profiles(repo_root: Path, errors: list[str]) -> None:
    supported_profiles = set(_load_installer_profiles())
    registry_profiles = {
        profile for surface in DEPENDENCY_SURFACES for profile in surface.shared_profiles
    }
    unsupported = sorted(registry_profiles - supported_profiles)
    if unsupported:
        errors.append(f"Registry names unsupported installer profiles: {unsupported}.")

    action_text = _read_text(repo_root, PYTHON_SETUP_ACTION)
    action_profile_labels = _shared_profile_case_labels(action_text)
    if not action_profile_labels:
        errors.append(f"{PYTHON_SETUP_ACTION}: missing requirements-profile case routing.")
    for profile in sorted(registry_profiles):
        if profile not in action_profile_labels:
            errors.append(f"{PYTHON_SETUP_ACTION}: missing shared profile {profile!r}.")
    for profile in FORBIDDEN_SHARED_PROFILE_NAMES:
        if profile in action_profile_labels:
            errors.append(
                f"{PYTHON_SETUP_ACTION}: local/manual dependency surface leaked into shared "
                f"profile routing via {profile!r}."
            )


def _validate_security_coverage(repo_root: Path, errors: list[str]) -> None:
    audit_text = _read_text(repo_root, PIP_AUDIT_HELPER)
    dependency_submission_text = _read_text(repo_root, DEPENDENCY_SUBMISSION_WORKFLOW)
    audited_lockfiles = _pip_audit_manifest_entries(audit_text)
    submitted_lockfiles = _dependency_submission_cp_entries(dependency_submission_text)
    submission_trigger_paths = _dependency_submission_trigger_paths(dependency_submission_text)
    for surface in DEPENDENCY_SURFACES:
        if surface.pip_audit_required and surface.lockfile not in audited_lockfiles:
            errors.append(f"{PIP_AUDIT_HELPER}: missing pip-audit coverage for {surface.lockfile}.")
        if surface.dependency_submission_required and surface.lockfile not in submitted_lockfiles:
            errors.append(
                f"{DEPENDENCY_SUBMISSION_WORKFLOW}: missing dependency submission coverage for "
                f"{surface.lockfile}."
            )
        if surface.dependency_submission_required:
            trigger_files = (surface.source_file, surface.lockfile)
            for event, trigger_paths in submission_trigger_paths.items():
                for trigger_file in trigger_files:
                    if trigger_file is not None and trigger_file not in trigger_paths:
                        errors.append(
                            f"{DEPENDENCY_SUBMISSION_WORKFLOW}: {event}.paths missing "
                            f"dependency submission trigger for {trigger_file}."
                        )


def _validate_docs(repo_root: Path, errors: list[str]) -> None:
    contract_text = _read_text(repo_root, CONTRACT_DOC)
    dependency_doc = _read_text(repo_root, DEPENDENCY_DOC)
    requirements_guide = _read_text(repo_root, REQUIREMENTS_GUIDE)
    for surface_file in sorted(_known_requirement_surfaces()):
        if surface_file not in contract_text:
            errors.append(f"{CONTRACT_DOC}: missing dependency surface {surface_file}.")
    for required_phrase in (
        "Noncanonical Aggregate Install Surfaces",
        "requirements-all.txt",
        "requirements-lock.txt",
        "scripts/ci/check_python_dependency_surfaces.py",
    ):
        if required_phrase not in contract_text:
            errors.append(f"{CONTRACT_DOC}: missing required phrase {required_phrase!r}.")
    for doc_path, text in (
        (DEPENDENCY_DOC, dependency_doc),
        (REQUIREMENTS_GUIDE, requirements_guide),
    ):
        for required_phrase in (
            str(CONTRACT_DOC),
            "scripts/ci/check_python_dependency_surfaces.py",
            "verify_requirements.py",
        ):
            if required_phrase not in text:
                errors.append(f"{doc_path}: missing reference to {required_phrase}.")


def validate_repo(repo_root: Path = REPO_ROOT) -> list[str]:
    """Return all dependency-surface contract violations for a repo root."""
    errors: list[str] = []
    expected_files = _known_requirement_surfaces()
    required_policy_files = {
        str(CONTRACT_DOC),
        str(DEPENDENCY_DOC),
        str(REQUIREMENTS_GUIDE),
        str(PYTHON_SETUP_ACTION),
        str(PIP_AUDIT_HELPER),
        str(DEPENDENCY_SUBMISSION_WORKFLOW),
    }
    for relative_path in sorted(expected_files | required_policy_files):
        if not (repo_root / relative_path).is_file():
            errors.append(f"Missing required dependency policy file: {relative_path}.")
    if errors:
        return errors

    unknown_surfaces = sorted(_existing_requirement_surfaces(repo_root) - expected_files)
    if unknown_surfaces:
        errors.append(
            f"Unknown root requirements surfaces are not in the registry: {unknown_surfaces}."
        )

    for surface in DEPENDENCY_SURFACES:
        _require_exact_lock_entries(repo_root=repo_root, surface=surface, errors=errors)

    _validate_shared_profiles(repo_root, errors)
    _validate_security_coverage(repo_root, errors)
    _validate_docs(repo_root, errors)
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root to validate. Defaults to the current checkout root.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors = validate_repo(args.repo_root)
    if errors:
        print("Python dependency surface contract violations:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: Python dependency surfaces match the canonical contract.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
