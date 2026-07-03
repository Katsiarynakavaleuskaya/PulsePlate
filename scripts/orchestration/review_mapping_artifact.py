"""Canonical Fixed in Commit Mapping artifact: repo file as source of truth."""

from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "docs" / "review"


def _review_dir() -> Path:
    """Return review dir; override via REVIEW_MAPPING_ARTIFACT_DIR for tests only."""
    override = os.environ.get("REVIEW_MAPPING_ARTIFACT_DIR")
    if not override:
        return REVIEW_DIR
    base = Path(override).resolve()
    if not base.is_dir():
        raise RuntimeError(f"REVIEW_MAPPING_ARTIFACT_DIR must be an existing directory: {base}")
    return base


DISCUSSION_THREAD_PASS_HEADING = "## Discussion Thread Pass"  # nosec B105: doc heading (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
# Canonical artifact uses ##; PR-body mirror/fallback may use ### (AGENTS.md)
FIXED_MAPPING_HEADINGS = ("## Fixed in Commit Mapping", "### Fixed in Commit Mapping")

CHECKBOX_DISCUSSION_PASS = "- [x] Discussion-thread pass completed"  # nosec B105: checkbox label (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
CHECKBOX_FIXED_MAPPING = "- [x] Fixed in commit mapping completed"

MAPPING_LINE_RE = re.compile(r"^\s*-\s+(https://github\.com/\S+)\s+->\s+([0-9a-f]{7,40})\s*$")
THREAD_LINE_RE = re.compile(r"^\s*-\s+(https://github\.com/\S+)\s*$")
NO_ACTIONABLE_LINE = "- No actionable review comments"
# Disposition/proof lines allowed in section (disposition guard format)
DETAIL_PREFIXES = ("Disposition:", "Commit:", "Evidence:", "Backlog:", "Reason:")
VALID_DISPOSITIONS = frozenset({"FIXED", "NOT-A-BUG", "DEFERRED"})
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _validate_fixed_mapping_block(lines: list[str]) -> list[str]:
    """Validate one disposition/proof block inside Fixed in Commit Mapping."""

    errors: list[str] = []
    disposition_values: list[str] = []
    has_sha_mapping = False
    has_url_only_mapping = False
    proof_prefixes: set[str] = set()
    commit_values: list[str] = []
    mapped_shas: list[str] = []

    for line in lines:
        if line.startswith("Disposition:"):
            disposition = line.removeprefix("Disposition:").strip()
            if disposition not in VALID_DISPOSITIONS:
                errors.append(
                    f"Invalid Disposition value: {disposition}. "
                    "Expected FIXED, NOT-A-BUG, or DEFERRED."
                )
            disposition_values.append(disposition)
            continue
        matched_detail = next(
            (prefix for prefix in DETAIL_PREFIXES[1:] if line.startswith(prefix)),
            None,
        )
        if matched_detail is not None:
            proof_value = line.removeprefix(matched_detail).strip()
            if not proof_value:
                errors.append(f"{matched_detail} proof value must not be empty.")
                continue
            proof_prefixes.add(matched_detail)
            if matched_detail == "Commit:":
                commit_values.append(proof_value)
            continue
        if mapping_match := MAPPING_LINE_RE.match(line):
            has_sha_mapping = True
            mapped_shas.append(mapping_match.group(2))
            continue
        if THREAD_LINE_RE.match(line):
            has_url_only_mapping = True
            continue
        errors.append(f"Invalid mapping line format in canonical artifact: {line}")

    saw_thread_line = has_sha_mapping or has_url_only_mapping
    if len(disposition_values) > 1:
        errors.append("Fixed in Commit Mapping proof block must contain one Disposition line.")
    if not errors and not saw_thread_line:
        errors.append(
            "Fixed in Commit Mapping proof block must contain at least one '- <url>' "
            "or '- <url> -> <sha>' line."
        )
    if not errors and saw_thread_line and not disposition_values:
        errors.append("Missing 'Disposition:' when review-thread entries are present.")
    if not errors and saw_thread_line and not proof_prefixes:
        errors.append(
            "Missing proof detail (Commit:/Evidence:/Backlog:) when review-thread entries are present."
        )
    if errors or not disposition_values:
        return errors

    disposition = disposition_values[0]
    if disposition == "FIXED":
        uses_mapping_entries_preamble = any(
            value.strip().lower() == "see mapping entries below" for value in commit_values
        )
        if uses_mapping_entries_preamble and has_sha_mapping:
            errors.append(
                "Disposition FIXED with 'Commit: see mapping entries below' requires "
                "a following SHA mapping-only block."
            )
        if not has_sha_mapping:
            errors.append("Disposition FIXED requires '- <url> -> <sha>' mapping lines.")
        if has_url_only_mapping:
            errors.append("Disposition FIXED must not use URL-only review-thread lines.")
        if "Commit:" not in proof_prefixes:
            errors.append("Disposition FIXED requires a 'Commit:' proof line.")
        if "Evidence:" not in proof_prefixes:
            errors.append("Disposition FIXED requires an 'Evidence:' proof line.")
        invalid_commit_values = [
            value
            for value in commit_values
            if not (
                COMMIT_SHA_RE.fullmatch(value)
                or value.strip().lower() == "see mapping entries below"
            )
        ]
        if invalid_commit_values:
            errors.append(
                "Disposition FIXED Commit proof must be a commit SHA or "
                "'see mapping entries below'."
            )
        commit_shas = {value for value in commit_values if COMMIT_SHA_RE.fullmatch(value)}
        mapped_sha_values = set(mapped_shas)
        if commit_shas and mapped_sha_values - commit_shas:
            errors.append(
                "Disposition FIXED Commit SHA must match mapped SHA entries "
                "or use 'Commit: see mapping entries below'."
            )
    elif disposition == "NOT-A-BUG":
        if has_sha_mapping:
            errors.append("Disposition NOT-A-BUG must use URL-only review-thread lines.")
        if "Evidence:" not in proof_prefixes:
            errors.append("Disposition NOT-A-BUG requires an 'Evidence:' proof line.")
        if "Reason:" not in proof_prefixes:
            errors.append("Disposition NOT-A-BUG requires a 'Reason:' proof line.")
    elif disposition == "DEFERRED":
        if has_sha_mapping:
            errors.append("Disposition DEFERRED must use URL-only review-thread lines.")
        if "Backlog:" not in proof_prefixes:
            errors.append("Disposition DEFERRED requires a 'Backlog:' proof line.")
    return errors


def _block_has_thread_entry(lines: list[str]) -> bool:
    return any(MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line) for line in lines)


def _block_has_sha_mapping(lines: list[str]) -> bool:
    return any(MAPPING_LINE_RE.match(line) for line in lines)


def _block_has_disposition(lines: list[str]) -> bool:
    return any(line.startswith("Disposition:") for line in lines)


def _is_mapping_only_block(lines: list[str]) -> bool:
    if not lines:
        return False
    return all(MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line) for line in lines)


def _is_sha_mapping_only_block(lines: list[str]) -> bool:
    if not lines:
        return False
    return all(MAPPING_LINE_RE.match(line) for line in lines)


def _split_fixed_mapping_blocks(raw_lines: list[str]) -> list[list[str]]:
    """Split physical blocks while preserving legacy mapping-first inline groups."""

    blocks: list[list[str]] = []
    current_block: list[str] = []
    for line in raw_lines:
        if not line:
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue
        is_thread_line = bool(MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line))
        current_has_thread = _block_has_thread_entry(current_block)
        current_has_disposition = _block_has_disposition(current_block)
        if (
            is_thread_line
            and current_has_thread
            and current_has_disposition
            and not (current_block and current_block[0].startswith("Disposition:"))
        ):
            blocks.append(current_block)
            current_block = [line]
            continue
        if line.startswith("Disposition:") and _block_has_disposition(current_block):
            blocks.append(current_block)
            current_block = [line]
            continue
        current_block.append(line)
    if current_block:
        blocks.append(current_block)
    return blocks


def _is_mapping_entries_preamble(lines: list[str]) -> bool:
    """Return True for PR_2068-style proof preambles that name following mappings."""

    return (
        not _block_has_sha_mapping(lines)
        and any(line == "Commit: see mapping entries below" for line in lines)
        and any(line.startswith("Disposition: FIXED") for line in lines)
        and any(line.startswith("Evidence:") for line in lines)
    )


def _validate_mapping_entries_preamble(
    preamble: list[str],
    following: list[str] | None,
) -> list[str]:
    errors: list[str] = []
    for line in preamble:
        if (
            line.startswith("Disposition:")
            or line.startswith("Commit:")
            or line.startswith("Evidence:")
            or THREAD_LINE_RE.match(line)
        ):
            continue
        errors.append(f"Invalid mapping line format in canonical artifact: {line}")
    evidence_values = [
        line.removeprefix("Evidence:").strip() for line in preamble if line.startswith("Evidence:")
    ]
    if not evidence_values or any(not value for value in evidence_values):
        errors.append("Disposition FIXED requires a non-empty 'Evidence:' proof line.")
    if following is None or not _is_sha_mapping_only_block(following):
        errors.append(
            "Disposition FIXED with 'Commit: see mapping entries below' requires "
            "a following SHA mapping-only block."
        )
        return errors
    mapping_entries = {
        match.group(1): match.group(2)
        for line in following
        if (match := MAPPING_LINE_RE.match(line))
    }
    if not mapping_entries:
        errors.append(
            "Disposition FIXED with 'Commit: see mapping entries below' requires "
            "SHA mapping lines in the following block."
        )
    missing_urls = [
        match.group(1)
        for line in preamble
        if (match := THREAD_LINE_RE.match(line)) and match.group(1) not in mapping_entries
    ]
    if missing_urls:
        errors.append(
            "Disposition FIXED with 'Commit: see mapping entries below' is missing "
            f"following SHA mappings for: {', '.join(missing_urls)}."
        )
    return errors


def mapping_artifact_path(pr_number: int) -> Path:
    """Return canonical review mapping artifact path for a PR number."""
    return _review_dir() / f"PR_{pr_number}_FIXED_MAPPING.md"


def read_mapping_artifact(pr_number: int) -> str:
    """Read canonical review mapping artifact text."""
    path = mapping_artifact_path(pr_number)
    if not path.is_file():
        raise FileNotFoundError(f"Missing canonical review mapping artifact: {path}")
    return path.read_text(encoding="utf-8")


def extract_section(markdown_text: str, heading: str) -> str:
    """
    Extract section body for a markdown heading (## or ###).
    Returns content after heading until next heading at same or higher level.
    """
    lines = markdown_text.splitlines()
    inside = False
    collected: list[str] = []
    heading_level = len(heading) - len(heading.lstrip("#"))

    for line in lines:
        # Normalize multiple spaces (markdown allows "##  Title")
        if re.sub(r"\s+", " ", line.strip()) == re.sub(r"\s+", " ", heading):
            inside = True
            continue

        if inside:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                next_level = len(stripped) - len(stripped.lstrip("#"))
                if next_level <= heading_level:
                    break
            collected.append(line)

    return "\n".join(collected).strip()


def extract_discussion_thread_pass_section(markdown_text: str) -> str:
    """Extract ## Discussion Thread Pass section."""
    return extract_section(markdown_text, DISCUSSION_THREAD_PASS_HEADING)


def extract_fixed_mapping_section(markdown_text: str) -> str:
    """Extract Fixed in Commit Mapping section (## or ###)."""
    for heading in FIXED_MAPPING_HEADINGS:
        section = extract_section(markdown_text, heading)
        if section:
            return section
    return ""


def validate_discussion_thread_pass_section(section: str) -> list[str]:
    """Validate Discussion Thread Pass section; return list of errors."""
    errors: list[str] = []

    if not section:
        errors.append("Missing '## Discussion Thread Pass' section.")
        return errors

    if CHECKBOX_DISCUSSION_PASS not in section:
        errors.append("Missing checkbox: '- [x] Discussion-thread pass completed'.")

    if CHECKBOX_FIXED_MAPPING not in section:
        errors.append("Missing checkbox: '- [x] Fixed in commit mapping completed'.")

    return errors


def validate_fixed_mapping_section(section: str) -> list[str]:
    """Validate Fixed in Commit Mapping section; return list of errors."""
    errors: list[str] = []

    if not section:
        errors.append("Missing '## Fixed in Commit Mapping' section.")
        return errors

    raw_lines = [ln.strip() for ln in section.splitlines()]
    non_empty_lines = [line for line in raw_lines if line]
    if not non_empty_lines:
        errors.append("'## Fixed in Commit Mapping' section is empty.")
        return errors

    if NO_ACTIONABLE_LINE in non_empty_lines:
        if len(non_empty_lines) > 1:
            errors.append(
                "Invalid mixed mode: 'No actionable review comments' "
                "cannot appear together with SHA mappings."
            )
        return errors

    blocks = _split_fixed_mapping_blocks(raw_lines)

    saw_thread_line = any(
        MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line)
        for block in blocks
        for line in block
    )
    skip_indexes: set[int] = set()
    for index, block in enumerate(blocks):
        if index in skip_indexes:
            continue
        next_block = blocks[index + 1] if index + 1 < len(blocks) else None
        if _is_mapping_entries_preamble(block):
            errors.extend(_validate_mapping_entries_preamble(block, next_block))
            if next_block is not None and _is_mapping_only_block(next_block):
                skip_indexes.add(index + 1)
            continue
        if (
            _is_mapping_only_block(block)
            and next_block is not None
            and _block_has_disposition(next_block)
        ):
            errors.extend(_validate_fixed_mapping_block([*block, *next_block]))
            skip_indexes.add(index + 1)
            continue
        errors.extend(_validate_fixed_mapping_block(block))

    if not saw_thread_line and not errors:
        errors.append(
            "Fixed in Commit Mapping must contain at least one '- <url>' or "
            "'- <url> -> <sha>' line, or '- No actionable review comments'."
        )

    return errors


def validate_mapping_artifact_text(markdown_text: str) -> list[str]:
    """Validate full artifact text; return list of errors."""
    errors: list[str] = []

    discussion_section = extract_discussion_thread_pass_section(markdown_text)
    fixed_mapping_section = extract_fixed_mapping_section(markdown_text)

    errors.extend(validate_discussion_thread_pass_section(discussion_section))
    errors.extend(validate_fixed_mapping_section(fixed_mapping_section))

    return errors


def parse_fixed_mapping_entries(section: str) -> dict[str, str]:
    """
    Parse review-thread lines.
    Returns {url: sha_or_empty_string}
    """
    entries: dict[str, str] = {}

    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or line == NO_ACTIONABLE_LINE:
            continue

        match = MAPPING_LINE_RE.match(line)
        if match:
            url, sha = match.groups()
            entries[url] = sha
            continue

        url_only_match = THREAD_LINE_RE.match(line)
        if url_only_match:
            entries[url_only_match.group(1)] = ""

    return entries


def has_no_actionable_marker(section: str) -> bool:
    """True if section contains 'No actionable review comments'."""
    return NO_ACTIONABLE_LINE in section


def render_phase2_body_mirror(pr_number: int) -> str:
    """Render the canonical PR-body mirror block from the artifact source of truth."""

    artifact_text = read_mapping_artifact(pr_number)
    errors = validate_mapping_artifact_text(artifact_text)
    if errors:
        joined_errors = "; ".join(errors)
        raise RuntimeError(f"Cannot render PR body mirror for PR #{pr_number}: {joined_errors}")

    artifact_ref = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    return "\n".join(
        [
            DISCUSSION_THREAD_PASS_HEADING,
            CHECKBOX_DISCUSSION_PASS,
            CHECKBOX_FIXED_MAPPING,
            "",
            "### Fixed in Commit Mapping",
            f"- canonical artifact: `{artifact_ref}`",
        ]
    )
