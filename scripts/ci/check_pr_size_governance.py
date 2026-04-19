#!/usr/bin/env python3
"""PR-size governance gate for Tier 1 CI/CD.

RU: Проверяет размер PR по LoC и требует явное split-обоснование для больших PR.
EN: Enforces the Tier 1 PR-size policy using changed-line counts and PR-body proof.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess  # nosec B404: subprocess is required for bounded local git diff execution (remove-by: 2026-09-30, ref: PR3-risk-topology)
import sys
import re
import shutil

REPO_ROOT = Path(__file__).resolve().parents[2]
NORMAL_MAX_LOC = 299
WARNING_MAX_LOC = 800
GIT_BINARY = shutil.which("git")
SPLIT_JUSTIFICATION_INLINE_PATTERN = re.compile(
    r"(?im)^(?:[*]{0,2})?split justification:\s*\S.+$",
)
SPLIT_JUSTIFICATION_HEADING_PATTERN = re.compile(
    r"(?im)^(?:##+\s*|[*]{0,2})?(?:pr size justification|split justification)\s*$",
)
SPLIT_JUSTIFICATION_TEMPLATE_PLACEHOLDERS = {
    "why this pr cannot be split safely:",
    "what invariant, contract, or rollout constraint requires one pr:",
    "what follow-up prs remain after this large change:",
}


def parse_numstat_output(numstat_output: str) -> tuple[int, int]:
    """Return total changed lines and counted files from git --numstat output."""
    total_changed_lines = 0
    counted_files = 0
    for raw_line in numstat_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t", maxsplit=2)
        if len(parts) != 3:
            continue
        added_raw, deleted_raw, _path = parts
        if added_raw == "-" or deleted_raw == "-":
            continue
        total_changed_lines += int(added_raw) + int(deleted_raw)
        counted_files += 1
    return total_changed_lines, counted_files


def classify_pr_size(total_changed_lines: int) -> str:
    """Classify PR size according to Tier 1 governance buckets."""
    if total_changed_lines <= NORMAL_MAX_LOC:
        return "normal"
    if total_changed_lines <= WARNING_MAX_LOC:
        return "warning"
    return "requires_split_justification"


def normalize_split_justification_candidate(candidate_text: str) -> str:
    """Return a normalized split-justification line for placeholder comparison."""
    normalized = re.sub(r"\s+", " ", candidate_text.strip()).casefold()
    return re.sub(r"^(?:[-*]\s*)", "", normalized)


def extract_markdown_heading_level(line: str) -> int:
    """Return markdown heading depth for a line, or zero when it is not a heading."""
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#")) if stripped.startswith("#") else 0


def has_split_justification(pr_body: str) -> bool:
    """Return True when the PR body contains an explicit split-justification block."""
    normalized_body = re.sub(r"<!--.*?-->", "", pr_body or "", flags=re.DOTALL)
    if SPLIT_JUSTIFICATION_INLINE_PATTERN.search(normalized_body):
        return True

    lines = normalized_body.splitlines()
    for index, line in enumerate(lines):
        if not SPLIT_JUSTIFICATION_HEADING_PATTERN.match(line.strip()):
            continue
        heading_level = extract_markdown_heading_level(line)
        for candidate in lines[index + 1 :]:
            candidate_text = candidate.strip()
            if not candidate_text:
                continue
            if candidate_text.startswith("#"):
                candidate_heading_level = extract_markdown_heading_level(candidate_text)
                if heading_level and candidate_heading_level > heading_level:
                    continue
                return False
            if (
                normalize_split_justification_candidate(candidate_text)
                in SPLIT_JUSTIFICATION_TEMPLATE_PLACEHOLDERS
            ):
                continue
            return True
        return False
    return False


def evaluate_pr_size_policy(
    *,
    total_changed_lines: int,
    counted_files: int,
    pr_body: str,
) -> tuple[int, list[str]]:
    """Evaluate size policy and return exit code plus deterministic terminal lines."""
    bucket = classify_pr_size(total_changed_lines)
    normal_range_text = f"<={NORMAL_MAX_LOC} LoC"
    warning_range_text = f"{NORMAL_MAX_LOC + 1}-{WARNING_MAX_LOC} LoC"
    split_required_text = f">{WARNING_MAX_LOC} LoC"
    lines = [
        f"PR size bucket: {bucket}",
        f"Changed lines: {total_changed_lines}",
        f"Counted files: {counted_files}",
    ]
    if bucket == "normal":
        lines.append(f"PR size governance: OK ({normal_range_text}).")
        return 0, lines

    if bucket == "warning":
        lines.append(
            f"PR size governance: WARNING ({warning_range_text}). Review split opportunities.",
        )
        return 0, lines

    if has_split_justification(pr_body):
        lines.append(
            f"PR size governance: OK ({split_required_text}) because explicit split justification is present.",
        )
        return 0, lines

    lines.append(
        f"PR size governance: FAIL ({split_required_text} without explicit split justification).",
    )
    lines.append("Add `## Split Justification` (or `Split justification:`) to the PR body.")
    return 1, lines


def collect_numstat_output(*, base_sha: str, head_sha: str) -> str:
    """Collect git --numstat output between two revisions."""
    if GIT_BINARY is None:
        raise RuntimeError("git executable not found in PATH")
    result = subprocess.run(  # nosec B603: fixed git argv without shell for local CI routing only (remove-by: 2026-09-30, ref: PR3-risk-topology)
        [
            GIT_BINARY,
            "diff",
            "--numstat",
            f"{base_sha}...{head_sha}",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def extract_pr_body(event_path: Path) -> str:
    """Extract PR body from a GitHub event payload."""
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return ""
    body = pull_request.get("body")
    return body if isinstance(body, str) else ""


def _read_flag_value(argv: list[str], index: int, flag: str) -> str:
    """Return the next argv token for a flag or exit with a deterministic error."""
    value_index = index + 1
    if value_index >= len(argv):
        raise SystemExit(f"Missing value for {flag}.")
    value = argv[value_index]
    if value.startswith("--"):
        raise SystemExit(f"Missing value for {flag}.")
    return value


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    argv = list(sys.argv[1:] if argv is None else argv)
    base_sha = ""
    head_sha = ""
    pr_body = ""
    event_path: Path | None = None

    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--base-sha":
            index += 1
            base_sha = _read_flag_value(argv, index - 1, argument)
        elif argument == "--head-sha":
            index += 1
            head_sha = _read_flag_value(argv, index - 1, argument)
        elif argument == "--body":
            index += 1
            pr_body = _read_flag_value(argv, index - 1, argument)
        elif argument == "--event-path":
            index += 1
            event_path = Path(_read_flag_value(argv, index - 1, argument))
        else:
            raise SystemExit(f"Unknown argument: {argument}")
        index += 1

    if not base_sha or not head_sha:
        raise SystemExit("Provide both --base-sha and --head-sha.")

    if event_path is not None and not pr_body:
        pr_body = extract_pr_body(event_path)

    total_changed_lines, counted_files = parse_numstat_output(
        collect_numstat_output(base_sha=base_sha, head_sha=head_sha),
    )
    exit_code, lines = evaluate_pr_size_policy(
        total_changed_lines=total_changed_lines,
        counted_files=counted_files,
        pr_body=pr_body,
    )
    for line in lines:
        print(line)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
