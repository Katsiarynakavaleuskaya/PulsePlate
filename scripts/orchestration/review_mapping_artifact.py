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


DISCUSSION_THREAD_PASS_HEADING = (
    "## Discussion Thread Pass"  # nosec B105: doc heading (remove-by: 2026-06-30, ref: PR-998)
)
# Canonical artifact uses ##; PR-body mirror/fallback may use ### (AGENTS.md)
FIXED_MAPPING_HEADINGS = ("## Fixed in Commit Mapping", "### Fixed in Commit Mapping")

CHECKBOX_DISCUSSION_PASS = "- [x] Discussion-thread pass completed"  # nosec B105: checkbox label (remove-by: 2026-06-30, ref: PR-998)
CHECKBOX_FIXED_MAPPING = "- [x] Fixed in commit mapping completed"

MAPPING_LINE_RE = re.compile(r"^\s*-\s+(https://github\.com/\S+)\s+->\s+([0-9a-f]{7,40})\s*$")
NO_ACTIONABLE_LINE = "- No actionable review comments"
# Disposition/proof lines allowed in section (disposition guard format)
DETAIL_PREFIXES = ("Disposition:", "Commit:", "Evidence:", "Backlog:")


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

    saw_mapping_line = False
    saw_disposition = False
    saw_proof = False
    for line in lines:
        if line.startswith("Disposition:"):
            saw_disposition = True
            continue
        if any(line.startswith(prefix) for prefix in ("Commit:", "Evidence:", "Backlog:")):
            saw_proof = True
            continue
        if MAPPING_LINE_RE.match(line):
            saw_mapping_line = True
            continue
        errors.append(f"Invalid mapping line format in canonical artifact: {line}")

    if not errors and not saw_mapping_line:
        errors.append(
            "Fixed in Commit Mapping must contain at least one '- <url> -> <sha>' line "
            "or '- No actionable review comments'."
        )
    if not errors and saw_mapping_line and not saw_disposition:
        errors.append("Missing 'Disposition:' when SHA mappings are present.")
    if not errors and saw_mapping_line and not saw_proof:
        errors.append(
            "Missing proof detail (Commit:/Evidence:/Backlog:) when SHA mappings are present."
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
