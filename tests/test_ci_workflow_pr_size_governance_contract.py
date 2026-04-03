"""Regression guards for PR-size governance workflow wiring."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _extract_section(workflow_text: str, start_anchor: str, end_anchor: str) -> str:
    """Return a stable workflow slice with explicit anchor assertions."""

    assert start_anchor in workflow_text, f"Missing workflow anchor: {start_anchor}"
    section_tail = workflow_text.split(start_anchor, maxsplit=1)[1]
    assert end_anchor in section_tail, f"Missing workflow anchor after {start_anchor}: {end_anchor}"
    return section_tail.split(end_anchor, maxsplit=1)[0]


def test_pr_size_governance_uses_pull_request_head_sha() -> None:
    """Guard against merge-SHA inflation in PR-size governance diff calculation."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    pr_scope_guard_section = _extract_section(
        workflow_text,
        "pr_scope_guard:",
        "      - name: Design invariant guard",
    )

    assert "python3 scripts/ci/check_pr_size_governance.py \\" in pr_scope_guard_section
    assert '--base-sha "${{ github.event.pull_request.base.sha }}" \\' in pr_scope_guard_section
    assert '--head-sha "${{ github.event.pull_request.head.sha }}" \\' in pr_scope_guard_section
    assert '--head-sha "${{ github.sha }}" \\' not in pr_scope_guard_section


def test_pr_risk_profile_uses_pull_request_head_sha() -> None:
    """Guard contract-risk routing against merge-SHA based diff calculations."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    risk_profile_section = _extract_section(
        workflow_text,
        "      - name: Build PR risk profile",
        "\n  pr_scope_guard:",
    )

    assert "python3 scripts/ci/ci_risk_profile.py \\" in risk_profile_section
    assert '--base-sha "${{ github.event.pull_request.base.sha }}" \\' in risk_profile_section
    assert '--head-sha "${{ github.event.pull_request.head.sha }}" \\' in risk_profile_section
    assert '--head-sha "${{ github.sha }}" \\' not in risk_profile_section
