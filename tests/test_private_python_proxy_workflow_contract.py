from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
HEALTH_JOB = "private_python_proxy_health"


def load_ci_workflow() -> dict[str, Any]:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def as_needs_set(job: dict[str, Any]) -> set[str]:
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    assert isinstance(needs, list), "job needs must be a string or list"
    return {str(need) for need in needs}


def job_uses_python_setup(job: dict[str, Any]) -> bool:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    return any(
        isinstance(step, dict) and step.get("uses") == "./.github/actions/python-setup"
        for step in steps
    )


def test_private_proxy_health_job_is_stdlib_fail_fast_gate() -> None:
    workflow = load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[HEALTH_JOB]
    assert isinstance(job, dict)

    assert job["name"] == "Private Python proxy health"
    assert job["needs"] == ["changes"]
    assert job["timeout-minutes"] <= 3
    assert job.get("continue-on-error") is None
    assert job.get("permissions") == {"contents": "read"}

    steps = job["steps"]
    assert isinstance(steps, list)
    step_uses = [step.get("uses") for step in steps if isinstance(step, dict)]
    assert "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd" in step_uses
    assert "actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405" in step_uses
    assert "./.github/actions/python-setup" not in step_uses
    checkout_step = next(
        step
        for step in steps
        if isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout@")
    )
    assert checkout_step.get("with", {}).get("persist-credentials") is False

    run_blocks = "\n".join(str(step.get("run", "")) for step in steps if isinstance(step, dict))
    assert "scripts/ci/check_private_python_proxy_health.py" in run_blocks
    assert "pip install" not in run_blocks
    assert "continue-on-error" not in run_blocks
    assert "--requirements-file requirements-test.txt" in run_blocks
    assert "--python-version 3.11" in run_blocks
    assert "--python-version 3.12" in run_blocks
    assert "--python-version 3.13" in run_blocks
    assert "--project pytest-xdist" in run_blocks
    assert "--project hypothesis" in run_blocks
    assert "--project pgvector" in run_blocks
    assert "--project pydantic-core" not in run_blocks

    step_names = [step.get("name") for step in steps if isinstance(step, dict)]
    assert step_names.index("Check private Python proxy health") < step_names.index(
        "Emergency wheel mirror parity"
    )
    assert step_names.index("Emergency wheel mirror parity") < step_names.index(
        "Cleanup protected main package proxy authentication"
    )
    parity_step = next(
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == "Emergency wheel mirror parity"
    )
    parity_run = str(parity_step.get("run", ""))
    assert "scripts/ci/check_emergency_wheel_mirror_parity.py" in parity_run
    assert "--manifest scripts/ci/emergency_python_wheels.json" in parity_run
    assert "--python-version 3.11" in parity_run
    assert "--python-version 3.12" in parity_run
    assert "--python-version 3.13" in parity_run
    assert "--format text" in parity_run
    assert parity_step.get("continue-on-error") is None

    cleanup_step = next(
        step
        for step in steps
        if (
            isinstance(step, dict)
            and step.get("name") == "Cleanup protected main package proxy authentication"
        )
    )
    assert (
        cleanup_step.get("if")
        == "always() && github.event_name != 'pull_request' && github.ref == 'refs/heads/main'"
    )
    cleanup_run = str(cleanup_step.get("run", ""))
    assert "pulseplate-private-proxy-health-netrc-created" in cleanup_run
    assert '[[ -n "${RUNNER_TEMP:-}" && -f "$marker" ]]' in cleanup_run
    assert 'rm -f "$HOME/.netrc" "$marker"' in cleanup_run
    assert cleanup_step.get("continue-on-error") is None


def test_private_proxy_health_uses_vars_for_pull_request_context() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    health_section = workflow_text.split(f"  {HEALTH_JOB}:", 1)[1].split("\n  lint:", 1)[0]

    assert (
        "PULSEPLATE_PR_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}" in health_section
    )
    assert (
        "PULSEPLATE_PR_PYTHON_TRUSTED_HOST: ${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
        in health_section
    )
    pr_resolver = health_section.split("- name: Resolve PR diagnostic package proxy", 1)[1].split(
        "- name: Resolve branch diagnostic package proxy",
        1,
    )[0]
    assert "secrets." not in pr_resolver
    assert "pull_request_target" not in workflow_text


def test_private_proxy_health_uses_vars_for_non_main_branch_pushes() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    health_section = workflow_text.split(f"  {HEALTH_JOB}:", 1)[1].split("\n  lint:", 1)[0]
    branch_resolver = health_section.split(
        "- name: Resolve branch diagnostic package proxy",
        1,
    )[
        1
    ].split("- name: Resolve protected main package proxy", 1,)[0]

    assert (
        "if: github.event_name != 'pull_request' && github.ref != 'refs/heads/main'"
        in branch_resolver
    )
    assert (
        "PULSEPLATE_BRANCH_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
        in branch_resolver
    )
    assert "secrets." not in branch_resolver
    assert "DEVPI_CI_USER:" not in branch_resolver
    assert "DEVPI_CI_PASSWORD:" not in branch_resolver


def test_private_proxy_health_main_auth_is_netrc_only() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    health_section = workflow_text.split(f"  {HEALTH_JOB}:", 1)[1].split("\n  lint:", 1)[0]
    protected_resolver = health_section.split(
        "- name: Resolve protected main package proxy",
        1,
    )[
        1
    ].split("- name: Configure protected main package proxy authentication", 1,)[0]
    protected_auth = health_section.split(
        "- name: Configure protected main package proxy authentication",
        1,
    )[1].split("- name: Check private Python proxy health", 1,)[0]

    assert (
        "if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'"
        in protected_resolver
    )
    assert (
        "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
        in protected_resolver
    )
    assert "secrets.PULSEPLATE_PYTHON_INDEX_URL" not in protected_resolver
    assert "secrets.DEVPI_CI_USER" in protected_auth
    assert "secrets.DEVPI_CI_PASSWORD" in protected_auth
    assert "://$DEVPI_CI_USER" not in protected_auth
    assert "://$DEVPI_CI_PASSWORD" not in protected_auth
    assert "$HOME/.netrc" in protected_auth
    assert "pulseplate-private-proxy-health-netrc-created" in protected_auth
    assert 'touch "$marker"' in protected_auth
    assert "[Rr][Oo][Oo][Tt]" in protected_auth
    assert "Root devpi credentials are forbidden" in protected_auth


def test_test_main_uses_same_protected_proxy_source_as_health_gate() -> None:
    workflow_text = CI_WORKFLOW.read_text(encoding="utf-8")
    test_main_section = workflow_text.split("  test-main:", 1)[1].split(
        "\n  diff-coverage:",
        1,
    )[0]
    protected_resolver = test_main_section.split(
        "- name: Resolve protected package proxy",
        1,
    )[
        1
    ].split("- name: Setup Python environment", 1)[0]

    assert (
        "PULSEPLATE_PROTECTED_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
        in protected_resolver
    )
    assert (
        "PULSEPLATE_PROTECTED_PYTHON_TRUSTED_HOST: ${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
        in protected_resolver
    )
    assert "secrets.PULSEPLATE_PYTHON_INDEX_URL" not in protected_resolver
    assert "secrets.PULSEPLATE_PYTHON_TRUSTED_HOST" not in protected_resolver
    assert (
        "Set PULSEPLATE_PYTHON_INDEX_URL repository variable for protected test-main runs."
        in protected_resolver
    )


def test_python_setup_jobs_depend_on_private_proxy_health_gate() -> None:
    workflow = load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    python_setup_jobs = {
        job_name
        for job_name, job in jobs.items()
        if isinstance(job, dict) and job_uses_python_setup(job)
    }

    assert python_setup_jobs == {
        "lint",
        "security",
        "openapi-sync",
        "test-pr",
        "test-feature",
        "test-main",
        "diff-coverage",
    }
    for job_name in python_setup_jobs:
        job = jobs[job_name]
        assert isinstance(job, dict)
        assert HEALTH_JOB in as_needs_set(job), f"{job_name} must need {HEALTH_JOB}"
