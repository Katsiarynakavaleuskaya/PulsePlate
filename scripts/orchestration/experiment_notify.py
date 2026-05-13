#!/usr/bin/env python3
"""Render safe, artifact-only notifications for governed experiment results.

RU: Пишет локальный markdown summary для experiment result без внешней доставки.
EN: Writes a local markdown summary for experiment results without external delivery.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shlex
import sys
from typing import Any

try:
    from scripts.orchestration.context_pack import (
        REPO_ROOT,
        normalize_repo_path,
        repo_relative_paths,
    )
    from scripts.orchestration.experiment_contract import (
        PROMOTION_TARGETS,
        SCHEMA_VERSION,
        validate_experiment_id,
        validate_experiment_packet,
        validate_experiment_result,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - direct script invocation guard.
    if exc.name != "scripts":
        raise
    print(
        "FAIL: run as `python -m scripts.orchestration.experiment_notify` from repo root.",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


NOTIFICATION_ARTIFACT_DIR = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "notifications"
)
PROMOTION_DISPOSITIONS: tuple[str, ...] = ("promoted", "deferred")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
SENSITIVE_PATH_PART_RE = re.compile(
    r"(secret|token|password|private|credential|key|\.ssh|id_rsa|id_dsa|id_ecdsa|id_ed25519|\.aws|\.gnupg|\.kube)",
    re.I,
)
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r'^(?:"?[A-Za-z]:|"?\\\\|"?//)')
SHELL_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
FILE_LIKE_SURFACE_SUFFIXES = {
    ".cfg",
    ".conf",
    ".ini",
    ".json",
    ".lock",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


class ExperimentNotificationError(RuntimeError):
    """Base error for notification rendering contract violations."""


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load {label} JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return payload


def _resolve_output_path(raw_output: str | None, experiment_id: str) -> Path:
    """Resolve a notification output path inside the local artifacts directory."""

    artifact_dir = NOTIFICATION_ARTIFACT_DIR.absolute()
    if raw_output:
        candidate = Path(raw_output)
        if any(part == ".." for part in candidate.parts):
            raise ValueError(
                "--output must stay within artifacts/orchestration/experiments/notifications"
            )
        if not candidate.is_absolute():
            candidate = artifact_dir / candidate
    else:
        candidate = artifact_dir / f"{experiment_id}.md"
    candidate = candidate.absolute()
    try:
        candidate.relative_to(artifact_dir)
    except ValueError as exc:
        raise ValueError(
            "--output must stay within artifacts/orchestration/experiments/notifications"
        ) from exc
    _reject_symlinked_output_components(candidate, artifact_dir=artifact_dir)
    return candidate


def _reject_symlinked_output_components(candidate: Path, *, artifact_dir: Path) -> None:
    """Reject writes through existing symlinks in the notification artifact path."""

    repo_artifact_root = REPO_ROOT.absolute() / "artifacts"
    artifact_dir.relative_to(repo_artifact_root)
    current = repo_artifact_root
    if current.is_symlink():
        raise ValueError("notification artifact ancestors must not be symlinks.")
    for part in artifact_dir.relative_to(repo_artifact_root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("notification artifact ancestors must not be symlinks.")
    if artifact_dir.is_symlink():
        raise ValueError("notification artifact directory must not be a symlink.")
    current = artifact_dir
    for part in candidate.relative_to(artifact_dir).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("notification output path must not traverse a symlink.")


def _require_matching_experiment(
    packet: dict[str, Any],
    result: dict[str, Any],
    promotion: dict[str, Any] | None,
) -> None:
    """Require packet, result, and optional promotion metadata to describe one run."""

    if packet["experiment_id"] != result["experiment_id"]:
        raise ExperimentNotificationError(
            "Experiment packet and result must reference the same experiment_id."
        )
    _require_result_evidence_matches_packet(packet, result)
    if promotion is not None and packet["experiment_id"] != promotion.get("experiment_id"):
        raise ExperimentNotificationError(
            "Experiment packet and promotion must reference the same experiment_id."
        )
    if promotion is None:
        return
    if promotion["promotion_target"] != packet["promotion_target"]:
        raise ExperimentNotificationError(
            "Promotion decision target must match experiment packet promotion_target."
        )
    if promotion["result_status"] != result["status"]:
        raise ExperimentNotificationError(
            "Promotion decision result_status must match experiment result status."
        )
    if promotion["failure_class"] != result["failure_class"]:
        raise ExperimentNotificationError(
            "Promotion decision failure_class must match experiment result failure_class."
        )
    if promotion["shared_tree_untouched"] != result["shared_tree_untouched"]:
        raise ExperimentNotificationError(
            "Promotion decision shared_tree_untouched must match experiment result."
        )
    _require_promotion_evidence_matches_result(packet, result, promotion)
    if (
        result["status"] == "accepted"
        and promotion["disposition"] == "promoted"
        and not result["shared_tree_untouched"]
    ):
        raise ExperimentNotificationError(
            "Accepted result is not promotable when shared_tree_untouched is false."
        )
    if result["status"] == "accepted" and promotion["disposition"] != "promoted":
        raise ExperimentNotificationError(
            "Accepted experiment results must have promotion disposition promoted."
        )
    if result["status"] == "rejected":
        if packet["promotion_target"] != "backlog_entry":
            raise ExperimentNotificationError(
                "Rejected experiment results may notify only backlog_entry promotions."
            )
        if promotion["disposition"] != "deferred":
            raise ExperimentNotificationError(
                "Rejected experiment results must have promotion disposition deferred."
            )


def _require_result_evidence_matches_packet(
    packet: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Fail closed when result evidence is stale or outside the packet contract."""

    mutable_surface = set(packet["mutable_candidate_surface"])
    outside_surface = sorted(
        _safe_repo_path(path)
        for path in result["mutated_paths"]
        if not _mutable_surface_contains_path(mutable_surface, path)
    )
    if outside_surface:
        joined = ", ".join(outside_surface)
        raise ExperimentNotificationError(
            "Experiment result mutated_paths must stay within packet "
            f"mutable_candidate_surface: {joined}"
        )

    expected_oracles = [oracle["command"] for oracle in packet["immutable_oracles"]]
    result_oracles = [oracle_result["command"] for oracle_result in result["oracle_results"]]
    unexpected_oracles = sorted(set(result_oracles) - set(expected_oracles))
    if unexpected_oracles:
        joined = ", ".join(_oracle_command_name(command) for command in unexpected_oracles)
        raise ExperimentNotificationError(
            f"Experiment result oracle_results include commands outside packet: {joined}"
        )
    if result["status"] == "accepted" and result_oracles != expected_oracles:
        raise ExperimentNotificationError(
            "Accepted experiment result oracle_results must match packet immutable_oracles."
        )
    if result["status"] == "rejected":
        _require_rejected_oracles_are_prefix(expected_oracles, result_oracles)
        if result["oracle_results"]:
            terminal_oracle = result["oracle_results"][-1]
            if terminal_oracle["returncode"] == 0 and not terminal_oracle["timed_out"]:
                raise ExperimentNotificationError(
                    "Rejected experiment result terminal oracle must fail or time out."
                )
    if result["status"] == "accepted":
        if result["failure_class"] is not None:
            raise ExperimentNotificationError(
                "Accepted experiment result failure_class must be null."
            )
        failed_oracles = [
            _oracle_command_name(oracle_result["command"])
            for oracle_result in result["oracle_results"]
            if oracle_result["returncode"] != 0 or oracle_result["timed_out"]
        ]
        if failed_oracles:
            joined = ", ".join(failed_oracles)
            raise ExperimentNotificationError(
                f"Accepted experiment result oracle_results must pass: {joined}"
            )


def _mutable_surface_contains_path(mutable_surface: set[str], path: str) -> bool:
    """Return whether a result path belongs to the packet mutable surface."""

    for surface in mutable_surface:
        if path == surface:
            return True
        if _surface_allows_nested_paths(surface) and path.startswith(f"{surface.rstrip('/')}/"):
            return True
    return False


def _surface_allows_nested_paths(surface: str) -> bool:
    """Return whether a mutable surface entry should match nested result paths."""

    if surface.endswith("/"):
        return True
    if Path(REPO_ROOT, surface).is_file():
        return False
    if PurePosixPath(surface).suffix.lower() in FILE_LIKE_SURFACE_SUFFIXES:
        return False
    return True


def _require_rejected_oracles_are_prefix(
    expected_oracles: list[str],
    result_oracles: list[str],
) -> None:
    """Require rejected results to describe a prefix of the immutable oracle list."""

    if result_oracles != expected_oracles[: len(result_oracles)]:
        raise ExperimentNotificationError(
            "Rejected experiment result oracle_results must be a packet immutable_oracles prefix."
        )


def _require_promotion_evidence_matches_result(
    packet: dict[str, Any],
    result: dict[str, Any],
    promotion: dict[str, Any],
) -> None:
    """Require promotion evidence to describe the same packet/result pair."""

    evidence = promotion["evidence"]
    expected_oracles = [oracle["command"] for oracle in packet["immutable_oracles"]]
    if evidence["oracle_commands"] != expected_oracles:
        raise ExperimentNotificationError(
            "Promotion decision evidence.oracle_commands must match packet immutable_oracles."
        )
    if evidence["mutated_paths"] != result["mutated_paths"]:
        raise ExperimentNotificationError(
            "Promotion decision evidence.mutated_paths must match experiment result."
        )
    if evidence["oracle_count"] != len(result["oracle_results"]):
        raise ExperimentNotificationError(
            "Promotion decision evidence.oracle_count must match experiment result."
        )


def _validate_promotion_decision(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the subset of promotion decision metadata safe to summarize."""

    schema_version = str(payload.get("schema_version", "")).strip()
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"Promotion decision schema_version must equal {SCHEMA_VERSION!r}, "
            f"got {schema_version!r}."
        )
    experiment_id = validate_experiment_id(
        payload.get("experiment_id", ""),
        label="Promotion decision",
    )
    normalized = dict(payload)
    normalized["schema_version"] = schema_version
    normalized["experiment_id"] = experiment_id
    normalized["promotion_target"] = str(payload.get("promotion_target", "")).strip()
    normalized["disposition"] = str(payload.get("disposition", "")).strip()
    normalized["durable_artifact_path"] = str(payload.get("durable_artifact_path", "")).strip()
    normalized["result_status"] = str(payload.get("result_status", "")).strip()
    normalized["failure_class"] = payload.get("failure_class")
    shared_tree_untouched = payload.get("shared_tree_untouched")
    evidence = payload.get("evidence")
    if normalized["promotion_target"] not in PROMOTION_TARGETS:
        allowed = ", ".join(PROMOTION_TARGETS)
        raise ValueError(f"Promotion decision promotion_target must be one of: {allowed}")
    if normalized["disposition"] not in PROMOTION_DISPOSITIONS:
        allowed = ", ".join(PROMOTION_DISPOSITIONS)
        raise ValueError(f"Promotion decision disposition must be one of: {allowed}")
    if normalized["result_status"] not in {"accepted", "rejected"}:
        raise ValueError("Promotion decision result_status must be accepted or rejected.")
    if normalized["failure_class"] is not None:
        normalized["failure_class"] = str(normalized["failure_class"]).strip()
    if not isinstance(shared_tree_untouched, bool):
        raise ValueError("Promotion decision shared_tree_untouched must be a boolean.")
    normalized["shared_tree_untouched"] = shared_tree_untouched
    if not isinstance(evidence, dict):
        raise ValueError("Promotion decision evidence must be an object.")
    oracle_commands = evidence.get("oracle_commands")
    mutated_paths = evidence.get("mutated_paths")
    oracle_count = evidence.get("oracle_count")
    if not isinstance(oracle_commands, list) or not all(
        isinstance(command, str) for command in oracle_commands
    ):
        raise ValueError("Promotion decision evidence.oracle_commands must be a string list.")
    if not isinstance(mutated_paths, list) or not all(
        isinstance(path, str) for path in mutated_paths
    ):
        raise ValueError("Promotion decision evidence.mutated_paths must be a string list.")
    if not isinstance(oracle_count, int):
        raise ValueError("Promotion decision evidence.oracle_count must be an integer.")
    normalized["evidence"] = {
        "oracle_commands": list(oracle_commands),
        "mutated_paths": repo_relative_paths(mutated_paths),
        "oracle_count": oracle_count,
    }
    durable_artifact_path = normalized["durable_artifact_path"]
    durable_path = PurePosixPath(durable_artifact_path)
    if (
        not durable_artifact_path
        or durable_path.is_absolute()
        or any(part == ".." for part in durable_path.parts)
    ):
        raise ValueError("Promotion decision durable_artifact_path must be repo-relative.")
    _validate_durable_artifact_path_for_target(
        experiment_id=experiment_id,
        promotion_target=normalized["promotion_target"],
        durable_artifact_path=durable_artifact_path,
    )
    return normalized


def _validate_durable_artifact_path_for_target(
    *,
    experiment_id: str,
    promotion_target: str,
    durable_artifact_path: str,
) -> None:
    """Require durable artifact paths to match the declared promotion target."""

    upper_id = experiment_id.upper().replace("-", "_")
    expected_paths = {
        "pr_packet": f"docs/orchestration/experiment_pr_packets/{experiment_id}.md",
        "audit_artifact": f"docs/audit/EXPERIMENT_{upper_id}.md",
        "guard_test_proposal": f"docs/orchestration/experiment_guard_proposals/{experiment_id}.md",
        "backlog_entry": "docs/roadmap/BACKLOG_LEDGER.md",
        "memory_capsule": f"docs/memory/{experiment_id}_capsule.md",
    }
    expected = expected_paths.get(promotion_target)
    if expected is None or durable_artifact_path != expected:
        raise ValueError("Promotion decision durable_artifact_path must match promotion_target.")


def _safe_inline(value: Any) -> str:
    """Render a scalar markdown inline value without backtick injection."""

    text = CONTROL_CHAR_RE.sub(" ", str(value)).strip()
    if not text:
        return "none"
    return text.replace("`", "'")


def _safe_repo_path(value: Any) -> str:
    """Render a repo-relative path or redact unsafe path-shaped values."""

    text = str(value).strip()
    if not text:
        return "none"
    if CONTROL_CHAR_RE.search(text) or text.startswith("~"):
        return "[redacted-path]"
    if WINDOWS_ABSOLUTE_PATH_RE.match(text) or "\\" in text:
        return "[redacted-path]"
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or any(part == ".." for part in path.parts)
        or any(SENSITIVE_PATH_PART_RE.search(part) for part in path.parts)
    ):
        return "[redacted-path]"
    return _safe_inline(path.as_posix())


def _oracle_command_name(command: Any) -> str:
    """Return only the executable name from an oracle command."""

    raw_command = str(command).strip()
    if WINDOWS_ABSOLUTE_PATH_RE.match(raw_command) or "\\" in raw_command:
        return "[redacted-command]"
    try:
        argv = shlex.split(raw_command)
    except ValueError:
        return "[unparseable-command]"
    if not argv:
        return "[empty-command]"
    while argv and SHELL_ENV_ASSIGNMENT_RE.match(argv[0]):
        argv.pop(0)
    if not argv:
        return "[redacted-command]"
    binary = argv[0]
    if WINDOWS_ABSOLUTE_PATH_RE.match(binary) or "\\" in binary:
        return "[redacted-command]"
    if "\\" in binary:
        return _safe_inline(PureWindowsPath(binary).name)
    if "/" in binary:
        if any(SENSITIVE_PATH_PART_RE.search(part) for part in PurePosixPath(binary).parts):
            return "[redacted-command]"
        return _safe_inline(Path(binary).name)
    return _safe_inline(binary)


def _oracle_lines(result: dict[str, Any]) -> list[str]:
    """Render safe oracle result summary lines."""

    lines: list[str] = []
    for oracle_result in result["oracle_results"]:
        lines.append(
            "- `"
            + _oracle_command_name(oracle_result["command"])
            + "` -> rc="
            + str(oracle_result["returncode"])
            + ", timed_out="
            + str(oracle_result["timed_out"]).lower()
            + ", truncated="
            + str(oracle_result["truncated"]).lower()
        )
    if not lines:
        lines.append("- No oracle commands executed.")
    return lines


def render_notification_markdown(
    packet: dict[str, Any],
    result: dict[str, Any],
    promotion: dict[str, Any] | None = None,
) -> str:
    """Render the stable, redacted markdown notification body."""

    _require_matching_experiment(packet, result, promotion)
    failure_class = result["failure_class"] if result["failure_class"] is not None else "none"
    mutated_paths = (
        "\n".join(f"- `{_safe_repo_path(path)}`" for path in result["mutated_paths"])
        if result["mutated_paths"]
        else "- No mutated paths recorded."
    )
    promotion_lines = [
        f"- Promotion target: `{_safe_inline(packet['promotion_target'])}`",
        "- Promotion disposition: `not-run`",
        "- Durable artifact: `none`",
    ]
    if promotion is not None:
        promotion_lines = [
            f"- Promotion target: `{_safe_inline(promotion['promotion_target'])}`",
            f"- Promotion disposition: `{_safe_inline(promotion['disposition'])}`",
            f"- Durable artifact: `{_safe_repo_path(promotion['durable_artifact_path'])}`",
        ]

    return (
        f"# Experiment Result Notification: {packet['experiment_id']}\n\n"
        f"- Result status: `{_safe_inline(result['status'])}`\n"
        f"- Failure class: `{_safe_inline(failure_class)}`\n"
        f"- Shared tree untouched: `{str(result['shared_tree_untouched']).lower()}`\n"
        f"{chr(10).join(promotion_lines)}\n\n"
        "## Mutated Paths\n\n"
        f"{mutated_paths}\n\n"
        "## Oracle Summary\n\n"
        f"{chr(10).join(_oracle_lines(result))}\n\n"
        "## Delivery Boundary\n\n"
        "- Artifact-only summary; no email, Slack, PR comment, or external delivery was sent.\n"
        "- Raw patch text, oracle stdout/stderr, cwd, and local absolute paths are intentionally omitted.\n"
    )


def _append_github_step_summary(markdown: str) -> None:
    """Append markdown to GitHub step summary only when explicitly requested."""

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not summary_path:
        raise ExperimentNotificationError(
            "--github-step-summary requires GITHUB_STEP_SUMMARY to be set."
        )
    try:
        with Path(summary_path).open("a", encoding="utf-8") as summary_file:
            summary_file.write(markdown)
            if not markdown.endswith("\n"):
                summary_file.write("\n")
    except OSError as exc:
        raise ExperimentNotificationError("Unable to write GITHUB_STEP_SUMMARY.") from exc


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI flags for artifact-only notification rendering."""

    parser = argparse.ArgumentParser(
        prog="experiment_notify",
        description="Render artifact-only notifications for governed experiment results.",
    )
    parser.add_argument("--packet", required=True, help="Experiment packet JSON path.")
    parser.add_argument("--result", required=True, help="Experiment result JSON path.")
    parser.add_argument("--promotion", default=None, help="Optional promotion decision JSON path.")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional notification markdown path under "
            "artifacts/orchestration/experiments/notifications/. "
            "Defaults to artifacts/orchestration/experiments/notifications/<id>.md"
        ),
    )
    parser.add_argument(
        "--github-step-summary",
        action="store_true",
        help="Also append the rendered markdown to GITHUB_STEP_SUMMARY when explicitly requested.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the notification renderer CLI."""

    args = _parse_args(argv)
    packet_path = Path(args.packet).expanduser().resolve()
    result_path = Path(args.result).expanduser().resolve()

    try:
        packet = validate_experiment_packet(
            _read_json_object(packet_path, label="experiment packet")
        )
        result = validate_experiment_result(
            _read_json_object(result_path, label="experiment result")
        )
        promotion = None
        if args.promotion:
            promotion = _validate_promotion_decision(
                _read_json_object(Path(args.promotion).expanduser().resolve(), label="promotion")
            )
        output_path = _resolve_output_path(args.output, packet["experiment_id"])
        markdown = render_notification_markdown(packet, result, promotion)
    except (ValueError, ExperimentNotificationError) as exc:
        print(f"FAIL: {exc}")
        return 1

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        if args.github_step_summary:
            _append_github_step_summary(markdown)
    except OSError:
        print("FAIL: unable to write experiment notification.")
        return 1
    except ExperimentNotificationError as exc:
        print(f"FAIL: unable to write experiment notification: {exc}")
        return 1

    print(
        json.dumps(
            {
                "experiment_id": packet["experiment_id"],
                "output": normalize_repo_path(output_path),
                "github_step_summary": bool(args.github_step_summary),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
