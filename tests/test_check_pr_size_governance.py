"""Deterministic tests for PR-size governance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.ci.check_pr_size_governance as size_gate


def test_parse_numstat_output_sums_text_rows_and_ignores_binary() -> None:
    total_lines, counted_files = size_gate.parse_numstat_output(
        "10\t5\tapp/main.py\n-\t-\tfrontend/src/assets/logo.png\n3\t2\tdocs/runbook.md\n",
    )

    assert total_lines == 20
    assert counted_files == 3


def test_parse_numstat_details_counts_binary_paths_for_file_policy() -> None:
    total_lines, counted_files, changed_files = size_gate.parse_numstat_details(
        "-\t-\tfrontend/src/assets/hero.png\n1\t0\tscripts/ci/check.py\n",
    )

    assert total_lines == 1
    assert counted_files == 2
    assert changed_files == ["frontend/src/assets/hero.png", "scripts/ci/check.py"]


def _standard_body(extra: str = "") -> str:
    return f"## Scope\nPolicy only.\n\n## Out of scope\nRuntime changes.\n\n## Tests\nFocused.\n{extra}"


def test_has_split_justification_accepts_heading_and_label() -> None:
    assert size_gate.has_split_justification("## Split Justification\nNeeded for parity.")
    assert size_gate.has_split_justification("Split justification: workflow rename parity.")
    assert size_gate.has_split_justification("## pr size justification\nNeeded for parity.")
    assert size_gate.has_split_justification("**Split justification:** workflow rename parity.")


def test_has_split_justification_rejects_empty_template_stub() -> None:
    assert not size_gate.has_split_justification("## Split Justification\n")
    assert not size_gate.has_split_justification(
        "## Summary\nLarge PR.\n\n## Split Justification\n\n## Risks\nLow.\n",
    )
    assert not size_gate.has_split_justification(
        (
            "## Split Justification\n\n"
            "- Why this PR cannot be split safely:\n"
            "- What invariant, contract, or rollout constraint requires one PR:\n"
            "- What follow-up PRs remain after this large change:\n"
        ),
    )
    assert not size_gate.has_split_justification(
        "Split justification: Why this PR cannot be split safely:",
    )
    assert not size_gate.has_split_justification("**Split justification:**   ")
    assert not size_gate.has_split_justification("## Split Justification\nTBD\n")
    assert not size_gate.has_split_justification("Split justification: N/A")
    assert not size_gate.has_split_justification("## Split Justification\nTODO\n")


def test_has_split_justification_accepts_nested_heading_content() -> None:
    assert size_gate.has_split_justification(
        "## Split Justification\n### Constraint\nNeed parity with current workflow wiring.\n",
    )


def test_has_split_justification_ignores_html_comments() -> None:
    assert not size_gate.has_split_justification(
        "## Split Justification\n<!-- fill this in -->\n",
    )
    assert size_gate.has_split_justification(
        "## Split Justification\n<!-- scaffold -->\nNeeded for parity.\n",
    )


def test_evaluate_pr_size_policy_passes_for_micro_pr_without_sections() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1200,
        counted_files=4,
        pr_body="",
        changed_files=[f"docs/example_{index}.md" for index in range(4)],
    )

    assert exit_code == 0
    assert any("category: micro" in line for line in lines)
    assert any("OK (micro PR" in line for line in lines)


def test_evaluate_pr_size_policy_passes_for_standard_governance_design_pr() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1200,
        counted_files=14,
        pr_body=_standard_body(),
        changed_files=[f"docs/design/example_{index}.md" for index in range(14)],
    )

    assert exit_code == 0
    assert any("category: standard_governance_design" in line for line in lines)
    assert any("OK (standard governance/design PR <= 20 files)" in line for line in lines)


def test_standard_pr_requires_scope_out_of_scope_and_tests_sections() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=80,
        counted_files=6,
        pr_body="## Summary\nPolicy update.\n",
        changed_files=[f"docs/design/example_{index}.md" for index in range(6)],
    )

    assert exit_code == 1
    assert any("Required section missing: ## Scope" in line for line in lines)
    assert any("Required section missing: ## Out Of Scope" in line for line in lines)
    assert any("Required section missing: ## Tests" in line for line in lines)
    assert any("How to fix:" in line for line in lines)


def test_standard_pr_over_15_files_requires_split_justification() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=200,
        counted_files=16,
        pr_body=_standard_body(),
        changed_files=[f"docs/design/example_{index}.md" for index in range(16)],
    )

    assert exit_code == 1
    assert any("Required section missing: ## Split Justification" in line for line in lines)
    assert any("file" in line for line in lines)


def test_standard_pr_between_16_and_20_files_passes_with_split_justification() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1200,
        counted_files=20,
        pr_body=_standard_body(
            "\n## Split Justification\nDesign guard and docs proof land together.\n"
        ),
        changed_files=[f"docs/design/example_{index}.md" for index in range(20)],
    )

    assert exit_code == 0
    assert any("standard governance/design PR <= 20 files" in line for line in lines)


def test_standard_pr_over_20_files_fails_closed() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=200,
        counted_files=21,
        pr_body=_standard_body("\n## Split Justification\nStill too large.\n"),
        changed_files=[f"docs/design/example_{index}.md" for index in range(21)],
    )

    assert exit_code == 1
    assert any("standard governance/design PR has 21 files; cap is 20" in line for line in lines)
    assert not any("emergency exception" in line for line in lines)


def test_frontend_mvp_pr_passes_only_with_approval_and_split_justification() -> None:
    changed_files = [f"frontend/src/flow/example_{index}.tsx" for index in range(25)]
    approved_body = _standard_body(
        "\n## Split Justification\nOne vertical user flow requires shared component and test updates.\n"
        "\nOperator approval: approved for frontend vertical MVP one vertical user flow.\n"
        "\nFrontend vertical MVP approval: approved for one vertical user flow.\n",
    )

    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1200,
        counted_files=25,
        pr_body=approved_body,
        changed_files=changed_files,
    )

    assert exit_code == 0
    assert any("frontend vertical MVP <= 30 files" in line for line in lines)

    failed_code, failed_lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1200,
        counted_files=25,
        pr_body=_standard_body("\n## Split Justification\nOne flow.\n"),
        changed_files=changed_files,
    )

    assert failed_code == 1
    assert any("operator approval for frontend vertical MVP" in line for line in failed_lines)


def test_frontend_mvp_pr_over_30_files_fails() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=400,
        counted_files=31,
        pr_body=_standard_body(
            "\n## Split Justification\nOne vertical flow.\n"
            "\nOperator approval: approved for frontend vertical MVP one vertical user flow.\n"
            "\nFrontend vertical MVP approval: approved for one vertical user flow.\n",
        ),
        changed_files=[f"frontend/src/flow/example_{index}.tsx" for index in range(31)],
    )

    assert exit_code == 1
    assert any(">30 files without emergency/operator exception" in line for line in lines)


def test_frontend_mvp_rejects_backend_api_ai_runtime_mix_without_exception() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=400,
        counted_files=22,
        pr_body=_standard_body(
            "\n## Split Justification\nOne vertical flow.\n"
            "\nOperator approval: approved for frontend vertical MVP one vertical user flow.\n"
            "\nFrontend vertical MVP approval: approved for one vertical user flow.\n",
        ),
        changed_files=[f"frontend/src/flow/example_{index}.tsx" for index in range(21)]
        + ["app/routers/example.py"],
    )

    assert exit_code == 1
    assert any(
        "frontend MVP mixes frontend UI with backend/API/AI runtime" in line for line in lines
    )
    assert any("How to fix:" in line for line in lines)


def test_standard_sized_frontend_backend_mix_requires_mix_approval() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=180,
        counted_files=15,
        pr_body=_standard_body(),
        changed_files=[f"frontend/src/flow/example_{index}.tsx" for index in range(10)]
        + [f"app/routers/example_{index}.py" for index in range(5)],
    )

    assert exit_code == 1
    assert any("Category: frontend_vertical_mvp" in line for line in lines)
    assert any("operator approval for frontend vertical MVP" in line for line in lines)


def test_frontend_mvp_allows_backend_api_ai_runtime_mix_with_explicit_mix_approval() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=400,
        counted_files=22,
        pr_body=_standard_body(
            "\n## Split Justification\nOne vertical flow needs one contract shim.\n"
            "\nOperator approval: approved for frontend vertical MVP one vertical user flow.\n"
            "\nFrontend vertical MVP approval: approved for one vertical user flow.\n"
            "\nFrontend/backend mix approval: approved for one contract shim.\n",
        ),
        changed_files=[f"frontend/src/flow/example_{index}.tsx" for index in range(21)]
        + ["app/routers/example.py"],
    )

    assert exit_code == 0
    assert any("frontend vertical MVP <= 30 files" in line for line in lines)


def test_privileged_pr_over_15_files_fails_without_exception() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=200,
        counted_files=16,
        pr_body=_standard_body("\n## Split Justification\nCI policy and tests.\n"),
        changed_files=["scripts/ci/check_pr_size_governance.py"]
        + [f"tests/example_{index}.py" for index in range(15)],
    )

    assert exit_code == 1
    assert any("privileged CI/security/workflow PR has 16 files" in line for line in lines)
    assert any("operator-approved privileged scope exception" in line for line in lines)


def test_micro_privileged_pr_uses_privileged_category() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=20,
        counted_files=2,
        pr_body="",
        changed_files=["scripts/ci/check_pr_size_governance.py", "tests/test_check.py"],
    )

    assert exit_code == 0
    assert any("category: privileged_ci_security_workflow" in line for line in lines)
    assert not any("OK (micro PR" in line for line in lines)


def test_dotfile_privileged_paths_are_not_normalized_out_of_privileged_lane() -> None:
    for path in (
        ".github/workflows/ci.yml",
        "./.github/workflows/ci.yml",
        ".trivyignore",
        "./.trivyignore",
    ):
        assert size_gate._is_privileged_path(path)


def test_privileged_pr_cannot_mix_frontend_product_without_exception() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=20,
        counted_files=2,
        pr_body="",
        changed_files=["scripts/ci/check_pr_size_governance.py", "frontend/src/App.tsx"],
    )

    assert exit_code == 1
    assert any("mixes with frontend product implementation" in line for line in lines)


def test_privileged_pr_over_15_files_passes_with_approved_exception() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=200,
        counted_files=16,
        pr_body=_standard_body(
            "\n## Split Justification\nCI policy and tests.\n"
            "\nOperator approval: approved for privileged CI scope exception.\n"
            "\nPrivileged scope exception: approved for current CI unblocker.\n",
        ),
        changed_files=["scripts/ci/check_pr_size_governance.py"]
        + [f"tests/example_{index}.py" for index in range(15)],
    )

    assert exit_code == 0
    assert any("privileged CI/security/workflow policy" in line for line in lines)


def test_privileged_pr_exception_requires_specific_privileged_label() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=200,
        counted_files=16,
        pr_body=_standard_body(
            "\n## Split Justification\nCI policy and tests.\n"
            "\nOperator approval: approved for generic exception.\n",
        ),
        changed_files=["scripts/ci/check_pr_size_governance.py"]
        + [f"tests/example_{index}.py" for index in range(15)],
    )

    assert exit_code == 1
    assert any("operator-approved privileged scope exception" in line for line in lines)


def test_mapping_and_ledger_closeout_files_are_allowed_same_pr() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=200,
        counted_files=16,
        pr_body=_standard_body(
            "\n## Split Justification\nCloseout proof belongs with the governance change.\n"
        ),
        changed_files=[f"docs/design/example_{index}.md" for index in range(14)]
        + ["docs/review/PR_1841_FIXED_MAPPING.md", "docs/roadmap/BACKLOG_LEDGER.md"],
    )

    assert exit_code == 0
    assert any("Closeout files allowed in same PR: 2" in line for line in lines)


def test_operator_exception_rejects_negated_or_ambiguous_approval() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=40,
        counted_files=31,
        pr_body=_standard_body(
            "\n## Split Justification\nToo large.\n"
            "\nNo operator-approved scope exception.\n"
            "\nOperator approval: yes/no\n"
            "\nScope exception: not approved.\n",
        ),
        changed_files=[f"docs/design/example_{index}.md" for index in range(31)],
    )

    assert exit_code == 1
    assert any(">30 files without emergency/operator exception" in line for line in lines)


def test_operator_exception_rejects_post_approval_negation() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=40,
        counted_files=31,
        pr_body=_standard_body(
            "\n## Split Justification\nToo large.\n"
            "\nOperator approval: approved but not really\n"
            "\nEmergency exception: approved but not really\n",
        ),
        changed_files=[f"docs/design/example_{index}.md" for index in range(31)],
    )

    assert exit_code == 1
    assert any(">30 files without emergency/operator exception" in line for line in lines)


def test_operator_exception_allows_unrelated_negation_outside_approval_lines() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=40,
        counted_files=31,
        pr_body=_standard_body(
            "\n## Split Justification\nEmergency CI unblocker must land together.\n"
            "\nOperator approval: approved for emergency CI unblocker.\n"
            "\nEmergency exception: approved for current CI unblocker.\n"
            "\n## Notes\nNo additional exception requested after this PR.\n",
        ),
        changed_files=[f"docs/design/example_{index}.md" for index in range(31)],
    )

    assert exit_code == 0
    assert any(">30 files" in line and "OK" in line for line in lines)


def test_standard_sections_ignore_comments_and_nested_headings() -> None:
    assert size_gate.missing_standard_sections(
        "<!--\n## Scope\n## Out of scope\n## Tests\n-->"
    ) == [
        "scope",
        "out of scope",
        "tests",
    ]
    assert size_gate.missing_standard_sections(
        "## Summary\n### Scope\nText\n### Out of scope\nText\n### Tests\nText\n",
    ) == ["scope", "out of scope", "tests"]


def test_micro_governance_docs_require_standard_sections() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=10,
        counted_files=1,
        pr_body="## Summary\nTiny governance doc.\n",
        changed_files=["docs/policy/PR_SCOPE_RULES.md"],
    )

    assert exit_code == 1
    assert any("micro governance/security PR body sections missing" in line for line in lines)


def test_micro_non_governance_pr_still_passes_without_sections() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=10,
        counted_files=1,
        pr_body="",
        changed_files=["docs/product/tiny-note.md"],
    )

    assert exit_code == 0
    assert any("OK (micro PR" in line for line in lines)


def test_frontend_mvp_requires_specific_lane_approval_line() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=100,
        counted_files=22,
        pr_body=_standard_body(
            "\n## Split Justification\nOne vertical flow.\n"
            "\nOperator approval: approved for this PR.\n"
            "\nQuoted example: frontend vertical MVP approval may be needed.\n",
        ),
        changed_files=[f"frontend/src/flow/example_{index}.tsx" for index in range(22)],
    )

    assert exit_code == 1
    assert any("operator approval for frontend vertical MVP" in line for line in lines)


def test_collect_changed_files_includes_rename_old_and_new_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResult:
        stdout = b"R100\0scripts/ci/old_guard.py\0docs/old_guard.md\0A\0docs/new.md\0"

    def fake_run(*args: object, **kwargs: object) -> FakeResult:
        return FakeResult()

    monkeypatch.setattr(size_gate.subprocess, "run", fake_run)

    assert size_gate.collect_changed_files(base_sha="base", head_sha="head") == [
        "scripts/ci/old_guard.py",
        "docs/old_guard.md",
        "docs/new.md",
    ]


def test_rename_from_privileged_old_path_uses_privileged_category() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1,
        counted_files=2,
        pr_body="",
        changed_files=["scripts/ci/old_guard.py", "docs/old_guard.md"],
    )

    assert exit_code == 0
    assert any("category: privileged_ci_security_workflow" in line for line in lines)


def test_guard_is_offline_and_does_not_require_network_for_event_body(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": {"body": "## Split Justification\nRequired."}}),
        encoding="utf-8",
    )

    assert size_gate.extract_pr_body(event_path) == "## Split Justification\nRequired."


def test_extract_pr_body_missing_body_without_token_does_not_call_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"repository": {"full_name": "owner/repo"}, "pull_request": {"number": 123}}),
        encoding="utf-8",
    )
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def fail_urlopen(*args: object, **kwargs: object) -> object:  # pragma: no cover
        raise AssertionError("network must not be called without a token")

    monkeypatch.setattr(size_gate.urllib.request, "urlopen", fail_urlopen)

    assert size_gate.extract_pr_body(event_path) == ""


def test_extract_pr_body_reads_github_event_payload(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": {"body": "## Split Justification\nRequired."}}),
        encoding="utf-8",
    )

    assert size_gate.extract_pr_body(event_path) == "## Split Justification\nRequired."


def test_extract_pr_body_falls_back_to_api_for_missing_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "repository": {"full_name": "owner/repo"},
                "pull_request": {"number": 123},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    class FakeResponse:
        def __init__(self, payload: str) -> None:
            self._payload = payload.encode("utf-8")

        def read(self) -> bytes:
            return self._payload

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
            return None

    def fake_urlopen(request, timeout=10):  # pragma: no cover
        assert request.full_url == "https://api.github.com/repos/owner/repo/pulls/123"
        assert request.headers["Authorization"] == "Bearer test-token"
        return FakeResponse('{"body": "## Split Justification\\nFrom api."}')

    monkeypatch.setattr(size_gate.urllib.request, "urlopen", fake_urlopen)

    assert size_gate.extract_pr_body(event_path) == "## Split Justification\nFrom api."


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--base-sha"], "Missing value for --base-sha."),
        (["--base-sha", "--head-sha"], "Missing value for --base-sha."),
        (["--head-sha"], "Missing value for --head-sha."),
        (["--body"], "Missing value for --body."),
        (["--event-path"], "Missing value for --event-path."),
    ],
)
def test_main_fails_cleanly_when_flag_value_is_missing(
    argv: list[str],
    message: str,
) -> None:
    with pytest.raises(SystemExit, match=message):
        size_gate.main(argv)
