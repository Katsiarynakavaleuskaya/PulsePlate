"""Canonical Fixed in Commit Mapping artifact: repo file as source of truth."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "docs" / "review"

DISCUSSION_THREAD_PASS_HEADING = (
    "## Discussion Thread Pass"  # nosec B105 - doc heading (remove-by: 2026-06-30, ref: PR-998)
)
FIXED_MAPPING_HEADING = "## Fixed in Commit Mapping"

CHECKBOX_DISCUSSION_PASS = "- [x] Discussion-thread pass completed"  # nosec B105 - checkbox label (remove-by: 2026-06-30, ref: PR-998)
CHECKBOX_FIXED_MAPPING = "- [x] Fixed in commit mapping completed"

MAPPING_LINE_RE = re.compile(r"^\s*-\s+(https://github\.com/\S+)\s+->\s+([0-9a-f]{7,40})\s*$")
NO_ACTIONABLE_LINE = "- No actionable review comments"


def mapping_artifact_path(pr_number: int) -> Path:
    """Return canonical review mapping artifact path for a PR number."""
    return REVIEW_DIR / f"PR_{pr_number}_FIXED_MAPPING.md"


def read_mapping_artifact(pr_number: int) -> str:
    """Read canonical review mapping artifact text."""
    path = mapping_artifact_path(pr_number)
    if not path.is_file():
        raise FileNotFoundError(f"Missing canonical review mapping artifact: {path}")
    return path.read_text(encoding="utf-8")


def extract_section(markdown_text: str, heading: str) -> str:
    """
    Extract section body for a level-2 markdown heading.
    Returns content after heading until next level-2 heading or EOF.
    """
    lines = markdown_text.splitlines()
    inside = False
    collected: list[str] = []

    for line in lines:
        if line.strip() == heading:
            inside = True
            continue

        if inside and line.startswith("## "):
            break

        if inside:
            collected.append(line)

    return "\n".join(collected).strip()


def extract_discussion_thread_pass_section(markdown_text: str) -> str:
    """Extract ## Discussion Thread Pass section."""
    return extract_section(markdown_text, DISCUSSION_THREAD_PASS_HEADING)


def extract_fixed_mapping_section(markdown_text: str) -> str:
    """Extract ## Fixed in Commit Mapping section."""
    return extract_section(markdown_text, FIXED_MAPPING_HEADING)


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

    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
    if not lines:
        errors.append("'## Fixed in Commit Mapping' section is empty.")
        return errors

    if NO_ACTIONABLE_LINE in lines:
        if len(lines) > 1:
            errors.append(
                "Invalid mixed mode: 'No actionable review comments' "
                "cannot appear together with SHA mappings."
            )
        return errors

    for line in lines:
        if not MAPPING_LINE_RE.match(line):
            errors.append(f"Invalid mapping line format in canonical artifact: {line}")

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
    Parse mapping lines: - <url> -> <sha>
    Returns {url: sha}
    """
    entries: dict[str, str] = {}

    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or line == NO_ACTIONABLE_LINE:
            continue

        match = MAPPING_LINE_RE.match(line)
        if not match:
            continue

        url, sha = match.groups()
        entries[url] = sha

    return entries


def has_no_actionable_marker(section: str) -> bool:
    """True if section contains 'No actionable review comments'."""
    return NO_ACTIONABLE_LINE in section
