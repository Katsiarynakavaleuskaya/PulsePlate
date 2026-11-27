"""Deterministic tests for canonical review mapping artifact module."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.orchestration import review_mapping_artifact as artifact

FIXTURE_ARTIFACT = """# PR 998 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234
"""


def test_mapping_artifact_path() -> None:
    p998 = artifact.mapping_artifact_path(998)
    assert p998.name == "PR_998_FIXED_MAPPING.md"
    assert "docs" in str(p998) and "review" in str(p998)


def test_render_phase2_body_mirror_is_stable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(FIXTURE_ARTIFACT, encoding="utf-8")
    monkeypatch.setattr(artifact, "_review_dir", lambda: tmp_path)
    body = artifact.render_phase2_body_mirror(
        998, repository="org/repo", ref="codex/review-closeout"
    )
    assert body == (
        "## Discussion Thread Pass\n"
        "- [x] Discussion-thread pass completed\n"
        "- [x] Fixed in commit mapping completed\n\n"
        "### Fixed in Commit Mapping\n"
        "- [canonical artifact](https://github.com/org/repo/blob/"
        "codex/review-closeout/docs/review/PR_998_FIXED_MAPPING.md)"
    )
    assert body.count("docs/review/PR_998_FIXED_MAPPING.md") == 1
    assert "`docs/review/PR_998_FIXED_MAPPING.md`" not in body


@pytest.mark.parametrize(
    ("ref", "encoded_ref"),
    [("feature#x", "feature%23x"), ("feature+test", "feature%2Btest")],
)
def test_render_phase2_body_mirror_encodes_valid_git_ref_characters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    ref: str,
    encoded_ref: str,
) -> None:
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(FIXTURE_ARTIFACT, encoding="utf-8")
    monkeypatch.setattr(artifact, "_review_dir", lambda: tmp_path)

    body = artifact.render_phase2_body_mirror(998, repository="org/repo", ref=ref)

    assert f"/blob/{encoded_ref}/docs/review/PR_998_FIXED_MAPPING.md" in body


def test_render_phase2_body_mirror_fails_for_invalid_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(
        "## Discussion Thread Pass\n- [x] Discussion-thread pass completed\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(artifact, "_review_dir", lambda: tmp_path)

    with pytest.raises(RuntimeError, match="Cannot render PR body mirror for PR #998"):
        artifact.render_phase2_body_mirror(998, repository="org/repo", ref="main")


@pytest.mark.parametrize(
    ("repository", "ref"),
    [
        ("foreign", "main"),
        ("org/repo", ""),
        ("org/repo", "../main"),
        ("org/repo", "bad?ref"),
    ],
)
def test_render_phase2_body_mirror_rejects_unsafe_link_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    repository: str,
    ref: str,
) -> None:
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(FIXTURE_ARTIFACT, encoding="utf-8")
    monkeypatch.setattr(artifact, "_review_dir", lambda: tmp_path)

    with pytest.raises(ValueError):
        artifact.render_phase2_body_mirror(998, repository=repository, ref=ref)


def test_read_mapping_artifact_existing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Read artifact from temp dir to avoid coupling to real repo file."""
    (tmp_path / "PR_998_FIXED_MAPPING.md").write_text(FIXTURE_ARTIFACT, encoding="utf-8")
    monkeypatch.setattr(artifact, "_review_dir", lambda: tmp_path)
    text = artifact.read_mapping_artifact(998)
    assert "## Discussion Thread Pass" in text
    assert "## Fixed in Commit Mapping" in text
    assert "->" in text


def test_mapping_artifact_path_invalid_override_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Non-existent override dir should fail with a clear RuntimeError."""
    bad_dir = tmp_path / "nonexistent_dir"
    monkeypatch.setenv("REVIEW_MAPPING_ARTIFACT_DIR", str(bad_dir))

    with pytest.raises(RuntimeError, match="REVIEW_MAPPING_ARTIFACT_DIR"):
        artifact.mapping_artifact_path(998)


def test_read_mapping_artifact_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure FileNotFoundError when artifact absent; isolate from REVIEW_MAPPING_ARTIFACT_DIR."""
    monkeypatch.delenv("REVIEW_MAPPING_ARTIFACT_DIR", raising=False)
    monkeypatch.setattr(artifact, "_review_dir", lambda: tmp_path)
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


def test_extract_fixed_mapping_section_accepts_triple_hash() -> None:
    """PR-body fallback uses ### Fixed in Commit Mapping."""
    text = """## Discussion Thread Pass
- [x] done

### Fixed in Commit Mapping
- https://github.com/org/repo/pull/1#d1 -> abc1234
"""
    section = artifact.extract_fixed_mapping_section(text)
    assert "abc1234" in section


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


def test_parse_fixed_mapping_entries_accepts_url_only_not_a_bug_entry() -> None:
    section = """- https://github.com/org/repo/pull/1#discussion_r1
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
Reason: Existing behavior already matches the contract.
"""
    entries = artifact.parse_fixed_mapping_entries(section)
    assert entries["https://github.com/org/repo/pull/1#discussion_r1"] == ""


def test_has_no_actionable_marker() -> None:
    assert artifact.has_no_actionable_marker("- No actionable review comments") is True
    assert artifact.has_no_actionable_marker("- https://x -> abc1234") is False


def test_validate_mapping_artifact_text_valid() -> None:
    text = """## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234
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


def test_validate_fixed_mapping_section_empty() -> None:
    errors = artifact.validate_fixed_mapping_section("")
    assert any("Missing" in error for error in errors)


def test_validate_fixed_mapping_section_mixed_mode() -> None:
    section = """- No actionable review comments
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("mixed mode" in error.lower() for error in errors)


def test_validate_fixed_mapping_section_requires_mapping_or_no_actionable() -> None:
    """Section with only Disposition/Commit lines must have at least one mapping."""
    section = """Disposition: FIXED
Commit: abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("at least one" in e for e in errors)


def test_validate_fixed_mapping_section_accepts_not_a_bug_reason_line() -> None:
    section = """Disposition: NOT-A-BUG
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
Reason: Existing behavior already matches the contract.
- https://github.com/org/repo/pull/1000#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_rejects_not_a_bug_without_reason() -> None:
    section = """Disposition: NOT-A-BUG
Evidence: Existing artifact has evidence-only proof for non-actionable bot output.
- https://github.com/org/repo/pull/1000#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("NOT-A-BUG requires a 'Reason:'" in error for error in errors)


def test_validate_fixed_mapping_section_accepts_deferred_backlog_line() -> None:
    section = """Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#review-thread-follow-up
- https://github.com/org/repo/pull/1000#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_accepts_multiple_disposition_blocks() -> None:
    section = """Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234

Disposition: NOT-A-BUG
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
Reason: Existing behavior already matches the contract.
- https://github.com/org/repo/pull/1000#discussion_r2
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_accepts_mapping_first_legacy_order() -> None:
    section = """- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py

- https://github.com/org/repo/pull/1000#discussion_r2 -> abc1234
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_accepts_mapping_first_without_blank_lines() -> None:
    section = """- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
- https://github.com/org/repo/pull/1000#discussion_r2 -> abc1234
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_accepts_disposition_first_multi_url_block() -> None:
    section = """Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
- https://github.com/org/repo/pull/1000#discussion_r2 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_accepts_explicit_mapping_entries_preamble() -> None:
    section = """Disposition: FIXED
Commit: see mapping entries below
Evidence: See mapping entries below.

- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
- https://github.com/org/repo/pull/1000#discussion_r2 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


@pytest.mark.parametrize(
    "disposition",
    ["Disposition: FIXED-BYPASS", "Disposition: FIXED later", "Disposition: fixed"],
)
def test_validate_fixed_mapping_section_rejects_nonexact_fixed_preamble(
    disposition: str,
) -> None:
    section = f"""{disposition}
Commit: see mapping entries below
Evidence: See mapping entries below.

- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
"""
    assert artifact.validate_fixed_mapping_section(section)


def test_validate_fixed_mapping_section_accepts_placeholder_preamble_with_thread_lines() -> None:
    section = """Disposition: FIXED
Commit: see mapping entries below
Evidence: See mapping entries below.
- https://github.com/org/repo/pull/1000#discussion_r1

- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_rejects_placeholder_with_same_block_mappings() -> None:
    section = """Disposition: FIXED
Commit: see mapping entries below
Evidence: See mapping entries below.
- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("following SHA mapping-only block" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_mixed_placeholder_following_block() -> None:
    section = """Disposition: FIXED
Commit: see mapping entries below
Evidence: See mapping entries below.
- https://github.com/org/repo/pull/1000#discussion_r1

- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
- https://github.com/org/repo/pull/1000#discussion_r2
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("following SHA mapping-only block" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_placeholder_trailing_period() -> None:
    section = """Disposition: FIXED
Commit: see mapping entries below.
Evidence: See mapping entries below.
- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Commit proof must be a commit SHA" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_fixed_sha_mapping_without_commit() -> None:
    section = """- https://github.com/org/repo/pull/1000#issuecomment-1 -> abc1234
Disposition: FIXED
Evidence: tests/test_review_mapping_artifact.py
Reason: Older artifacts used the mapping SHA as the commit proof.
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Disposition FIXED requires a 'Commit:'" in error for error in errors)


def test_validate_fixed_mapping_section_requires_disposition_for_sha_mappings() -> None:
    section = """Commit: abc1234
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert "Missing 'Disposition:' when review-thread entries are present." in errors


def test_validate_fixed_mapping_section_requires_proof_for_sha_mappings() -> None:
    section = """Disposition: FIXED
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Missing proof detail" in error for error in errors)


def test_validate_fixed_mapping_section_requires_proof_for_url_only_entries() -> None:
    section = """Disposition: NOT-A-BUG
- https://github.com/org/repo/pull/1#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Missing proof detail" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_unknown_disposition() -> None:
    section = """Disposition: HANDLED
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
- https://github.com/org/repo/pull/1#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Invalid Disposition value" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_fixed_url_only() -> None:
    section = """Disposition: FIXED
Commit: abc1234
- https://github.com/org/repo/pull/1#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Disposition FIXED requires" in error for error in errors)


def test_validate_fixed_mapping_section_accepts_mapping_first_with_blank_proof_block() -> None:
    section = """- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234

Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert errors == []


def test_validate_fixed_mapping_section_rejects_orphan_disposition_before_mapping() -> None:
    section = """Disposition: FIXED
Commit: abc1234

- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("proof block must contain at least one" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_conflicting_fixed_commit_sha() -> None:
    section = """Disposition: FIXED
Commit: abc1234
Evidence: tests/test_review_mapping_artifact.py
- https://github.com/org/repo/pull/1000#discussion_r1 -> deadbee
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Commit SHA must match mapped SHA entries" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_invalid_fixed_commit_value() -> None:
    section = """Disposition: FIXED
Commit: not-a-sha
Evidence: tests/test_review_mapping_artifact.py
- https://github.com/org/repo/pull/1000#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("Commit proof must be a commit SHA" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_empty_proof_detail_values() -> None:
    section = """Disposition: NOT-A-BUG
Evidence:
Reason:
- https://github.com/org/repo/pull/1000#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert "Evidence: proof value must not be empty." in errors
    assert "Reason: proof value must not be empty." in errors


def test_validate_fixed_mapping_section_rejects_not_a_bug_sha_mapping() -> None:
    section = """Disposition: NOT-A-BUG
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
Reason: Existing behavior already matches the contract.
- https://github.com/org/repo/pull/1#discussion_r1 -> abc1234
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("NOT-A-BUG must use URL-only" in error for error in errors)


def test_validate_fixed_mapping_section_rejects_deferred_without_backlog() -> None:
    section = """Disposition: DEFERRED
Evidence: docs/review/PR_1000_FIXED_MAPPING.md:1
- https://github.com/org/repo/pull/1#discussion_r1
"""
    errors = artifact.validate_fixed_mapping_section(section)
    assert any("DEFERRED requires a 'Backlog:'" in error for error in errors)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("## Other\nplain text", "Missing '## Fixed in Commit Mapping' section."),
        (
            "## Fixed in Commit Mapping\n\n## Other",
            "'## Fixed in Commit Mapping' section is empty.",
        ),
        ("### Fixed in Commit Mapping\n \t", "'## Fixed in Commit Mapping' section is empty."),
        (
            "## Fixed in Commit Mapping\n## Fixed in Commit Mapping\nproof",
            "Expected exactly one Fixed in Commit Mapping section; found 2.",
        ),
        (
            "## Fixed in Commit Mapping\n\n## Other\n### Fixed in Commit Mapping\nproof",
            "Expected exactly one Fixed in Commit Mapping section; found 2.",
        ),
        (
            "### Fixed in Commit Mapping\nproof\n## Other\n## Fixed in Commit Mapping",
            "Expected exactly one Fixed in Commit Mapping section; found 2.",
        ),
        (
            "## Fixed in Commit Mapping\nproof\n### Fixed in Commit Mapping\nproof",
            "Expected exactly one Fixed in Commit Mapping section; found 2.",
        ),
        (
            "## Fixed in Commit Mapping\nproof\n```\n## Fixed in Commit Mapping\n```",
            "Expected exactly one Fixed in Commit Mapping section; found 2.",
        ),
        (
            "##  Fixed\t in Commit Mapping\nproof\n## Other\n### Fixed in Commit Mapping\nproof",
            "Expected exactly one Fixed in Commit Mapping section; found 2.",
        ),
        (
            "##\u00a0Fixed in Commit Mapping\nproof\n## Other\n### Fixed in Commit Mapping\nproof",
            "Expected exactly one Fixed in Commit Mapping section; found 2.",
        ),
    ],
    ids=[
        "missing",
        "empty-double",
        "empty-triple",
        "adjacent",
        "empty-first-mixed",
        "empty-last-mixed",
        "nested",
        "lexical-fence",
        "normalized-duplicate",
        "unicode-duplicate",
    ],
)
def test_complete_consumers_reject_ambiguous_fixed_spans(body: str, message: str) -> None:
    """Reject structural ambiguity consistently before any complete consumer selects content."""
    for extract in (
        artifact.extract_fixed_mapping_section,
        lambda text: artifact.extract_section(text, "## Fixed in Commit Mapping"),
        lambda text: artifact.extract_section(text, "### Fixed in Commit Mapping"),
        lambda text: artifact.parse_canonical_fingerprint_records(text, pr_number=998),
    ):
        with pytest.raises(artifact.ReviewEvidenceError) as rejected:
            extract(body)
        assert str(rejected.value) == message
    assert artifact.validate_mapping_artifact_text(body) == [message]


@pytest.mark.parametrize(
    "reserved",
    [
        "- https://github.com/org/repo/pull/998#discussion_r1 -> abc1234",
        "- https://github.com/org/repo/pull/998#discussion_r1",
        "Disposition: FIXED",
        "Commit: abc1234",
        "Evidence: file.py:1",
        "Backlog: docs/roadmap/BACKLOG_LEDGER.md#item",
        "Reason: retained proof",
        "Fingerprint:",
        "Cause:",
        "Material-Digest:",
        "Verified-Fix:",
        "- No actionable review comments",
        "  Evidence: indented.py:1",
    ],
)
@pytest.mark.parametrize("placement", ["before", "after", "lexical-fence"])
def test_complete_consumers_reject_reserved_lines_outside_fixed_span(
    reserved: str, placement: str
) -> None:
    """Retain known proof markers anywhere outside the sole span, including partial fields."""
    valid = "## Fixed in Commit Mapping\n- No actionable review comments\n"
    if placement == "before":
        text = f"{reserved}\n{valid}"
        line = 1
    else:
        text = valid + "## Retained context\n"
        if placement == "lexical-fence":
            text += "```\n"
        line = len(text.splitlines()) + 1
        text += reserved + "\n"
        if placement == "lexical-fence":
            text += "```\n"
    message = (
        "Recognized proof or No-actionables marker outside Fixed in Commit Mapping "
        f"section at line {line}."
    )
    for extract in (
        artifact.extract_fixed_mapping_section,
        lambda value: artifact.extract_section(value, "### Fixed in Commit Mapping"),
        lambda value: artifact.parse_canonical_fingerprint_records(value, pr_number=998),
    ):
        with pytest.raises(artifact.ReviewEvidenceError) as rejected:
            extract(text)
        assert str(rejected.value) == message
    assert artifact.validate_mapping_artifact_text(text) == [message]


@pytest.mark.parametrize(
    "heading",
    [
        "## Fixed in Commit Mapping",
        "### Fixed in Commit Mapping",
        "  ##  Fixed\t in Commit Mapping  ",
        "##\u00a0Fixed in Commit Mapping",
    ],
)
def test_complete_inventory_preserves_singleton_heading_compatibility(heading: str) -> None:
    """Admit supported singleton whitespace forms while leaving benign outer prose alone."""
    text = (
        "## Discussion Thread Pass\n"
        "- [x] Discussion-thread pass completed\n- [x] Fixed in commit mapping completed\n"
        f"{heading}\n- No actionable review comments\n## Context\nPlain retained prose.\n"
    )
    assert artifact.extract_fixed_mapping_section(text) == artifact.NO_ACTIONABLE_LINE
    assert artifact.validate_mapping_artifact_text(text) == []
    assert artifact.parse_canonical_fingerprint_records(text, pr_number=998) == {}


def test_complete_inventory_preserves_valid_fingerprint_record() -> None:
    """Recognize a real canonical fingerprint inside the sole span without changing its meaning."""
    material_digest = "sha256:" + "a" * 64
    fix = "b" * 40
    fingerprint = artifact.unavailable_review_ref_fingerprint(
        pr_number=998, material_digest=material_digest, verified_real_fix_sha=fix
    )
    text = (
        "## Discussion Thread Pass\n"
        "- [x] Discussion-thread pass completed\n- [x] Fixed in commit mapping completed\n"
        "### Fixed in Commit Mapping\nDisposition: NOT-A-BUG\n"
        "Evidence: policy.py:1\nReason: Ref unavailable\n"
        f"Fingerprint: {fingerprint}\nCause: {artifact.UNAVAILABLE_REVIEW_REF_CAUSE}\n"
        f"Material-Digest: {material_digest}\nVerified-Fix: {fix}\n"
        "- https://github.com/org/repo/pull/998#discussion_r1\n"
    )
    records = artifact.parse_canonical_fingerprint_records(text, pr_number=998)
    assert set(records) == {fingerprint}
    assert records[fingerprint].verified_fix == fix
    assert artifact.validate_mapping_artifact_text(text) == []


@pytest.mark.parametrize("placement", ["before", "after"])
def test_complete_inventory_rejects_full_fingerprint_record_outside_span(placement: str) -> None:
    """Retain even a fully valid fingerprint record when its location is outside the sole span."""
    material_digest = "sha256:" + "a" * 64
    fix = "b" * 40
    fingerprint = artifact.unavailable_review_ref_fingerprint(
        pr_number=998, material_digest=material_digest, verified_real_fix_sha=fix
    )
    record = (
        "Disposition: NOT-A-BUG\nEvidence: policy.py:1\nReason: Ref unavailable\n"
        f"Fingerprint: {fingerprint}\nCause: {artifact.UNAVAILABLE_REVIEW_REF_CAUSE}\n"
        f"Material-Digest: {material_digest}\nVerified-Fix: {fix}\n"
        "- https://github.com/org/repo/pull/998#discussion_r1\n"
    )
    discussion = (
        "## Discussion Thread Pass\n- [x] Discussion-thread pass completed\n"
        "- [x] Fixed in commit mapping completed\n"
    )
    valid = discussion + "## Fixed in Commit Mapping\n" + record
    assert artifact.validate_mapping_artifact_text(valid) == []
    assert set(artifact.parse_canonical_fingerprint_records(valid, pr_number=998)) == {fingerprint}
    empty = discussion + "## Fixed in Commit Mapping\n- No actionable review comments\n"
    if placement == "before":
        text = record + empty
        line = 1
    else:
        text = empty + "## Retained proof\n"
        line = len(text.splitlines()) + 1
        text += record
    message = (
        "Recognized proof or No-actionables marker outside Fixed in Commit Mapping "
        f"section at line {line}."
    )
    for extract in (
        artifact.extract_fixed_mapping_section,
        lambda value: artifact.parse_canonical_fingerprint_records(value, pr_number=998),
    ):
        with pytest.raises(artifact.ReviewEvidenceError) as rejected:
            extract(text)
        assert str(rejected.value) == message
    assert artifact.validate_mapping_artifact_text(text) == [message]
