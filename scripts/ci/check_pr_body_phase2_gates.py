from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

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


DISCUSSION_SECTION_RE = _section_heading_re("##", PHASE2_CONFIG["discussion_heading"])
MAPPING_SECTION_RE = _section_heading_re("###", PHASE2_CONFIG["mapping_heading"])
DISCUSSION_CHECKBOX_RE = _checkbox_re(PHASE2_CONFIG["discussion_checkbox_label"])
MAPPING_CHECKBOX_RE = _checkbox_re(PHASE2_CONFIG["mapping_checkbox_label"])

MAPPING_ENTRY_RE = re.compile(
    r"(?im)^\s*-\s*`?(https?://[^\s`]+)`?\s*->\s*`?([0-9a-f]{7,40})`?\s*$"
)
_na_alternatives = "|".join(re.escape(a) for a in PHASE2_CONFIG["mapping_na_alternatives"])
MAPPING_NA_RE = re.compile(rf"(?im)^\s*-\s*(?:{_na_alternatives})\s*$")


def _strip_fenced_code_blocks(text: str) -> str:
    cleaned = re.sub(r"(?s)```.*?```", "", text)
    return re.sub(r"(?s)~~~.*?~~~", "", cleaned)


def _extract_checked(match: re.Match[str] | None) -> bool:
    return bool(match and match.group("checked").lower() == "x")


def _extract_pr_body(event_path: Path) -> str:
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ""
    except json.JSONDecodeError:
        return ""
    return str(payload.get("pull_request", {}).get("body", ""))


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


def check_pr_body_phase2_gates(body: str) -> list[str]:
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

    mapping_section = _extract_mapping_section(cleaned)
    has_mapping_entries = bool(MAPPING_ENTRY_RE.search(mapping_section))
    has_na_mapping = bool(MAPPING_NA_RE.search(mapping_section))
    if not has_mapping_entries and not has_na_mapping:
        errors.append(
            "Add at least one mapping entry "
            "(`- <review-comment-url> -> <commit-sha>`) or `- No actionable review comments`."
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
    args = parser.parse_args()

    body = args.body
    if not body and args.event_path:
        body = _extract_pr_body(Path(args.event_path))

    if not body.strip():
        print("ERROR: Empty PR body. Fill the required Phase2 checklist sections.")
        return 1

    errors = check_pr_body_phase2_gates(body=body)
    if errors:
        print("ERROR: phase2 PR body gates failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("phase2-pr-body-gates: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
