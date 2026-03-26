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
    assert counted_files == 2


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


def test_evaluate_pr_size_policy_passes_for_normal_bucket() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=220,
        counted_files=4,
        pr_body="",
    )

    assert exit_code == 0
    assert any(f"OK (<={size_gate.NORMAL_MAX_LOC} LoC)" in line for line in lines)


def test_evaluate_pr_size_policy_warns_for_medium_bucket() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=540,
        counted_files=8,
        pr_body="",
    )

    assert exit_code == 0
    assert any(
        f"WARNING ({size_gate.NORMAL_MAX_LOC + 1}-{size_gate.WARNING_MAX_LOC} LoC)" in line
        for line in lines
    )


def test_evaluate_pr_size_policy_fails_without_split_justification() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1200,
        counted_files=11,
        pr_body="## Summary\nLarge PR.\n",
    )

    assert exit_code == 1
    assert any(
        f"FAIL (>{size_gate.WARNING_MAX_LOC} LoC without explicit split justification)" in line
        for line in lines
    )


def test_evaluate_pr_size_policy_passes_with_split_justification() -> None:
    exit_code, lines = size_gate.evaluate_pr_size_policy(
        total_changed_lines=1200,
        counted_files=11,
        pr_body="## Summary\nLarge PR.\n\n## Split Justification\nWorkflow parity must land together.\n",
    )

    assert exit_code == 0
    assert any("split justification is present" in line for line in lines)


def test_extract_pr_body_reads_github_event_payload(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": {"body": "## Split Justification\nRequired."}}),
        encoding="utf-8",
    )

    assert size_gate.extract_pr_body(event_path) == "## Split Justification\nRequired."


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--base-sha"], "Missing value for --base-sha."),
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
