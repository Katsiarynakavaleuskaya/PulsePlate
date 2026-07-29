#!/usr/bin/env python3
"""Validate the canonical Python dependency surface registry.

The registry in this file is executable policy. Docs mirror it for humans, but
the validator must stay offline and must not resolve packages.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys

from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.dependabot_requirement_carriers import (
    DependabotRequirementDiscoveryError,
    discover_dependabot_requirement_carriers,
)

CONTRACT_DOC = Path("docs/contracts/PYTHON_DEPENDENCY_SURFACES.md")
DEPENDENCY_DOC = Path("docs/DEPENDENCY_MANAGEMENT.md")
REQUIREMENTS_GUIDE = Path("REQUIREMENTS.md")
ACTIVE_LOCK_WORKFLOW_DOCS = (
    Path("AGENTS.md"),
    REQUIREMENTS_GUIDE,
    DEPENDENCY_DOC,
    CONTRACT_DOC,
    Path("docs/orchestration/workflow.md"),
    Path("docs/evals/RAGAS_SETUP.md"),
    Path("docs/security/CVE-2025-14009-nltk.md"),
    Path("docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md"),
    Path("docs/security/GHSA-58qw-9mgm-455v-pip.md"),
    Path("docs/security/PYSEC_2026_CLICK_PILLOW_HOTFIX.md"),
)
FORBIDDEN_ACTIVE_LOCK_WORKFLOW_TOKENS = (
    "pip-compile",
    "piptools compile",
    "--allow-unsafe",
)
PYTHON_SETUP_ACTION = Path(".github/actions/python-setup/action.yml")
PIP_AUDIT_HELPER = Path("scripts/ci_pip_audit.sh")
DEPENDENCY_SUBMISSION_WORKFLOW = Path(".github/workflows/python-dependency-submission.yml")
INSTALLER_MODULE = "scripts.ci.install_locked_python_requirements"
INSTALLER_PATH = Path(*INSTALLER_MODULE.split(".")).with_suffix(".py")

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

OWNERSHIP_ERROR = "error"
OWNERSHIP_WARNING = "warning"
OWNERSHIP_INFO = "info"
OWNERSHIP_SEVERITIES = (OWNERSHIP_ERROR, OWNERSHIP_WARNING, OWNERSHIP_INFO)

AUDITED_OWNERSHIP_PACKAGES = (
    "pyarrow",
    "pandas",
    "httpx2",
    "reportlab",
    "matplotlib",
    "numpy",
    "aiosqlite",
)
RUNTIME_REQUIREMENT_SURFACES = (
    "requirements.in",
    "requirements.txt",
)
CI_LITE_REQUIREMENT_SURFACES = (
    "requirements-ci-lite.in",
    "requirements-ci-lite.txt",
)
DOCKER_RUNTIME_REQUIREMENT_SURFACES = (
    "requirements-docker-runtime.in",
    "requirements-docker-runtime.txt",
)
RUNTIME_CI_LITE_REQUIREMENT_SURFACES = (
    *RUNTIME_REQUIREMENT_SURFACES,
    *CI_LITE_REQUIREMENT_SURFACES,
)
RUNTIME_DOCKER_CI_LITE_REQUIREMENT_SURFACES = (
    *RUNTIME_REQUIREMENT_SURFACES,
    *CI_LITE_REQUIREMENT_SURFACES,
    *DOCKER_RUNTIME_REQUIREMENT_SURFACES,
)
PYARROW_FORBIDDEN_RUNTIME_SURFACES = (
    *RUNTIME_DOCKER_CI_LITE_REQUIREMENT_SURFACES,
    "requirements-lock.txt",
)
RUNTIME_DECLARATION_SURFACES = (
    "requirements.in",
    "requirements-ci-lite.in",
    "requirements-docker-runtime.in",
)
CANONICAL_RUNTIME_OWNER_ROOTS = (
    Path("app/bootstrap"),
    Path("app/routers"),
    Path("app/services"),
    Path("core"),
    Path("providers"),
)
LEGACY_COMPAT_OWNER_PATHS = (
    Path("legacy_app.py"),
    Path("bmi_visualization.py"),
    Path("app/services/bmi_compat.py"),
)
LEGACY_COMPAT_TRANSITIONAL_PATHS = set(LEGACY_COMPAT_OWNER_PATHS)
SQLITE_ASYNC_FALLBACK_OWNER_PATH = Path("core/db.py")
SQLITE_ASYNC_FALLBACK_OWNER_MARKERS = (
    "_derive_async_url",
    "sqlite+aiosqlite",
    "_sqlite_connect_args",
)
PACKAGE_IMPORT_ALIASES = {
    "pydantic-core": ("pydantic_core",),
    "pytest-xdist": ("xdist",),
}


@dataclass(frozen=True)
class DependencyOwnershipFinding:
    """One first-pass dependency ownership audit finding."""

    package: str
    severity: str
    reason_code: str
    surfaces: tuple[str, ...]
    detail: str

    def to_message(self) -> str:
        surface_text = ", ".join(self.surfaces) if self.surfaces else "repo imports"
        return f"{self.package}: {self.severity}:{self.reason_code}: {self.detail} [{surface_text}]"


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
    compile_profile: str | None = None
    compile_sources: tuple[str, ...] = ()


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
        compile_profile="runtime",
        compile_sources=("requirements.in",),
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
        compile_profile="docker-runtime",
        compile_sources=("requirements-docker-runtime.in",),
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
        compile_profile="ci-lite",
        compile_sources=("requirements-ci-lite.in",),
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
        compile_profile="test",
        compile_sources=("requirements-test.in",),
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
        compile_profile="dev",
        compile_sources=("requirements-dev.in",),
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
        compile_profile="rag-vector",
        compile_sources=("requirements-rag-vector.in",),
    ),
    DependencySurface(
        name="rag-vector-cpu",
        source_file="requirements-rag-vector-cpu.in",
        lockfile="requirements-rag-vector-cpu.txt",
        owner="Local optional vector runtime",
        use_case="Local CPU-only vector runtime without shared CI install authority",
        install_authority="Manual local locked-installer sync only",
        pip_audit_required=True,
        dependency_submission_required=True,
        compile_profile="rag-vector-cpu",
        compile_sources=("requirements-rag-vector-cpu.in",),
    ),
    DependencySurface(
        name="data",
        source_file="requirements-data.in",
        lockfile="requirements-data.txt",
        owner="Offline data builders",
        use_case="Manual FoodDB/recipe snapshot build tooling",
        install_authority="Manual local locked-installer sync only",
        pip_audit_required=True,
        dependency_submission_required=True,
        compile_profile="data",
        compile_sources=("requirements-data.in",),
    ),
    DependencySurface(
        name="evals",
        source_file="requirements-evals.in",
        lockfile="requirements-evals.txt",
        owner="Offline eval companion",
        use_case="Manual eval tooling; native RAGAS deps remain disabled until patched",
        install_authority="Manual local locked-installer sync only",
        pip_audit_required=True,
        dependency_submission_required=True,
        allow_empty_lock=True,
        compile_profile="evals",
        compile_sources=("requirements-evals.in",),
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
        compile_profile="aggregate",
        compile_sources=("requirements-dev.in", "requirements.in"),
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


def compiled_dependency_surfaces() -> tuple[DependencySurface, ...]:
    """Return the registry-owned surfaces that the governed compiler may write."""

    return tuple(surface for surface in DEPENDENCY_SURFACES if surface.compile_profile is not None)


def validate_compile_registry() -> None:
    """Reject source duplication between the primary registry and compiler metadata."""

    for surface in compiled_dependency_surfaces():
        if surface.source_file is None:
            if surface.compile_profile != "aggregate" or len(surface.compile_sources) < 2:
                raise ValueError(
                    f"{surface.name}: only aggregate may have compiler sources without "
                    "a primary source file"
                )
            continue
        if surface.compile_sources != (surface.source_file,):
            raise ValueError(f"{surface.name}: compile_sources must mirror source_file exactly")


def render_governed_lock_header(surface: DependencySurface) -> str:
    """Render stable Make-only provenance for a compiled dependency surface."""

    if surface.compile_profile is None or not surface.compile_sources:
        raise ValueError(f"Surface is not compile-enabled: {surface.name}")
    source_list = ", ".join(surface.compile_sources)
    return (
        "#\n"
        "# Managed by the PulsePlate private-proxy lock workflow.\n"
        f"# Profile: {surface.compile_profile}\n"
        f"# Sources: {source_list}\n"
        "# Regenerate with:\n"
        "#\n"
        f'#    LOCK_PROFILES="{surface.compile_profile}" make requirements-locks\n'
        "#\n"
    )


def _relative(path: str) -> Path:
    return Path(path)


def _read_text(repo_root: Path, relative_path: str | Path) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8")


def _existing_requirement_surfaces(repo_root: Path) -> set[str]:
    carriers: set[str] = discover_dependabot_requirement_carriers(repo_root)
    return carriers


def _known_requirement_surfaces() -> set[str]:
    known: set[str] = set()
    for surface in DEPENDENCY_SURFACES:
        known.add(surface.lockfile)
        if surface.source_file is not None:
            known.add(surface.source_file)
    return known


def registered_dependabot_requirement_carriers() -> set[str]:
    """Return every carrier whose dependency ownership is explicitly governed."""

    return _known_requirement_surfaces() | {"constraints.txt"}


def _literal_str_tuple(value: ast.AST) -> tuple[str, ...] | None:
    try:
        literal = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(literal, tuple):
        return None
    if not all(isinstance(item, str) for item in literal):
        return None
    return tuple(literal)


def _load_installer_profiles(repo_root: Path) -> tuple[str, ...]:
    installer_tree = ast.parse(
        _read_text(repo_root, INSTALLER_PATH),
        filename=str(INSTALLER_PATH),
    )
    for node in installer_tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "REQUIREMENTS_PROFILES"
            and node.value is not None
        ):
            profiles = _literal_str_tuple(node.value)
            return profiles or ()
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "REQUIREMENTS_PROFILES"
            for target in node.targets
        ):
            profiles = _literal_str_tuple(node.value)
            return profiles or ()
    return ()


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


def _normalize_package_name(package_name: str) -> str:
    return str(canonicalize_name(package_name))


def _requirement_package_names(repo_root: Path, relative_path: str | Path) -> set[str]:
    names: set[str] = set()
    for raw_line in _read_text(repo_root, relative_path).splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not _is_requirement_line(line):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        names.add(_normalize_package_name(requirement.name))
    return names


def _surfaces_containing_package(
    repo_root: Path,
    package: str,
    surfaces: tuple[str, ...],
) -> tuple[str, ...]:
    package_name = _normalize_package_name(package)
    matches: list[str] = []
    for surface in surfaces:
        if not (repo_root / surface).is_file():
            continue
        if package_name in _requirement_package_names(repo_root, surface):
            matches.append(surface)
    return tuple(matches)


def _iter_python_files(repo_root: Path, paths: tuple[Path, ...]) -> tuple[Path, ...]:
    python_files: list[Path] = []
    for relative_path in paths:
        candidate = repo_root / relative_path
        if candidate.is_file() and candidate.suffix == ".py":
            python_files.append(relative_path)
            continue
        if candidate.is_dir():
            python_files.extend(
                path.relative_to(repo_root)
                for path in sorted(candidate.rglob("*.py"))
                if path.is_file()
            )
    return tuple(python_files)


def _top_level_import_name(module_name: str) -> str:
    return module_name.split(".", 1)[0]


def _package_import_names(package: str) -> frozenset[str]:
    package_name = _normalize_package_name(package)
    return frozenset((package_name, *PACKAGE_IMPORT_ALIASES.get(package_name, ())))


def _imports_package(repo_root: Path, relative_path: Path, package: str) -> bool:
    package_import_names = _package_import_names(package)
    try:
        tree = ast.parse(
            _read_text(repo_root, relative_path),
            filename=str(relative_path),
        )
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _top_level_import_name(alias.name) in package_import_names:
                    return True
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if _top_level_import_name(node.module) in package_import_names:
                return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and _top_level_import_name(node.args[0].value) in package_import_names
        ):
            return True
    return False


def _package_import_evidence(
    repo_root: Path,
    package: str,
    paths: tuple[Path, ...],
) -> tuple[str, ...]:
    return tuple(
        str(relative_path)
        for relative_path in _iter_python_files(repo_root, paths)
        if _imports_package(repo_root, relative_path, package)
    )


def _canonical_runtime_import_evidence(repo_root: Path, package: str) -> tuple[str, ...]:
    evidence = []
    for relative_path in _package_import_evidence(
        repo_root, package, CANONICAL_RUNTIME_OWNER_ROOTS
    ):
        if Path(relative_path) not in LEGACY_COMPAT_TRANSITIONAL_PATHS:
            evidence.append(relative_path)
    return tuple(evidence)


def _legacy_compat_import_evidence(repo_root: Path, package: str) -> tuple[str, ...]:
    return _package_import_evidence(repo_root, package, LEGACY_COMPAT_OWNER_PATHS)


def _sqlite_async_fallback_owner_evidence(repo_root: Path) -> tuple[str, ...]:
    """Return explicit SQLite async fallback ownership evidence for aiosqlite."""
    owner_file = repo_root / SQLITE_ASYNC_FALLBACK_OWNER_PATH
    if not owner_file.is_file():
        return ()
    owner_text = owner_file.read_text(encoding="utf-8")
    if all(marker in owner_text for marker in SQLITE_ASYNC_FALLBACK_OWNER_MARKERS):
        return (str(SQLITE_ASYNC_FALLBACK_OWNER_PATH),)
    return ()


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

    if surface.compile_profile is None:
        errors.append(f"{surface.lockfile}: compiled surface lacks a compiler profile.")
    else:
        expected_header = render_governed_lock_header(surface)
        if not lock_text.startswith(expected_header):
            errors.append(
                f"{surface.lockfile}: header must match governed profile "
                f"{surface.compile_profile!r} and sources {list(surface.compile_sources)!r}."
            )

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


def _validate_active_lock_workflow_docs(repo_root: Path, errors: list[str]) -> None:
    """Reject obsolete direct lock-compilation commands in active authorities."""

    for relative_path in ACTIVE_LOCK_WORKFLOW_DOCS:
        text = _read_text(repo_root, relative_path)
        for token in FORBIDDEN_ACTIVE_LOCK_WORKFLOW_TOKENS:
            if token in text:
                errors.append(
                    f"{relative_path}: active lock workflow must use make requirements-locks; "
                    f"forbidden token {token!r}."
                )


def _validate_shared_profiles(repo_root: Path, errors: list[str]) -> None:
    supported_profiles = set(_load_installer_profiles(repo_root))
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


def _validate_direct_owner_containment(repo_root: Path, errors: list[str]) -> None:
    """Require each managed lock to retain its normalized direct package owners."""
    for surface in compiled_dependency_surfaces():
        direct_packages: set[str] = set()
        for source_file in surface.compile_sources:
            direct_packages.update(_requirement_package_names(repo_root, source_file))
        lock_packages = _requirement_package_names(repo_root, surface.lockfile)
        missing_packages = sorted(direct_packages - lock_packages)
        if missing_packages:
            source_label = " + ".join(surface.compile_sources)
            errors.append(
                f"{surface.lockfile}: missing direct packages from "
                f"{source_label}: {missing_packages}."
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
        "Dependency Ownership Audit",
        "legacy_compat_transitional",
        "Legacy usage is evidence of transitional compatibility pressure",
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


def _ownership_finding(
    *,
    package: str,
    severity: str,
    reason_code: str,
    surfaces: tuple[str, ...],
    detail: str,
) -> DependencyOwnershipFinding:
    if severity not in OWNERSHIP_SEVERITIES:
        raise ValueError(f"Unknown dependency ownership severity: {severity}")
    return DependencyOwnershipFinding(
        package=package,
        severity=severity,
        reason_code=reason_code,
        surfaces=surfaces,
        detail=detail,
    )


def _legacy_only_runtime_authority_finding(
    *,
    package: str,
    evidence: tuple[str, ...],
) -> DependencyOwnershipFinding:
    return _ownership_finding(
        package=package,
        severity=OWNERSHIP_ERROR,
        reason_code="legacy_only_runtime_authority_forbidden",
        surfaces=evidence,
        detail="legacy compatibility evidence cannot create canonical runtime ownership",
    )


def collect_dependency_ownership_findings(
    repo_root: Path = REPO_ROOT,
) -> tuple[DependencyOwnershipFinding, ...]:
    """Return first-pass audited dependency ownership findings.

    This audit intentionally covers only the approved package subset. Import
    evidence is policy context, not a generic dependency trimmer.
    """

    findings: list[DependencyOwnershipFinding] = []

    pyarrow_surfaces = _surfaces_containing_package(
        repo_root,
        "pyarrow",
        PYARROW_FORBIDDEN_RUNTIME_SURFACES,
    )
    if pyarrow_surfaces:
        canonical_pyarrow = _canonical_runtime_import_evidence(repo_root, "pyarrow")
        legacy_pyarrow = _legacy_compat_import_evidence(repo_root, "pyarrow")
        if canonical_pyarrow:
            findings.append(
                _ownership_finding(
                    package="pyarrow",
                    severity=OWNERSHIP_INFO,
                    reason_code="canonical_runtime_owner_documented",
                    surfaces=canonical_pyarrow,
                    detail="canonical runtime import evidence exists; do not quarantine blindly",
                )
            )
        elif legacy_pyarrow:
            findings.append(
                _legacy_only_runtime_authority_finding(
                    package="pyarrow",
                    evidence=legacy_pyarrow,
                )
            )
        else:
            findings.append(
                _ownership_finding(
                    package="pyarrow",
                    severity=OWNERSHIP_ERROR,
                    reason_code="runtime_direct_no_canonical_owner",
                    surfaces=pyarrow_surfaces,
                    detail=(
                        "runtime/ci-lite or aggregate surfaces include pyarrow without "
                        "canonical app/core/provider ownership"
                    ),
                )
            )

    pandas_surfaces = _surfaces_containing_package(
        repo_root,
        "pandas",
        RUNTIME_DOCKER_CI_LITE_REQUIREMENT_SURFACES,
    )
    if pandas_surfaces:
        findings.append(
            _ownership_finding(
                package="pandas",
                severity=OWNERSHIP_ERROR,
                reason_code="data_eval_dependency_in_runtime",
                surfaces=pandas_surfaces,
                detail="pandas is owned by data/eval scripts and must stay out of runtime/Docker/ci-lite",
            )
        )

    httpx2_surfaces = _surfaces_containing_package(
        repo_root,
        "httpx2",
        RUNTIME_DOCKER_CI_LITE_REQUIREMENT_SURFACES,
    )
    if httpx2_surfaces:
        findings.append(
            _ownership_finding(
                package="httpx2",
                severity=OWNERSHIP_ERROR,
                reason_code="test_dev_dependency_in_runtime",
                surfaces=httpx2_surfaces,
                detail="httpx2 is the Starlette TestClient backend and must stay test/dev-only",
            )
        )

    reportlab_surfaces = _surfaces_containing_package(
        repo_root,
        "reportlab",
        RUNTIME_DOCKER_CI_LITE_REQUIREMENT_SURFACES,
    )
    if reportlab_surfaces:
        reportlab_evidence = _canonical_runtime_import_evidence(repo_root, "reportlab")
        reportlab_legacy_evidence = _legacy_compat_import_evidence(repo_root, "reportlab")
        if reportlab_evidence:
            findings.append(
                _ownership_finding(
                    package="reportlab",
                    severity=OWNERSHIP_INFO,
                    reason_code="canonical_runtime_owner_documented",
                    surfaces=reportlab_evidence,
                    detail="export/pdf modules provide canonical runtime ownership",
                )
            )
        elif reportlab_legacy_evidence:
            findings.append(
                _legacy_only_runtime_authority_finding(
                    package="reportlab",
                    evidence=reportlab_legacy_evidence,
                )
            )
        else:
            findings.append(
                _ownership_finding(
                    package="reportlab",
                    severity=OWNERSHIP_ERROR,
                    reason_code="runtime_direct_no_canonical_owner",
                    surfaces=reportlab_surfaces,
                    detail="reportlab is in runtime surfaces without canonical export/pdf evidence",
                )
            )

    matplotlib_surfaces = _surfaces_containing_package(
        repo_root,
        "matplotlib",
        RUNTIME_CI_LITE_REQUIREMENT_SURFACES,
    )
    if matplotlib_surfaces:
        matplotlib_canonical = _canonical_runtime_import_evidence(repo_root, "matplotlib")
        matplotlib_legacy = _legacy_compat_import_evidence(repo_root, "matplotlib")
        if not matplotlib_canonical and matplotlib_legacy:
            findings.append(
                _ownership_finding(
                    package="matplotlib",
                    severity=OWNERSHIP_WARNING,
                    reason_code="legacy_compat_transitional",
                    surfaces=matplotlib_legacy,
                    detail=(
                        "legacy BMI visualization evidence is transitional pressure, "
                        "not canonical runtime authority"
                    ),
                )
            )
        elif matplotlib_canonical:
            findings.append(
                _ownership_finding(
                    package="matplotlib",
                    severity=OWNERSHIP_INFO,
                    reason_code="canonical_runtime_owner_documented",
                    surfaces=matplotlib_canonical,
                    detail="canonical BMI visualization owner is documented by import evidence",
                )
            )
        else:
            findings.append(
                _ownership_finding(
                    package="matplotlib",
                    severity=OWNERSHIP_WARNING,
                    reason_code="legacy_compat_transitional",
                    surfaces=matplotlib_surfaces,
                    detail="matplotlib remains pending the BMI visualization ownership decision",
                )
            )

    numpy_direct_surfaces = _surfaces_containing_package(
        repo_root,
        "numpy",
        RUNTIME_DECLARATION_SURFACES,
    )
    if numpy_direct_surfaces and not _canonical_runtime_import_evidence(repo_root, "numpy"):
        findings.append(
            _ownership_finding(
                package="numpy",
                severity=OWNERSHIP_WARNING,
                reason_code="transitive_only_direct_runtime_candidate",
                surfaces=numpy_direct_surfaces,
                detail="numpy has no direct canonical runtime import evidence and may be transitive-only",
            )
        )

    aiosqlite_surfaces = _surfaces_containing_package(
        repo_root,
        "aiosqlite",
        RUNTIME_DOCKER_CI_LITE_REQUIREMENT_SURFACES,
    )
    if aiosqlite_surfaces:
        aiosqlite_evidence = _sqlite_async_fallback_owner_evidence(repo_root)
        if aiosqlite_evidence:
            findings.append(
                _ownership_finding(
                    package="aiosqlite",
                    severity=OWNERSHIP_INFO,
                    reason_code="sqlite_async_fallback_owner_documented",
                    surfaces=aiosqlite_evidence,
                    detail=(
                        "core DB URL derivation documents SQLite async fallback/local-test "
                        "ownership; this is not production Postgres authority"
                    ),
                )
            )
        else:
            findings.append(
                _ownership_finding(
                    package="aiosqlite",
                    severity=OWNERSHIP_WARNING,
                    reason_code="db_fallback_test_split_pending",
                    surfaces=aiosqlite_surfaces,
                    detail="sqlite async fallback/test ownership needs a separate DB-surface decision",
                )
            )

    return tuple(findings)


def validate_repo(repo_root: Path = REPO_ROOT) -> list[str]:
    """Return all dependency-surface contract violations for a repo root."""
    errors: list[str] = []
    try:
        validate_compile_registry()
    except ValueError as exc:
        errors.append(str(exc))
    expected_files = _known_requirement_surfaces()
    required_policy_files = {
        *(str(path) for path in ACTIVE_LOCK_WORKFLOW_DOCS),
        str(PYTHON_SETUP_ACTION),
        str(PIP_AUDIT_HELPER),
        str(DEPENDENCY_SUBMISSION_WORKFLOW),
    }
    for relative_path in sorted(expected_files | required_policy_files):
        if not (repo_root / relative_path).is_file():
            errors.append(f"Missing required dependency policy file: {relative_path}.")
    if errors:
        return errors

    try:
        unknown_surfaces = sorted(
            _existing_requirement_surfaces(repo_root) - registered_dependabot_requirement_carriers()
        )
    except DependabotRequirementDiscoveryError:
        errors.append(
            "Dependabot-discoverable requirement carrier scan could not inspect "
            "the repository tree."
        )
        unknown_surfaces = []
    if unknown_surfaces:
        errors.append(
            "Dependabot-discoverable requirement carriers are not in the registry: "
            f"{unknown_surfaces}."
        )

    for surface in DEPENDENCY_SURFACES:
        _require_exact_lock_entries(repo_root=repo_root, surface=surface, errors=errors)

    _validate_shared_profiles(repo_root, errors)
    _validate_security_coverage(repo_root, errors)
    _validate_direct_owner_containment(repo_root, errors)
    _validate_active_lock_workflow_docs(repo_root, errors)
    _validate_docs(repo_root, errors)
    errors.extend(
        finding.to_message()
        for finding in collect_dependency_ownership_findings(repo_root)
        if finding.severity == OWNERSHIP_ERROR
    )
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

    findings = collect_dependency_ownership_findings(args.repo_root)
    reported_findings = [
        finding for finding in findings if finding.severity in {OWNERSHIP_WARNING, OWNERSHIP_INFO}
    ]
    if reported_findings:
        print("Python dependency ownership audit:")
        for finding in reported_findings:
            print(f"- {finding.to_message()}")

    print("PASS: Python dependency surfaces match the canonical contract.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
