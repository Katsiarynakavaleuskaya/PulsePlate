"""Regression tests for Python supply-chain hardening controls."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import scripts.ci.install_locked_python_requirements as locked_installer

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCKED_INSTALL_WORKFLOW_PATHS: tuple[str, ...] = (
    ".github/workflows/ci.yml",
    ".github/workflows/frontend-ci.yml",
    ".github/workflows/nightly-tests.yml",
    ".github/workflows/nightly.yml",
    ".github/workflows/security.yml",
)
CI_RECLAIM_JOB_NAMES: tuple[str, ...] = (
    "openapi-sync",
    "test-pr",
    "test-feature",
    "test-main",
)
PROXY_WORKFLOW_ENV_PATHS: tuple[str, ...] = LOCKED_INSTALL_WORKFLOW_PATHS + (
    ".github/workflows/build.yml",
    ".github/workflows/docker-image.yml",
    ".github/workflows/docker-openapi-smoke.yml",
    ".github/workflows/trivy.yml",
    ".github/workflows/cd.yml",
)
APPROVED_PROXY_ENV_EXPRESSION = (
    "${{ vars.PULSEPLATE_PYTHON_INDEX_URL || secrets.PULSEPLATE_PYTHON_INDEX_URL }}"
)
APPROVED_TRUSTED_HOST_EXPRESSION = (
    "${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST || secrets.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
)
DOCKER_RECLAIM_WORKFLOW_PATHS: tuple[str, ...] = (
    ".github/workflows/docker-image.yml",
    ".github/workflows/build.yml",
)
RECLAIM_STEP_NAME = "Reclaim runner disk before Python install"
RECLAIM_COMMAND = "sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc"
DOCKER_RECLAIM_STEP_NAME = "Reclaim runner disk before Docker build"
PIP_INSTALL_PATTERN = re.compile(r"\b\S*python\S*\s+-m\s+pip\s+install\b")


def _extract_workflow_job_block(*, workflow_text: str, job_name: str) -> str:
    job_marker = f"\n  {job_name}:\n"
    start_index = workflow_text.index(job_marker) + len(job_marker)
    next_job_match = re.search(r"^  [a-z0-9_-]+:\n", workflow_text[start_index:], re.MULTILINE)
    if next_job_match is None:
        return workflow_text[start_index:]
    next_job_index = start_index + next_job_match.start()
    return workflow_text[start_index:next_job_index]


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
    assert "${{ inputs.install-dev-deps }}" in action_text
    assert "${{ inputs.install-test-deps }}" in action_text
    assert "pre-commit>=" not in action_text
    assert "bandit>=" not in action_text
    assert "pytest>=" not in action_text
    assert "pytest-cov>=" not in action_text


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
    assert '--index-url "${PULSEPLATE_PYTHON_INDEX_URL}"' in docker_text
    assert APPROVED_PROXY_ENV_EXPRESSION in ci_text
    assert APPROVED_TRUSTED_HOST_EXPRESSION in ci_text
    assert APPROVED_PROXY_ENV_EXPRESSION in security_text
    assert APPROVED_PROXY_ENV_EXPRESSION in nightly_text
    assert "PULSEPLATE_PYTHON_INDEX_URL: ${PULSEPLATE_PYTHON_INDEX_URL:?" in compose_text
    assert "PULSEPLATE_PYTHON_TRUSTED_HOST: ${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" in compose_text
    assert "--build-arg PULSEPLATE_PYTHON_INDEX_URL" in makefile_text
    assert "!constraints.txt" in dockerignore_text
    assert "!scripts/ci/check_python_startup_hooks.py" in dockerignore_text
    assert "!scripts/ci/install_locked_python_requirements.py" in dockerignore_text
    assert "install_locked_python_requirements.py" in dependency_docs_text
    assert "PULSEPLATE_PYTHON_INDEX_URL" in dependency_docs_text
    assert "Run: make venv-sync" in init_test_db_text


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


def test_ci_locked_python_install_jobs_reclaim_runner_disk_before_install() -> None:
    workflow_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert workflow_text.count(RECLAIM_STEP_NAME) >= len(CI_RECLAIM_JOB_NAMES)
    assert RECLAIM_COMMAND in workflow_text
    assert "df -h" in workflow_text

    for job_name in CI_RECLAIM_JOB_NAMES:
        job_block = _extract_workflow_job_block(workflow_text=workflow_text, job_name=job_name)

        assert RECLAIM_STEP_NAME in job_block
        assert RECLAIM_COMMAND in job_block
        if job_name == "openapi-sync":
            assert job_block.index(RECLAIM_STEP_NAME) < job_block.index(
                "uses: ./.github/actions/python-setup"
            )
        else:
            assert job_block.index(RECLAIM_STEP_NAME) < job_block.index("Install dependencies")


@pytest.mark.parametrize("workflow_path", DOCKER_RECLAIM_WORKFLOW_PATHS)
def test_docker_build_workflows_reclaim_runner_disk_before_build(workflow_path: str) -> None:
    workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")

    assert DOCKER_RECLAIM_STEP_NAME in workflow_text
    assert RECLAIM_COMMAND in workflow_text
    assert "df -h" in workflow_text
