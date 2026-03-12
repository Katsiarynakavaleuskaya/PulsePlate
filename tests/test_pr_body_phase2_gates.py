"""Deterministic tests for Phase2 PR body gates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import scripts.ci.check_pr_body_phase2_gates as gates

VALID_BODY_WITH_MAPPING = """## Summary
Phase2 PR body gate implementation.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4
"""

VALID_BODY_MIRROR_ONLY = """## Summary
Phase2 PR body gate implementation.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- canonical artifact: `docs/review/PR_998_FIXED_MAPPING.md`
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
    """When event has pr_number, Phase2 validates the artifact and body mirror."""
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


def test_phase2_rejects_invalid_pr_body_even_when_artifact_is_valid(tmp_path: Path) -> None:
    """Artifact success must not bypass required body mirror sections."""
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
    assert "Missing required section" in result.stdout


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
