"""Regression guards for CI workflow diff-routing contracts."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
from typing import cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
CODECOV_UPLOAD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "codecov-upload.yml"
IOS_APPSTORE_ASSETS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ios-appstore-assets.yml"
NIGHTLY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "nightly.yml"
PR_AUTOMATION_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pr-automation.yml"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
RUNBOOK_PATH = REPO_ROOT / "RUNBOOK_AGENT.md"
ORCHESTRATION_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "orchestration" / "PR_ORCHESTRATION_CONTRACT_MATRIX.md"
)
PATHS_FILTER_NODE24_SHA = "".join(
    (
        "fbd0",
        "ab8f",
        "3e69",
        "293a",
        "f611",
        "ebae",
        "e636",
        "3fc2",
        "5e6d",
        "187d",
    )
)
DOWNLOAD_ARTIFACT_NODE24_SHA = "".join(
    (
        "3e5f",
        "45b2",
        "cfb9",
        "1720",
        "54b4",
        "087a",
        "40e8",
        "e0b5",
        "a546",
        "1e7c",
    )
)
GITHUB_SCRIPT_NODE24_SHA = "".join(
    (
        "3a28",
        "44b7",
        "e9c4",
        "22d3",
        "c10d",
        "287c",
        "8955",
        "73f7",
        "108d",
        "a1b3",
    )
)
CODECOV_ACTION_NODE24_SHA = "".join(
    (
        "57e3",
        "a136",
        "b779",
        "b570",
        "ffcd",
        "bf80",
        "b3bd",
        "c90e",
        "7fab",
        "3de2",
    )
)
PYTHON_TEST_JOB_NAMES = ("test-pr", "test-feature", "test-main")
OLD_DOWNLOAD_ARTIFACT_SHA = "".join(
    (
        "fa0a",
        "91b8",
        "5d4f",
        "404e",
        "444e",
        "00e0",
        "0597",
        "1372",
        "dc80",
        "1d16",
    )
)
OLD_GITHUB_SCRIPT_SHA = "".join(
    (
        "f28e",
        "40c7",
        "f34b",
        "de8b",
        "3046",
        "d885",
        "e986",
        "cb62",
        "90c5",
        "673b",
    )
)
OLD_CODECOV_ACTION_SHA = "".join(
    (
        "af09",
        "b5e3",
        "94c9",
        "3991",
        "b95a",
        "5e76",
        "46ae",
        "b90c",
        "1917",
        "f78f",
    )
)
GITHUB_SCRIPT_V9_TAG_OBJECT_SHA = "".join(
    (
        "d746",
        "ffe3",
        "5508",
        "b191",
        "7358",
        "783b",
        "479e",
        "04fe",
        "bd2b",
        "8f71",
    )
)


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
    return _load_workflow(CI_WORKFLOW_PATH)


def _load_workflow(path: Path) -> dict[str, object]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _iter_job_steps(path: Path) -> Iterator[tuple[str, dict[str, object]]]:
    workflow = _load_workflow(path)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    for job_id, job in jobs.items():
        assert isinstance(job_id, str)
        assert isinstance(job, dict)
        steps = job.get("steps", [])
        assert isinstance(steps, list)
        for step in steps:
            assert isinstance(step, dict)
            yield job_id, step


def _assert_contains_all_tokens(expression: str, expected_tokens: tuple[str, ...]) -> None:
    """Assert that a workflow expression keeps all required routing tokens."""

    for token in expected_tokens:
        assert (
            token in expression
        ), f"Missing token {token!r} in expression excerpt: {expression[:500]!r}"


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


def test_docs_phase1_gates_include_schema_only_contract_changes() -> None:
    """SC-G5 schema-only edits must still run the docs Phase1 validator."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    docs_phase1_section = _extract_job_section(workflow_text, "  docs_phase1_gates:")

    assert "PHASE1_CHANGED_FILES=()" in docs_phase1_section
    assert "'docs/orchestration/contracts/*.schema.json'" in docs_phase1_section
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json'"
        in docs_phase1_section
    )
    assert (
        "'docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json'" in docs_phase1_section
    )
    assert (
        "':(glob)docs/orchestration/contracts/philosophy_alignment_rules/**/*.json'"
        in docs_phase1_section
    )
    assert (
        "docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json" in docs_phase1_section
    )
    assert (
        "'tests/fixtures/orchestration/philosophy_admission_claim_oracle.json'"
        in docs_phase1_section
    )
    assert (
        "No changed markdown or Phase1 schema files; skipping docs Phase1 gates."
        in docs_phase1_section
    )
    assert (
        'if [ "${PR4_PRECONDITION_CHANGED}" -eq 0 ] && [ "${PR5_SOURCE_CORPUS_CHANGED}" -eq 0 ] && [ "${#PHASE1_CHANGED_FILES[@]}" -eq 0 ] && [ "${#LINT_MD[@]}" -eq 0 ]; then'
        in docs_phase1_section
    )
    assert (
        "No changed docs markdown or Phase1 schema files; skipping docs Phase1 validator."
        in docs_phase1_section
    )
    assert (
        'python scripts/ci/check_docs_phase1_gates.py --files "${PHASE1_CHANGED_FILES[@]}"'
        in docs_phase1_section
    )
    assert "PR4_PRECONDITION_CHANGED=0" in docs_phase1_section
    assert "PR5_SOURCE_CORPUS_CHANGED=0" in docs_phase1_section
    assert 'git diff --name-status -z --diff-filter=ACDMRT "$BASE_REF"...HEAD' in (
        docs_phase1_section
    )
    assert 'case "$status" in' in docs_phase1_section
    assert "R*|C*)" in docs_phase1_section
    assert 'CHANGED_PATHS+=("$old_path" "$new_path")' in docs_phase1_section
    assert 'CHANGED_PATHS+=("$path")' in docs_phase1_section
    for pr4_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json",
        "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json",
        "tests/fixtures/orchestration/philosophy_admission_claim_oracle.json",
        "docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json",
        "docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json",
        "docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.schema.json",
        "docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json",
        "docs/orchestration/contracts/philosophy_alignment_rules/*.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR4_GATE_OPEN_PRECONDITIONS_PACKET_2026-05-21.md",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        "scripts/ci/check_philosophy_gate_open_preconditions.py",
        "tests/test_philosophy_gate_open_preconditions.py",
    ):
        assert pr4_companion_input in docs_phase1_section
    for pr5_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json",
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md",
        "scripts/ci/check_philosophy_source_corpus_index.py",
        "tests/test_philosophy_source_corpus_index.py",
    ):
        assert pr5_companion_input in docs_phase1_section
    pr5_case = _extract_section(
        docs_phase1_section,
        '              case "$path" in\n'
        "                docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json",
        "                  PR5_SOURCE_CORPUS_CHANGED=1",
    )
    for pr5_companion_input in (
        "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json",
        "docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md",
        "scripts/ci/check_philosophy_source_corpus_index.py",
        "tests/test_philosophy_source_corpus_index.py",
    ):
        assert pr5_companion_input in pr5_case
    for unrelated_pr5_trigger in (
        "docs/roadmap/BACKLOG_LEDGER.md",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
        "scripts/ci/check_docs_phase1_gates.py",
    ):
        assert unrelated_pr5_trigger not in pr5_case
    assert (
        "python scripts/ci/check_philosophy_gate_open_preconditions.py --check --files"
        in docs_phase1_section
    )
    assert (
        "python scripts/ci/check_philosophy_source_corpus_index.py --check --files"
        in docs_phase1_section
    )
    assert (
        'python scripts/ci/check_docs_phase1_gates.py --files "${CHANGED_DOCS[@]}"'
        not in docs_phase1_section
    )


def test_semantic_cache_contract_suites_include_philosophy_policy_oracle() -> None:
    """Current-head CI must execute the Philosophy policy/oracle drift regressions."""

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert workflow_text.count("tests/test_philosophy_admission_dry_run_report.py \\") >= 2
    assert workflow_text.count("tests/test_philosophy_admission_policy_oracle.py \\") >= 2


def test_changes_job_uses_node24_paths_filter_pin_and_keeps_ios_filters() -> None:
    """Guard the Node 24 paths-filter migration and iOS path-gating contract."""

    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    changes = jobs["changes"]
    assert isinstance(changes, dict)
    steps = changes["steps"]
    assert isinstance(steps, list)

    filter_step = next(step for step in steps if step.get("id") == "filter")
    assert filter_step["uses"] == f"dorny/paths-filter@{PATHS_FILTER_NODE24_SHA}"

    with_section = filter_step["with"]
    assert isinstance(with_section, dict)
    assert with_section["token"] == "${{ secrets.GITHUB_TOKEN }}"
    filters = with_section["filters"]
    assert isinstance(filters, str)
    assert "ios:" in filters
    assert "- 'ios/**'" in filters
    assert "- '.github/workflows/**'" in filters
    assert "- '.github/actions/**'" in filters


def test_node24_artifact_and_script_action_pins_use_verified_commit_shas() -> None:
    """Guard remaining Node 20 action migrations against tag-object drift."""

    download_workflows = {
        CI_WORKFLOW_PATH: 6,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH: 1,
        NIGHTLY_WORKFLOW_PATH: 1,
    }
    expected_download_line = (
        f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA} # v8.0.1 / Node 24"
    )

    observed_download_steps = 0
    for workflow_path, expected_count in download_workflows.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_download_line) == expected_count
        assert f"actions/download-artifact@{OLD_DOWNLOAD_ARTIFACT_SHA}" not in workflow_text

        for _job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/download-artifact@"):
                observed_download_steps += 1
                assert uses == f"actions/download-artifact@{DOWNLOAD_ARTIFACT_NODE24_SHA}"

    assert observed_download_steps == sum(download_workflows.values())

    pr_automation_text = PR_AUTOMATION_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert (
        f"actions/github-script@{GITHUB_SCRIPT_NODE24_SHA} # v9.0.0 / Node 24" in pr_automation_text
    )
    assert f"actions/github-script@{OLD_GITHUB_SCRIPT_SHA}" not in pr_automation_text
    assert GITHUB_SCRIPT_V9_TAG_OBJECT_SHA not in pr_automation_text


def test_codecov_action_pin_uses_node24_transitive_github_script() -> None:
    """Guard Codecov uploads against reintroducing the old Node 20 github-script dependency."""

    expected_codecov_line = (
        f"codecov/codecov-action@{CODECOV_ACTION_NODE24_SHA} "
        "# v6.0.0 / Node 24 transitive github-script"
    )
    workflow_counts = {
        CI_WORKFLOW_PATH: 3,
        CODECOV_UPLOAD_WORKFLOW_PATH: 1,
    }

    observed_codecov_steps = []
    for workflow_path, expected_count in workflow_counts.items():
        workflow_text = workflow_path.read_text(encoding="utf-8")
        assert workflow_text.count(expected_codecov_line) == expected_count
        assert f"codecov/codecov-action@{OLD_CODECOV_ACTION_SHA}" not in workflow_text

        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("codecov/codecov-action@"):
                observed_codecov_steps.append((workflow_path, job_id, step))
                assert uses == f"codecov/codecov-action@{CODECOV_ACTION_NODE24_SHA}"

    assert len(observed_codecov_steps) == sum(workflow_counts.values())


def test_node24_artifact_migration_preserves_download_contracts() -> None:
    """Guard artifact names, paths, and merge behavior during action runtime bumps."""

    expected_download_contracts = [
        (
            ".github/workflows/ci.yml",
            "coverage-pr",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "diff-coverage",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            None,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-feature",
            "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})",
            {"name": "coverage-xml-${{ env.PYTHON_VERSION }}", "path": "./coverage-artifacts"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.11)",
            {"name": "coverage-main-xml-3.11", "path": "./coverage-artifacts/3.11"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.12)",
            {"name": "coverage-main-xml-3.12", "path": "./coverage-artifacts/3.12"},
            True,
        ),
        (
            ".github/workflows/ci.yml",
            "coverage-main",
            "Download coverage artifact (Python 3.13)",
            {"name": "coverage-main-xml-3.13", "path": "./coverage-artifacts/3.13"},
            True,
        ),
        (
            ".github/workflows/codecov-upload.yml",
            "upload",
            "Download coverage artifact",
            {"name": "${{ inputs['coverage-artifact'] }}", "path": "./coverage-artifact"},
            None,
        ),
        (
            ".github/workflows/nightly.yml",
            "coverage-merge",
            "Download coverage artifacts",
            {
                "pattern": "coverage-reports-shard-*",
                "merge-multiple": True,
                "path": "coverage-artifacts",
            },
            None,
        ),
        (
            ".github/workflows/ios-appstore-assets.yml",
            "upload-assets",
            "Download screenshot artifacts",
            {"name": "ios-appstore-screenshots", "path": "ios/fastlane/screenshots"},
            None,
        ),
    ]

    observed_download_contracts = []
    for workflow_path in (
        CI_WORKFLOW_PATH,
        CODECOV_UPLOAD_WORKFLOW_PATH,
        NIGHTLY_WORKFLOW_PATH,
        IOS_APPSTORE_ASSETS_WORKFLOW_PATH,
    ):
        for job_id, step in _iter_job_steps(workflow_path):
            uses = step.get("uses")
            if isinstance(uses, str) and uses.startswith("actions/download-artifact@"):
                observed_download_contracts.append(
                    (
                        str(workflow_path.relative_to(REPO_ROOT)),
                        job_id,
                        step.get("name"),
                        step.get("with"),
                        step.get("continue-on-error"),
                    )
                )

    assert observed_download_contracts == expected_download_contracts


def test_node24_github_script_migration_preserves_pr_read_permissions() -> None:
    """Guard the PR automation script runtime bump against permission drift."""

    workflow = _load_workflow(PR_AUTOMATION_WORKFLOW_PATH)
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    validate_pr_job = jobs["validate-pr"]
    assert isinstance(validate_pr_job, dict)

    assert validate_pr_job["permissions"] == {"pull-requests": "read"}

    github_script_steps = []
    for _job_id, step in _iter_job_steps(PR_AUTOMATION_WORKFLOW_PATH):
        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith("actions/github-script@"):
            github_script_steps.append(step)

    assert len(github_script_steps) == 1
    script_step = github_script_steps[0]
    assert script_step["uses"] == f"actions/github-script@{GITHUB_SCRIPT_NODE24_SHA}"
    with_section = script_step["with"]
    assert isinstance(with_section, dict)
    assert sorted(with_section) == ["github-token", "script"]
    assert with_section["github-token"] == "${{ secrets.GITHUB_TOKEN }}"
    assert "github.rest.pulls.get" in str(with_section["script"])


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
    on_section = workflow.get("on")
    if on_section is None:
        on_section = cast(dict[object, object], workflow).get(True)
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
    assert "Start fast-feedback timing" in feature_step_names
    assert "Summarize fast-feedback budget" in feature_step_names
    assert "Upload fast-feedback budget artifact" in feature_step_names
    test_feature_env = test_feature["env"]
    assert isinstance(test_feature_env, dict)
    assert test_feature_env["FEATURE_FEEDBACK_TARGET_MINUTES"] == "45"

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
        "Download coverage artifact (Python ${{ env.PYTHON_VERSION }})"
        in coverage_feature_step_names
    )
    assert "Upload to Codecov" in coverage_feature_step_names


def test_feature_push_fast_feedback_budget_is_warning_only_evidence() -> None:
    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    test_feature_section = _extract_job_section(workflow_text, "  test-feature:")

    assert "Feature/fix fast-feedback exceeded" in test_feature_section
    assert "::warning::Feature/fix fast-feedback exceeded" in test_feature_section
    assert "Fast-feedback timing seed is missing" in test_feature_section
    assert 'status="timing_unavailable"' in test_feature_section
    assert "elapsed_seconds=-1" in test_feature_section
    assert "FEATURE_FEEDBACK_STARTED_AT:-$(date +%s)" not in test_feature_section
    assert "feature-feedback-budget.json" in test_feature_section
    assert "feature-feedback-budget-${{ env.PYTHON_VERSION }}" in test_feature_section
    assert "if-no-files-found: error" in test_feature_section


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


def test_machine_heavy_local_verify_deferral_contract_is_documented() -> None:
    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    runbook_text = RUNBOOK_PATH.read_text(encoding="utf-8")
    contract_text = ORCHESTRATION_CONTRACT_PATH.read_text(encoding="utf-8")

    required_tokens = (
        "Machine-heavy PR exception",
        "operator-approved",
        "`make verify` by default",
        "canonical current-head CI parity",
        "`lint`",
        "required/current-head checks",
        "relevant `test-main` matrix",
        "`diff-coverage`",
        "≥97%",
        "security/governance checks",
        "`check_merge_ready.py --require-auth`",
        "`make validate-changed`",
        "`pre-commit run --all-files`",
    )
    _assert_contains_all_tokens(agents_text, required_tokens)

    runbook_tokens = (
        "Machine-heavy CI/tooling PRs",
        "operator explicitly defers full local",
        "canonical current-head CI parity",
        "`lint`",
        "required/current-head checks",
        "relevant `test-main` matrix",
        "`diff-coverage` at ≥97%",
        "security/governance checks",
        "`check_merge_ready.py --require-auth`",
        "documented narrow bundle",
    )
    _assert_contains_all_tokens(runbook_text, runbook_tokens)

    contract_tokens = (
        "Operator-approved machine-heavy deferral",
        "fixed mapping document the deferral",
        "canonical current-head CI parity is green",
        "relevant `test-main` matrix",
        "`diff-coverage` ≥97%",
        "security/governance checks",
    )
    _assert_contains_all_tokens(contract_text, contract_tokens)


def test_main_branch_python_sharded_runner_preserves_required_check_policy() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    test_main = jobs["test-main"]
    assert isinstance(test_main, dict)
    test_main_needs = test_main["needs"]
    assert isinstance(test_main_needs, list)
    assert "changes" in test_main_needs
    test_main_if = test_main["if"]
    assert isinstance(test_main_if, str)
    assert "github.ref == 'refs/heads/main'" in test_main_if
    assert "needs.changes.outputs.run_main_ci_diagnostic == 'true'" in test_main_if
    matrix = test_main["strategy"]["matrix"]["include"]
    assert isinstance(matrix, list)

    timeouts = {entry["python-version"]: entry["timeout-minutes"] for entry in matrix}
    assert timeouts == {"3.11": 60, "3.12": 90, "3.13": 90}

    workflow_text = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    test_main_section = _extract_job_section(workflow_text, "  test-main:")
    assert (
        "python-version: ${{ matrix.python-version == '3.13' && env.PYTHON_VERSION || "
        "matrix.python-version }}"
    ) in test_main_section

    py311_block = _extract_shell_conditional_block(
        test_main_section,
        'if [[ "$PYVER" == 3.11* ]]; then',
        '          elif [[ "$PYVER" == 3.12* ]]; then',
    )
    py312_block = _extract_shell_conditional_block(
        test_main_section,
        '          elif [[ "$PYVER" == 3.12* ]]; then',
        '          elif [[ "$PYVER" == 3.13* ]]; then',
    )
    py313_block = _extract_shell_conditional_block(
        test_main_section,
        '          elif [[ "$PYVER" == 3.13* ]]; then',
        "          else",
    )
    default_block = _extract_shell_conditional_block(
        test_main_section,
        "          else",
        "          fi",
    )
    shared_shard_runner_block = _extract_shell_conditional_block(
        test_main_section,
        '          if [[ -n "${MAIN_TEST_SHARDS:-}" ]]; then',
        '          echo "PYTEST_XDIST_ARGS=${PYTEST_XDIST_ARGS[*]}"',
    )

    assert "MAIN_TEST_SHARDS=4" in py311_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py311_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py311_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py311_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py311_block

    assert "MAIN_TEST_SHARDS=16" in py312_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py312_block
    assert "export MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800" in py312_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py312_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py312_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py312_block
    assert "TEST_STEP_STARTED_AT=" in test_main_section
    assert "TEST_STEP_FINISHED_AT=" in shared_shard_runner_block

    assert "MAIN_TEST_SHARDS=8" in py313_block
    assert "MAIN_TEST_MAX_PARALLEL=4" in py313_block
    assert "export MAIN_TEST_SHARD_TIMEOUT_SECONDS=4800" in py313_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in py313_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in py313_block

    assert "python scripts/ci/run_main_test_shards.py" in shared_shard_runner_block
    assert '--python-version "${PYVER}"' in shared_shard_runner_block
    assert '--shard-count "${MAIN_TEST_SHARDS}"' in shared_shard_runner_block
    assert '--max-parallel "${MAIN_TEST_MAX_PARALLEL}"' in shared_shard_runner_block
    assert 'echo "MAIN_TEST_SHARDS=${MAIN_TEST_SHARDS}"' in shared_shard_runner_block
    assert 'echo "MAIN_TEST_MAX_PARALLEL=${MAIN_TEST_MAX_PARALLEL}"' in shared_shard_runner_block
    assert (
        'echo "MAIN_TEST_SHARD_TIMEOUT_SECONDS=${MAIN_TEST_SHARD_TIMEOUT_SECONDS:-default}"'
        in shared_shard_runner_block
    )
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in shared_shard_runner_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in shared_shard_runner_block
    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" not in shared_shard_runner_block

    assert '-m "not slow"' in test_main_section
    assert '-m "not serial and not slow"' not in test_main_section
    assert '-m "serial and not slow"' not in test_main_section
    assert "--cov-append" not in test_main_section
    assert "tests/results-serial.xml" not in test_main_section
    assert "tests/results-py312-shard-*.xml" in test_main_section
    assert "tests/results-py313-shard-*.xml" in test_main_section
    assert (
        "name: coverage-main-xml-${{ matrix.python-version }}\n"
        "          path: coverage.xml\n"
        "          if-no-files-found: ignore\n"
        "          overwrite: true"
    ) in test_main_section
    assert (
        "name: junit-main-${{ matrix.python-version }}\n"
        "          path: |\n"
        "            tests/results.xml\n"
        "            tests/results-py311-shard-*.xml\n"
        "            tests/results-py312-shard-*.xml\n"
        "            tests/results-py313-shard-*.xml\n"
        "          if-no-files-found: ignore\n"
        "          overwrite: true"
    ) in test_main_section
    coverage_main_section = _extract_job_section(workflow_text, "  coverage-main:")
    assert "name: coverage-main-xml-3.11" in coverage_main_section
    assert "name: coverage-main-xml-3.12" in coverage_main_section
    assert "name: coverage-main-xml-3.13" in coverage_main_section

    assert "PYTEST_XDIST_ARGS=(-n 4 --dist=loadscope)" in default_block
    assert "PYTEST_XDIST_ARGS=(-p no:xdist)" not in default_block
    assert "PYTEST_XDIST_ARGS=(-n 2 --dist=loadscope)" not in default_block


def test_python_test_jobs_install_frontend_dependencies_before_pytest() -> None:
    workflow = _load_ci_workflow()
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    for job_name in PYTHON_TEST_JOB_NAMES:
        steps = jobs[job_name]["steps"]
        step_names = [step.get("name") for step in steps]
        root_index = step_names.index("Install root Node dependencies")
        frontend_index = step_names.index("Install frontend dependencies")
        clean_index = step_names.index("Clean Python cache")

        root_step = steps[root_index]
        frontend_step = steps[frontend_index]
        assert root_step["uses"] == "./.github/actions/npm-ci-with-retry"
        assert root_step["with"]["working-directory"] == "."
        assert frontend_step["uses"] == "./.github/actions/npm-ci-with-retry"
        assert frontend_step["with"]["working-directory"] == "frontend"
        assert root_index < frontend_index < clean_index
