from __future__ import annotations

import argparse
import json
import os
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
from scripts.orchestration.experiment_contract import (
    validate_contribution_attribution,
    validate_experiment_result,
)

# Phase2 contract: headings and checkbox labels (single source for parser and docs).
# Changing template wording requires updating these constants and re-running tests.
PHASE2_CONFIG = {
    "discussion_heading": "Discussion Thread Pass",
    "mapping_heading": "Fixed in Commit Mapping",
    "experiment_runner_heading": "Experiment Runner Evidence",
    "lane_start_heading": "Lane Start Provenance",
    "discussion_checkbox_label": "Discussion-thread pass completed",
    "mapping_checkbox_label": "Fixed in commit mapping completed",
    "mapping_na_alternatives": ("N/A", "No actionable review comments"),
    "pre_closeout_marker": "phase2-pre-closeout: final-security-pending",
    "pre_closeout_pending_text": "Pending final clean scan and the single mapping/closeout commit.",
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
_PRE_CLOSEOUT_MARKER = str(PHASE2_CONFIG["pre_closeout_marker"])
_PRE_CLOSEOUT_PENDING_TEXT = str(PHASE2_CONFIG["pre_closeout_pending_text"])
PRE_CLOSEOUT_MARKER_RE = re.compile(rf"(?im)^\s*<!--\s*{re.escape(_PRE_CLOSEOUT_MARKER)}\s*-->\s*$")
PRE_CLOSEOUT_PENDING_RE = re.compile(rf"(?im)^\s*-\s*{re.escape(_PRE_CLOSEOUT_PENDING_TEXT)}\s*$")
HTML_COMMENT_RE = re.compile(r"(?s)<!--.*?-->")
EXPERIMENT_RUNNER_ARTIFACT_RE = re.compile(
    r"(?im)^\s*(?:-\s*)?Artifact:\s*`?(?P<path>[^`\s]+)`?\s*$"
)
EXPERIMENT_RUNNER_NA_RE = re.compile(r"(?im)^\s*(?:-\s*)?Not applicable:\s*(?P<reason>\S.+?)\s*$")
EXPERIMENT_RUNNER_ARTIFACT_PREFIX = "artifacts/orchestration/experiments/results/"
LANE_START_PACKET_RE = re.compile(r"(?im)^\s*(?:-\s*)?Packet:\s*`?(?P<path>[^`\s]+)`?\s*$")
LANE_STARTER_RE = re.compile(r"(?im)^\s*(?:-\s*)?Starter:\s*`?(?P<path>[^`\s]+)`?\s*$")
LANE_START_EXCEPTION_RE = re.compile(r"(?im)^\s*(?:-\s*)?Exception:\s*(?P<reason>\S.+?)\s*$")
FORBIDDEN_PREFLIGHT_AUTHORITY_RE = re.compile(
    r"(?im)^"
    r"(?!\s*(?:-\s*)?(?:host/codex|host|codex|cursor|raw|local)\s+preflight\s+"
    r"(?:is\s+not|isn't)\s+authoritative(?:\s+lane\s+provenance)?"
    r"(?![^\n]*(?:\bbut\b|\balready\b|\bran\b|\bcompleted\b))[^\n]*$)"
    r"(?!\s*(?:-\s*)?(?:host/codex|host|codex|cursor|raw|local)\s+preflight\s+"
    r"must\s+not\s+(?:be\s+)?(?:used|treated|cited)\s+as\s+authority\.?\s*$)"
    r"[^\n]*\b(?:host/codex|host|codex|cursor|raw|local)\s+preflight\b"
)
LANE_START_PACKET_PREFIX = "artifacts/orchestration/task_packets/"
LANE_STARTER_PATH = "scripts/orchestration/start_pr_lane.sh"
COMMIT_MESSAGE_SEPARATOR = "\x1e"
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
INVALID_EXPERIMENT_RUNNER_ARTIFACT_METADATA_WARNING = (
    "Advisory: Experiment Runner artifact `{path}` has invalid co-author metadata, "
    "so coauthor_required cannot be verified against branch commits."
)
MISSING_LANE_START_PROVENANCE_WARNING = (
    "Dry-run advisory: missing `## Lane Start Provenance` section with "
    "`Packet: artifacts/orchestration/task_packets/<id>.json` or "
    "`Exception: <reason>`; `Starter: scripts/orchestration/start_pr_lane.sh` "
    "is supplemental and cannot be used alone. "
    "This would fail when lane-start provenance is promoted to a hard gate."
)
UNVERIFIED_LANE_START_PACKET_WARNING = (
    "Dry-run advisory: Lane Start Provenance packet `{path}` is referenced but "
    "is not available locally, so bootstrap provenance cannot be verified. "
    "This would fail when lane-start provenance is promoted to a hard gate."
)


def _lane_start_missing_warnings(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if warning == MISSING_LANE_START_PROVENANCE_WARNING]


def _lane_start_non_missing_warnings(warnings: list[str]) -> list[str]:
    return [warning for warning in warnings if warning != MISSING_LANE_START_PROVENANCE_WARNING]


def _lane_start_source_seen(errors: list[str], warnings: list[str]) -> bool:
    return not errors and MISSING_LANE_START_PROVENANCE_WARNING not in warnings


class BodyValidationMode(str, Enum):
    """Explicit Phase2 body validation modes for artifact-first vs fallback checks."""

    FULL_MAPPING = "full_mapping"
    MIRROR_ONLY = "mirror_only"
    PRE_CLOSEOUT = "pre_closeout"


class ExperimentRunnerEvidenceMode(str, Enum):
    """Phase2 enforcement mode for Experiment Runner Evidence."""

    ADVISORY = "advisory"
    REQUIRED = "required"


def _experiment_runner_evidence_mode(
    value: str | ExperimentRunnerEvidenceMode | None,
) -> ExperimentRunnerEvidenceMode:
    """Normalize Experiment Runner evidence enforcement mode."""

    if isinstance(value, ExperimentRunnerEvidenceMode):
        return value
    normalized = str(value or ExperimentRunnerEvidenceMode.ADVISORY.value).strip().lower()
    try:
        return ExperimentRunnerEvidenceMode(normalized)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in ExperimentRunnerEvidenceMode)
        raise argparse.ArgumentTypeError(
            f"Experiment Runner evidence mode must be one of: {allowed}"
        ) from exc


def _strip_fenced_code_blocks(text: str) -> str:
    cleaned = re.sub(r"(?s)```.*?```", "", text)
    return re.sub(r"(?s)~~~.*?~~~", "", cleaned)


def _normalize_phase2_body(text: str) -> str:
    """Remove non-authoritative Markdown content before Phase2 parsing."""

    cleaned = _strip_fenced_code_blocks(text)

    def preserve_pre_closeout_marker(match: re.Match[str]) -> str:
        comment = match.group(0)
        return comment if PRE_CLOSEOUT_MARKER_RE.fullmatch(comment) else ""

    return HTML_COMMENT_RE.sub(preserve_pre_closeout_marker, cleaned)


def _extract_checked(match: re.Match[str] | None) -> bool:
    return bool(match and match.group("checked").lower() == "x")


def _has_pre_closeout_marker(text: str) -> bool:
    """Return whether a body explicitly declares the non-mergeable closeout phase."""

    return bool(PRE_CLOSEOUT_MARKER_RE.search(_normalize_phase2_body(text)))


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


def _valid_lane_start_packet_path(path: str) -> bool:
    """Return True for repo bootstrap packet references accepted as provenance."""
    cleaned = path.strip().strip("`")
    if "\\" in cleaned:
        return False
    if cleaned.startswith(("/", "../", "./")):
        return False
    if "/../" in cleaned or cleaned.endswith("/.."):
        return False

    if cleaned.startswith(LANE_START_PACKET_PREFIX):
        if not cleaned.endswith(".json"):
            return False
        relative_path = cleaned.removeprefix(LANE_START_PACKET_PREFIX)
        path_parts = relative_path.split("/")
        if any(part in ("", ".", "..") for part in path_parts):
            return False
        return len(path_parts[-1].removesuffix(".json")) > 0

    return False


def _valid_lane_start_exception_reason(reason: str) -> bool:
    """Return True for narrow documented provenance exceptions."""
    normalized = re.sub(r"\s+", " ", reason.strip().lower())
    allowed_phrases = (
        "trivial docs cleanup",
        "docs-only cleanup",
        "main cleanup",
        "cache cleanup",
        "operator-declared emergency infrastructure repair",
        "operator-declared emergency infra repair",
        "emergency infrastructure repair",
    )
    return any(
        normalized == phrase
        or normalized.startswith(f"{phrase}:")
        or normalized.startswith(f"{phrase} -")
        for phrase in allowed_phrases
    )


def _lane_start_packet_available(path: str, *, repo_root: Path) -> bool:
    """Return True when a lane-start packet reference is locally verifiable."""
    cleaned = path.strip().strip("`")
    try:
        candidate = (repo_root / cleaned).resolve(strict=False)
        candidate.relative_to(repo_root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return candidate.is_file()


def check_lane_start_provenance(
    text: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[str], list[str]]:
    """Validate dry-run lane-start provenance.

    Missing provenance is advisory in this wave. Malformed present provenance is
    an error because it would create false proof that repo bootstrap ran.
    """

    cleaned = _strip_fenced_code_blocks(text)
    section = _extract_section_by_h2(cleaned, str(PHASE2_CONFIG["lane_start_heading"]))
    if not section:
        return [], [MISSING_LANE_START_PROVENANCE_WARNING]

    packet_matches = list(LANE_START_PACKET_RE.finditer(section))
    starter_matches = list(LANE_STARTER_RE.finditer(section))
    exception_matches = list(LANE_START_EXCEPTION_RE.finditer(section))
    errors: list[str] = []
    warnings: list[str] = []

    if exception_matches and packet_matches:
        errors.append(
            "Lane Start Provenance must use repo bootstrap evidence or Exception, not both."
        )

    invalid_packets = [
        match.group("path")
        for match in packet_matches
        if not _valid_lane_start_packet_path(match.group("path"))
    ]
    if invalid_packets:
        errors.append(
            "Lane Start Provenance packet must be "
            f"`{LANE_START_PACKET_PREFIX}<id>.json`: " + ", ".join(invalid_packets)
        )
    for match in packet_matches:
        path = match.group("path")
        if path not in invalid_packets and not _lane_start_packet_available(
            path, repo_root=repo_root
        ):
            warnings.append(UNVERIFIED_LANE_START_PACKET_WARNING.format(path=path))

    if starter_matches and not packet_matches and not exception_matches:
        errors.append("Lane Start Provenance starter is supplemental and cannot be used alone.")

    invalid_starters = [
        match.group("path").strip().strip("`")
        for match in starter_matches
        if match.group("path").strip().strip("`") != LANE_STARTER_PATH
    ]
    if invalid_starters:
        errors.append(
            "Lane Start Provenance starter must be "
            f"`{LANE_STARTER_PATH}`: " + ", ".join(invalid_starters)
        )

    invalid_exceptions = [
        match.group("reason")
        for match in exception_matches
        if not _valid_lane_start_exception_reason(match.group("reason"))
    ]
    if invalid_exceptions:
        errors.append(
            "Lane Start Provenance exception must be limited to trivial docs cleanup, "
            "main cleanup, cache cleanup, or operator-declared emergency infrastructure repair."
        )

    if FORBIDDEN_PREFLIGHT_AUTHORITY_RE.search(section):
        errors.append(
            "Lane Start Provenance must not cite host/Codex/Cursor/raw preflight as authority; "
            "use repo `check_preflight.py`, `task_bootstrap.py`, or `start_pr_lane.sh` evidence."
        )

    if not packet_matches and not starter_matches and not exception_matches:
        errors.append(
            "Lane Start Provenance must include `Packet: ...` or "
            "`Exception: <reason>`; `Starter: ...` is supplemental."
        )

    return errors, warnings


def _experiment_runner_artifact_paths(text: str) -> list[str]:
    """Return valid local Experiment Runner artifact paths referenced by text."""

    section = _extract_section_by_h2(
        _strip_fenced_code_blocks(text), str(PHASE2_CONFIG["experiment_runner_heading"])
    )
    if not section:
        return []

    paths: list[str] = []
    for match in EXPERIMENT_RUNNER_ARTIFACT_RE.finditer(section):
        path = match.group("path").strip().strip("`")
        if _valid_experiment_runner_artifact_path(path):
            paths.append(path)
    return list(dict.fromkeys(paths))


def _required_experiment_runner_artifact_errors(
    artifact_paths: list[str],
    *,
    repo_root: Path,
) -> list[str]:
    """Return fail-closed required-mode errors for unverifiable runner artifacts."""

    errors: list[str] = []
    resolved_repo_root = repo_root.resolve()
    for artifact_path in artifact_paths:
        absolute_path = repo_root / artifact_path
        try:
            resolved_path = absolute_path.resolve(strict=True)
            resolved_path.relative_to(resolved_repo_root)
        except (OSError, RuntimeError, ValueError):
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` is referenced but unavailable locally."
            )
            continue
        if not resolved_path.is_file():
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` is referenced but unavailable locally."
            )
            continue
        try:
            payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` is referenced but cannot be read."
            )
            continue
        except json.JSONDecodeError:
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` is referenced but cannot be parsed as JSON."
            )
            continue
        if not isinstance(payload, dict):
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` must be a JSON object result artifact."
            )
            continue
        try:
            result = validate_experiment_result(payload)
        except ValueError as exc:
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` has invalid result metadata: {exc}"
            )
            continue
        if result["status"] != "accepted":
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` is not accepted evidence: status={result['status']}."
            )
            continue
        if not result["oracle_results"]:
            errors.append(
                "Required: Experiment Runner artifact "
                f"`{artifact_path}` is not accepted evidence: oracle_results is empty."
            )
    return errors


def check_experiment_runner_evidence(
    text: str,
    *,
    mode: ExperimentRunnerEvidenceMode = ExperimentRunnerEvidenceMode.ADVISORY,
    missing_section_is_warning: bool = False,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[str], list[str]]:
    """Validate Experiment Runner evidence.

    Missing evidence is a warning in advisory mode and an error in required
    mode. Malformed evidence is always an error because invalid paths or empty
    N/A reasons create false governance proof.
    """

    cleaned = _strip_fenced_code_blocks(text)
    section = _extract_section_by_h2(cleaned, str(PHASE2_CONFIG["experiment_runner_heading"]))
    if not section:
        if missing_section_is_warning:
            return [], [MISSING_EXPERIMENT_RUNNER_EVIDENCE_WARNING]
        if mode is ExperimentRunnerEvidenceMode.REQUIRED:
            return [
                MISSING_EXPERIMENT_RUNNER_EVIDENCE_WARNING.replace("Advisory:", "Required:")
            ], []
        return [], [MISSING_EXPERIMENT_RUNNER_EVIDENCE_WARNING]

    artifact_matches = list(EXPERIMENT_RUNNER_ARTIFACT_RE.finditer(section))
    na_matches = list(EXPERIMENT_RUNNER_NA_RE.finditer(section))
    errors: list[str] = []

    if artifact_matches and na_matches:
        errors.append(
            "Experiment Runner Evidence must use either Artifact or Not applicable, not both."
        )

    if artifact_matches:
        artifact_paths = [match.group("path") for match in artifact_matches]
        invalid_paths = [
            path for path in artifact_paths if not _valid_experiment_runner_artifact_path(path)
        ]
        if invalid_paths:
            errors.append(
                "Experiment Runner artifact path must stay under "
                f"`{EXPERIMENT_RUNNER_ARTIFACT_PREFIX}` and end with `.json`: "
                + ", ".join(invalid_paths)
            )
        if mode is ExperimentRunnerEvidenceMode.REQUIRED:
            required_paths = [path for path in artifact_paths if path not in invalid_paths]
            errors.extend(
                _required_experiment_runner_artifact_errors(required_paths, repo_root=repo_root)
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


def _validate_git_commit_range_arg(value: str, *, arg_name: str) -> str:
    """Reject values that could be parsed as git options instead of ranges."""

    if value.startswith("-"):
        raise argparse.ArgumentTypeError(
            f"{arg_name} must be a git revision range/ref and cannot start with '-'."
        )
    return value


def _git_commit_messages(
    commit_range: str = "origin/main..HEAD",
    *,
    fallback_range: str = "",
) -> str | None:
    """Read branch commit messages, or None when local inspection is unavailable."""

    git_bin = shutil.which("git")
    if git_bin is None:
        return None

    ranges = [commit_range]
    if fallback_range and fallback_range != commit_range:
        ranges.append(fallback_range)
    for resolved_range in ranges:
        try:
            completed = subprocess.run(  # nosec B603: absolute git binary, fixed log command, no shell (remove-by: 2026-07-31, ref: experiment-runner-oracle-attribution-semantics)
                [
                    git_bin,
                    "log",
                    f"--format=%B{COMMIT_MESSAGE_SEPARATOR}",
                    "--end-of-options",
                    resolved_range,
                    "--",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode == 0:
            return completed.stdout
    return None


def _commit_message_has_expected_coauthor_trailer(message: str) -> bool:
    git_bin = shutil.which("git")
    if git_bin is None:
        return False
    try:
        completed = subprocess.run(  # nosec B603: absolute git binary parses local commit-message text without shell (remove-by: 2026-07-31, ref: experiment-runner-oracle-attribution-semantics)
            [git_bin, "interpret-trailers", "--parse", "--no-divider"],
            cwd=REPO_ROOT,
            input=message,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode != 0:
        return False
    return any(line.strip() == EXPECTED_CO_AUTHOR_TRAILER for line in completed.stdout.splitlines())


def _commit_messages_have_expected_coauthor_trailer(commit_messages: str) -> bool:
    return any(
        _commit_message_has_expected_coauthor_trailer(message)
        for message in commit_messages.split(COMMIT_MESSAGE_SEPARATOR)
    )


def check_experiment_runner_coauthor_advisory(
    text: str,
    *,
    commit_messages: str | None,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Warn when a local runner artifact requires co-authoring but commits lack it."""

    has_expected_trailer = commit_messages is not None and (
        _commit_messages_have_expected_coauthor_trailer(commit_messages)
    )

    warnings: list[str] = []
    resolved_repo_root = repo_root.resolve()
    for artifact_path in _experiment_runner_artifact_paths(text):
        absolute_path = repo_root / artifact_path
        try:
            resolved_path = absolute_path.resolve(strict=True)
            resolved_path.relative_to(resolved_repo_root)
        except (OSError, RuntimeError, ValueError):
            warnings.append(
                UNVERIFIED_EXPERIMENT_RUNNER_ARTIFACT_WARNING.format(path=artifact_path)
            )
            continue
        if not resolved_path.is_file():
            warnings.append(
                UNVERIFIED_EXPERIMENT_RUNNER_ARTIFACT_WARNING.format(path=artifact_path)
            )
            continue
        try:
            payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            warnings.append(
                UNVERIFIED_EXPERIMENT_RUNNER_ARTIFACT_WARNING.format(path=artifact_path)
            )
            continue
        if not isinstance(payload, dict):
            warnings.append(
                INVALID_EXPERIMENT_RUNNER_ARTIFACT_METADATA_WARNING.format(path=artifact_path)
            )
            continue
        status = payload.get("status")
        try:
            _, coauthor_required, reason = validate_contribution_attribution(
                contribution_kind=payload.get("contribution_kind", "none"),
                coauthor_required=payload.get("coauthor_required", False),
                coauthor_reason=payload.get("coauthor_reason", ""),
                status=status if isinstance(status, str) else None,
            )
        except ValueError:
            warnings.append(
                INVALID_EXPERIMENT_RUNNER_ARTIFACT_METADATA_WARNING.format(path=artifact_path)
            )
            continue
        if coauthor_required and not has_expected_trailer:
            if commit_messages is None:
                warning = (
                    "Advisory: branch commit messages could not be inspected locally, "
                    "so the Experiment Runner co-author trailer was not verified for "
                    f"`{artifact_path}`."
                )
            else:
                warning = MISSING_EXPERIMENT_RUNNER_COAUTHOR_WARNING.format(path=artifact_path)
            if reason:
                warning = f"{warning} Reason: {reason}"
            warnings.append(warning)
    return warnings


def _required_experiment_runner_artifact_warning_to_error(warning: str) -> str | None:
    """Promote artifact-unverifiable advisories to required-mode hard errors."""

    if not warning.startswith("Advisory: Experiment Runner artifact `"):
        return None
    if " unavailable locally" in warning or " invalid co-author metadata" in warning:
        return warning.replace("Advisory:", "Required:", 1)
    return None


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
    cleaned = _normalize_phase2_body(body)

    d_heading = f"## {PHASE2_CONFIG['discussion_heading']}"
    m_heading = f"### {PHASE2_CONFIG['mapping_heading']}"
    discussion_sections = list(DISCUSSION_SECTION_RE.finditer(cleaned))
    mapping_sections = list(MAPPING_SECTION_RE.finditer(cleaned))
    discussion_checks = list(DISCUSSION_CHECKBOX_RE.finditer(cleaned))
    mapping_checks = list(MAPPING_CHECKBOX_RE.finditer(cleaned))
    if not discussion_sections:
        errors.append(f"Missing required section: `{d_heading}`.")
    elif len(discussion_sections) > 1:
        errors.append(f"Duplicate required section: `{d_heading}`.")
    if not mapping_sections:
        errors.append(f"Missing required section: `{m_heading}`.")
    elif len(mapping_sections) > 1:
        errors.append(f"Duplicate required section: `{m_heading}`.")

    discussion_check = discussion_checks[0] if discussion_checks else None
    mapping_check = mapping_checks[0] if mapping_checks else None
    for checks, label in (
        (discussion_checks, str(PHASE2_CONFIG["discussion_checkbox_label"])),
        (mapping_checks, str(PHASE2_CONFIG["mapping_checkbox_label"])),
    ):
        if len(checks) > 1:
            errors.append(f"Duplicate checklist item: `{label}`.")

    if mode is BodyValidationMode.PRE_CLOSEOUT:
        if not PRE_CLOSEOUT_MARKER_RE.search(cleaned):
            errors.append(
                "Pre-closeout requires the exact marker: " f"`<!-- {_PRE_CLOSEOUT_MARKER} -->`."
            )
        for check, label in (
            (discussion_check, str(PHASE2_CONFIG["discussion_checkbox_label"])),
            (mapping_check, str(PHASE2_CONFIG["mapping_checkbox_label"])),
        ):
            if check is None:
                errors.append(f"Missing checklist item: `{label}`.")
            elif _extract_checked(check):
                errors.append(
                    "Pre-closeout checklist item must remain unchecked until the "
                    f"canonical mapping/seal is published: `{label}`."
                )
        mapping_section = _extract_mapping_section(cleaned)
        if not PRE_CLOSEOUT_PENDING_RE.search(mapping_section):
            errors.append(
                "Pre-closeout mapping section must declare the exact pending final scan "
                "and single mapping/closeout commit status."
            )
        if (
            MAPPING_ENTRY_RE.search(mapping_section)
            or THREAD_ENTRY_RE.search(mapping_section)
            or MAPPING_NA_RE.search(mapping_section)
        ):
            errors.append(
                "Pre-closeout mapping section must not contain completed mapping entries."
            )
    else:
        if PRE_CLOSEOUT_MARKER_RE.search(cleaned):
            errors.append(
                "Pre-closeout marker must be removed after the canonical mapping/seal is "
                "published."
            )
        if PRE_CLOSEOUT_PENDING_RE.search(cleaned):
            errors.append(
                "Pre-closeout pending status must be removed after the canonical mapping/seal "
                "is published."
            )
        if not _extract_checked(discussion_check):
            errors.append(
                f"Checklist item must be checked: `{PHASE2_CONFIG['discussion_checkbox_label']}`."
            )
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
        type=lambda value: _validate_git_commit_range_arg(value, arg_name="--commit-range"),
        default="origin/main..HEAD",
        help=(
            "Git commit range for advisory Experiment Runner co-author diagnostics. "
            "Defaults to origin/main..HEAD."
        ),
    )
    parser.add_argument(
        "--commit-range-fallback",
        type=lambda value: (
            _validate_git_commit_range_arg(value, arg_name="--commit-range-fallback")
            if value != ""
            else value
        ),
        default="",
        help=(
            "Fallback git commit range for advisory Experiment Runner co-author "
            "diagnostics when --commit-range is unavailable. Empty by default so "
            "detached or shallow checkouts report the trailer check as unverifiable "
            "instead of scanning unrelated history."
        ),
    )
    parser.add_argument(
        "--experiment-runner-evidence-mode",
        default=os.environ.get(
            "PULSEPLATE_EXPERIMENT_RUNNER_EVIDENCE_MODE",
            ExperimentRunnerEvidenceMode.ADVISORY.value,
        ),
        help=(
            "Experiment Runner Evidence enforcement mode: advisory (default) or required. "
            "Can also be set with PULSEPLATE_EXPERIMENT_RUNNER_EVIDENCE_MODE."
        ),
    )
    args = parser.parse_args()
    try:
        args.experiment_runner_evidence_mode = _experiment_runner_evidence_mode(
            args.experiment_runner_evidence_mode
        )
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    body = args.body
    if not body and args.event_path:
        body = _extract_pr_body(Path(args.event_path))
    pre_closeout_requested = _has_pre_closeout_marker(body)

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
    lane_start_warning_candidates: list[str] = []
    lane_start_seen = False

    if pr_number is not None:
        try:
            artifact_text = read_mapping_artifact(pr_number)
        except FileNotFoundError as exc:
            if not pre_closeout_requested:
                print(f"ERROR: {exc}")
                return 1
            advisory_warnings.append(
                "Pre-closeout: canonical mapping artifact is intentionally pending final "
                "material review/security scan; merge readiness remains blocked."
            )
        else:
            artifact_checked = True
            artifact_errors.extend(validate_mapping_artifact_text(artifact_text))
            evidence_texts.append(artifact_text)
            evidence_errors, evidence_warnings = check_experiment_runner_evidence(
                artifact_text,
                mode=args.experiment_runner_evidence_mode,
                missing_section_is_warning=True,
            )
            artifact_errors.extend(evidence_errors)
            evidence_warning_candidates.extend(evidence_warnings)
            if not evidence_errors and not evidence_warnings:
                experiment_runner_evidence_seen = True
            lane_errors, lane_warnings = check_lane_start_provenance(artifact_text)
            artifact_errors.extend(lane_errors)
            lane_start_warning_candidates.extend(lane_warnings)
            if _lane_start_source_seen(lane_errors, lane_warnings):
                lane_start_seen = True

    if body.strip():
        cleaned_body = _normalize_phase2_body(body)
        has_pre_closeout_marker = bool(PRE_CLOSEOUT_MARKER_RE.search(cleaned_body))
        has_phase2_mirror = bool(
            DISCUSSION_SECTION_RE.search(cleaned_body) or MAPPING_SECTION_RE.search(cleaned_body)
        )
        has_experiment_runner_evidence = bool(
            _extract_section_by_h2(cleaned_body, str(PHASE2_CONFIG["experiment_runner_heading"]))
        )
        has_lane_start_provenance = bool(
            _extract_section_by_h2(cleaned_body, str(PHASE2_CONFIG["lane_start_heading"]))
        )
        if not artifact_checked or has_phase2_mirror or has_pre_closeout_marker:
            body_checked = True
            body_mode = (
                BodyValidationMode.PRE_CLOSEOUT
                if not artifact_checked and pre_closeout_requested
                else _select_body_validation_mode(artifact_checked=artifact_checked)
            )
            body_errors.extend(
                check_pr_body_phase2_gates(
                    body=body,
                    mode=body_mode,
                )
            )
        if not artifact_checked or has_experiment_runner_evidence:
            evidence_texts.append(body)
            evidence_errors, evidence_warnings = check_experiment_runner_evidence(
                body,
                mode=args.experiment_runner_evidence_mode,
                missing_section_is_warning=True,
            )
            if evidence_errors:
                body_checked = True
            body_errors.extend(evidence_errors)
            evidence_warning_candidates.extend(evidence_warnings)
            if not evidence_errors and not evidence_warnings:
                experiment_runner_evidence_seen = True
        if not artifact_checked or has_lane_start_provenance:
            lane_errors, lane_warnings = check_lane_start_provenance(body)
            if lane_errors:
                body_checked = True
            body_errors.extend(lane_errors)
            lane_start_warning_candidates.extend(lane_warnings)
            if _lane_start_source_seen(lane_errors, lane_warnings):
                lane_start_seen = True
    elif not artifact_checked:
        print("ERROR: Empty PR body. Fill the required Phase2 checklist sections.")
        return 1

    if not experiment_runner_evidence_seen:
        missing_evidence = list(dict.fromkeys(evidence_warning_candidates))
        if args.experiment_runner_evidence_mode is ExperimentRunnerEvidenceMode.REQUIRED:
            artifact_errors.extend(
                warning.replace("Advisory:", "Required:") for warning in missing_evidence
            )
        else:
            advisory_warnings.extend(missing_evidence)
    if experiment_runner_evidence_seen:
        commit_messages = _git_commit_messages(
            args.commit_range,
            fallback_range=args.commit_range_fallback,
        )
        for evidence_text in evidence_texts:
            advisory_warnings.extend(
                check_experiment_runner_coauthor_advisory(
                    evidence_text,
                    commit_messages=commit_messages,
                )
            )
        advisory_warnings = list(dict.fromkeys(advisory_warnings))
        if args.experiment_runner_evidence_mode is ExperimentRunnerEvidenceMode.REQUIRED:
            promoted_artifact_errors = [
                promoted
                for warning in advisory_warnings
                if (promoted := _required_experiment_runner_artifact_warning_to_error(warning))
                is not None
            ]
            if promoted_artifact_errors:
                artifact_errors.extend(promoted_artifact_errors)
                advisory_warnings = [
                    warning
                    for warning in advisory_warnings
                    if _required_experiment_runner_artifact_warning_to_error(warning) is None
                ]
    advisory_warnings.extend(
        dict.fromkeys(_lane_start_non_missing_warnings(lane_start_warning_candidates))
    )
    if not lane_start_seen:
        advisory_warnings.extend(
            dict.fromkeys(_lane_start_missing_warnings(lane_start_warning_candidates))
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
    if pre_closeout_requested:
        print(
            "phase2-pr-body-gates: explicit non-mergeable pre-closeout state passed; "
            "canonical mapping artifact remains required for merge."
        )
        return 0

    print("phase2-pr-body-gates: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
