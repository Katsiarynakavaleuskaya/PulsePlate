"""Deterministic tests for canonical review mapping artifact module."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.orchestration import review_mapping_artifact as artifact


def test_mapping_artifact_path() -> None:
    p998 = artifact.mapping_artifact_path(998)
    assert p998.name == "PR_998_FIXED_MAPPING.md"
    assert "docs" in str(p998) and "review" in str(p998)


def test_read_mapping_artifact_existing() -> None:
    """Read real artifact docs/review/PR_998_FIXED_MAPPING.md."""
    text = artifact.read_mapping_artifact(998)
    assert "## Discussion Thread Pass" in text
    assert "## Fixed in Commit Mapping" in text
    assert "No actionable review comments" in text


def test_read_mapping_artifact_missing() -> None:
    with pytest.raises(FileNotFoundError, match="Missing canonical review mapping artifact"):
        artifact.read_mapping_artifact(99999)


def test_extract_fixed_mapping_section() -> None:
    text = """# PR 1

## Discussion Thread Pass
- [x] done

## Fixed in Commit Mapping
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
"""
    section = artifact.extract_fixed_mapping_section(text)
    assert "https://github.com/org/repo/pull/1#discussion_r1" in section
    assert "abc1234" in section


def test_extract_fixed_mapping_section_no_actionable() -> None:
    text = """## Fixed in Commit Mapping
- No actionable review comments
"""
    section = artifact.extract_fixed_mapping_section(text)
    assert "No actionable review comments" in section


def test_parse_fixed_mapping_entries() -> None:
    section = """- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
- https://github.com/org/repo/pull/1#issuecomment-2 -> deadbeef
"""
    entries = artifact.parse_fixed_mapping_entries(section)
    assert entries["https://github.com/org/repo/pull/1#discussion_r1"] == "abc1234"
    assert entries["https://github.com/org/repo/pull/1#issuecomment-2"] == "deadbeef"


def test_parse_fixed_mapping_entries_no_actionable() -> None:
    section = "- No actionable review comments"
    entries = artifact.parse_fixed_mapping_entries(section)
    assert entries == {}


def test_has_no_actionable_marker() -> None:
    assert artifact.has_no_actionable_marker("- No actionable review comments") is True
    assert artifact.has_no_actionable_marker("- https://x -> abc1234") is False


def test_validate_mapping_artifact_text_valid() -> None:
    text = """## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments
"""
    errors = artifact.validate_mapping_artifact_text(text)
    assert errors == []


def test_validate_mapping_artifact_text_missing_checkbox() -> None:
    text = """## Discussion Thread Pass
- [ ] Discussion-thread pass completed

## Fixed in Commit Mapping
- No actionable review comments
"""
    errors = artifact.validate_mapping_artifact_text(text)
    assert any("Discussion-thread pass completed" in e for e in errors)


def test_validate_fixed_mapping_section_invalid_line() -> None:
    section = "- invalid mapping line"
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Invalid mapping line" in e for e in errors)
