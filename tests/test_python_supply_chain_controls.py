"""Regression tests for Python supply-chain hardening controls."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

import scripts.ci.install_locked_python_requirements as locked_installer

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
    ".github/workflows/docker-image.yml",
    ".github/workflows/docker-openapi-smoke.yml",
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


def _workflow_step_names(path: str, job_name: str) -> list[str]:
    """Return display names for a workflow job's steps."""

    return [str(step["name"]) for step in _workflow_steps(path, job_name)]


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
    docker_image_workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "docker-image.yml"
    ).read_text(encoding="utf-8")
    trivy_workflow_text = (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(
        encoding="utf-8"
    )
    for workflow_text in (
        build_workflow_text,
        docker_image_workflow_text,
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

    assert setup_step["with"]["python-version"] == "3.13.6"
    assert setup_step["with"]["requirements-profile"] == "ci-lite"
    assert setup_step["with"]["install-mode"] == "direct-proxy"

    install_step = next(
        step
        for step in _workflow_steps(".github/workflows/security.yml", "bandit")
        if step.get("name") == "Install security tooling"
    )
    install_script = install_step["run"]
    assert '"bandit==1.8.6"' in install_script
    assert '"safety>=3.7.0"' in install_script
    assert 'python -m pip install "${pip_index_args[@]}"' in install_script
    assert "-c constraints.txt" in install_script


@pytest.mark.parametrize(
    "job_name", ("test", "performance-test", "integration-test", "coverage-merge")
)
def test_nightly_workflow_jobs_use_runtime_dev_direct_proxy_setup(job_name: str) -> None:
    setup_step = _python_setup_step(".github/workflows/nightly.yml", job_name)

    assert setup_step["with"]["python-version"] == "3.13"
    assert setup_step["with"]["requirements-profile"] == "runtime-dev"
    assert setup_step["with"]["install-mode"] == "direct-proxy"

    assert all(
        "install_locked_python_requirements.py" not in step.get("run", "")
        for step in _workflow_steps(".github/workflows/nightly.yml", job_name)
    )


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


def test_test_dependency_profile_is_split_from_dev_tooling() -> None:
    requirements_test = (REPO_ROOT / "requirements-test.txt").read_text(encoding="utf-8")

    assert "pytest==9.0.3" in requirements_test
    assert "pytest-cov==7.1.0" in requirements_test
    assert "pytest-xdist==3.8.0" in requirements_test
    assert "coverage[toml]==7.13.5" in requirements_test
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


def test_production_target_docker_workflows_use_runtime_requirements_profile() -> None:
    cd_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "cd.yml").read_text(encoding="utf-8")
    )
    docker_image_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "docker-image.yml").read_text(encoding="utf-8")
    )
    docker_smoke_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "docker-openapi-smoke.yml").read_text(
            encoding="utf-8"
        )
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

    docker_image_build_args = _build_args_for_step(
        docker_image_workflow, "build", "Build the Docker image"
    )
    docker_smoke_build_args = _build_args_for_step(
        docker_smoke_workflow, "smoke", "Build Docker image"
    )
    local_build_args = _build_args_for_step(
        build_workflow, "build", "Build Docker image (local, for tests)"
    )
    publish_build_args = _build_args_for_step(
        build_workflow, "publish", "Build and push Docker image"
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
    assert expected_arg in docker_image_build_args
    assert expected_arg in docker_smoke_build_args
    assert expected_arg in local_build_args
    assert expected_arg in publish_build_args
    assert expected_arg in cd_staging_build_args
    assert expected_arg in cd_production_build_args
    assert expected_arg in trivy_build_args


def test_production_target_docker_workflows_run_runtime_surface_guard() -> None:
    workflow_paths = (
        ".github/workflows/build.yml",
        ".github/workflows/docker-image.yml",
        ".github/workflows/docker-openapi-smoke.yml",
        ".github/workflows/trivy.yml",
    )

    for workflow_path in workflow_paths:
        workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")
        assert "scripts/ci/check_docker_runtime_dependency_surface.py" in workflow_text
        assert "--output-json docker-runtime-dependency-surface.json" in workflow_text


def test_dependency_submission_workflow_tracks_runtime_and_optional_manifests() -> None:
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "python-dependency-submission.yml"
    ).read_text(encoding="utf-8")

    assert '"requirements-docker-runtime.in"' in workflow_text
    assert '"requirements-docker-runtime.txt"' in workflow_text
    assert '"requirements-rag-vector.in"' in workflow_text
    assert '"requirements-rag-vector.txt"' in workflow_text


def test_security_scan_workflow_audits_runtime_and_optional_manifests() -> None:
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    security_text = (REPO_ROOT / ".github" / "workflows" / "security.yml").read_text(
        encoding="utf-8"
    )
    ci_pip_audit_text = (REPO_ROOT / "scripts" / "ci_pip_audit.sh").read_text(encoding="utf-8")

    assert "requirements-docker-runtime.txt" in ci_text
    assert "requirements-docker-runtime.txt" in security_text
    assert "requirements-docker-runtime.txt" in ci_pip_audit_text
    assert "requirements-rag-vector.txt" in ci_text
    assert "requirements-rag-vector.txt" in security_text
    assert "requirements-rag-vector.txt" in ci_pip_audit_text


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
    assert '"requirements-rag-vector.in"' in risk_profile_text
    assert '"requirements-rag-vector.txt"' in risk_profile_text


def test_docker_workflows_emit_image_telemetry_artifacts() -> None:
    build_workflow_text = (REPO_ROOT / ".github" / "workflows" / "build.yml").read_text(
        encoding="utf-8"
    )
    docker_image_workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "docker-image.yml"
    ).read_text(encoding="utf-8")
    trivy_workflow_text = (REPO_ROOT / ".github" / "workflows" / "trivy.yml").read_text(
        encoding="utf-8"
    )

    for workflow_text in (
        build_workflow_text,
        docker_image_workflow_text,
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
    docker_image_workflow = _load_workflow(".github/workflows/docker-image.yml")
    trivy_workflow = _load_workflow(".github/workflows/trivy.yml")

    build_job_permissions = build_workflow["jobs"]["build"]["permissions"]
    docker_image_permissions = docker_image_workflow["permissions"]
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
    docker_image_resolve_step = _workflow_step_by_name(
        ".github/workflows/docker-image.yml",
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
    docker_image_budget_step = _workflow_step_by_name(
        ".github/workflows/docker-image.yml",
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
    docker_image_fail_budget_step = _workflow_step_by_name(
        ".github/workflows/docker-image.yml",
        "build",
        "Fail docker-image job when Docker budget check failed",
    )
    trivy_fail_budget_step = _workflow_step_by_name(
        ".github/workflows/trivy.yml",
        "build",
        "Fail trivy job when Docker budget check failed",
    )
    build_step_names = _workflow_step_names(".github/workflows/build.yml", "build")
    docker_image_step_names = _workflow_step_names(".github/workflows/docker-image.yml", "build")
    trivy_step_names = _workflow_step_names(".github/workflows/trivy.yml", "build")

    assert build_job_permissions["actions"] == "read"
    assert build_job_permissions["contents"] == "read"
    assert docker_image_permissions["actions"] == "read"
    assert docker_image_permissions["contents"] == "read"
    assert trivy_job_permissions["actions"] == "read"
    assert trivy_job_permissions["contents"] == "read"
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in build_workflow_text
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in build_workflow_text
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in docker_image_workflow_text
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in docker_image_workflow_text
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in trivy_workflow_text
    assert "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}" in trivy_workflow_text
    assert producer_artifact_name == "docker-image-telemetry-build"
    assert producer_artifact_paths.splitlines().count("docker-image-telemetry.json") == 1
    assert f"--artifact-name {producer_artifact_name}" in build_resolve_step
    assert f"--artifact-name {producer_artifact_name}" in docker_image_resolve_step
    assert f"--artifact-name {producer_artifact_name}" in trivy_resolve_step
    assert "--workflow build.yml" in build_resolve_step
    assert "--workflow build.yml" in docker_image_resolve_step
    assert "--workflow build.yml" in trivy_resolve_step
    assert (
        "--budget-json docs/telemetry/docker_image_budget.production.json"
        in build_budget_step["run"]
    )
    assert (
        "--budget-json docs/telemetry/docker_image_budget.production.json"
        in docker_image_budget_step["run"]
    )
    assert (
        "--budget-json docs/telemetry/docker_image_budget.production.json"
        in trivy_budget_step["run"]
    )
    assert build_budget_step["continue-on-error"] is True
    assert docker_image_budget_step["continue-on-error"] is True
    assert trivy_budget_step["continue-on-error"] is True
    assert build_fail_budget_step["if"] == "${{ steps.docker_image_budget.outcome == 'failure' }}"
    assert (
        docker_image_fail_budget_step["if"]
        == "${{ steps.docker_image_budget.outcome == 'failure' }}"
    )
    assert trivy_fail_budget_step["if"] == "${{ steps.docker_image_budget.outcome == 'failure' }}"
    assert build_step_names.index("Enforce Docker image budget") < build_step_names.index(
        "Test Docker image"
    )
    assert build_step_names.index("Test Docker image") < build_step_names.index(
        "Fail build job when Docker budget check failed"
    )
    assert docker_image_step_names.index("Enforce Docker image budget") < (
        docker_image_step_names.index("Fail docker-image job when Docker budget check failed")
    )
    assert trivy_step_names.index("Enforce Docker image budget") < trivy_step_names.index(
        "Run Trivy vulnerability scanner"
    )
    assert trivy_step_names.index("Run Trivy vulnerability scanner") < trivy_step_names.index(
        "Fail trivy job when Docker budget check failed"
    )


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
