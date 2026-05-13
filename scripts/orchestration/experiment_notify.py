#!/usr/bin/env python3
"""Render safe, artifact-only notifications for governed experiment results.

RU: Пишет локальный markdown summary для experiment result без внешней доставки.
EN: Writes a local markdown summary for experiment results without external delivery.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sys
from typing import Any

try:
    from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
    from scripts.orchestration.experiment_contract import (
        PROMOTION_TARGETS,
        SCHEMA_VERSION,
        validate_experiment_id,
        validate_experiment_packet,
        validate_experiment_result,
    )
except ImportError:  # pragma: no cover - CLI fallback for direct script execution.
    experiment_notify_repo_root = Path(__file__).resolve().parents[2]
    if str(experiment_notify_repo_root) not in sys.path:
        sys.path.insert(0, str(experiment_notify_repo_root))
    from scripts.orchestration.context_pack import REPO_ROOT, normalize_repo_path
    from scripts.orchestration.experiment_contract import (
        PROMOTION_TARGETS,
        SCHEMA_VERSION,
        validate_experiment_id,
        validate_experiment_packet,
        validate_experiment_result,
    )


NOTIFICATION_ARTIFACT_DIR = (
    REPO_ROOT / "artifacts" / "orchestration" / "experiments" / "notifications"
)
PROMOTION_DISPOSITIONS: tuple[str, ...] = ("promoted", "deferred")
SENSITIVE_PATH_PART_RE = re.compile(r"(secret|token|password|private|credential|key)", re.I)


class ExperimentNotificationError(RuntimeError):
    """Base error for notification rendering contract violations."""


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return payload


def _resolve_output_path(raw_output: str | None, experiment_id: str) -> Path:
    if raw_output:
        candidate = Path(raw_output)
        if not candidate.is_absolute():
            candidate = NOTIFICATION_ARTIFACT_DIR / candidate
    else:
        candidate = NOTIFICATION_ARTIFACT_DIR / f"{experiment_id}.md"
    candidate = candidate.resolve()
    try:
        candidate.relative_to(NOTIFICATION_ARTIFACT_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "--output must stay within artifacts/orchestration/experiments/notifications"
        ) from exc
    return candidate


def _require_matching_experiment(
    packet: dict[str, Any],
    result: dict[str, Any],
    promotion: dict[str, Any] | None,
) -> None:
    if packet["experiment_id"] != result["experiment_id"]:
        raise ExperimentNotificationError(
            "Experiment packet and result must reference the same experiment_id."
        )
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


def _validate_promotion_decision(payload: dict[str, Any]) -> dict[str, Any]:
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
    text = str(value).strip()
    if not text:
        return "none"
    return text.replace("`", "'")


def _safe_repo_path(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return "none"
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or any(part == ".." for part in path.parts)
        or any(SENSITIVE_PATH_PART_RE.search(part) for part in path.parts)
    ):
        return "[redacted-path]"
    return _safe_inline(path.as_posix())


def _oracle_command_name(command: Any) -> str:
    try:
        argv = shlex.split(str(command))
    except ValueError:
        return "[unparseable-command]"
    if not argv:
        return "[empty-command]"
    binary = argv[0]
    if "/" in binary or "\\" in binary:
        return _safe_inline(Path(binary).name)
    return _safe_inline(binary)


def _oracle_lines(result: dict[str, Any]) -> list[str]:
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
        raise ExperimentNotificationError(f"Unable to write GITHUB_STEP_SUMMARY: {exc}") from exc


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
    except (OSError, ExperimentNotificationError) as exc:
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
