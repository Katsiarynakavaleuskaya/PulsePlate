"""Deterministic tests for Phase2 PR body gates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.ci.check_pr_body_phase2_gates as gates

VALID_BODY_WITH_MAPPING = """## Summary
Phase2 PR body gate implementation.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4

## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-719.json
"""

VALID_BODY_MIRROR_ONLY = """## Summary
Phase2 PR body gate implementation.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- canonical artifact: `docs/review/PR_998_FIXED_MAPPING.md`

## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-998.json
"""


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


def test_phase2_guard_uses_last_mapping_section_when_multiple_exist() -> None:
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
    assert errors == []


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
    event = {"pull_request": {"number": 998, "body": VALID_BODY_MIRROR_ONLY}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: canonical artifact evidence controls artifact-first mode.
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
    assert "canonical mapping artifact and PR body mirror passed" in result.stdout
    assert "WARNING:" not in result.stdout


def test_phase2_accepts_empty_pr_body_when_artifact_is_valid(tmp_path: Path) -> None:
    """Artifact-first mode does not fail solely because the body mirror is omitted."""
    event = {"pull_request": {"number": 998, "body": ""}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
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
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert result.returncode == 0
    assert "canonical mapping artifact passed" in result.stdout


def test_phase2_accepts_non_mirror_body_when_artifact_is_valid(tmp_path: Path) -> None:
    """Artifact-first mode should not force optional PR body mirrors."""
    event = {"pull_request": {"number": 998, "body": "minimal"}}
    (tmp_path / "event.json").write_text(json.dumps(event), encoding="utf-8")
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture artifact only checks body mirror failure behavior.
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
    assert "canonical mapping artifact passed" in result.stdout


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
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture artifact only checks body mirror failure behavior.
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
    assert "PR body validation failed" in result.stdout
    assert "Checklist item must be checked" in result.stdout


def test_phase2_accepts_pr_number_without_explicit_body_when_artifact_is_valid(
    tmp_path: Path,
) -> None:
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Artifact: artifacts/orchestration/experiments/results/exp-998.json
"""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(artifact_content, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "REVIEW_MAPPING_ARTIFACT_DIR": str(tmp_path)}
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
    artifact_content = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234

## Experiment Runner Evidence
Not applicable: fixture artifact only checks body mirror failure behavior.
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
    assert "PR body validation failed" in result.stdout
    assert "canonical mapping artifact validation failed" not in result.stdout
