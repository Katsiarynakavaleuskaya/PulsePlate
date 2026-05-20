from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404: bounded git log advisory for local co-author diagnostics (remove-by: 2026-07-31, ref: experiment-runner-oracle-attribution-semantics)
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
from scripts.orchestration.check_experiment_runner_identity import EXPECTED_CO_AUTHOR_TRAILER

# Phase2 contract: headings and checkbox labels (single source for parser and docs).
# Changing template wording requires updating these constants and re-running tests.
PHASE2_CONFIG = {
    "discussion_heading": "Discussion Thread Pass",
    "mapping_heading": "Fixed in Commit Mapping",
    "experiment_runner_heading": "Experiment Runner Evidence",
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
EXPERIMENT_RUNNER_SECTION_RE = _section_heading_re(
    "##", str(PHASE2_CONFIG["experiment_runner_heading"])
)
DISCUSSION_CHECKBOX_RE = _checkbox_re(str(PHASE2_CONFIG["discussion_checkbox_label"]))
MAPPING_CHECKBOX_RE = _checkbox_re(str(PHASE2_CONFIG["mapping_checkbox_label"]))

MAPPING_ENTRY_RE = re.compile(
    r"(?im)^\s*-\s*`?(https?://[^\s`]+)`?\s*->\s*`?([0-9a-f]{7,40})`?\s*$"
)
THREAD_ENTRY_RE = re.compile(r"(?im)^\s*-\s*`?(https?://[^\s`]+)`?\s*$")
_na_alternatives = "|".join(re.escape(a) for a in PHASE2_CONFIG["mapping_na_alternatives"])
MAPPING_NA_RE = re.compile(rf"(?im)^\s*-\s*(?:{_na_alternatives})\s*$")
EXPERIMENT_RUNNER_ARTIFACT_RE = re.compile(
    r"(?im)^\s*(?:-\s*)?Artifact:\s*`?(?P<path>[^`\s]+)`?\s*$"
)
EXPERIMENT_RUNNER_NA_RE = re.compile(r"(?im)^\s*(?:-\s*)?Not applicable:\s*(?P<reason>\S.+?)\s*$")
EXPERIMENT_RUNNER_ARTIFACT_PREFIX = "artifacts/orchestration/experiments/results/"
MISSING_EXPERIMENT_RUNNER_EVIDENCE_WARNING = (
    "Advisory: missing `## Experiment Runner Evidence` section with "
    "`Artifact: artifacts/orchestration/experiments/results/<id>.json` "
    "or `Not applicable: <reason>`."
)
MISSING_EXPERIMENT_RUNNER_COAUTHOR_WARNING = (
    "Advisory: Experiment Runner artifact `{path}` sets coauthor_required=true, "
    "but branch commits do not include the canonical Experiment Runner co-author trailer."
)
UNVERIFIED_EXPERIMENT_RUNNER_ARTIFACT_WARNING = (
    "Advisory: Experiment Runner artifact `{path}` is referenced but unavailable "
    "locally, so coauthor_required cannot be verified against branch commits."
)


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


def _extract_markdown_section(
    text: str,
    *,
    level: str,
    title: str,
    stop_at_heading_level: int,
) -> str:
    """Return content of the last matching markdown section."""
    matches = list(_section_heading_re(level, title).finditer(text))
    if not matches:
        return ""
    match = matches[-1]
    start = match.end()
    next_heading = re.search(rf"(?im)^\s*#{{1,{stop_at_heading_level}}}\s+", text[start:])
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def _extract_mapping_section(text: str) -> str:
    """Return content of the last ### Fixed in Commit Mapping section."""
    return _extract_markdown_section(
        text,
        level="###",
        title=str(PHASE2_CONFIG["mapping_heading"]),
        stop_at_heading_level=3,
    )


def _extract_section_by_h2(text: str, heading: str) -> str:
    """Return content of the last matching H2 section."""
    return _extract_markdown_section(
        text,
        level="##",
        title=heading,
        stop_at_heading_level=2,
    )


def _valid_experiment_runner_artifact_path(path: str) -> bool:
    """Return True for local Experiment Runner result artifacts only."""
    cleaned = path.strip().strip("`")
    if "\\" in cleaned:
        return False
    if not cleaned.endswith(".json"):
        return False
    if cleaned.startswith(("/", "../", "./")):
        return False
    if "/../" in cleaned or cleaned.endswith("/.."):
        return False
    if not cleaned.startswith(EXPERIMENT_RUNNER_ARTIFACT_PREFIX):
        return False

    relative_path = cleaned.removeprefix(EXPERIMENT_RUNNER_ARTIFACT_PREFIX)
    path_parts = relative_path.split("/")
    if any(part in ("", ".", "..") for part in path_parts):
        return False
    return len(path_parts[-1].removesuffix(".json")) > 0


def _experiment_runner_artifact_paths(text: str) -> list[str]:
    """Return valid local Experiment Runner artifact paths referenced by text."""

    paths: list[str] = []
    for match in EXPERIMENT_RUNNER_ARTIFACT_RE.finditer(_strip_fenced_code_blocks(text)):
        path = match.group("path").strip().strip("`")
        if _valid_experiment_runner_artifact_path(path):
            paths.append(path)
    return list(dict.fromkeys(paths))


def check_experiment_runner_evidence(text: str) -> tuple[list[str], list[str]]:
    """Validate advisory Experiment Runner evidence.

    Missing evidence is a warning for this PR series. Malformed evidence is an
    error because an invalid path or empty N/A reason creates false governance
    proof.
    """

    cleaned = _strip_fenced_code_blocks(text)
    section = _extract_section_by_h2(cleaned, str(PHASE2_CONFIG["experiment_runner_heading"]))
    if not section:
        return [], [MISSING_EXPERIMENT_RUNNER_EVIDENCE_WARNING]

    artifact_matches = list(EXPERIMENT_RUNNER_ARTIFACT_RE.finditer(section))
    na_matches = list(EXPERIMENT_RUNNER_NA_RE.finditer(section))
    errors: list[str] = []

    if artifact_matches and na_matches:
        errors.append(
            "Experiment Runner Evidence must use either Artifact or Not applicable, not both."
        )

    if artifact_matches:
        invalid_paths = [
            match.group("path")
            for match in artifact_matches
            if not _valid_experiment_runner_artifact_path(match.group("path"))
        ]
        if invalid_paths:
            errors.append(
                "Experiment Runner artifact path must stay under "
                f"`{EXPERIMENT_RUNNER_ARTIFACT_PREFIX}` and end with `.json`: "
                + ", ".join(invalid_paths)
            )

    if na_matches:
        empty_reasons = [
            match.group("reason") for match in na_matches if len(match.group("reason").strip()) < 8
        ]
        if empty_reasons:
            errors.append("Experiment Runner not-applicable reason must be explicit.")

    if not artifact_matches and not na_matches:
        errors.append(
            "Experiment Runner Evidence must include `Artifact: ...` or "
            "`Not applicable: <reason>`."
        )

    return errors, []


def _git_commit_messages(commit_range: str = "origin/main..HEAD") -> str:
    """Read branch commit messages for local advisory attribution diagnostics."""

    git_bin = shutil.which("git")
    if git_bin is None:
        return ""
    try:
        completed = subprocess.run(  # nosec B603: absolute git binary, fixed log command, no shell (remove-by: 2026-07-31, ref: experiment-runner-oracle-attribution-semantics)
            [git_bin, "log", "--format=%B", commit_range],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout


def check_experiment_runner_coauthor_advisory(
    text: str,
    *,
    commit_messages: str,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Warn when a local runner artifact requires co-authoring but commits lack it."""

    if EXPECTED_CO_AUTHOR_TRAILER in commit_messages:
        return []

    warnings: list[str] = []
    for artifact_path in _experiment_runner_artifact_paths(text):
        absolute_path = repo_root / artifact_path
        if not absolute_path.is_file():
            warnings.append(
                UNVERIFIED_EXPERIMENT_RUNNER_ARTIFACT_WARNING.format(path=artifact_path)
            )
            continue
        try:
            payload = json.loads(absolute_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            warnings.append(
                UNVERIFIED_EXPERIMENT_RUNNER_ARTIFACT_WARNING.format(path=artifact_path)
            )
            continue
        if isinstance(payload, dict) and payload.get("coauthor_required") is True:
            warning = MISSING_EXPERIMENT_RUNNER_COAUTHOR_WARNING.format(path=artifact_path)
            reason = str(payload.get("coauthor_reason", "")).strip()
            if reason:
                warning = f"{warning} Reason: {reason}"
            warnings.append(warning)
    return warnings


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
    parser.add_argument(
        "--commit-range",
        default="origin/main..HEAD",
        help=(
            "Git commit range for advisory Experiment Runner co-author diagnostics. "
            "Defaults to origin/main..HEAD."
        ),
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
    advisory_warnings: list[str] = []
    evidence_warning_candidates: list[str] = []
    evidence_texts: list[str] = []
    experiment_runner_evidence_seen = False

    if pr_number is not None:
        try:
            artifact_text = read_mapping_artifact(pr_number)
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}")
            return 1
        artifact_checked = True
        artifact_errors.extend(validate_mapping_artifact_text(artifact_text))
        evidence_texts.append(artifact_text)
        evidence_errors, evidence_warnings = check_experiment_runner_evidence(artifact_text)
        artifact_errors.extend(evidence_errors)
        evidence_warning_candidates.extend(evidence_warnings)
        if not evidence_errors and not evidence_warnings:
            experiment_runner_evidence_seen = True

    if body.strip():
        cleaned_body = _strip_fenced_code_blocks(body)
        evidence_texts.append(body)
        has_phase2_mirror = bool(
            DISCUSSION_SECTION_RE.search(cleaned_body) or MAPPING_SECTION_RE.search(cleaned_body)
        )
        if not artifact_checked or has_phase2_mirror:
            body_checked = True
            body_errors.extend(
                check_pr_body_phase2_gates(
                    body=body,
                    mode=_select_body_validation_mode(artifact_checked=artifact_checked),
                )
            )
        evidence_errors, evidence_warnings = check_experiment_runner_evidence(body)
        if evidence_errors:
            body_checked = True
        body_errors.extend(evidence_errors)
        evidence_warning_candidates.extend(evidence_warnings)
        if not evidence_errors and not evidence_warnings:
            experiment_runner_evidence_seen = True
    elif not artifact_checked:
        print("ERROR: Empty PR body. Fill the required Phase2 checklist sections.")
        return 1

    if not experiment_runner_evidence_seen:
        advisory_warnings.extend(dict.fromkeys(evidence_warning_candidates))
    if experiment_runner_evidence_seen:
        commit_messages = _git_commit_messages(args.commit_range)
        for evidence_text in evidence_texts:
            advisory_warnings.extend(
                check_experiment_runner_coauthor_advisory(
                    evidence_text,
                    commit_messages=commit_messages,
                )
            )
        advisory_warnings = list(dict.fromkeys(advisory_warnings))

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

    for item in advisory_warnings:
        print(f"WARNING: {item}")

    if artifact_checked and body_checked:
        print("phase2-pr-body-gates: canonical mapping artifact and PR body mirror passed.")
        return 0
    if artifact_checked:
        print(
            "phase2-pr-body-gates: canonical mapping artifact passed "
            "(PR body mirror optional in artifact-first mode)."
        )
        return 0

    print("phase2-pr-body-gates: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
