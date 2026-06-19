"""Regression tests for Python supply-chain hardening controls."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess

from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version
import pytest
import yaml

import scripts.ci.install_locked_python_requirements as locked_installer
from scripts.ci.check_docker_provenance_attestation import SBOM_PREDICATE_TYPE
from tests.runtime_toolchain_versions import CANONICAL_PYTHON

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCKED_INSTALL_WORKFLOW_PATHS: tuple[str, ...] = (
    ".github/workflows/ci.yml",
    ".github/workflows/frontend-ci.yml",
    ".github/workflows/nightly-tests.yml",
    ".github/workflows/nightly.yml",
    ".github/workflows/security.yml",
)
PROXY_WORKFLOW_ENV_PATHS: tuple[str, ...] = LOCKED_INSTALL_WORKFLOW_PATHS + (
    ".github/workflows/build.yml",
    ".github/workflows/trivy.yml",
    ".github/workflows/cd.yml",
)
APPROVED_PROXY_ENV_EXPRESSION = (
    "${{ secrets.PULSEPLATE_PYTHON_INDEX_URL || vars.PULSEPLATE_PYTHON_INDEX_URL }}"
)
APPROVED_TRUSTED_HOST_EXPRESSION = (
    "${{ secrets.PULSEPLATE_PYTHON_TRUSTED_HOST || vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
)
PIP_INSTALL_PATTERN = re.compile(r"\b\S*python\S*\s+-m\s+pip\s+install\b")
PIP_REQUIREMENT_DIRECTIVE_PREFIXES = (
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
PINNED_CHECKOUT_ACTION = "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd"
OPTIONAL_VECTOR_STACK_PACKAGES = (
    "pgvector",
    "sentence-transformers",
    "torch",
    "transformers",
)
DEFAULT_INSTALL_REQUIREMENT_FILES = (
    "requirements.in",
    "requirements.txt",
    "requirements-ci-lite.in",
    "requirements-ci-lite.txt",
    "requirements-docker-runtime.in",
    "requirements-docker-runtime.txt",
    "requirements-lock.txt",
    "requirements-test.txt",
)
OPTIONAL_VECTOR_REQUIREMENT_FILES = (
    "requirements-rag-vector.in",
    "requirements-rag-vector.txt",
    "requirements-rag-vector-cpu.in",
    "requirements-rag-vector-cpu.txt",
)
LOCAL_MANUAL_EVAL_DATA_REQUIREMENT_FILES = (
    "requirements-data.in",
    "requirements-data.txt",
    "requirements-evals.in",
    "requirements-evals.txt",
)
LOCAL_MANUAL_EVAL_DATA_LOCKFILES = (
    "requirements-data.txt",
    "requirements-evals.txt",
)
LOCAL_MANUAL_EVAL_DATA_PACKAGES = (
    "diskcache",
    "datasets",
    "ragas",
    "pandas",
)
DISABLED_RAGAS_EVAL_PACKAGES = (
    "diskcache",
    "datasets",
    "ragas",
)
DEFAULT_AND_TOOLING_REQUIREMENT_FILES = DEFAULT_INSTALL_REQUIREMENT_FILES + (
    "requirements-dev.in",
    "requirements-dev.txt",
    "requirements-all.txt",
    "constraints.txt",
)


def _load_workflow(path: str) -> dict[str, object]:
    """Load a GitHub Actions workflow as structured YAML."""
    return yaml.safe_load((REPO_ROOT / path).read_text(encoding="utf-8"))


def _workflow_events(path: str) -> dict[str, object]:
    """Return the GitHub Actions `on` block, including YAML boolean-key normalization."""

    workflow = _load_workflow(path)
    events = workflow.get("on", workflow.get(True))
    assert isinstance(events, dict), f"Missing workflow events block for {path}"
    return events


def _workflow_steps(path: str, job_name: str) -> list[dict[str, object]]:
    """Return workflow steps for a specific job."""
    workflow = _load_workflow(path)
    return workflow["jobs"][job_name]["steps"]


def _python_setup_step(path: str, job_name: str) -> dict[str, object]:
    """Return the canonical python-setup step for a workflow job."""
    for step in _workflow_steps(path, job_name):
        if step.get("uses") == "./.github/actions/python-setup":
            return step
    raise AssertionError(f"Missing python-setup step for {path}:{job_name}")


def _workflow_step_by_name(path: str, job_name: str, step_name: str) -> dict[str, object]:
    """Return a workflow step by its display name."""

    for step in _workflow_steps(path, job_name):
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"Missing step {step_name!r} for {path}:{job_name}")


def _pushed_docker_steps_with_secret_index_args() -> tuple[dict[str, object], ...]:
    """Return pushed Docker build steps that receive private index inputs."""

    return (
        _workflow_step_by_name(
            ".github/workflows/cd.yml",
            "build",
            "Build & Push image (staging)",
        ),
        _workflow_step_by_name(
            ".github/workflows/cd.yml",
            "build-production",
            "Build & Push image (production)",
        ),
    )


def _build_publish_scan_step_with_secret_index_args() -> dict[str, object]:
    """Return the build.yml publish image build that feeds the fail-closed scan."""

    return _workflow_step_by_name(
        ".github/workflows/build.yml",
        "publish",
        "Build Docker image for publish scan",
    )


def _workflow_step_names(path: str, job_name: str) -> list[str]:
    """Return display names for a workflow job's steps."""

    return [str(step["name"]) for step in _workflow_steps(path, job_name)]


def _requirement_package_versions(path: Path, package_name: str) -> set[str]:
    """Return exact or minimum package versions declared in a requirement surface."""

    canonical_package_name = canonicalize_name(package_name)
    versions: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(PIP_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        if canonicalize_name(requirement.name) != canonical_package_name:
            continue
        for specifier in requirement.specifier:
            if specifier.operator in {"==", ">="}:
                versions.add(specifier.version)
    return versions


def _requirement_package_names(path: Path) -> set[str]:
    """Return canonical package names declared in a requirement surface."""

    package_names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(PIP_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        package_names.add(canonicalize_name(requirement.name))
    return package_names


def _requirement_entries(path: Path) -> list[Requirement]:
    """Return parsed package requirement entries, excluding pip directives."""

    requirements: list[Requirement] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(PIP_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        try:
            requirements.append(Requirement(line))
        except InvalidRequirement as exc:
            raise AssertionError(f"{path.name}: invalid requirement entry: {line}") from exc
    return requirements


def _requirement_is_exact_pin(requirement: Requirement) -> bool:
    """Return True when a requirement entry uses a concrete package==version pin."""

    return requirement.url is None and any(
        specifier.operator == "==" and not specifier.version.endswith(".*")
        for specifier in requirement.specifier
    )


def test_requirement_parser_canonicalizes_names_and_skips_non_requirements(tmp_path: Path) -> None:
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text(
        "\n".join(
            (
                "--extra-index-url https://download.pytorch.org/whl/cpu",
                "Torch~=2.11",
                "sentence-transformers @ https://example.invalid/sentence.whl",
                "-e git+https://example.invalid/repo.git#egg=ignored",
            )
        ),
        encoding="utf-8",
    )

    package_names = _requirement_package_names(requirements_path)
    assert "torch" in package_names
    assert "sentence-transformers" in package_names
    assert "ignored" not in package_names


def test_dependency_security_schema_blocks_known_bad_litellm_versions() -> None:
    schema = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "dependency_security_schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert schema["blocked_versions"]["litellm"] == ["==1.82.7", "==1.82.8"]


def test_python_setup_action_uses_locked_installer_not_floating_tools() -> None:
    action_text = (REPO_ROOT / ".github" / "actions" / "python-setup" / "action.yml").read_text(
        encoding="utf-8"
    )

    assert "install_locked_python_requirements.py" in action_text
    assert "${{ github.workspace }}/scripts/ci/install_locked_python_requirements.py" in action_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in action_text
    assert '--index-url "$PULSEPLATE_PYTHON_INDEX_URL"' in action_text
    assert "${{ inputs.requirements-profile }}" in action_text
    assert "${{ inputs.ci-lite-requirements-file }}" in action_text
    assert "${{ inputs.rag-vector-requirements-file }}" in action_text
    assert "${{ inputs.install-dev-deps }}" in action_text
    assert "${{ inputs.install-test-deps }}" in action_text
    assert "${{ inputs.test-requirements-file }}" in action_text
    assert "${{ inputs.install-mode }}" in action_text
    assert "${{ inputs.skip-base-install != 'true' }}" in action_text
    assert (
        "::error::requirements-profile cannot be combined with install-dev-deps/install-test-deps"
        in action_text
    )
    assert "::error::Expected requirements.txt when requirements-profile is runtime" in action_text
    assert (
        "::error::Expected requirements-dev.txt when requirements-profile is runtime-dev"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.test-requirements-file }} when requirements-profile is runtime-test"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.ci-lite-requirements-file }} when requirements-profile is ci-test"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.test-requirements-file }} when requirements-profile is ci-test"
        in action_text
    )
    assert (
        "::error::Expected ${{ inputs.ci-lite-requirements-file }} when requirements-profile is ci-lite"
        in action_text
    )
    assert (
        "::error::Expected requirements.txt when requirements-profile is rag-vector" in action_text
    )
    assert (
        "::error::Expected ${{ inputs.rag-vector-requirements-file }} when requirements-profile is rag-vector"
        in action_text
    )
    assert "::error::Expected requirements.txt for locked dependency install" in action_text
    assert "::error::Expected requirements-dev.txt when install-dev-deps is true" in action_text
    assert (
        "::error::Expected ${{ inputs.test-requirements-file }} when install-test-deps is true"
        in action_text
    )
    assert "--requirements-profile" in action_text
    assert "--ci-lite-requirements-file" in action_text
    assert "--rag-vector-requirements-file" in action_text
    assert "skipping base dependency install" not in action_text
    assert "pre-commit>=" not in action_text
    assert "bandit>=" not in action_text
    assert "pytest>=" not in action_text
    assert "pytest-cov>=" not in action_text
    assert "requirements-dev.txt via install_locked_python_requirements.py" in action_text
    assert (
        "${{ inputs.test-requirements-file }} via install_locked_python_requirements.py"
        in action_text
    )


def test_local_bootstrap_surfaces_use_locked_installer_and_virtualenv_guard() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    dev_shell_text = (REPO_ROOT / "scripts" / "dev_shell.sh").read_text(encoding="utf-8")
    installer_text = (
        REPO_ROOT / "scripts" / "ci" / "install_locked_python_requirements.py"
    ).read_text(encoding="utf-8")

    assert "install_locked_python_requirements.py" in makefile_text
    assert "--require-virtualenv" in makefile_text
    assert "ensure-python-proxy" in makefile_text
    assert "Export PULSEPLATE_PYTHON_INDEX_URL" in makefile_text
    assert "PIP_REQUIRE_VIRTUALENV=1" in dev_shell_text
    assert "install_locked_python_requirements.py" in dev_shell_text
    assert "Export PULSEPLATE_PYTHON_INDEX_URL" in dev_shell_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in installer_text


def test_canonical_ci_and_docker_use_supply_chain_guardrails() -> None:
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    nightly_text = (REPO_ROOT / ".github" / "workflows" / "nightly.yml").read_text(encoding="utf-8")
    docker_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose_text = (REPO_ROOT / "docker-compose.yaml").read_text(encoding="utf-8")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    dockerignore_text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    installer_text = (
        REPO_ROOT / "scripts" / "ci" / "install_locked_python_requirements.py"
    ).read_text(encoding="utf-8")
    init_test_db_text = (
        REPO_ROOT / ".github" / "actions" / "init-test-db" / "action.yml"
    ).read_text(encoding="utf-8")
    dependency_docs_text = (REPO_ROOT / "docs" / "DEPENDENCY_MANAGEMENT.md").read_text(
        encoding="utf-8"
    )
    blocked_hosts = set(locked_installer.BLOCKED_INDEX_HOSTS)

    assert "check_python_startup_hooks.py" in installer_text
    assert "--only-binary" in installer_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in installer_text
    assert any(host == ".".join(("pypi", "org")) for host in blocked_hosts)
    assert any(host == ".".join(("files", "pythonhosted", "org")) for host in blocked_hosts)
    assert any(host == ".".join(("test", "pypi", "org")) for host in blocked_hosts)
    assert "install_locked_python_requirements.py" in docker_text
    assert "ARG PULSEPLATE_PYTHON_INDEX_URL" in docker_text
    assert "constraints.txt" in docker_text
    assert "requirements-docker-runtime.txt" in docker_text
    assert "requirements-ci-lite.txt" in docker_text
    assert '--index-url "${PULSEPLATE_PYTHON_INDEX_URL}"' in docker_text
    assert 'ARG PULSEPLATE_REQUIREMENTS_FILE="requirements-docker-runtime.txt"' in docker_text
    assert (
        "requirements.txt|requirements-ci-lite.txt|requirements-docker-runtime.txt" in docker_text
    )
    assert '--requirements-file "${PULSEPLATE_REQUIREMENTS_FILE}"' in docker_text
    assert APPROVED_PROXY_ENV_EXPRESSION in ci_text
    assert APPROVED_TRUSTED_HOST_EXPRESSION in ci_text
    assert APPROVED_PROXY_ENV_EXPRESSION in security_text
    assert APPROVED_PROXY_ENV_EXPRESSION in nightly_text
    assert "PULSEPLATE_PYTHON_INDEX_URL: ${PULSEPLATE_PYTHON_INDEX_URL:?" in compose_text
    assert "PULSEPLATE_PYTHON_TRUSTED_HOST: ${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" in compose_text
    assert "--build-arg PULSEPLATE_PYTHON_INDEX_URL" in makefile_text
    assert "!requirements-docker-runtime.in" in dockerignore_text
    assert "!requirements-docker-runtime.txt" in dockerignore_text
    assert "!requirements-ci-lite.txt" in dockerignore_text
    assert "!constraints.txt" in dockerignore_text
    assert "!scripts/ci/check_python_startup_hooks.py" in dockerignore_text
    assert "!scripts/ci/emergency_python_wheels.json" in dockerignore_text
    assert "!scripts/ci/install_locked_python_requirements.py" in dockerignore_text
    assert (
        "COPY requirements.txt requirements-ci-lite.txt requirements-docker-runtime.txt constraints.txt ./"
        in docker_text
    )
    assert "COPY requirements.txt requirements-dev.txt constraints.txt ./" in docker_text
    production_root_index = docker_text.index("FROM runtime-base AS production")
    switch_to_root_index = docker_text.index("USER root", production_root_index)
    uninstall_pip_index = docker_text.index("/opt/venv/bin/python -m pip uninstall -y pip")
    return_to_non_root_index = docker_text.index("USER pulseplate", uninstall_pip_index)
    assert (
        production_root_index
        < switch_to_root_index
        < uninstall_pip_index
        < return_to_non_root_index
    )
    assert "install_locked_python_requirements.py" in dependency_docs_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in dependency_docs_text
    assert "Run: make venv-sync" in init_test_db_text
    build_workflow_text = (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(
        encoding="utf-8"
    )
    trivy_workflow_text = (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(
        encoding="utf-8"
    )
    for workflow_text in (
        build_workflow_text,
        trivy_workflow_text,
    ):
        assert "Docker image telemetry collection failed; reporting remains advisory-only." not in (
            workflow_text
        )
        assert "scripts/ci/check_docker_image_budget.py" in workflow_text
        assert "docs/telemetry/docker_image_budget.production.json" in workflow_text
        assert "docker-image-budget-check.json" in workflow_text
        assert "docker-image-budget-check.md" in workflow_text
        assert "if-no-files-found: warn" in workflow_text

    assert "if-no-files-found: warn" in trivy_workflow_text
    assert "set -euo pipefail" in trivy_workflow_text.split("- name: Install Trivy via apt", 1)[1]


@pytest.mark.parametrize("workflow_path", LOCKED_INSTALL_WORKFLOW_PATHS)
def test_all_changed_python_install_surfaces_use_locked_installer(workflow_path: str) -> None:
    workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")

    assert (
        "install_locked_python_requirements.py" in workflow_text
        or ".github/actions/python-setup" in workflow_text
        or 'pip_index_args=(--index-url "$PULSEPLATE_PYTHON_INDEX_URL")' in workflow_text
    )
    assert "PULSEPLATE_PYTHON_INDEX_URL" in workflow_text
    for blocked_host in locked_installer.BLOCKED_INDEX_HOSTS:
        assert blocked_host not in workflow_text


@pytest.mark.parametrize("workflow_path", PROXY_WORKFLOW_ENV_PATHS)
def test_proxy_backed_workflows_support_vars_or_secrets(workflow_path: str) -> None:
    workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")

    assert APPROVED_PROXY_ENV_EXPRESSION in workflow_text
    assert APPROVED_TRUSTED_HOST_EXPRESSION in workflow_text


def test_no_canonical_workflow_uses_unscoped_public_pip_install() -> None:
    for workflow_path in LOCKED_INSTALL_WORKFLOW_PATHS:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        lines = workflow_text.splitlines()
        for index, line in enumerate(lines):
            if not PIP_INSTALL_PATTERN.search(line):
                continue
            context = "\n".join(lines[max(0, index - 6) : index + 1])
            assert "PULSEPLATE_PYTHON_INDEX_URL" in context


def test_security_scan_workflow_uses_ci_lite_direct_proxy_setup() -> None:
    setup_step = _python_setup_step(".github/workflows/security.yml", "bandit")

    assert setup_step["with"]["python-version"] == CANONICAL_PYTHON
    assert setup_step["with"]["requirements-profile"] == "ci-lite"
    assert setup_step["with"]["install-mode"] == "direct-proxy"

    install_step = next(
        step
        for step in _workflow_steps(".github/workflows/security.yml", "bandit")
        if step.get("name") == "Install security tooling"
    )
    install_script = install_step["run"]
    assert "bandit==" not in install_script
    assert '"safety>=3.8.1"' in install_script
    assert 'python -m pip install "${pip_index_args[@]}"' in install_script
    assert "-c constraints.txt" in install_script


def test_constraints_keep_dependency_security_floors_aligned() -> None:
    constraints_path = REPO_ROOT / "constraints.txt"
    requirements_in = REPO_ROOT / "requirements.in"
    requirements_ci_lite_in = REPO_ROOT / "requirements-ci-lite.in"

    constraints_text = constraints_path.read_text(encoding="utf-8")
    assert "flake8 removed in favor of ruff" not in constraints_text
    assert "replaces flake8" not in constraints_text
    assert _requirement_package_versions(constraints_path, "safety") == {"3.8.1"}

    constraints_pyarrow = _requirement_package_versions(constraints_path, "pyarrow")
    assert constraints_pyarrow == {"20.0.0"}
    assert constraints_pyarrow == _requirement_package_versions(requirements_in, "pyarrow")
    assert constraints_pyarrow == _requirement_package_versions(
        requirements_ci_lite_in,
        "pyarrow",
    )
    for lock_surface in (
        REPO_ROOT / "requirements.txt",
        REPO_ROOT / "requirements-ci-lite.txt",
        REPO_ROOT / "requirements-lock.txt",
    ):
        pinned_versions = _requirement_package_versions(lock_surface, "pyarrow")
        assert pinned_versions
        assert all(Version(version) >= Version("20.0.0") for version in pinned_versions)


def test_ci_security_job_installs_safety_through_locked_installer() -> None:
    install_step = next(
        step
        for step in _workflow_steps(".github/workflows/ci.yml", "security")
        if step.get("name") == "Install Safety"
    )
    install_script = install_step["run"]

    assert "scripts/ci/install_locked_python_requirements.py" in install_script
    assert "--python-executable python" not in install_script
    assert "--requirements-file requirements-security.txt" in install_script
    assert "--install-mode direct-proxy" in install_script
    assert "--emergency-wheel-manifest scripts/ci/emergency_python_wheels.json" in install_script
    assert "python -m pip install" not in install_script


def test_security_requirements_pin_safety_and_regex_floor() -> None:
    requirements_text = (REPO_ROOT / "requirements-security.txt").read_text(encoding="utf-8")
    emergency_manifest = json.loads(
        (REPO_ROOT / "scripts/ci/emergency_python_wheels.json").read_text(encoding="utf-8")
    )

    assert "safety==3.8.1" in requirements_text
    assert "pyyaml==6.0.3" in requirements_text
    assert "regex==2026.5.9" in requirements_text
    assert any(
        artifact.get("package") == "regex"
        and artifact.get("version") == "2026.5.9"
        and artifact.get("filename", "").endswith("manylinux_2_28_x86_64.whl")
        and "sha256_parts" in artifact
        for artifact in emergency_manifest["artifacts"]
    )


@pytest.mark.parametrize(
    "job_name", ("test", "performance-test", "integration-test", "coverage-merge")
)
def test_nightly_workflow_jobs_use_runtime_dev_direct_proxy_setup(job_name: str) -> None:
    setup_step = _python_setup_step(".github/workflows/nightly.yml", job_name)

    assert setup_step["with"]["python-version"] == CANONICAL_PYTHON
    assert setup_step["with"]["requirements-profile"] == "runtime-dev"
    assert setup_step["with"]["install-mode"] == "direct-proxy"

    assert all(
        "install_locked_python_requirements.py" not in step.get("run", "")
        for step in _workflow_steps(".github/workflows/nightly.yml", job_name)
    )


def test_ci_main_full_suite_checkout_uses_pinned_checkout_action() -> None:
    """Ensure the main CI diagnostic job keeps the immutable checkout action pin."""
    checkout_step = _workflow_step_by_name(".github/workflows/ci.yml", "test-main", "Checkout")

    assert checkout_step["uses"] == PINNED_CHECKOUT_ACTION


def test_ci_workflow_uses_single_direct_proxy_python_install_path_per_job() -> None:
    import yaml

    ci_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    jobs = ci_workflow["jobs"]

    direct_proxy_jobs = (
        "lint",
        "security",
        "openapi-sync",
        "diff-coverage",
        "test-pr",
        "test-feature",
        "test-main",
    )
    for job_name in direct_proxy_jobs:
        setup_step = _python_setup_step(".github/workflows/ci.yml", job_name)
        assert setup_step["with"]["install-mode"] == "direct-proxy"

    for job_name in ("lint", "security", "openapi-sync", "diff-coverage"):
        setup_step = _python_setup_step(".github/workflows/ci.yml", job_name)
        assert setup_step["with"]["requirements-profile"] == "ci-lite"
        assert "install-dev-deps" not in setup_step["with"]

    for job_name in ("test-pr", "test-feature", "test-main"):
        setup_step = _python_setup_step(".github/workflows/ci.yml", job_name)
        assert setup_step["with"]["requirements-profile"] == "ci-test"
        assert "install-test-deps" not in setup_step["with"]
        assert all(step.get("name") != "Install dependencies" for step in jobs[job_name]["steps"])


def test_frontend_ci_workflow_uses_ci_lite_python_setup() -> None:
    setup_step = _python_setup_step(".github/workflows/frontend-ci.yml", "build-and-test")
    workflow_events = _workflow_events(".github/workflows/frontend-ci.yml")
    expected_paths = (
        "requirements.txt",
        "requirements-ci-lite.in",
        "requirements-ci-lite.txt",
        "constraints.txt",
        ".github/actions/python-setup/**",
        "scripts/ci/install_locked_python_requirements.py",
        "scripts/ci/check_python_startup_hooks.py",
        "scripts/ci/emergency_python_wheels.json",
        "tests/test_python_supply_chain_controls.py",
    )

    assert setup_step["with"]["python-version"] == "${{ env.PYTHON_VERSION }}"
    assert setup_step["with"]["requirements-profile"] == "ci-lite"
    assert setup_step["with"]["install-mode"] == "direct-proxy"
    for event_name in ("pull_request", "push"):
        event_paths = workflow_events[event_name]["paths"]
        for expected_path in expected_paths:
            assert expected_path in event_paths


def test_frontend_build_keeps_codecov_token_out_of_branch_controlled_build() -> None:
    build_step = _workflow_step_by_name(
        ".github/workflows/frontend-ci.yml",
        "build-and-test",
        "Build frontend",
    )
    build_env = build_step.get("env")
    vite_config = (REPO_ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")

    assert isinstance(build_env, dict)
    assert "CODECOV_TOKEN" not in build_env
    assert "secrets.CODECOV_TOKEN" not in str(build_step)
    assert build_env["CODECOV_BUNDLE_ANALYSIS"] == (
        "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' && 'true' || 'false' }}"
    )
    assert "@codecov/vite-plugin" not in vite_config
    assert "codecovVitePlugin" not in vite_config
    assert "uploadToken" not in vite_config
    assert "process.env.CODECOV_TOKEN" not in vite_config


def test_test_dependency_profile_is_split_from_dev_tooling() -> None:
    requirements_test = (REPO_ROOT / "requirements-test.txt").read_text(encoding="utf-8")

    assert "pytest==9.1.0" in requirements_test
    assert "pytest-cov==7.1.0" in requirements_test
    assert "pytest-xdist==3.8.0" in requirements_test
    assert "coverage[toml]==7.14.1" in requirements_test
    assert "pgvector==" in requirements_test
    assert "bandit==" not in requirements_test
    assert "pre-commit==" not in requirements_test
    assert "pip-audit==" not in requirements_test
    assert "mypy==" not in requirements_test
    assert "ruff==" not in requirements_test
    assert "sentence-transformers==" not in requirements_test
    assert "transformers==" not in requirements_test
    assert "torch==" not in requirements_test


def test_ci_lite_dependency_profile_excludes_ml_gpu_stack() -> None:
    requirements_ci_lite = (REPO_ROOT / "requirements-ci-lite.txt").read_text(encoding="utf-8")

    assert "fastapi==" in requirements_ci_lite
    assert "sqlalchemy==" in requirements_ci_lite
    assert "openai==" in requirements_ci_lite
    assert "pre-commit==" in requirements_ci_lite
    assert "bandit==" in requirements_ci_lite
    assert "diff-cover==" in requirements_ci_lite
    assert "pytest==" in requirements_ci_lite
    assert "sentence-transformers==" not in requirements_ci_lite
    assert "transformers==" not in requirements_ci_lite
    assert "torch==" not in requirements_ci_lite
    assert "pgvector==" not in requirements_ci_lite
    assert "triton==" not in requirements_ci_lite
    assert "cuda-bindings==" not in requirements_ci_lite
    assert "nvidia-cublas-cu12==" not in requirements_ci_lite


def test_base_runtime_dependency_profile_excludes_vector_ml_stack() -> None:
    requirements_runtime = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "fastapi==" in requirements_runtime
    assert "sqlalchemy==" in requirements_runtime
    assert "sentence-transformers==" not in requirements_runtime
    assert "transformers==" not in requirements_runtime
    assert "torch==" not in requirements_runtime
    assert "pgvector==" not in requirements_runtime


def test_docker_runtime_dependency_profile_excludes_ci_and_vector_stack() -> None:
    requirements_runtime = (REPO_ROOT / "requirements-docker-runtime.txt").read_text(
        encoding="utf-8"
    )

    assert "fastapi==" in requirements_runtime
    assert "sqlalchemy==" in requirements_runtime
    assert "bandit==" not in requirements_runtime
    assert "diff-cover==" not in requirements_runtime
    assert "pyarrow==" not in requirements_runtime
    assert "pre-commit==" not in requirements_runtime
    assert "pytest==" not in requirements_runtime
    assert "sentence-transformers==" not in requirements_runtime
    assert "transformers==" not in requirements_runtime
    assert "torch==" not in requirements_runtime
    assert "pgvector==" not in requirements_runtime


def test_rag_vector_dependency_profile_contains_extracted_vector_ml_stack() -> None:
    requirements_rag_vector = (REPO_ROOT / "requirements-rag-vector.txt").read_text(
        encoding="utf-8"
    )

    assert "sentence-transformers==" in requirements_rag_vector
    assert "transformers==" in requirements_rag_vector
    assert "torch==" in requirements_rag_vector
    assert "pgvector==" in requirements_rag_vector


def test_torch_and_vector_stack_stay_optional_to_rag_vector_profiles() -> None:
    for requirement_file in DEFAULT_INSTALL_REQUIREMENT_FILES:
        package_names = _requirement_package_names(REPO_ROOT / requirement_file)
        disallowed_packages = (
            OPTIONAL_VECTOR_STACK_PACKAGES
            if requirement_file != "requirements-test.txt"
            else ("sentence-transformers", "torch", "transformers")
        )
        for package in disallowed_packages:
            assert canonicalize_name(package) not in package_names

    observed_torch_versions: set[str] = set()
    for requirement_file in OPTIONAL_VECTOR_REQUIREMENT_FILES:
        requirement_path = REPO_ROOT / requirement_file
        package_names = _requirement_package_names(requirement_path)
        for package in OPTIONAL_VECTOR_STACK_PACKAGES:
            assert canonicalize_name(package) in package_names
        observed_torch_versions.update(_requirement_package_versions(requirement_path, "torch"))

    assert observed_torch_versions == {"2.11.0", "2.11.0+cpu"}


def test_eval_and_data_dependency_profiles_are_compiled_and_pinned() -> None:
    expected_sources = {
        "requirements-data.txt": "requirements-data.in",
        "requirements-evals.txt": "requirements-evals.in",
    }
    assert set(expected_sources) == set(LOCAL_MANUAL_EVAL_DATA_LOCKFILES)

    for requirement_file in LOCAL_MANUAL_EVAL_DATA_REQUIREMENT_FILES:
        assert (REPO_ROOT / requirement_file).is_file()

    data_input = REPO_ROOT / "requirements-data.in"
    eval_input = REPO_ROOT / "requirements-evals.in"
    assert _requirement_package_names(data_input) >= {"pandas", "pyarrow"}
    assert _requirement_package_names(eval_input).isdisjoint(
        {canonicalize_name(package) for package in DISABLED_RAGAS_EVAL_PACKAGES}
    )
    assert "\n-c requirements.txt\n" in f"\n{data_input.read_text(encoding='utf-8')}\n"
    eval_input_text = eval_input.read_text(encoding="utf-8")
    assert "\n-c requirements.txt\n" not in f"\n{eval_input_text}\n"
    assert "GHSA-95ww-475f-pr4f" in eval_input_text
    assert "GHSA-w8v5-vhqr-4h9v" in eval_input_text
    assert "RAGAS native execution is disabled" in eval_input_text

    for lockfile, source_file in expected_sources.items():
        lock_path = REPO_ROOT / lockfile
        lock_text = lock_path.read_text(encoding="utf-8")
        requirements = _requirement_entries(lock_path)

        assert "# This file is autogenerated by pip-compile" in lock_text
        assert "--allow-unsafe --no-emit-index-url" in lock_text
        assert f"--output-file={lockfile}" in lock_text
        assert source_file in lock_text
        if lockfile == "requirements-evals.txt":
            assert not requirements
        else:
            assert requirements
        assert "--index-url" not in lock_text
        assert "--extra-index-url" not in lock_text
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in lock_text
        assert str(REPO_ROOT) not in lock_text
        assert "/Users/" not in lock_text
        assert "http://" not in lock_text
        assert "https://" not in lock_text
        assert "ssh://" not in lock_text
        assert "file://" not in lock_text
        assert "git+" not in lock_text
        assert " @ " not in lock_text
        assert "--find-links" not in lock_text
        assert "--editable" not in lock_text
        assert "\n-e " not in lock_text
        assert all(_requirement_is_exact_pin(requirement) for requirement in requirements)


def test_eval_and_data_dependencies_stay_out_of_default_install_profiles() -> None:
    blocked_packages = {canonicalize_name(package) for package in LOCAL_MANUAL_EVAL_DATA_PACKAGES}

    for requirement_file in DEFAULT_AND_TOOLING_REQUIREMENT_FILES:
        requirement_path = REPO_ROOT / requirement_file
        if not requirement_path.exists():
            continue
        package_names = _requirement_package_names(requirement_path)
        assert blocked_packages.isdisjoint(package_names)


def test_eval_and_data_profiles_do_not_join_shared_install_routing() -> None:
    action_text = (REPO_ROOT / ".github" / "actions" / "python-setup" / "action.yml").read_text(
        encoding="utf-8"
    )
    docker_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore_text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "data" not in locked_installer.REQUIREMENTS_PROFILES
    assert "evals" not in locked_installer.REQUIREMENTS_PROFILES
    assert "requirements-data" not in action_text
    assert "requirements-evals" not in action_text
    assert "requirements-data" not in docker_text
    assert "requirements-evals" not in docker_text
    assert "!requirements-data" not in dockerignore_text
    assert "!requirements-evals" not in dockerignore_text


def test_dependency_docs_describe_eval_and_data_profiles_as_local_manual() -> None:
    dependency_docs = (REPO_ROOT / "docs" / "DEPENDENCY_MANAGEMENT.md").read_text(encoding="utf-8")
    evals_agents = (REPO_ROOT / "evals" / "AGENTS.md").read_text(encoding="utf-8")
    ragas_setup = (REPO_ROOT / "docs" / "evals" / "RAGAS_SETUP.md").read_text(encoding="utf-8")

    for requirement_file in LOCAL_MANUAL_EVAL_DATA_REQUIREMENT_FILES:
        assert requirement_file in dependency_docs

    assert "local/manual offline" in dependency_docs
    assert "not shared GitHub Actions `requirements-profile` values" in dependency_docs
    assert "runtime, Docker, or generic CI lanes" in dependency_docs
    assert "scripts/build_food_db.py" in dependency_docs
    assert "scripts/build_recipe_db.py" in dependency_docs
    assert "pandas" in dependency_docs
    assert "pyarrow" in dependency_docs
    assert "RAGAS native execution is disabled" in dependency_docs
    assert "GHSA-95ww-475f-pr4f" in dependency_docs
    assert "GHSA-w8v5-vhqr-4h9v" in dependency_docs
    assert "diskcache" in dependency_docs.casefold()
    assert (
        ".venv/bin/python -m piptools compile --allow-unsafe --no-emit-index-url "
        "--output-file=requirements-data.txt requirements-data.in"
    ) in dependency_docs
    assert (
        ".venv/bin/python -m piptools compile --allow-unsafe --no-emit-index-url "
        "--output-file=requirements-evals.txt requirements-evals.in"
    ) in dependency_docs
    assert "requirements-evals.in" in evals_agents
    assert "requirements-evals.txt" in evals_agents
    assert "RAGAS native execution is disabled" in evals_agents
    assert "lazy-imported" in evals_agents
    assert "requirements-evals.in" in ragas_setup
    assert "requirements-evals.txt" in ragas_setup
    assert "RAGAS native execution is disabled" in ragas_setup
    assert "GHSA-95ww-475f-pr4f" in ragas_setup
    assert "GHSA-w8v5-vhqr-4h9v" in ragas_setup
    assert "--no-emit-index-url --output-file=requirements-evals.txt" in ragas_setup


def test_production_target_docker_workflows_use_runtime_requirements_profile() -> None:
    cd_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "cd.yml").read_text(encoding="utf-8")
    )
    build_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
    )
    trivy_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(encoding="utf-8")
    )

    def _build_args_for_step(workflow: dict[str, object], job_name: str, step_name: str) -> str:
        steps = workflow["jobs"][job_name]["steps"]
        for step in steps:
            if step.get("name") == step_name:
                return step["with"]["build-args"]
        raise AssertionError(f"Missing workflow step: {job_name}.{step_name}")

    local_build_args = _build_args_for_step(
        build_workflow, "build", "Build Docker image (local, for tests)"
    )
    publish_build_args = _build_args_for_step(
        build_workflow, "publish", "Build Docker image for publish scan"
    )
    cd_staging_build_args = _build_args_for_step(
        cd_workflow, "build", "Build & Push image (staging)"
    )
    cd_production_build_args = _build_args_for_step(
        cd_workflow, "build-production", "Build & Push image (production)"
    )
    trivy_build_args = _build_args_for_step(
        trivy_workflow, "build", "Build Docker image (production target)"
    )

    expected_arg = "PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt"
    assert expected_arg in local_build_args
    assert expected_arg in publish_build_args
    assert expected_arg in cd_staging_build_args
    assert expected_arg in cd_production_build_args
    assert expected_arg in trivy_build_args


def test_provenance_enabled_docker_builds_keep_private_index_out_of_build_args() -> None:
    publish_scan_step = _build_publish_scan_step_with_secret_index_args()
    publish_scan_with = publish_scan_step["with"]
    publish_scan_build_args = publish_scan_with["build-args"]
    publish_scan_secret_envs = publish_scan_with["secret-envs"]

    assert publish_scan_with["push"] is False
    assert publish_scan_with["load"] is True
    assert publish_scan_with["provenance"] is False
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in publish_scan_build_args
    assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in publish_scan_build_args
    assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in publish_scan_secret_envs
    assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in publish_scan_secret_envs

    for step in _pushed_docker_steps_with_secret_index_args():
        assert step["with"]["provenance"] == "mode=min"
        build_args = step["with"]["build-args"]
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in build_args
        assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in build_args
        build_secret_envs = step["with"]["secret-envs"]
        assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in build_secret_envs
        assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in build_secret_envs


def test_production_target_docker_workflows_run_runtime_surface_guard() -> None:
    workflow_paths = (
        ".github/workflows/build.yml",
        ".github/workflows/trivy.yml",
    )

    for workflow_path in workflow_paths:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        assert "scripts/ci/check_docker_runtime_dependency_surface.py" in workflow_text
        assert "--blocked-debian-package apt" in workflow_text
        assert "--blocked-debian-package gpgv" in workflow_text
        assert "--blocked-debian-package libgnutls30" in workflow_text
        assert "--output-json docker-runtime-dependency-surface.json" in workflow_text


def test_dependency_submission_workflow_tracks_runtime_and_optional_manifests() -> None:
    workflow_events = _workflow_events(".github/workflows/python-dependency-submission.yml")
    expected_paths = {
        "requirements-data.in",
        "requirements-data.txt",
        "requirements-docker-runtime.in",
        "requirements-docker-runtime.txt",
        "requirements-evals.in",
        "requirements-evals.txt",
        "requirements-rag-vector.in",
        "requirements-rag-vector.txt",
        "requirements-rag-vector-cpu.in",
        "requirements-rag-vector-cpu.txt",
    }

    for event_name in ("push", "pull_request"):
        event_paths = set(workflow_events[event_name]["paths"])
        assert expected_paths <= event_paths


def test_python_dependency_submission_uses_profile_scoped_graph_roots() -> None:
    workflow = _load_workflow(".github/workflows/python-dependency-submission.yml")
    jobs = workflow["jobs"]
    action = "advanced-security/component-detection-dependency-submission-action@" + "".join(
        (
            "b876b8cc",
            "341a5397",
            "0394b33e",
            "a0ca4e86",
            "c25542de",
        )
    )

    pr_validation_job = jobs["dependency-submission-pr-validation"]
    assert pr_validation_job["if"] == "github.event_name == 'pull_request'"
    assert pr_validation_job["permissions"] == {"contents": "read"}
    assert "dependency submission API" in pr_validation_job["steps"][0]["run"]

    expected_jobs = {
        "runtime-dependency-submission": {
            "correlator": "python-dependency-submission-runtime",
            "root": "pulseplate-python-runtime-dependency-root",
            "must_copy": ("requirements-ci-lite.txt", "requirements-docker-runtime.txt"),
            "must_not_copy": ("requirements-evals.txt", "requirements-rag-vector.txt"),
        },
        "eval-data-dependency-submission": {
            "correlator": "python-dependency-submission-eval-data",
            "root": "pulseplate-python-eval-data-dependency-root",
            "must_copy": ("requirements-data.txt", "requirements-evals.txt"),
            "must_not_copy": ("requirements-ci-lite.txt", "requirements-rag-vector.txt"),
        },
        "rag-vector-dependency-submission": {
            "correlator": "python-dependency-submission-rag-vector",
            "root": "pulseplate-python-rag-vector-dependency-root",
            "must_copy": ("requirements-rag-vector.txt", "requirements-rag-vector-cpu.txt"),
            "must_not_copy": ("requirements-ci-lite.txt", "requirements-evals.txt"),
        },
    }
    observed_correlators: set[str] = set()

    for job_name, expectation in expected_jobs.items():
        job = jobs[job_name]
        assert job["if"] == "github.event_name != 'pull_request'"
        checkout_step = next(
            step for step in job["steps"] if step.get("uses") == PINNED_CHECKOUT_ACTION
        )
        assert checkout_step["with"] == {"persist-credentials": False}
        prepare_step = next(
            step for step in job["steps"] if step.get("name", "").startswith("Prepare ")
        )
        prepare_script = prepare_step["run"]
        assert expectation["root"] in prepare_script
        for manifest in expectation["must_copy"]:
            assert manifest in prepare_script
        for manifest in expectation["must_not_copy"]:
            assert manifest not in prepare_script

        submit_step = next(step for step in job["steps"] if step.get("uses") == action)
        submit_with = submit_step["with"]
        observed_correlators.add(submit_with["correlator"])
        assert submit_with["correlator"] == expectation["correlator"]
        assert submit_with["filePath"] == f"${{{{ runner.temp }}}}/{expectation['root']}"
        assert submit_with["detectorsCategories"] == "Pip"
        assert submit_with["detectorArgs"] == "Pip=EnableIfDefaultOff,SimplePip=EnableIfDefaultOff"

    assert observed_correlators == {
        "python-dependency-submission-runtime",
        "python-dependency-submission-eval-data",
        "python-dependency-submission-rag-vector",
    }
    assert "python-dependency-submission" not in observed_correlators


def test_security_scan_workflow_audits_runtime_and_optional_manifests() -> None:
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    ci_pip_audit_text = (REPO_ROOT / "scripts" / "ci_pip_audit.sh").read_text(encoding="utf-8")
    safety_audit_text = (REPO_ROOT / "scripts" / "ci" / "run_safety_audit.py").read_text(
        encoding="utf-8"
    )

    assert "python3 scripts/ci/run_safety_audit.py" in ci_text
    assert "python3 scripts/ci/run_safety_audit.py" in security_text
    assert "requirements-docker-runtime.txt" in safety_audit_text
    assert "requirements-docker-runtime.txt" in ci_pip_audit_text
    assert "requirements-data.txt" in safety_audit_text
    assert "requirements-data.txt" in ci_pip_audit_text
    assert "requirements-evals.txt" in safety_audit_text
    assert "requirements-evals.txt" in ci_pip_audit_text
    assert "requirements-rag-vector.txt" in safety_audit_text
    assert "requirements-rag-vector.txt" in ci_pip_audit_text
    assert "requirements-rag-vector-cpu.txt" in safety_audit_text
    assert "requirements-rag-vector-cpu.txt" in ci_pip_audit_text


def test_pip_audit_helper_invokes_cpu_rag_vector_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log_path = tmp_path / "pip-audit-args.log"
    fake_pip_audit = fake_bin / "pip-audit"
    fake_pip_audit.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${PIP_AUDIT_LOG}"
output=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -o)
      output="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [[ -n "${output}" ]]; then
  printf '{}\n' > "${output}"
fi
""",
        encoding="utf-8",
    )
    fake_pip_audit.chmod(0o755)
    for manifest in (
        "requirements.txt",
        "requirements-docker-runtime.txt",
        "requirements-data.txt",
        "requirements-evals.txt",
        "requirements-rag-vector.txt",
        "requirements-rag-vector-cpu.txt",
    ):
        (tmp_path / manifest).write_text("example==1.0.0\n", encoding="utf-8")

    env = os.environ.copy()
    env["CI"] = "1"
    env["PATH"] = os.pathsep.join((str(fake_bin), "/usr/bin", "/bin", "/usr/sbin", "/sbin"))
    env["PIP_AUDIT_LOG"] = str(log_path)

    result = subprocess.run(
        ["/bin/bash", str(REPO_ROOT / "scripts" / "ci_pip_audit.sh")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert (
        "-r requirements-rag-vector-cpu.txt -f json -o pip-audit-requirements-rag-vector-cpu.json"
        in log_path.read_text(encoding="utf-8")
    )
    assert (
        "-r requirements-data.txt -f json -o pip-audit-requirements-data.json"
        in log_path.read_text(encoding="utf-8")
    )
    assert (
        "-r requirements-evals.txt -f json -o pip-audit-requirements-evals.json"
        in log_path.read_text(encoding="utf-8")
    )
    assert (tmp_path / "pip-audit-requirements-rag-vector-cpu.json").exists()
    assert (tmp_path / "pip-audit-requirements-data.json").exists()
    assert (tmp_path / "pip-audit-requirements-evals.json").exists()


def test_safety_dependency_audit_uses_shared_helper_without_shell_loop() -> None:
    workflow_paths = (
        ".github/workflows/ci.yml",
        ".github/workflows/security.yml",
    )
    safety_audit_text = (REPO_ROOT / "scripts" / "ci" / "run_safety_audit.py").read_text(
        encoding="utf-8"
    )

    for workflow_path in workflow_paths:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        step_name = (
            "Dependency audit with Safety"
            if workflow_path.endswith("ci.yml")
            else "Run Safety (dependency audit with policy)"
        )
        job_name = "security" if workflow_path.endswith("ci.yml") else "bandit"
        safety_step = _workflow_step_by_name(workflow_path, job_name, step_name)

        assert "python3 scripts/ci/run_safety_audit.py" in workflow_text
        assert safety_step["env"]["SAFETY_API_KEY"] == "${{ secrets.SAFETY_API_KEY }}"
        assert "safety-*.json" in workflow_text
        assert "safety-*.txt" in workflow_text
        assert "safety-*.log" in workflow_text
        assert 'manifests=("requirements.txt")' not in workflow_text
        assert 'cp "${report_json}" safety-report.json' not in workflow_text
        assert ".github/scripts/parse-safety-report.py" not in workflow_text

    assert '"scan"' in safety_audit_text
    assert '"check"' not in safety_audit_text
    assert "SAFETY_API_KEY" in safety_audit_text

    nightly_text = (REPO_ROOT / ".github" / "workflows" / "nightly.yml").read_text(encoding="utf-8")
    assert "safety check --json" not in nightly_text
    assert "SAFETY_API_KEY" in nightly_text


def test_bandit_high_gate_uses_shared_summary_helper_without_inline_parsers() -> None:
    workflow_paths = (
        ".github/workflows/ci.yml",
        ".github/workflows/security.yml",
    )
    summary_helper_text = (REPO_ROOT / "scripts" / "ci" / "summarize_bandit_report.py").read_text(
        encoding="utf-8"
    )

    for workflow_path in workflow_paths:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        step_name = (
            "Enforce Bandit HIGH severity gate"
            if workflow_path.endswith("ci.yml")
            else "Run Bandit (security lint)"
        )
        job_name = "security" if workflow_path.endswith("ci.yml") else "bandit"
        bandit_step = _workflow_step_by_name(workflow_path, job_name, step_name)
        bandit_script = str(bandit_step["run"])

        assert "python3 scripts/ci/summarize_bandit_report.py" in workflow_text
        assert "--report bandit-report.json" in bandit_script
        assert "--fail-on-high" in bandit_script
        assert 'select(.issue_severity == "HIGH")' not in workflow_text
        assert "json.loads(report.read_text())" not in bandit_script

    assert "issue_severity" in summary_helper_text
    assert "fail_on_high" in summary_helper_text


def test_requirements_lock_excludes_optional_rag_vector_stack() -> None:
    requirements_lock = (REPO_ROOT / "requirements-lock.txt").read_text(encoding="utf-8")

    assert "pgvector==" not in requirements_lock
    assert "sentence-transformers==" not in requirements_lock
    assert "transformers==" not in requirements_lock
    assert "torch==" not in requirements_lock


def test_ci_risk_profile_tracks_runtime_and_optional_manifests() -> None:
    risk_profile_text = (REPO_ROOT / "scripts" / "ci" / "ci_risk_profile.py").read_text(
        encoding="utf-8"
    )

    assert '"requirements-docker-runtime.in"' in risk_profile_text
    assert '"requirements-docker-runtime.txt"' in risk_profile_text
    assert '"requirements-data.in"' in risk_profile_text
    assert '"requirements-data.txt"' in risk_profile_text
    assert '"requirements-evals.in"' in risk_profile_text
    assert '"requirements-evals.txt"' in risk_profile_text
    assert '"requirements-rag-vector.in"' in risk_profile_text
    assert '"requirements-rag-vector.txt"' in risk_profile_text
    assert '"requirements-rag-vector-cpu.in"' in risk_profile_text
    assert '"requirements-rag-vector-cpu.txt"' in risk_profile_text


def test_docker_workflows_emit_image_telemetry_artifacts() -> None:
    build_workflow_text = (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(
        encoding="utf-8"
    )
    trivy_workflow_text = (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(
        encoding="utf-8"
    )

    for workflow_text in (
        build_workflow_text,
        trivy_workflow_text,
    ):
        assert "docker-runtime-dependency-surface.json" in workflow_text
        assert "scripts/ci/fetch_docker_image_baseline.py" in workflow_text
        assert "scripts/ci/docker_image_telemetry.py" in workflow_text
        assert "scripts/ci/check_docker_image_budget.py" in workflow_text
        assert "docs/telemetry/docker_image_baseline.production.json" in workflow_text
        assert "docs/telemetry/docker_image_budget.production.json" in workflow_text
        assert "--baseline-json docker-image-baseline.json" in workflow_text
        assert "docker-image-telemetry.json" in workflow_text
        assert "docker-image-telemetry.md" in workflow_text
        assert "docker-image-budget-check.json" in workflow_text
        assert "docker-image-budget-check.md" in workflow_text
        assert "GITHUB_STEP_SUMMARY" in workflow_text
        assert "actions/upload-artifact@" in workflow_text
        assert "workflow remains advisory-only" not in workflow_text

    build_workflow = _load_workflow(".github/workflows/build.yml")
    trivy_workflow = _load_workflow(".github/workflows/trivy.yml")

    build_job_permissions = build_workflow["jobs"]["build"]["permissions"]
    trivy_job_permissions = trivy_workflow["jobs"]["build"]["permissions"]
    producer_artifact_name = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Upload Docker telemetry artifact",
    )["with"]["name"]
    producer_artifact_paths = str(
        _workflow_step_by_name(
            ".github/workflows/build.yml",
            "build",
            "Upload Docker telemetry artifact",
        )["with"]["path"]
    )
    build_resolve_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Resolve Docker image telemetry baseline",
    )["run"]
    trivy_resolve_step = _workflow_step_by_name(
        ".github/workflows/trivy.yml",
        "build",
        "Resolve Docker image telemetry baseline",
    )["run"]
    build_budget_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Enforce Docker image budget",
    )
    trivy_budget_step = _workflow_step_by_name(
        ".github/workflows/trivy.yml",
        "build",
        "Enforce Docker image budget",
    )
    build_fail_budget_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Fail build job when Docker budget check failed",
    )
    trivy_fail_budget_step = _workflow_step_by_name(
        ".github/workflows/trivy.yml",
        "build",
        "Fail trivy job when Docker budget check failed",
    )
    build_step_names = _workflow_step_names(".github/workflows/build.yml", "build")
    trivy_step_names = _workflow_step_names(".github/workflows/trivy.yml", "build")

    assert build_job_permissions["actions"] == "read"
    assert build_job_permissions["contents"] == "read"
    assert trivy_job_permissions["actions"] == "read"
    assert trivy_job_permissions["contents"] == "read"
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in build_workflow_text
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in build_workflow_text
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in trivy_workflow_text
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in trivy_workflow_text
    assert producer_artifact_name == "docker-image-telemetry-build"
    assert producer_artifact_paths.splitlines().count("docker-image-telemetry.json") == 1
    assert f"--artifact-name {producer_artifact_name}" in build_resolve_step
    assert f"--artifact-name {producer_artifact_name}" in trivy_resolve_step
    assert "--workflow build.yml" in build_resolve_step
    assert "--workflow build.yml" in trivy_resolve_step
    assert (
        "--budget-json docs/telemetry/docker_image_budget.production.json"
        in build_budget_step["run"]
    )
    assert (
        "--budget-json docs/telemetry/docker_image_budget.production.json"
        in trivy_budget_step["run"]
    )
    assert build_budget_step["continue-on-error"] is True
    assert trivy_budget_step["continue-on-error"] is True
    assert build_fail_budget_step["if"] == "${{ steps.docker_image_budget.outcome == 'failure' }}"
    assert trivy_fail_budget_step["if"] == "${{ steps.docker_image_budget.outcome == 'failure' }}"
    assert build_step_names.index("Enforce Docker image budget") < build_step_names.index(
        "Test Docker image"
    )
    assert build_step_names.index("Test Docker image") < build_step_names.index(
        "Fail build job when Docker budget check failed"
    )
    assert trivy_step_names.index("Enforce Docker image budget") < trivy_step_names.index(
        "Run Trivy vulnerability scanner"
    )
    assert trivy_step_names.index("Run Trivy vulnerability scanner") < trivy_step_names.index(
        "Fail trivy job when Docker budget check failed"
    )


def test_pushed_docker_builds_do_not_use_max_provenance_with_secret_index_args() -> None:
    """Max-mode BuildKit provenance can expose secret-derived build arguments."""

    publish_scan_step = _build_publish_scan_step_with_secret_index_args()
    publish_scan_with = publish_scan_step["with"]
    publish_scan_build_args = publish_scan_with["build-args"]
    publish_scan_secret_envs = publish_scan_with["secret-envs"]

    assert publish_scan_with["push"] is False
    assert publish_scan_with["load"] is True
    assert publish_scan_with["provenance"] is False
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in publish_scan_build_args
    assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in publish_scan_build_args
    assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in publish_scan_secret_envs
    assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in publish_scan_secret_envs

    for step in _pushed_docker_steps_with_secret_index_args():
        step_with = step["with"]
        build_args = step_with["build-args"]
        secret_envs = step_with["secret-envs"]

        assert step_with["push"] is True
        assert step_with["provenance"] == "mode=min"
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in build_args
        assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in build_args
        assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in secret_envs
        assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in secret_envs


def test_push_to_registry_workflows_restore_signed_attestations_on_publish_lanes() -> None:
    build_workflow = _load_workflow(".github/workflows/build.yml")
    cd_workflow = _load_workflow(".github/workflows/cd.yml")

    local_build_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "build",
        "Build Docker image (local, for tests)",
    )
    publish_scan_step = _build_publish_scan_step_with_secret_index_args()
    publish_push_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "publish",
        "Push scanned Docker image",
    )
    pushed_steps = _pushed_docker_steps_with_secret_index_args()
    publish_sbom_step = _workflow_step_by_name(
        ".github/workflows/build.yml",
        "publish",
        "Attest Docker image SBOM",
    )
    staging_verify_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Verify staged image attestations",
    )
    staging_provenance_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Attest staged image provenance",
    )
    staging_sbom_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Attest staged image SBOM",
    )
    production_verify_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Verify production image attestations",
    )
    production_provenance_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Attest production image provenance",
    )
    production_sbom_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Attest production image SBOM",
    )
    staging_upload_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build",
        "Upload staging attestation verification artifact",
    )
    production_upload_step = _workflow_step_by_name(
        ".github/workflows/cd.yml",
        "build-production",
        "Upload production attestation verification artifact",
    )
    staging_step_names = _workflow_step_names(".github/workflows/cd.yml", "build")
    production_step_names = _workflow_step_names(".github/workflows/cd.yml", "build-production")

    assert local_build_step["with"]["load"] is True
    assert local_build_step["with"]["provenance"] is False
    assert publish_scan_step["with"]["load"] is True
    assert publish_scan_step["with"]["push"] is False
    assert publish_scan_step["with"]["provenance"] is False
    assert publish_push_step["id"] == "docker-build-push"
    assert "docker image push" in publish_push_step["run"]
    assert "digest=${digest}" in publish_push_step["run"]
    assert cd_workflow["jobs"]["build"]["permissions"]["attestations"] == "write"
    assert cd_workflow["jobs"]["build-production"]["permissions"]["attestations"] == "write"

    for step in pushed_steps:
        assert step["with"]["push"] is True
        assert step["with"]["provenance"] == "mode=min"
        assert step["with"]["sbom"] is True
        assert "PULSEPLATE_PYTHON_INDEX_URL" not in step["with"]["build-args"]
        assert "PULSEPLATE_PYTHON_TRUSTED_HOST" not in step["with"]["build-args"]
        assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in step["with"]["secret-envs"]
        assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in step["with"]["secret-envs"]

    for provenance_step in (staging_provenance_step, production_provenance_step):
        assert provenance_step["uses"].startswith(
            "actions/attest-build-provenance@b3e506e8c389afc651c5bacf2b8f2a1ea0557215"
        )
        assert provenance_step["with"]["push-to-registry"] is True
        assert provenance_step["with"]["subject-digest"] == "${{ steps.build.outputs.digest }}"

    for sbom_step in (staging_sbom_step, production_sbom_step):
        assert sbom_step["uses"].startswith(
            "actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26"
        )
        assert sbom_step["with"]["push-to-registry"] is True
        assert sbom_step["with"]["predicate-type"] == SBOM_PREDICATE_TYPE
        assert sbom_step["with"]["predicate-path"] == "docker-image-sbom.spdx.json"
        assert "sbom-path" not in sbom_step["with"]
        assert sbom_step["with"]["subject-digest"] == "${{ steps.build.outputs.digest }}"

    assert publish_sbom_step["uses"].startswith(
        "actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26"
    )
    assert publish_sbom_step["with"]["push-to-registry"] is True
    assert publish_sbom_step["with"]["predicate-type"] == SBOM_PREDICATE_TYPE
    assert publish_sbom_step["with"]["predicate-path"] == "sbom.spdx.json"
    assert "sbom-path" not in publish_sbom_step["with"]
    assert (
        publish_sbom_step["with"]["subject-digest"]
        == "${{ steps.docker-build-push.outputs.digest }}"
    )

    for verify_step in (staging_verify_step, production_verify_step):
        verify_script = verify_step["run"]
        verify_if = verify_step["if"]
        assert "always()" in verify_if
        assert "steps.build.outcome == 'success'" in verify_if
        assert "scripts/ci/check_docker_provenance_attestation.py" in verify_script
        assert '--repo "${{ github.repository }}"' in verify_script
        assert '--signer-workflow "${{ github.repository }}/.github/workflows/cd.yml"' in (
            verify_script
        )
        assert '--source-ref "${{ github.ref }}"' in verify_script
        assert "docker-provenance-attestation-check.json" in verify_script
        assert "docker-provenance-attestation-check.md" in verify_script

    # Staging verify must depend on all staging attestation steps
    staging_verify_if = staging_verify_step["if"]
    assert "steps.attest-staged-provenance.outcome == 'success'" in staging_verify_if
    assert "steps.generate-staged-sbom.outcome == 'success'" in staging_verify_if
    assert "steps.attest-staged-sbom.outcome == 'success'" in staging_verify_if

    # Production verify must depend on all production attestation steps
    production_verify_if = production_verify_step["if"]
    assert "steps.attest-production-provenance.outcome == 'success'" in production_verify_if
    assert "steps.generate-production-sbom.outcome == 'success'" in production_verify_if
    assert "steps.attest-production-sbom.outcome == 'success'" in production_verify_if

    assert staging_upload_step["with"]["name"] == "docker-provenance-attestation-check-cd-staging"
    assert (
        production_upload_step["with"]["name"]
        == "docker-provenance-attestation-check-cd-production"
    )
    assert staging_upload_step["with"]["if-no-files-found"] == "warn"
    assert production_upload_step["with"]["if-no-files-found"] == "warn"
    assert staging_step_names.index("Build & Push image (staging)") < staging_step_names.index(
        "Attest staged image provenance"
    )
    assert staging_step_names.index("Attest staged image SBOM") < staging_step_names.index(
        "Verify staged image attestations"
    )
    assert staging_step_names.index("Verify staged image attestations") < staging_step_names.index(
        "Check staging deploy readiness"
    )
    assert production_step_names.index(
        "Build & Push image (production)"
    ) < production_step_names.index("Attest production image provenance")
    assert production_step_names.index(
        "Attest production image SBOM"
    ) < production_step_names.index("Verify production image attestations")
    assert production_step_names.index("Verify production image attestations") < (
        production_step_names.index("Upload production attestation verification artifact")
    )
    assert cd_workflow["jobs"]["production-deploy-config"]["needs"] == [
        "production-gates",
        "build-production",
    ]
    expected_deploy_needs = [
        "production-gates",
        "build-production",
        "production-deploy-config",
        "release-control-plane-production-evidence",
    ]
    assert cd_workflow["jobs"]["deploy-production"]["needs"] == expected_deploy_needs
    assert cd_workflow["jobs"]["deploy-production-self-hosted"]["needs"] == expected_deploy_needs


def test_checked_in_docker_image_baseline_seed_has_expected_schema() -> None:
    baseline_payload = json.loads(
        (REPO_ROOT / "docs" / "telemetry" / "docker_image_baseline.production.json").read_text(
            encoding="utf-8"
        )
    )

    assert baseline_payload["baseline_source"] == "repo-seed-fallback"
    assert baseline_payload["image_size_bytes"] > 0
    assert baseline_payload["image_size_human"].endswith("MB")
    assert baseline_payload["baseline_reference"]["artifact_name"] == "docker-image-telemetry-build"
    assert baseline_payload["baseline_reference"]["workflow"] == "build.yml"
    assert baseline_payload["baseline_reference"]["seeded_from_run_id"] == 24771474567


def test_checked_in_docker_image_budget_policy_has_expected_schema() -> None:
    budget_payload = json.loads(
        (REPO_ROOT / "docs" / "telemetry" / "docker_image_budget.production.json").read_text(
            encoding="utf-8"
        )
    )

    assert budget_payload["budget_name"] == "production-backend-image"
    assert budget_payload["budget_version"] == 1
    assert budget_payload["budget_scope"] == "production-backend-image"
    assert budget_payload["max_image_size_bytes"] == 470000000
    assert budget_payload["max_positive_delta_bytes"] == 20000000
    assert (
        budget_payload["baseline_reference"]["baseline_file"]
        == "docs/telemetry/docker_image_baseline.production.json"
    )
    assert budget_payload["baseline_reference"]["workflow"] == "build.yml"
