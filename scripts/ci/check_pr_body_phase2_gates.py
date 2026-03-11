from __future__ import annotations

import argparse
import json
import re
import sys
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestration.review_mapping_artifact import (
    read_mapping_artifact,
    validate_mapping_artifact_text,
)

# Phase2 contract: headings and checkbox labels (single source for parser and docs).
# Changing template wording requires updating these constants and re-running tests.
PHASE2_CONFIG = {
    "discussion_heading": "Discussion Thread Pass",
    "mapping_heading": "Fixed in Commit Mapping",
    "discussion_checkbox_label": "Discussion-thread pass completed",
    "mapping_checkbox_label": "Fixed in commit mapping completed",
    "mapping_na_alternatives": ("N/A", "No actionable review comments"),
}


def _section_heading_re(level: str, title: str) -> re.Pattern[str]:
    escaped = re.escape(title).replace(r"\ ", r"\s+")
    return re.compile(rf"(?im)^\s*{level}\s+{escaped}\s*$")


def _checkbox_re(label: str) -> re.Pattern[str]:
    escaped = re.escape(label)
    return re.compile(rf"(?im)^\s*-\s*\[(?P<checked>[ xX])\]\s*{escaped}\s*$")


DISCUSSION_SECTION_RE = _section_heading_re("##", str(PHASE2_CONFIG["discussion_heading"]))
MAPPING_SECTION_RE = _section_heading_re("###", str(PHASE2_CONFIG["mapping_heading"]))
DISCUSSION_CHECKBOX_RE = _checkbox_re(str(PHASE2_CONFIG["discussion_checkbox_label"]))
MAPPING_CHECKBOX_RE = _checkbox_re(str(PHASE2_CONFIG["mapping_checkbox_label"]))

MAPPING_ENTRY_RE = re.compile(
    r"(?im)^\s*-\s*`?(https?://[^\s`]+)`?\s*->\s*`?([0-9a-f]{7,40})`?\s*$"
)
THREAD_ENTRY_RE = re.compile(r"(?im)^\s*-\s*`?(https?://[^\s`]+)`?\s*$")
_na_alternatives = "|".join(re.escape(a) for a in PHASE2_CONFIG["mapping_na_alternatives"])
MAPPING_NA_RE = re.compile(rf"(?im)^\s*-\s*(?:{_na_alternatives})\s*$")


class BodyValidationMode(str, Enum):
    """Explicit Phase2 body validation modes for artifact-first vs fallback checks."""

    FULL_MAPPING = "full_mapping"
    MIRROR_ONLY = "mirror_only"


def _strip_fenced_code_blocks(text: str) -> str:
    cleaned = re.sub(r"(?s)```.*?```", "", text)
    return re.sub(r"(?s)~~~.*?~~~", "", cleaned)


def _extract_checked(match: re.Match[str] | None) -> bool:
    return bool(match and match.group("checked").lower() == "x")


def _load_event_pull_request(event_path: Path) -> dict[str, object]:
    """Load pull_request dict from GitHub event payload."""
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    pull_request = payload.get("pull_request")
    return pull_request if isinstance(pull_request, dict) else {}


def _extract_pr_number(event_path: Path) -> int | None:
    """Extract PR number from GitHub event payload."""
    pr = _load_event_pull_request(event_path)
    num = pr.get("number")
    if isinstance(num, bool) or num is None:
        return None
    if isinstance(num, int):
        return num
    if isinstance(num, str):
        try:
            return int(num)
        except ValueError:
            return None
    return None


def _extract_pr_body(event_path: Path) -> str:
    """Extract PR body from GitHub event payload."""
    pr = _load_event_pull_request(event_path)
    body = pr.get("body")
    return body if isinstance(body, str) else ""


def _extract_mapping_section(text: str) -> str:
    """Return content of the last ### Fixed in Commit Mapping section."""
    matches = list(MAPPING_SECTION_RE.finditer(text))
    if not matches:
        return ""
    match = matches[-1]
    start = match.end()
    next_h2 = re.search(r"(?im)^\s*##\s+", text[start:])
    end = start + next_h2.start() if next_h2 else len(text)
    return text[start:end]


def _select_body_validation_mode(*, artifact_checked: bool) -> BodyValidationMode:
    """Choose body validation mode from the canonical artifact/body contract."""
    if artifact_checked:
        return BodyValidationMode.MIRROR_ONLY
    return BodyValidationMode.FULL_MAPPING


def check_pr_body_phase2_gates(
    body: str,
    *,
    mode: BodyValidationMode = BodyValidationMode.FULL_MAPPING,
) -> list[str]:
    errors: list[str] = []
    cleaned = _strip_fenced_code_blocks(body)

    d_heading = f"## {PHASE2_CONFIG['discussion_heading']}"
    m_heading = f"### {PHASE2_CONFIG['mapping_heading']}"
    if not DISCUSSION_SECTION_RE.search(cleaned):
        errors.append(f"Missing required section: `{d_heading}`.")
    if not MAPPING_SECTION_RE.search(cleaned):
        errors.append(f"Missing required section: `{m_heading}`.")

    discussion_check = DISCUSSION_CHECKBOX_RE.search(cleaned)
    if not _extract_checked(discussion_check):
        errors.append(
            f"Checklist item must be checked: `{PHASE2_CONFIG['discussion_checkbox_label']}`."
        )

    mapping_check = MAPPING_CHECKBOX_RE.search(cleaned)
    if not _extract_checked(mapping_check):
        errors.append(
            f"Checklist item must be checked: `{PHASE2_CONFIG['mapping_checkbox_label']}`."
        )

    if mode is BodyValidationMode.FULL_MAPPING:
        mapping_section = _extract_mapping_section(cleaned)
        has_mapping_entries = bool(
            MAPPING_ENTRY_RE.search(mapping_section) or THREAD_ENTRY_RE.search(mapping_section)
        )
        has_na_mapping = bool(MAPPING_NA_RE.search(mapping_section))
        if not has_mapping_entries and not has_na_mapping:
            errors.append(
                "Add at least one review-thread entry "
                "(`- <review-comment-url>` or `- <review-comment-url> -> <commit-sha>`) "
                "or `- No actionable review comments`."
            )
        if has_mapping_entries and has_na_mapping:
            errors.append(
                "Invalid mixed mode: 'No actionable review comments' cannot appear "
                "together with SHA mappings (use one or the other)."
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase2 PR body quality gates.")
    parser.add_argument(
        "--event-path",
        default="",
        help="Path to GitHub event JSON payload (e.g., $GITHUB_EVENT_PATH).",
    )
    parser.add_argument(
        "--body",
        default="",
        help="Explicit PR body text (optional, overrides event body if provided).",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="PR number for artifact lookup (optional, extracted from event-path if not set).",
    )
    args = parser.parse_args()

    body = args.body
    if not body and args.event_path:
        body = _extract_pr_body(Path(args.event_path))

    # Canonical SoT: repo artifact (docs/review/PR_<N>_FIXED_MAPPING.md)
    pr_number = args.pr_number
    if pr_number is None and args.event_path:
        pr_number = _extract_pr_number(Path(args.event_path))

    artifact_checked = False
    body_checked = False
    artifact_errors: list[str] = []
    body_errors: list[str] = []

    if pr_number is not None:
        try:
            artifact_text = read_mapping_artifact(pr_number)
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}")
            return 1
        artifact_checked = True
        artifact_errors.extend(validate_mapping_artifact_text(artifact_text))

    if not body.strip():
        print("ERROR: Empty PR body. Fill the required Phase2 checklist sections.")
        return 1
    body_checked = True
    body_errors.extend(
        check_pr_body_phase2_gates(
            body=body,
            mode=_select_body_validation_mode(artifact_checked=artifact_checked),
        )
    )

    errors = [*artifact_errors, *body_errors]
    if errors:
        print("ERROR: phase2 gates failed:")
        if artifact_checked and artifact_errors:
            print("- canonical mapping artifact validation failed")
        if body_checked and body_errors:
            print("- PR body validation failed")
        for item in errors:
            print(f"- {item}")
        return 1

    if artifact_checked:
        print("phase2-pr-body-gates: canonical mapping artifact and PR body mirror passed.")
        return 0

    print("phase2-pr-body-gates: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
