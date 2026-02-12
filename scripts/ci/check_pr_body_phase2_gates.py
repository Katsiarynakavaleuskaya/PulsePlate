from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DISCUSSION_SECTION_RE = re.compile(r"(?im)^\s*##\s*Discussion Thread Pass\s*$")
MAPPING_SECTION_RE = re.compile(r"(?im)^\s*###\s*Fixed in Commit Mapping\s*$")

DISCUSSION_CHECKBOX_RE = re.compile(
    r"(?im)^\s*-\s*\[(?P<checked>[ xX])\]\s*Discussion-thread pass completed\s*$"
)
MAPPING_CHECKBOX_RE = re.compile(
    r"(?im)^\s*-\s*\[(?P<checked>[ xX])\]\s*Fixed in commit mapping completed\s*$"
)

MAPPING_ENTRY_RE = re.compile(
    r"(?im)^\s*-\s*`?(https?://[^\s`]+)`?\s*->\s*`?([0-9a-f]{7,40})`?\s*$"
)
MAPPING_NA_RE = re.compile(r"(?im)^\s*-\s*(?:N/A|No actionable review comments)\s*$")


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


def check_pr_body_phase2_gates(body: str) -> list[str]:
    errors: list[str] = []
    cleaned = _strip_fenced_code_blocks(body)

    if not DISCUSSION_SECTION_RE.search(cleaned):
        errors.append("Missing required section: `## Discussion Thread Pass`.")
    if not MAPPING_SECTION_RE.search(cleaned):
        errors.append("Missing required section: `### Fixed in Commit Mapping`.")

    discussion_check = DISCUSSION_CHECKBOX_RE.search(cleaned)
    if not _extract_checked(discussion_check):
        errors.append("Checklist item must be checked: `Discussion-thread pass completed`.")

    mapping_check = MAPPING_CHECKBOX_RE.search(cleaned)
    if not _extract_checked(mapping_check):
        errors.append("Checklist item must be checked: `Fixed in commit mapping completed`.")

    has_mapping_entries = bool(MAPPING_ENTRY_RE.search(cleaned))
    has_na_mapping = bool(MAPPING_NA_RE.search(cleaned))
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
