"""Deterministic tests for Phase2 PR body gates."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.ci.check_pr_body_phase2_gates as gates
import scripts.ci.check_pr_merge_readiness as merge_readiness
import scripts.orchestration.review_mapping_artifact as mapping_artifact

LANE_START_PACKET_ID = "a733b2e09986"
LANE_START_PACKET_PATH = f"{gates.LANE_START_PACKET_PREFIX}{LANE_START_PACKET_ID}.json"
PR_TEMPLATE_PRODUCERS = [
    gates.REPO_ROOT / ".github/pull_request_template.md",
    *sorted((gates.REPO_ROOT / ".github/PULL_REQUEST_TEMPLATE").glob("*.md")),
    gates.REPO_ROOT / "docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md",
]

VALID_BODY_WITH_MAPPING = """## Summary
Phase2 PR body gate implementation.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4

## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-719.json

## Lane Start Provenance
Packet: {packet_path}
Starter: scripts/orchestration/start_pr_lane.sh
""".format(packet_path=LANE_START_PACKET_PATH)

VALID_BODY_MIRROR_ONLY = """## Summary
Phase2 PR body gate implementation.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- canonical artifact: `docs/review/PR_998_FIXED_MAPPING.md`

## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-998.json

## Lane Start Provenance
Packet: {packet_path}
Starter: scripts/orchestration/start_pr_lane.sh
""".format(packet_path=LANE_START_PACKET_PATH)

PRE_CLOSEOUT_BODY = """## Summary
Phase2 PR body gate pre-closeout state.

<!-- phase2-pre-closeout: final-security-pending -->

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping
- Pending final clean scan and the single mapping/closeout commit.

## Experiment Runner Evidence
Not applicable: fixture only exercises the non-mergeable pre-closeout state.

## Lane Start Provenance
Packet: {packet_path}
Starter: scripts/orchestration/start_pr_lane.sh
""".format(packet_path=LANE_START_PACKET_PATH)


def _valid_experiment_result_payload(*, status: str = "accepted") -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "experiment_id": "exp-1800",
        "runner_mode": "oracle_only_governance_reviewer",
        "candidate_patch": "oracle_only_governance_reviewer",
        "status": status,
        "failure_class": None if status == "accepted" else "policy_violation",
        "mutated_paths": [],
        "oracle_results": (
            [
                {
                    "command": ".venv/bin/python -m pytest -q tests/test_pr_body_phase2_gates.py",
                    "returncode": 0,
                    "timed_out": False,
                    "truncated": False,
                    "stdout": "passed",
                    "stderr": "",
                    "cwd": ".",
                }
            ]
            if status == "accepted"
            else []
        ),
        "budget_observations": {
            "wall_clock_seconds": 1,
            "attempts": 1 if status == "accepted" else 0,
            "retries_consumed": 0,
            **(
                {"runner_error": "candidate rejected before oracle execution"}
                if status == "rejected"
                else {}
            ),
        },
        "shared_tree_untouched": True,
        "promotion_ready": False,
        "contribution_kind": "none",
        "coauthor_required": False,
        "coauthor_reason": "",
    }


def _write_experiment_result(
    repo_root: Path,
    relative_path: str,
    payload: dict[str, object] | None = None,
) -> None:
    artifact = repo_root / relative_path
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(payload or _valid_experiment_result_payload()),
        encoding="utf-8",
    )


def _write_lane_start_packet(repo_root: Path) -> None:
    packet = repo_root / LANE_START_PACKET_PATH
    packet.parent.mkdir(parents=True, exist_ok=True)
    packet.write_text("{}", encoding="utf-8")


def _cleanup_lane_start_packet(repo_root: Path) -> None:
    packet = repo_root / LANE_START_PACKET_PATH
    packet.unlink(missing_ok=True)


def test_phase2_guard_accepts_valid_mapping() -> None:
    errors = gates.check_pr_body_phase2_gates(body=VALID_BODY_WITH_MAPPING)
    assert errors == []


def test_phase2_guard_accepts_url_only_entry() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- https://github.com/org/repo/pull/719#issuecomment-123",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert errors == []


def test_phase2_guard_accepts_backticked_url() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- `https://github.com/org/repo/pull/719#issuecomment-123` -> 28069fd4",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert errors == []


def test_phase2_guard_accepts_backticked_sha() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> `28069fd4`",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert errors == []


def test_phase2_guard_accepts_backticked_url_and_sha() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- `https://github.com/org/repo/pull/719#issuecomment-123` -> `28069fd4`",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert errors == []


def test_phase2_guard_accepts_na_mapping() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- N/A",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert errors == []


def test_phase2_guard_accepts_no_actionable_comments_marker() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- No actionable review comments",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert errors == []


def test_phase2_guard_accepts_mirror_only_body_when_mapping_details_not_required() -> None:
    errors = gates.check_pr_body_phase2_gates(
        body=VALID_BODY_MIRROR_ONLY,
        mode=gates.BodyValidationMode.MIRROR_ONLY,
    )
    assert errors == []


def test_phase2_guard_rejects_stale_pre_closeout_marker_in_mirror_only_body() -> None:
    body = VALID_BODY_MIRROR_ONLY.replace(
        "## Discussion Thread Pass",
        "<!-- phase2-pre-closeout: final-security-pending -->\n\n## Discussion Thread Pass",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.MIRROR_ONLY,
    )

    assert errors == [
        "Pre-closeout marker must be removed after the canonical mapping/seal is published."
    ]


@pytest.mark.parametrize(
    ("mode", "body"),
    [
        (gates.BodyValidationMode.MIRROR_ONLY, VALID_BODY_MIRROR_ONLY),
        (gates.BodyValidationMode.FULL_MAPPING, VALID_BODY_WITH_MAPPING),
    ],
)
def test_phase2_guard_rejects_stale_pending_status_in_final_modes(
    mode: gates.BodyValidationMode,
    body: str,
) -> None:
    stale_body = body.replace(
        "## Experiment Runner Evidence",
        "## Risks / rollback\n"
        "- Pending final clean scan and the single mapping/closeout commit.\n\n"
        "## Experiment Runner Evidence",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=stale_body,
        mode=mode,
    )

    assert errors == [
        "Pre-closeout pending status must be removed after the canonical mapping/seal is "
        "published."
    ]


@pytest.mark.parametrize(
    ("reserved_line", "expected_error"),
    [
        (
            "<!--   phase2-pre-closeout: final-security-pending   -->\r",
            "Pre-closeout marker must be removed",
        ),
        (
            "<!-- phase2-pre-closeout:\tfinal-security-pending -->",
            "Pre-closeout marker must be removed",
        ),
        (
            "-  Pending final clean scan and the single mapping/closeout commit. \t\r",
            "Pre-closeout pending status must be removed",
        ),
        (
            "- Pending\tfinal  clean scan and the single mapping/closeout commit.",
            "Pre-closeout pending status must be removed",
        ),
    ],
)
@pytest.mark.parametrize(
    ("mode", "body"),
    [
        (gates.BodyValidationMode.MIRROR_ONLY, VALID_BODY_MIRROR_ONLY),
        (gates.BodyValidationMode.FULL_MAPPING, VALID_BODY_WITH_MAPPING),
    ],
)
def test_phase2_final_modes_deny_render_equivalent_reserved_tokens(
    mode: gates.BodyValidationMode,
    body: str,
    reserved_line: str,
    expected_error: str,
) -> None:
    stale_body = body.replace(
        "## Experiment Runner Evidence",
        f"{reserved_line}\n\n## Experiment Runner Evidence",
    )

    errors = gates.check_pr_body_phase2_gates(body=stale_body, mode=mode)

    assert any(expected_error in error for error in errors)


@pytest.mark.parametrize(
    "reserved_carrier",
    [
        "```\n- Pending final clean scan and the single mapping/closeout commit.\n```",
        "<!--\n- Pending final clean scan and the single mapping/closeout commit.\n-->",
        "`<!--`\n- Pending final clean scan and the single mapping/closeout commit.",
        "```bad`info\n- Pending final clean scan and the single mapping/closeout commit.",
        "~~~\n<!-- phase2-pre-closeout: final-security-pending -->\n~~~",
    ],
)
def test_phase2_final_denial_is_reserved_physical_line_carrier_independent(
    reserved_carrier: str,
) -> None:
    body = VALID_BODY_MIRROR_ONLY.replace(
        "## Experiment Runner Evidence",
        f"{reserved_carrier}\n\n## Experiment Runner Evidence",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.MIRROR_ONLY,
    )

    assert any("Pre-closeout" in error and "must be removed" in error for error in errors)


def test_phase2_guard_accepts_explicit_non_mergeable_pre_closeout_state() -> None:
    errors = gates.check_pr_body_phase2_gates(
        body=PRE_CLOSEOUT_BODY,
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert errors == []


def test_phase2_reserved_protocol_lines_are_exact_template_tokens() -> None:
    marker_line = f"<!-- {gates.PHASE2_CONFIG['pre_closeout_marker']} -->"
    pending_line = f"- {gates.PHASE2_CONFIG['pre_closeout_pending_text']}"
    template = (gates.REPO_ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")

    assert gates._PRE_CLOSEOUT_MARKER_LINE == marker_line
    assert gates._PRE_CLOSEOUT_PENDING_LINE == pending_line
    for reserved_line in (marker_line, pending_line):
        assert template.split("\n").count(reserved_line) == 1
        assert gates._contains_exact_line(reserved_line, reserved_line)
        assert not gates._contains_exact_line(f"{reserved_line} ", reserved_line)


def test_default_pr_template_satisfies_pre_closeout_contract() -> None:
    template = (gates.REPO_ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")

    errors = gates.check_pr_body_phase2_gates(
        body=template,
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert errors == []


@pytest.mark.parametrize(
    "template_path",
    PR_TEMPLATE_PRODUCERS,
    ids=lambda path: str(path.relative_to(gates.REPO_ROOT)),
)
def test_all_pr_template_producers_satisfy_pre_closeout_contract(
    template_path: Path,
) -> None:
    errors = gates.check_pr_body_phase2_gates(
        body=template_path.read_text(encoding="utf-8"),
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert errors == []


def test_pre_closeout_template_inside_unmatched_fence_is_not_admitted() -> None:
    errors = gates.check_pr_body_phase2_gates(
        body=f"```\n{PRE_CLOSEOUT_BODY}",
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert any("Pre-closeout requires the exact marker" in error for error in errors)
    assert any("Missing required section" in error for error in errors)


def test_indented_fence_literal_cannot_erase_visible_stale_pending_status() -> None:
    body = VALID_BODY_MIRROR_ONLY.replace(
        "## Experiment Runner Evidence",
        "    ~~~\n"
        "- Pending final clean scan and the single mapping/closeout commit.\n"
        "~~~\n\n"
        "## Experiment Runner Evidence",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.MIRROR_ONLY,
    )

    assert any("Pre-closeout pending status must be removed" in error for error in errors)


def test_html_comment_syntax_inside_fence_does_not_leak_parser_state() -> None:
    body = f"```\n<!--\n```\n{VALID_BODY_MIRROR_ONLY}"

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.MIRROR_ONLY,
    )

    assert errors == []


def test_default_pr_template_without_pre_closeout_marker_fails() -> None:
    template = (gates.REPO_ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    without_marker = template.replace(
        "<!-- phase2-pre-closeout: final-security-pending -->\n\n",
        "",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=without_marker,
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert errors == [
        "Pre-closeout requires the exact marker: "
        "`<!-- phase2-pre-closeout: final-security-pending -->`."
    ]


def test_default_pr_template_without_rendered_link_is_not_closeout_evidence() -> None:
    template = (gates.REPO_ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    closeout_body = (
        template.replace(
            "<!-- phase2-pre-closeout: final-security-pending -->\n\n",
            "",
        )
        .replace("- [ ]", "- [x]")
        .replace(
            "- Pending final clean scan and the single mapping/closeout commit.\n",
            "",
        )
    )

    errors = gates.check_pr_body_phase2_gates(
        body=closeout_body,
        mode=gates.BodyValidationMode.FULL_MAPPING,
    )

    assert errors == [
        "Add at least one review-thread entry (`- <review-comment-url>` or "
        "`- <review-comment-url> -> <commit-sha>`) or "
        "`- No actionable review comments`."
    ]


@pytest.mark.parametrize(
    "template_path",
    PR_TEMPLATE_PRODUCERS,
    ids=lambda path: str(path.relative_to(gates.REPO_ROOT)),
)
def test_pr_template_producers_closeout_use_exact_branch_link(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    template_path: Path,
) -> None:
    template = template_path.read_text(encoding="utf-8")
    pr_number = 2192
    repository = "Katsiarynakavaleuskaya/PulsePlate"
    head_ref = "codex/align-pr-template-body-gates"
    (tmp_path / f"PR_{pr_number}_FIXED_MAPPING.md").write_text(
        f"""# PR {pr_number} — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(mapping_artifact, "_review_dir", lambda: tmp_path)
    closeout_body = mapping_artifact.replace_phase2_body_mirror(
        template,
        pr_number,
        repository=repository,
        ref=head_ref,
    )

    assert "docs/review/PR_<N>_FIXED_MAPPING.md" not in template
    assert (
        gates.check_pr_body_phase2_gates(
            body=closeout_body,
            mode=gates.BodyValidationMode.MIRROR_ONLY,
        )
        == []
    )
    assert (
        merge_readiness._canonical_artifact_markdown_link_count(
            closeout_body,
            pr_number,
            repository,
            head_ref,
        )
        == 1
    )


@pytest.mark.parametrize(
    ("anchor", "replacement"),
    [
        (
            "Closeout automation must replace the entire Phase2 block",
            "## Hidden guidance heading\n"
            "Closeout automation must replace the entire Phase2 block",
        ),
        (
            "- URL→SHA and disposition details belong only in the canonical artifact.",
            "```\n## Fenced example heading\n```\n\n"
            "- URL→SHA and disposition details belong only in the canonical artifact.",
        ),
    ],
)
def test_phase2_replacement_ignores_non_rendered_h2_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    anchor: str,
    replacement: str,
) -> None:
    pr_number = 2192
    (tmp_path / f"PR_{pr_number}_FIXED_MAPPING.md").write_text(
        f"""# PR {pr_number} — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(mapping_artifact, "_review_dir", lambda: tmp_path)
    template = (gates.REPO_ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    body = template.replace(anchor, replacement)

    assert (
        gates.check_pr_body_phase2_gates(
            body=body,
            mode=gates.BodyValidationMode.PRE_CLOSEOUT,
        )
        == []
    )

    rendered = mapping_artifact.replace_phase2_body_mirror(
        body,
        pr_number,
        repository="Katsiarynakavaleuskaya/PulsePlate",
        ref="codex/align-pr-template-body-gates",
    )

    assert "## Hidden guidance heading" not in rendered
    assert "## Fenced example heading" not in rendered
    assert "Pending final clean scan" not in rendered
    assert "## Split justification" in rendered


def test_phase2_body_replacement_requires_one_complete_ordered_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mapping_artifact, "read_mapping_artifact", lambda _pr_number: "")
    malformed = "## Discussion Thread Pass\n## Discussion Thread Pass\n## Split justification\n"

    with pytest.raises(ValueError, match="exactly one `## Discussion Thread Pass`"):
        mapping_artifact.replace_phase2_body_mirror(
            malformed,
            2192,
            repository="owner/repo",
            ref="codex/example",
        )


def test_phase2_guard_rejects_checked_pre_closeout_boxes() -> None:
    body = PRE_CLOSEOUT_BODY.replace("- [ ]", "- [x]")

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert any("must remain unchecked" in error for error in errors)


def test_phase2_guard_rejects_pre_closeout_without_pending_status() -> None:
    body = PRE_CLOSEOUT_BODY.replace(
        "- Pending final clean scan and the single mapping/closeout commit.\n",
        "",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert any("must declare the exact pending" in error for error in errors)


def test_phase2_guard_rejects_mapping_entries_during_pre_closeout() -> None:
    body = PRE_CLOSEOUT_BODY.replace(
        "- Pending final clean scan and the single mapping/closeout commit.",
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert any("must not contain completed mapping entries" in error for error in errors)


def test_phase2_guard_ignores_hidden_duplicate_pre_closeout_content() -> None:
    visible_checked = PRE_CLOSEOUT_BODY.replace("- [ ]", "- [x]")
    body = visible_checked.replace(
        "<!-- phase2-pre-closeout: final-security-pending -->",
        """<!--
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed
### Fixed in Commit Mapping
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
-->
<!-- phase2-pre-closeout: final-security-pending -->""",
    )

    errors = gates.check_pr_body_phase2_gates(
        body=body,
        mode=gates.BodyValidationMode.PRE_CLOSEOUT,
    )

    assert sum("must remain unchecked" in error for error in errors) == 2


def test_phase2_guard_rejects_duplicate_required_checklist_items() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- [x] Discussion-thread pass completed",
        "- [x] Discussion-thread pass completed\n- [x] Discussion-thread pass completed",
    )

    errors = gates.check_pr_body_phase2_gates(body=body)

    assert errors == ["Duplicate checklist item: `Discussion-thread pass completed`."]


def test_phase2_cli_accepts_explicit_pre_closeout_without_mapping_artifact(
    tmp_path: Path,
) -> None:
    event = {"pull_request": {"number": 998, "body": PRE_CLOSEOUT_BODY}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
                "--commit-range",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)

    assert result.returncode == 0
    assert "Pre-closeout: canonical mapping artifact is intentionally pending" in result.stdout
    assert "explicit non-mergeable pre-closeout state passed" in result.stdout


def test_phase2_cli_rejects_missing_mapping_without_pre_closeout(tmp_path: Path) -> None:
    event = {"pull_request": {"number": 998, "body": VALID_BODY_WITH_MAPPING}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_pr_body_phase2_gates.py",
            "--event-path",
            str(tmp_path / "event.json"),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert result.returncode == 1
    assert "Missing canonical review mapping artifact" in result.stdout


def test_select_body_validation_mode_prefers_mirror_when_artifact_exists() -> None:
    assert (
        gates._select_body_validation_mode(artifact_checked=True)
        is gates.BodyValidationMode.MIRROR_ONLY
    )
    assert (
        gates._select_body_validation_mode(artifact_checked=False)
        is gates.BodyValidationMode.FULL_MAPPING
    )


def test_mapping_section_stops_before_sibling_h3() -> None:
    section = gates._extract_mapping_section("""## Discussion Thread Pass

### Fixed in Commit Mapping
- No actionable review comments

### Other Details
- should not be parsed as mapping

## Merge Readiness
Not claimed.
""")

    assert "- No actionable review comments" in section
    assert "should not be parsed as mapping" not in section


def test_experiment_runner_evidence_accepts_valid_artifact_path() -> None:
    errors, warnings = gates.check_experiment_runner_evidence("""## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/nested/result.json
""")

    assert errors == []
    assert warnings == []


def test_experiment_runner_evidence_accepts_not_applicable_reason() -> None:
    errors, warnings = gates.check_experiment_runner_evidence("""## Experiment Runner Evidence
Not applicable: docs-only operator exception with no runner signal.
""")

    assert errors == []
    assert warnings == []


def test_experiment_runner_evidence_rejects_short_not_applicable_reason() -> None:
    errors, warnings = gates.check_experiment_runner_evidence("""## Experiment Runner Evidence
Not applicable: no
""")

    assert warnings == []
    assert any("not-applicable reason" in error for error in errors)


def test_experiment_runner_evidence_missing_is_advisory_warning() -> None:
    errors, warnings = gates.check_experiment_runner_evidence("## Summary\nNo evidence.\n")

    assert errors == []
    assert any("missing `## Experiment Runner Evidence`" in warning for warning in warnings)


def test_experiment_runner_evidence_required_mode_fails_missing_block() -> None:
    errors, warnings = gates.check_experiment_runner_evidence(
        "## Summary\nNo evidence.\n",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
    )

    assert warnings == []
    assert any("Required: missing `## Experiment Runner Evidence`" in error for error in errors)


def test_experiment_runner_evidence_required_mode_rejects_valid_but_missing_artifact_path() -> None:
    errors, warnings = gates.check_experiment_runner_evidence(
        """## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-required.json
""",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
    )

    assert warnings == []
    assert any("unavailable locally" in error for error in errors)


def test_experiment_runner_evidence_required_mode_rejects_nonexistent_artifact(
    tmp_path: Path,
) -> None:
    errors, warnings = gates.check_experiment_runner_evidence(
        """## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/missing.json
""",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
        repo_root=tmp_path,
    )

    assert warnings == []
    assert any("unavailable locally" in error for error in errors)


def test_experiment_runner_evidence_required_mode_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    relative_path = "artifacts/orchestration/experiments/results/malformed.json"
    artifact = tmp_path / relative_path
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{", encoding="utf-8")

    errors, warnings = gates.check_experiment_runner_evidence(
        f"""## Experiment Runner Evidence
Artifact: {relative_path}
""",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
        repo_root=tmp_path,
    )

    assert warnings == []
    assert any("cannot be parsed as JSON" in error for error in errors)


def test_experiment_runner_evidence_required_mode_rejects_missing_metadata(
    tmp_path: Path,
) -> None:
    relative_path = "artifacts/orchestration/experiments/results/missing-metadata.json"
    _write_experiment_result(tmp_path, relative_path, {"schema_version": "1.0"})

    errors, warnings = gates.check_experiment_runner_evidence(
        f"""## Experiment Runner Evidence
Artifact: {relative_path}
""",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
        repo_root=tmp_path,
    )

    assert warnings == []
    assert any("invalid result metadata" in error for error in errors)


def test_experiment_runner_evidence_required_mode_rejects_rejected_artifact(
    tmp_path: Path,
) -> None:
    relative_path = "artifacts/orchestration/experiments/results/rejected.json"
    _write_experiment_result(
        tmp_path,
        relative_path,
        _valid_experiment_result_payload(status="rejected"),
    )

    errors, warnings = gates.check_experiment_runner_evidence(
        f"""## Experiment Runner Evidence
Artifact: {relative_path}
""",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
        repo_root=tmp_path,
    )

    assert warnings == []
    assert any("not accepted evidence" in error for error in errors)


def test_experiment_runner_evidence_required_mode_accepts_valid_local_artifact(
    tmp_path: Path,
) -> None:
    relative_path = "artifacts/orchestration/experiments/results/accepted.json"
    _write_experiment_result(tmp_path, relative_path)

    errors, warnings = gates.check_experiment_runner_evidence(
        f"""## Experiment Runner Evidence
Artifact: {relative_path}
""",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
        repo_root=tmp_path,
    )

    assert errors == []
    assert warnings == []


def test_experiment_runner_evidence_required_mode_accepts_not_applicable_reason() -> None:
    errors, warnings = gates.check_experiment_runner_evidence(
        """## Experiment Runner Evidence
Not applicable: trivial docs cleanup with no runner result used.
""",
        mode=gates.ExperimentRunnerEvidenceMode.REQUIRED,
    )

    assert errors == []
    assert warnings == []


def test_experiment_runner_evidence_rejects_artifact_outside_results() -> None:
    errors, warnings = gates.check_experiment_runner_evidence("""## Experiment Runner Evidence
Artifact: artifacts/orchestration/task_packets/packet.json
""")

    assert warnings == []
    assert any("artifacts/orchestration/experiments/results/" in error for error in errors)


def test_experiment_runner_evidence_rejects_empty_artifact_basename() -> None:
    errors, warnings = gates.check_experiment_runner_evidence("""## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/.json
""")

    assert warnings == []
    assert any("artifacts/orchestration/experiments/results/" in error for error in errors)


def test_experiment_runner_evidence_rejects_windows_parent_traversal() -> None:
    errors, warnings = gates.check_experiment_runner_evidence(r"""## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/..\outside.json
""")

    assert warnings == []
    assert any("artifacts/orchestration/experiments/results/" in error for error in errors)


def test_experiment_runner_evidence_rejects_mixed_artifact_and_not_applicable() -> None:
    errors, warnings = gates.check_experiment_runner_evidence("""## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp.json
Not applicable: this should not be mixed with an artifact.
""")

    assert warnings == []
    assert any("not both" in error for error in errors)


def test_phase2_cli_required_mode_fails_missing_experiment_runner_evidence() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        """## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-719.json

""",
        "",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(Path(gates.__file__)),
            "--body",
            body,
            "--experiment-runner-evidence-mode",
            "required",
            "--commit-range",
            "HEAD..HEAD",
        ],
        cwd=gates.REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 1
    assert "Required: missing `## Experiment Runner Evidence`" in result.stdout


def test_phase2_cli_env_required_mode_fails_missing_experiment_runner_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        """## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-719.json

""",
        "",
    )
    monkeypatch.setenv("PULSEPLATE_EXPERIMENT_RUNNER_EVIDENCE_MODE", "required")

    result = subprocess.run(
        [
            sys.executable,
            str(Path(gates.__file__)),
            "--body",
            body,
            "--commit-range",
            "HEAD..HEAD",
        ],
        cwd=gates.REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
        env=os.environ.copy(),
    )

    assert result.returncode == 1
    assert "Required: missing `## Experiment Runner Evidence`" in result.stdout


def test_lane_start_provenance_accepts_local_task_packet_and_starter(tmp_path: Path) -> None:
    _write_lane_start_packet(tmp_path)

    errors, warnings = gates.check_lane_start_provenance(
        f"""## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
""",
        repo_root=tmp_path,
    )

    assert errors == []
    assert warnings == []


def test_lane_start_provenance_rejects_repo_markdown_packet_reference() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Packet: docs/orchestration/EXPERIMENT_RUNNER_LANE_START_PROVENANCE_PACKET_2026-05-21.md
""")

    assert warnings == []
    assert errors
    assert any(gates.LANE_START_PACKET_PREFIX in error for error in errors)


def test_lane_start_provenance_rejects_fake_repo_packet_even_when_file_exists(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "docs" / "orchestration" / "FAKE_PACKET.md"
    packet.parent.mkdir(parents=True)
    packet.write_text("# Fake Packet\n", encoding="utf-8")

    errors, warnings = gates.check_lane_start_provenance(
        """## Lane Start Provenance
Packet: docs/orchestration/FAKE_PACKET.md
""",
        repo_root=tmp_path,
    )

    assert warnings == []
    assert errors
    assert any(gates.LANE_START_PACKET_PREFIX in error for error in errors)


def test_lane_start_provenance_rejects_mixed_case_repo_packet_reference(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "docs" / "orchestration" / "Philosophy_Epic_V2_Packet_2026-05-20.md"
    packet.parent.mkdir(parents=True)
    packet.write_text(
        """# Packet

Bootstrap packet: `artifacts/orchestration/task_packets/abc123.json`

Coordinator start: check_preflight.py -> task_bootstrap.py -> agent-coordinator
""",
        encoding="utf-8",
    )

    errors, warnings = gates.check_lane_start_provenance(
        """## Lane Start Provenance
Packet: docs/orchestration/Philosophy_Epic_V2_Packet_2026-05-20.md
""",
        repo_root=tmp_path,
    )

    assert warnings == []
    assert errors
    assert any(gates.LANE_START_PACKET_PREFIX in error for error in errors)


def test_lane_start_provenance_accepts_narrow_exception() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup: no branch bootstrap needed.
""")

    assert errors == []
    assert warnings == []


def test_lane_start_provenance_missing_is_dry_run_warning() -> None:
    errors, warnings = gates.check_lane_start_provenance("## Summary\nNo lane provenance.\n")

    assert errors == []
    assert any(
        "would fail when lane-start provenance is promoted" in warning for warning in warnings
    )


def test_lane_start_provenance_rejects_local_only_packet_escape() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Packet: artifacts/orchestration/experiments/results/not-a-packet.json
""")

    assert warnings == []
    assert errors
    assert any(gates.LANE_START_PACKET_PREFIX in error for error in errors)


def test_lane_start_provenance_rejects_non_packet_orchestration_doc() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Packet: docs/orchestration/AGENTS.md
""")

    assert warnings == []
    assert errors
    assert any(gates.LANE_START_PACKET_PREFIX in error for error in errors)


def test_lane_start_provenance_rejects_negated_exception_reason() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: not a trivial docs cleanup, real governance work.
""")

    assert warnings == []
    assert any("exception must be limited" in error for error in errors)


def test_lane_start_provenance_rejects_starter_only() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Starter: scripts/orchestration/start_pr_lane.sh
""")

    assert warnings == []
    assert any("starter is supplemental" in error for error in errors)


def test_lane_start_provenance_allows_exception_with_supplemental_starter() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup
Starter: scripts/orchestration/start_pr_lane.sh
""")

    assert errors == []
    assert warnings == []


def test_lane_start_provenance_warns_on_unavailable_local_packet() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Packet: artifacts/orchestration/task_packets/fake.json
Starter: scripts/orchestration/start_pr_lane.sh
""")

    assert errors == []
    assert any("not available locally" in warning for warning in warnings)


def test_lane_start_provenance_rejects_unavailable_repo_packet_path(
    tmp_path: Path,
) -> None:
    errors, warnings = gates.check_lane_start_provenance(
        """## Lane Start Provenance
Packet: docs/orchestration/MISSING_PACKET_2099-01-01.md
Starter: scripts/orchestration/start_pr_lane.sh
""",
        repo_root=tmp_path,
    )

    assert warnings == []
    assert errors
    assert any(gates.LANE_START_PACKET_PREFIX in error for error in errors)


def test_lane_start_provenance_warns_on_symlink_loop_packet(
    tmp_path: Path,
) -> None:
    packet = tmp_path / "artifacts" / "orchestration" / "task_packets" / "loop.json"
    packet.parent.mkdir(parents=True)
    packet.symlink_to(packet)

    errors, warnings = gates.check_lane_start_provenance(
        """## Lane Start Provenance
Packet: artifacts/orchestration/task_packets/loop.json
Starter: scripts/orchestration/start_pr_lane.sh
""",
        repo_root=tmp_path,
    )

    assert errors == []
    assert any("not available locally" in warning for warning in warnings)


def test_lane_start_provenance_rejects_host_preflight_authority() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Host preflight: Codex preflight already ran.
""")

    assert warnings == []
    assert any("must not cite host/Codex/Cursor/raw preflight" in error for error in errors)


def test_lane_start_provenance_rejects_host_preflight_sentence_authority() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup
Host preflight already ran.
""")

    assert warnings == []
    assert any("must not cite host/Codex/Cursor/raw preflight" in error for error in errors)


def test_lane_start_provenance_rejects_labeled_host_preflight_authority() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup
Authority note: host preflight already ran.
""")

    assert warnings == []
    assert any("must not cite host/Codex/Cursor/raw preflight" in error for error in errors)


def test_lane_start_provenance_rejects_weak_negation_preflight_authority() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup
Host preflight cannot be ignored; it already ran.
""")

    assert warnings == []
    assert any("must not cite host/Codex/Cursor/raw preflight" in error for error in errors)


def test_lane_start_provenance_rejects_contradictory_negated_preflight() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup
Host preflight is not authoritative, but it already ran.
""")

    assert warnings == []
    assert any("must not cite host/Codex/Cursor/raw preflight" in error for error in errors)


def test_lane_start_provenance_rejects_cursor_preflight_authority() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Starter: scripts/orchestration/start_pr_lane.sh
Cursor preflight: already ran.
""")

    assert warnings == []
    assert any("must not cite host/Codex/Cursor/raw preflight" in error for error in errors)


def test_lane_start_provenance_allows_negated_host_preflight_context() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup
Starter: scripts/orchestration/start_pr_lane.sh
Host/Codex preflight is not authoritative lane provenance.
""")

    assert errors == []
    assert warnings == []


def test_lane_start_provenance_allows_negated_host_preflight_explanation() -> None:
    errors, warnings = gates.check_lane_start_provenance("""## Lane Start Provenance
Exception: trivial docs cleanup
Starter: scripts/orchestration/start_pr_lane.sh
Host/Codex preflight is not authoritative lane provenance; use repo bootstrap evidence.
""")

    assert errors == []
    assert warnings == []


def test_experiment_runner_coauthor_advisory_warns_when_required_trailer_missing(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "oracle.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "Runner oracle shaped the fixed mapping.",
            }
        ),
        encoding="utf-8",
    )
    body = """## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/oracle.json
"""

    warnings = gates.check_experiment_runner_coauthor_advisory(
        body,
        commit_messages="feat: human-only commit\n",
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/oracle.json` sets "
        "coauthor_required=true, but branch commits do not include the canonical "
        "Experiment Runner co-author trailer. Reason: Runner oracle shaped the fixed mapping."
    ]


def test_experiment_runner_coauthor_advisory_clears_when_trailer_present(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "oracle.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "Runner oracle shaped the fixed mapping.",
            }
        ),
        encoding="utf-8",
    )

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/oracle.json\n",
        commit_messages=(
            "feat: governed contribution\n\n"
            "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        ),
        repo_root=tmp_path,
    )

    assert warnings == []


def test_experiment_runner_coauthor_advisory_ignores_body_mentions_of_trailer(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "oracle.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "Runner oracle shaped the fixed mapping.",
            }
        ),
        encoding="utf-8",
    )

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/oracle.json\n",
        commit_messages=(
            "feat: mention trailer\n\n"
            "The following text is documentation, not a commit trailer:\n"
            "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
            "Additional prose after the mention keeps it outside the trailer block.\n"
        ),
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/oracle.json` sets "
        "coauthor_required=true, but branch commits do not include the canonical "
        "Experiment Runner co-author trailer. Reason: Runner oracle shaped the fixed mapping."
    ]


def test_experiment_runner_coauthor_advisory_requires_git_trailer_block(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "oracle.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "Runner oracle shaped the fixed mapping.",
            }
        ),
        encoding="utf-8",
    )

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/oracle.json\n",
        commit_messages=(
            "feat: mention trailer without trailer block\n"
            "Some prose\n"
            "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        ),
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/oracle.json` sets "
        "coauthor_required=true, but branch commits do not include the canonical "
        "Experiment Runner co-author trailer. Reason: Runner oracle shaped the fixed mapping."
    ]


def test_experiment_runner_coauthor_advisory_accepts_trailer_after_divider_text(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "oracle.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "Runner oracle shaped the fixed mapping.",
            }
        ),
        encoding="utf-8",
    )

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/oracle.json\n",
        commit_messages=(
            "feat: governed contribution\n\n"
            "Body mentions a divider-like line.\n"
            "---\n\n"
            "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        ),
        repo_root=tmp_path,
    )

    assert warnings == []


def test_experiment_runner_coauthor_advisory_ignores_not_applicable() -> None:
    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Not applicable: docs-only operator exception with no runner signal.\n",
        commit_messages=None,
    )

    assert warnings == []


def test_experiment_runner_coauthor_advisory_ignores_artifact_outside_evidence_section() -> None:
    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Summary\n"
        "Artifact: artifacts/orchestration/experiments/results/missing.json\n"
        "\n"
        "## Experiment Runner Evidence\n"
        "Not applicable: docs-only operator exception with no runner signal.\n",
        commit_messages=None,
    )

    assert warnings == []


def test_experiment_runner_coauthor_advisory_warns_on_missing_artifact_without_trailer(
    tmp_path: Path,
) -> None:
    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/missing.json\n",
        commit_messages="feat: human-only commit\n",
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/missing.json` is referenced "
        "but unavailable locally, so coauthor_required cannot be verified against "
        "branch commits."
    ]


def test_experiment_runner_coauthor_advisory_warns_on_missing_artifact_with_trailer(
    tmp_path: Path,
) -> None:
    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/missing.json\n",
        commit_messages=(
            "feat: governed contribution\n\n"
            "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        ),
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/missing.json` is referenced "
        "but unavailable locally, so coauthor_required cannot be verified against "
        "branch commits."
    ]


def test_experiment_runner_coauthor_advisory_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text(
        json.dumps(
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "External artifact must not be trusted.",
            }
        ),
        encoding="utf-8",
    )
    repo_root = tmp_path / "repo"
    artifact = repo_root / "artifacts" / "orchestration" / "experiments" / "results" / "link.json"
    artifact.parent.mkdir(parents=True)
    artifact.symlink_to(outside)

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/link.json\n",
        commit_messages=(
            "feat: governed contribution\n\n"
            "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        ),
        repo_root=repo_root,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/link.json` is referenced "
        "but unavailable locally, so coauthor_required cannot be verified against "
        "branch commits."
    ]


def test_experiment_runner_coauthor_advisory_handles_symlink_loop(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    result_dir = repo_root / "artifacts" / "orchestration" / "experiments" / "results"
    result_dir.mkdir(parents=True)
    (result_dir / "loop-a.json").symlink_to("loop-b.json")
    (result_dir / "loop-b.json").symlink_to("loop-a.json")

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/loop-a.json\n",
        commit_messages="feat: human-only commit\n",
        repo_root=repo_root,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/loop-a.json` is referenced "
        "but unavailable locally, so coauthor_required cannot be verified against "
        "branch commits."
    ]


def test_experiment_runner_coauthor_advisory_warns_on_malformed_coauthor_metadata(
    tmp_path: Path,
) -> None:
    artifact = (
        tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "malformed.json"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "contribution_kind": "oracle_review",
                "coauthor_required": "true",
                "coauthor_reason": "Runner oracle shaped the fixed mapping.",
            }
        ),
        encoding="utf-8",
    )

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/malformed.json\n",
        commit_messages=(
            "feat: governed contribution\n\n"
            "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        ),
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/malformed.json` has invalid "
        "co-author metadata, so coauthor_required cannot be verified against branch commits."
    ]


def test_experiment_runner_coauthor_advisory_warns_on_non_object_artifact(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "array.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps([]), encoding="utf-8")

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/array.json\n",
        commit_messages="feat: human-only commit\n",
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/array.json` has invalid "
        "co-author metadata, so coauthor_required cannot be verified against branch commits."
    ]


def test_git_commit_messages_falls_back_when_primary_range_is_unavailable() -> None:
    messages = gates._git_commit_messages(
        "refs/heads/definitely-missing..HEAD",
        fallback_range="HEAD",
    )

    assert isinstance(messages, str)
    assert messages.strip()


def test_git_commit_messages_does_not_fallback_by_default() -> None:
    assert gates._git_commit_messages("refs/heads/definitely-missing..HEAD") is None


def test_git_commit_messages_passes_end_of_options_separator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    class _Completed:
        returncode = 0
        stdout = "ok"

    def _fake_run(argv, **_kwargs):
        captured.extend(argv)
        return _Completed()

    monkeypatch.setattr(gates.shutil, "which", lambda _binary: "/usr/bin/git")
    monkeypatch.setattr(gates.subprocess, "run", _fake_run)

    assert gates._git_commit_messages("HEAD") == "ok"
    assert captured[-3:] == ["--end-of-options", "HEAD", "--"]


def test_commit_range_arg_accepts_valid_input() -> None:
    assert (
        gates._validate_git_commit_range_arg("HEAD~5..HEAD", arg_name="--commit-range")
        == "HEAD~5..HEAD"
    )


def test_commit_range_arg_rejects_git_option_like_input() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        gates._validate_git_commit_range_arg("--output=/tmp/pwned", arg_name="--commit-range")


@pytest.mark.parametrize("arg_name", ["--commit-range", "--commit-range-fallback"])
def test_commit_range_arg_rejects_git_option_like_input_through_argparse(
    arg_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_pr_body_phase2_gates.py",
            f"{arg_name}=--output=/tmp/pwned",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        gates.main()

    assert exc_info.value.code == 2
    assert "cannot start with '-'" in capsys.readouterr().err


def test_git_commit_messages_returns_none_when_git_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gates.shutil, "which", lambda _binary: None)

    assert gates._git_commit_messages() is None


def test_experiment_runner_coauthor_advisory_warns_when_commit_messages_unverifiable(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifacts" / "orchestration" / "experiments" / "results" / "oracle.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "contribution_kind": "oracle_review",
                "coauthor_required": True,
                "coauthor_reason": "Runner oracle shaped the fixed mapping.",
            }
        ),
        encoding="utf-8",
    )

    warnings = gates.check_experiment_runner_coauthor_advisory(
        "## Experiment Runner Evidence\n"
        "Artifact: artifacts/orchestration/experiments/results/oracle.json\n",
        commit_messages=None,
        repo_root=tmp_path,
    )

    assert warnings == [
        "Advisory: branch commit messages could not be inspected locally, "
        "so the Experiment Runner co-author trailer was not verified for "
        "`artifacts/orchestration/experiments/results/oracle.json`. "
        "Reason: Runner oracle shaped the fixed mapping."
    ]


def test_phase2_guard_rejects_missing_sections() -> None:
    body = "## Summary\nOnly summary.\n"
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert any("Discussion Thread Pass" in error for error in errors)
    assert any("Fixed in Commit Mapping" in error for error in errors)


def test_phase2_guard_rejects_unchecked_checkboxes() -> None:
    body = VALID_BODY_WITH_MAPPING.replace("[x]", "[ ]")
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert any("Discussion-thread pass completed" in error for error in errors)
    assert any("Fixed in commit mapping completed" in error for error in errors)


def test_phase2_guard_rejects_missing_mapping_details() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert any("Add at least one review-thread entry" in error for error in errors)


def test_phase2_guard_rejects_mixed_mapping_and_na_marker() -> None:
    """Mixed mode (mapping + No actionable) is invalid; align with artifact contract."""
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4\n"
        "- No actionable review comments",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert any("mixed mode" in e.lower() or "cannot appear together" in e.lower() for e in errors)


def test_phase2_guard_rejects_malformed_mapping_line() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- https://github.com/org/repo/pull/719#issuecomment-123 28069fd4",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert any("Add at least one review-thread entry" in error for error in errors)


def test_phase2_guard_requires_mapping_in_section_not_elsewhere() -> None:
    """Mapping entry in Summary does not satisfy the gate; only content under ### Fixed in Commit Mapping counts."""
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "",
    )
    body = body.replace(
        "Phase2 PR body gate implementation.\n\n",
        "Phase2 PR body gate implementation.\n- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4\n\n",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert any("Add at least one review-thread entry" in error for error in errors)


def test_phase2_guard_rejects_duplicate_required_sections() -> None:
    body = """## Summary
Example.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- malformed mapping row

## Deferred / Follow-ups
- None.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
### Fixed in Commit Mapping
- No actionable review comments
"""
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert "Duplicate required section: `## Discussion Thread Pass`." in errors
    assert "Duplicate required section: `### Fixed in Commit Mapping`." in errors
    assert "Duplicate checklist item: `Discussion-thread pass completed`." in errors
    assert "Duplicate checklist item: `Fixed in commit mapping completed`." in errors


def test_phase2_guard_ignores_fake_content_in_code_block() -> None:
    body = """## Summary
Example.

```md
## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
### Fixed in Commit Mapping
- https://github.com/org/repo/pull/1#issuecomment-2 -> deadbee
```
"""
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert any("Missing required section" in error for error in errors)


def test_extract_pr_body_from_event_payload(tmp_path: Path) -> None:
    event_payload = {
        "pull_request": {
            "body": VALID_BODY_WITH_MAPPING,
        }
    }
    payload_path = tmp_path / "event.json"
    payload_path.write_text(json.dumps(event_payload), encoding="utf-8")

    assert gates._extract_pr_body(payload_path) == VALID_BODY_WITH_MAPPING


def test_extract_pr_body_returns_empty_on_missing_file() -> None:
    result = gates._extract_pr_body(Path("/nonexistent/event.json"))
    assert result == ""


def test_extract_pr_body_returns_empty_on_invalid_json(tmp_path: Path) -> None:
    payload_path = tmp_path / "event.json"
    payload_path.write_text("not valid json", encoding="utf-8")
    result = gates._extract_pr_body(payload_path)
    assert result == ""


def test_extract_pr_body_returns_empty_for_non_object_payload(tmp_path: Path) -> None:
    payload_path = tmp_path / "event.json"
    payload_path.write_text("[]", encoding="utf-8")
    assert gates._extract_pr_body(payload_path) == ""
    assert gates._extract_pr_number(payload_path) is None


def test_extract_pr_body_returns_empty_for_non_object_pull_request(tmp_path: Path) -> None:
    payload_path = tmp_path / "event.json"
    payload_path.write_text(json.dumps({"pull_request": []}), encoding="utf-8")
    assert gates._extract_pr_body(payload_path) == ""
    assert gates._extract_pr_number(payload_path) is None


def test_phase2_uses_artifact_when_pr_number_in_event(tmp_path: Path) -> None:
    """When event has pr_number, Phase2 validates canonical artifact evidence."""
    mirror_body = """## Summary
Artifact-first validation fixture.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- canonical artifact: `docs/review/PR_998_FIXED_MAPPING.md`
"""
    event = {"pull_request": {"number": 998, "body": mirror_body}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: canonical artifact evidence controls artifact-first mode.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
                "--experiment-runner-evidence-mode",
                "required",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)
    assert result.returncode == 0
    assert "canonical mapping artifact and PR body mirror passed" in result.stdout
    assert "WARNING:" not in result.stdout


def test_phase2_body_can_satisfy_evidence_when_mapping_lacks_it(tmp_path: Path) -> None:
    """Experiment Runner Evidence may live in body or mapping artifact."""
    event = {
        "pull_request": {
            "number": 998,
            "body": """## Summary
Body-owned runner evidence.

## Experiment Runner Evidence
Not applicable: trivial docs cleanup without runner output.
""",
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_pr_body_phase2_gates.py",
            "--event-path",
            str(tmp_path / "event.json"),
            "--experiment-runner-evidence-mode",
            "required",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert result.returncode == 0
    assert "missing `## Experiment Runner Evidence`" not in result.stdout


def test_phase2_body_can_satisfy_lane_provenance_when_mapping_lacks_it(
    tmp_path: Path,
) -> None:
    """Lane Start Provenance may live in body or mapping artifact."""
    event = {
        "pull_request": {
            "number": 998,
            "body": f"""## Summary
Body-owned lane provenance.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
""",
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture keeps runner evidence out of this split-source check.
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)

    assert result.returncode == 0
    assert "missing `## Lane Start Provenance`" not in result.stdout


def test_phase2_body_does_not_hide_unverified_mapping_packet_warning(
    tmp_path: Path,
) -> None:
    """Body provenance should only satisfy missing sections, not hide artifact warnings."""
    event = {
        "pull_request": {
            "number": 998,
            "body": """## Summary
Body-owned valid lane provenance.

## Lane Start Provenance
Exception: trivial docs cleanup: body mirror fixture.
""",
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture only checks lane-start warning visibility.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_pr_body_phase2_gates.py",
            "--event-path",
            str(tmp_path / "event.json"),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert result.returncode == 0
    assert "not available locally" in result.stdout
    assert "missing `## Lane Start Provenance`" not in result.stdout


def test_phase2_unverified_body_packet_satisfies_missing_mapping_lane_section(
    tmp_path: Path,
) -> None:
    """A valid packet reference still counts as present when only availability is advisory."""
    event = {
        "pull_request": {
            "number": 998,
            "body": f"""## Summary
Body-owned lane provenance.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
""",
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture only checks missing-section suppression.
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_pr_body_phase2_gates.py",
            "--event-path",
            str(tmp_path / "event.json"),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert result.returncode == 0
    assert "not available locally" in result.stdout
    assert "missing `## Lane Start Provenance`" not in result.stdout


def test_phase2_rejects_malformed_mapping_lane_even_when_body_is_valid(
    tmp_path: Path,
) -> None:
    """Malformed present mapping provenance remains an error in split-source mode."""
    event = {
        "pull_request": {
            "number": 998,
            "body": f"""## Summary
Body-owned valid lane provenance.

## Experiment Runner Evidence
Not applicable: split-source negative fixture with no runner output.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
""",
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Lane Start Provenance
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    result = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_pr_body_phase2_gates.py",
            "--event-path",
            str(tmp_path / "event.json"),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )

    assert result.returncode == 1
    assert "starter is supplemental" in result.stdout


def test_phase2_accepts_empty_pr_body_when_artifact_is_valid(tmp_path: Path) -> None:
    """Artifact-first mode does not fail solely because the body mirror is omitted."""
    event = {"pull_request": {"number": 998, "body": ""}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: empty body fixture uses artifact-first validation only.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)
    assert result.returncode == 0
    assert "canonical mapping artifact passed" in result.stdout


def test_phase2_accepts_non_mirror_body_when_artifact_is_valid(tmp_path: Path) -> None:
    """Artifact-first mode should not force optional PR body mirrors."""
    event = {"pull_request": {"number": 998, "body": "minimal"}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture artifact only checks body mirror failure behavior.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)
    assert result.returncode == 0
    assert "canonical mapping artifact passed" in result.stdout


@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        (
            "<!--   phase2-pre-closeout: final-security-pending   -->\r",
            "Pre-closeout marker must be removed",
        ),
        (
            "<!-- phase2-pre-closeout:\tfinal-security-pending -->",
            "Pre-closeout marker must be removed",
        ),
        (
            "-  Pending final clean scan and the single mapping/closeout commit. \t\r",
            "Pre-closeout pending status must be removed",
        ),
        (
            "- Pending\tfinal  clean scan and the single mapping/closeout commit.",
            "Pre-closeout pending status must be removed",
        ),
    ],
)
def test_phase2_rejects_stale_pre_closeout_state_without_mirror(
    tmp_path: Path,
    body: str,
    expected_error: str,
) -> None:
    event = {
        "pull_request": {
            "number": 998,
            "body": body,
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture artifact only checks stale pre-closeout state behavior.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)

    assert result.returncode == 1
    assert expected_error in result.stdout


def test_phase2_rejects_invalid_present_body_mirror_when_artifact_is_valid(
    tmp_path: Path,
) -> None:
    event = {
        "pull_request": {
            "number": 998,
            "body": "## Discussion Thread Pass\n- [ ] Discussion-thread pass completed\n",
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture artifact only checks body mirror failure behavior.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)
    assert result.returncode == 1
    assert "PR body validation failed" in result.stdout
    assert "canonical mapping artifact validation failed" not in result.stdout
    assert "Checklist item must be checked" in result.stdout


def test_phase2_accepts_pr_number_without_explicit_body_when_artifact_is_valid(
    tmp_path: Path,
) -> None:
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-998.json

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--pr-number",
                "998",
                "--commit-range",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)
    assert result.returncode == 0
    assert "canonical mapping artifact passed" in result.stdout


def test_phase2_failure_output_only_reports_failing_scope(tmp_path: Path) -> None:
    """Failure summary should mention only the scope that actually failed."""
    event = {
        "pull_request": {
            "number": 998,
            "body": "### Fixed in Commit Mapping\n- canonical artifact: docs/review/PR_998_FIXED_MAPPING.md\n",
        }
    }
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = f"""# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture artifact only checks body mirror failure behavior.

## Lane Start Provenance
Packet: {LANE_START_PACKET_PATH}
Starter: scripts/orchestration/start_pr_lane.sh
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    _write_lane_start_packet(repo_root)
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ci/check_pr_body_phase2_gates.py",
                "--event-path",
                str(tmp_path / "event.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=env,
        )
    finally:
        _cleanup_lane_start_packet(repo_root)
    assert result.returncode == 1
    assert "PR body validation failed" in result.stdout
    assert "canonical mapping artifact validation failed" not in result.stdout


def test_required_mode_promotes_unavailable_experiment_artifact_to_error() -> None:
    warning = (
        "Advisory: Experiment Runner artifact "
        "`artifacts/orchestration/experiments/results/missing.json` is referenced "
        "but unavailable locally, so coauthor_required cannot be verified against "
        "branch commits."
    )

    promoted = gates._required_experiment_runner_artifact_warning_to_error(warning)

    assert promoted is not None
    assert promoted.startswith("Required: Experiment Runner artifact")


def test_required_mode_does_not_promote_unrelated_advisory() -> None:
    warning = "Advisory: unrelated governance note should remain advisory."

    promoted = gates._required_experiment_runner_artifact_warning_to_error(warning)

    assert promoted is None


def test_phase2_cli_required_mode_fails_unavailable_experiment_runner_artifact() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "artifacts/orchestration/experiments/results/exp-719.json",
        "artifacts/orchestration/experiments/results/does-not-exist.json",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path(gates.__file__)),
            "--body",
            body,
            "--experiment-runner-evidence-mode",
            "required",
            "--commit-range",
            "HEAD..HEAD",
        ],
        cwd=gates.REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 1
    assert "unavailable locally" in result.stdout


def test_phase2_cli_advisory_mode_allows_unavailable_experiment_runner_artifact() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "artifacts/orchestration/experiments/results/exp-719.json",
        "artifacts/orchestration/experiments/results/does-not-exist.json",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path(gates.__file__)),
            "--body",
            body,
            "--experiment-runner-evidence-mode",
            "advisory",
            "--commit-range",
            "HEAD..HEAD",
        ],
        cwd=gates.REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0
    assert "WARNING:" in result.stdout
    assert "unavailable locally" in result.stdout


def test_phase2_cli_default_mode_allows_unavailable_experiment_runner_artifact() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "artifacts/orchestration/experiments/results/exp-719.json",
        "artifacts/orchestration/experiments/results/does-not-exist.json",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path(gates.__file__)),
            "--body",
            body,
            "--commit-range",
            "HEAD..HEAD",
        ],
        cwd=gates.REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0
    assert "WARNING:" in result.stdout
    assert "unavailable locally" in result.stdout
