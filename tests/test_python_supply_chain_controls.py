"""Regression tests for Python supply-chain hardening controls."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCKED_INSTALL_WORKFLOW_PATHS: tuple[str, ...] = (
    ".github/workflows/ci.yml",
    ".github/workflows/frontend-ci.yml",
    ".github/workflows/nightly-tests.yml",
    ".github/workflows/nightly.yml",
)
CI_RECLAIM_JOB_NAMES: tuple[str, ...] = (
    "openapi-sync",
    "test-pr",
    "test-feature",
    "test-main",
)
RECLAIM_STEP_NAME = "Reclaim runner disk before Python install"
RECLAIM_COMMAND = "sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc"


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
    assert "${{ inputs.install-dev-deps }}" in action_text
    assert "${{ inputs.install-test-deps }}" in action_text
    assert "pre-commit>=" not in action_text
    assert "bandit>=" not in action_text
    assert "pytest>=" not in action_text
    assert "pytest-cov>=" not in action_text


def test_local_bootstrap_surfaces_use_locked_installer_and_virtualenv_guard() -> None:
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    dev_shell_text = (REPO_ROOT / "scripts" / "dev_shell.sh").read_text(encoding="utf-8")

    assert "install_locked_python_requirements.py" in makefile_text
    assert "--require-virtualenv" in makefile_text
    assert "PIP_REQUIRE_VIRTUALENV=1" in dev_shell_text
    assert "install_locked_python_requirements.py" in dev_shell_text


def test_canonical_ci_and_docker_use_supply_chain_guardrails() -> None:
    docker_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore_text = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    verify_env_text = (
        REPO_ROOT / "scripts" / "ci" / "check_local_verify_environment.py"
    ).read_text(encoding="utf-8")
    installer_text = (
        REPO_ROOT / "scripts" / "ci" / "install_locked_python_requirements.py"
    ).read_text(encoding="utf-8")

    assert "check_python_startup_hooks.py" in installer_text
    assert "spec_from_file_location" not in verify_env_text
    assert "sys.modules[" not in verify_env_text
    assert "--only-binary" in installer_text
    assert "spec_from_file_location" not in installer_text
    assert "sys.modules[" not in installer_text
    assert "install_locked_python_requirements.py" in docker_text
    assert "--guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py" in docker_text
    assert "constraints.txt" in docker_text
    assert "--upgrade-pip" not in docker_text
    assert "!constraints.txt" in dockerignore_text
    assert "!scripts/ci/check_python_startup_hooks.py" in dockerignore_text
    assert "!scripts/ci/install_locked_python_requirements.py" in dockerignore_text


@pytest.mark.parametrize("workflow_path", LOCKED_INSTALL_WORKFLOW_PATHS)
def test_all_changed_python_install_surfaces_use_locked_installer(workflow_path: str) -> None:
    workflow_text = (REPO_ROOT / workflow_path).read_text(encoding="utf-8")

    assert "install_locked_python_requirements.py" in workflow_text
    assert "--constraints-file constraints.txt" in workflow_text


def test_ci_locked_python_install_jobs_reclaim_runner_disk_before_install() -> None:
    workflow_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert workflow_text.count(RECLAIM_STEP_NAME) >= len(CI_RECLAIM_JOB_NAMES)
    assert RECLAIM_COMMAND in workflow_text
    assert "df -h" in workflow_text

    for job_name in CI_RECLAIM_JOB_NAMES:
        job_block = _extract_workflow_job_block(workflow_text=workflow_text, job_name=job_name)

        assert RECLAIM_STEP_NAME in job_block
        assert RECLAIM_COMMAND in job_block
