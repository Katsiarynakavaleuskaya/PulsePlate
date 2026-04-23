"""Regression guards for CI workflow diff-routing contracts."""

from __future__ import annotations

from pathlib import Path
import re

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _extract_section(workflow_text: str, start_anchor: str, end_anchor: str) -> str:
    """Return a stable workflow slice with explicit anchor assertions."""

    assert start_anchor in workflow_text, f"Missing workflow anchor: {start_anchor}"
    section_tail = workflow_text.split(start_anchor, maxsplit=1)[1]
    assert end_anchor in section_tail, f"Missing workflow anchor after {start_anchor}: {end_anchor}"
    return section_tail.split(end_anchor, maxsplit=1)[0]


def _extract_job_section(workflow_text: str, job_anchor: str) -> str:
    """Return a top-level GitHub Actions job block bounded by the next job or EOF."""

    assert job_anchor in workflow_text, f"Missing workflow anchor: {job_anchor}"
    start_index = workflow_text.index(job_anchor)
    section_tail = workflow_text[start_index + len(job_anchor) :]
    next_job_match = re.search(r"\n  [A-Za-z0-9][A-Za-z0-9_-]*:\n", section_tail)
    end_index = (
        start_index + len(job_anchor) + next_job_match.start()
        if next_job_match
        else len(workflow_text)
    )
    return workflow_text[start_index:end_index]


def _load_ci_workflow() -> dict[str, object]:
    workflow = yaml.safe_load(CI_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _assert_contains_all_tokens(expression: str, expected_tokens: tuple[str, ...]) -> None:
    """Assert that a workflow expression keeps all required routing tokens."""

    for token in expected_tokens:
        assert token in expression


def _extract_shell_conditional_block(
    script_text: str,
    branch_marker: str,
    next_marker: str,
) -> str:
    """Return the shell branch body between two explicit workflow markers."""

    start_anchor = f"{branch_marker}\n"
    end_anchor = f"\n{next_marker}"
    assert start_anchor in script_text, f"Missing shell branch marker: {branch_marker}"
    branch_tail = script_text.split(start_anchor, maxsplit=1)[1]
    assert end_anchor in branch_tail, f"Missing shell branch boundary after {branch_marker}"
    return branch_tail.split(end_anchor, maxsplit=1)[0]


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
        "      - name: Build CI risk profile",
        "\n  pr_scope_guard:",
    )

    assert "python3 scripts/ci/ci_risk_profile.py \\" in risk_profile_section
    assert 'BASE_SHA="${{ github.event.pull_request.base.sha }}"' in risk_profile_section
    assert 'HEAD_SHA="${{ github.event.pull_request.head.sha }}"' in risk_profile_section
    assert '--base-sha "${BASE_SHA}" \\' in risk_profile_section
    assert '--head-sha "${HEAD_SHA}" \\' in risk_profile_section


def test_feature_push_risk_profile_uses_origin_main_merge_base() -> None:
    """Feature/fix pushes must diff against origin/main merge-base."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    risk_profile_section = _extract_section(
        workflow_text,
        "      - name: Build CI risk profile",
        "\n  pr_scope_guard:",
    )

    assert "git fetch --no-tags --prune origin main" in risk_profile_section
    assert 'BASE_SHA="$(git merge-base origin/main "${GITHUB_SHA}")"' in risk_profile_section
    assert 'HEAD_SHA="${GITHUB_SHA}"' in risk_profile_section
    assert "Risk-profile diff: ${BASE_SHA}...${HEAD_SHA}" in risk_profile_section


def test_feature_push_branches_include_feature_prefix() -> None:
    workflow = _load_ci_workflow()
    on_section = workflow.get("on", workflow.get(True))
    assert isinstance(on_section, dict)
    push_section = on_section["push"]
    assert isinstance(push_section, dict)
    push_branches = push_section["branches"]
    assert isinstance(push_branches, list)

    assert {"main", "feat/**", "fix/**", "feature/**"}.issubset(set(push_branches))


def test_feature_push_jobs_use_changes_gate_and_smoke_risk_topology() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    feature_push_tokens = (
        "github.event_name == 'push'",
        "refs/heads/feat/",
        "refs/heads/fix/",
        "refs/heads/feature/",
    )

    test_feature = jobs["test-feature"]
    assert isinstance(test_feature, dict)
    test_feature_needs = test_feature["needs"]
    assert isinstance(test_feature_needs, list)
    assert "changes" in test_feature_needs
    test_feature_if = test_feature["if"]
    assert isinstance(test_feature_if, str)
    _assert_contains_all_tokens(test_feature_if, feature_push_tokens)
    assert "needs.changes.outputs.run_backend_blocking == 'true'" in test_feature_if
    feature_step_names = [step.get("name") for step in test_feature["steps"]]
    assert "Critical smoke (deterministic merge blocker)" in feature_step_names
    assert "Contract and risk suites" in feature_step_names
    assert "Finalize coverage artifacts" in feature_step_names

    coverage_feature = jobs["coverage-feature"]
    assert isinstance(coverage_feature, dict)
    coverage_feature_needs = coverage_feature["needs"]
    assert isinstance(coverage_feature_needs, list)
    assert "changes" in coverage_feature_needs
    assert "test-feature" in coverage_feature_needs
    coverage_feature_if = coverage_feature["if"]
    assert isinstance(coverage_feature_if, str)
    _assert_contains_all_tokens(coverage_feature_if, feature_push_tokens)
    assert "needs.changes.outputs.run_backend_blocking == 'true'" in coverage_feature_if
    coverage_feature_step_names = [step.get("name") for step in coverage_feature["steps"]]
    assert (
        "Download coverage artifact (Python ${{ env.COVERAGE_PY }})" in coverage_feature_step_names
    )
    assert "Upload to Codecov" in coverage_feature_step_names


def test_feature_branch_alias_stays_in_sync_for_ios_push_jobs() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    ios_routing_tokens = (
        "github.event_name == 'pull_request'",
        "refs/heads/feat/",
        "refs/heads/fix/",
        "refs/heads/feature/",
        "refs/heads/main",
    )

    ios_tests = jobs["ios-tests"]
    assert isinstance(ios_tests, dict)
    ios_tests_if = ios_tests["if"]
    assert isinstance(ios_tests_if, str)
    _assert_contains_all_tokens(ios_tests_if, ios_routing_tokens)

    ios_ui_smoke = jobs["ios-ui-smoke"]
    assert isinstance(ios_ui_smoke, dict)
    ios_ui_smoke_if = ios_ui_smoke["if"]
    assert isinstance(ios_ui_smoke_if, str)
    _assert_contains_all_tokens(ios_ui_smoke_if, ios_routing_tokens)


def test_ios_unit_tests_stay_in_blocking_ios_job() -> None:
    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    ios_tests_section = _extract_job_section(workflow_text, "  ios-tests:")
    ios_ui_smoke_section = _extract_job_section(workflow_text, "  ios-ui-smoke:")

    assert 'ONLY_TESTING="$(../scripts/ios_test_targets.sh)"' in ios_tests_section
    assert "::error::ONLY_TESTING is empty" in ios_tests_section
    assert "no test targets were found" in ios_tests_section
    assert '"xcodebuild", "test-without-building"' in ios_tests_section
    assert 'ONLY_TESTING="$(../scripts/ios_test_targets.sh)"' not in ios_ui_smoke_section


def test_main_branch_xdist_fallback_stays_scoped_to_unstable_interpreters() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    test_main = jobs["test-main"]
    assert isinstance(test_main, dict)
    matrix = test_main["strategy"]["matrix"]["include"]
    assert isinstance(matrix, list)

    timeouts = {entry["python-version"]: entry["timeout-minutes"] for entry in matrix}
    assert timeouts == {"3.11": 60, "3.12": 60, "3.13": 90}

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    test_main_section = _extract_job_section(workflow_text, "  test-main:")

    py313_block = _extract_shell_conditional_block(
        test_main_section,
        'if [[ "$PYVER" == 3.13* ]]; then',
        '          elif [[ "$PYVER" == 3.12* ]]; then',
    )
    py312_block = _extract_shell_conditional_block(
        test_main_section,
        '          elif [[ "$PYVER" == 3.12* ]]; then',
        "          else",
    )
    default_block = _extract_shell_conditional_block(
        test_main_section,
        "          else",
        "          fi",
    )

    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py313_block

    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" in py312_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py312_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py312_block
    assert '-m "not serial and not slow"' in test_main_section
    assert '-m "serial and not slow"' in test_main_section
    assert "--cov-append" in test_main_section
    assert "--junitxml=tests/results-serial.xml" in test_main_section
    assert "--junitxml=tests/results-serial.xml" not in py313_block
    assert "--junitxml=tests/results-serial.xml" not in default_block
    assert test_main_section.count("--junitxml=tests/results-serial.xml") == 1

    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" in default_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in default_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in default_block
