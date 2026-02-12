"""Deterministic tests for Phase2 PR body gates."""

from __future__ import annotations

import json
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


def test_phase2_guard_accepts_valid_mapping() -> None:
    errors = gates.check_pr_body_phase2_gates(body=VALID_BODY_WITH_MAPPING)
    assert errors == []


def test_phase2_guard_accepts_no_actionable_comments_marker() -> None:
    body = VALID_BODY_WITH_MAPPING.replace(
        "- https://github.com/org/repo/pull/719#issuecomment-123 -> 28069fd4",
        "- No actionable review comments",
    )
    errors = gates.check_pr_body_phase2_gates(body=body)
    assert errors == []


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
    assert any("Add at least one mapping entry" in error for error in errors)


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
