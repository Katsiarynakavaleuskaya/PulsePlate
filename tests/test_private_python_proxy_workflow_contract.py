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

    run_blocks = "\n".join(str(step.get("run", "")) for step in steps if isinstance(step, dict))
    assert "scripts/ci/check_private_python_proxy_health.py" in run_blocks
    assert "pip install" not in run_blocks
    assert "continue-on-error" not in run_blocks


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
        "- name: Resolve protected package proxy",
        1,
    )[0]
    assert "secrets." not in pr_resolver
    assert "DEVPI_CI_USER:" not in health_section
    assert "DEVPI_CI_PASSWORD:" not in health_section
    assert "pull_request_target" not in workflow_text


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
