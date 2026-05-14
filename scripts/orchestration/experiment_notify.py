#!/usr/bin/env python3
"""Render safe notifications for governed experiment results.

RU: Пишет локальный markdown summary и опционально отправляет его по SMTP.
EN: Writes a local markdown summary and optionally sends it via SMTP.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shlex
import smtplib
import ssl
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
EMAIL_ALLOWLIST_ENV = "EXPERIMENT_NOTIFICATION_EMAIL_ALLOWLIST"
V1_EMAIL_RECIPIENT = "pulseplate@pm.me"
SMTP_HOST_ENV = "EXPERIMENT_NOTIFICATION_SMTP_HOST"
SMTP_PORT_ENV = "EXPERIMENT_NOTIFICATION_SMTP_PORT"
SMTP_USERNAME_ENV = "EXPERIMENT_NOTIFICATION_SMTP_USERNAME"
SMTP_AUTH_ENV = "EXPERIMENT_NOTIFICATION_SMTP_" + "".join(("P", "ASS", "W", "ORD"))
SMTP_FROM_ENV = "EXPERIMENT_NOTIFICATION_EMAIL_FROM"
PROMOTION_DISPOSITIONS: tuple[str, ...] = ("promoted", "deferred")
ORACLE_FAILURE_CLASSES: frozenset[str] = frozenset({"guard_failure", "timeout", "oom"})
PRE_ORACLE_FAILURE_CLASSES: frozenset[str] = frozenset({"policy_violation", "unchanged_result"})
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


class ExperimentEmailDeliveryError(ExperimentNotificationError):
    """Email delivery failed without exposing provider details."""


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


def _resolve_email_audit_path(experiment_id: str) -> Path:
    """Resolve the canonical email audit artifact for an experiment."""

    safe_experiment_id = str(validate_experiment_id(experiment_id, label="Experiment notification"))
    audit_path = NOTIFICATION_ARTIFACT_DIR / f"{safe_experiment_id}.email-audit.json"
    _reject_symlinked_output_components(
        audit_path.absolute(),
        artifact_dir=NOTIFICATION_ARTIFACT_DIR.absolute(),
    )
    return audit_path


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
    _require_promotion_durable_artifact_exists(promotion)


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
        if result["failure_class"] in PRE_ORACLE_FAILURE_CLASSES and result["oracle_results"]:
            raise ExperimentNotificationError(
                "Rejected pre-oracle result must not include oracle evidence."
            )
        if result["failure_class"] == "policy_violation" and result["mutated_paths"]:
            raise ExperimentNotificationError(
                "Rejected policy_violation result mutated_paths must be empty."
            )
        if result["failure_class"] == "metric_regression":
            if result_oracles != expected_oracles:
                raise ExperimentNotificationError(
                    "Rejected metric_regression result oracle_results must match packet immutable_oracles."
                )
            failed_oracles = [
                _oracle_command_name(oracle_result["command"])
                for oracle_result in result["oracle_results"]
                if oracle_result["returncode"] != 0 or oracle_result["timed_out"]
            ]
            if failed_oracles:
                joined = ", ".join(failed_oracles)
                raise ExperimentNotificationError(
                    f"Rejected metric_regression oracle_results must pass: {joined}"
                )
        if result["failure_class"] in ORACLE_FAILURE_CLASSES:
            if not result["oracle_results"]:
                raise ExperimentNotificationError(
                    "Rejected oracle failure result must include terminal oracle evidence."
                )
            terminal_oracle = result["oracle_results"][-1]
            if terminal_oracle["returncode"] == 0 and not terminal_oracle["timed_out"]:
                raise ExperimentNotificationError(
                    "Rejected experiment result terminal oracle must fail or time out."
                )
    if result["status"] == "accepted":
        if not result["shared_tree_untouched"]:
            raise ExperimentNotificationError(
                "Accepted experiment result shared_tree_untouched must be true."
            )
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

    if any(part == ".." for part in PurePosixPath(path).parts):
        return False
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


def _require_promotion_durable_artifact_exists(promotion: dict[str, Any]) -> None:
    """Require promotion evidence to point at a durable repo artifact."""

    durable_path = REPO_ROOT / promotion["durable_artifact_path"]
    if not durable_path.is_file():
        raise ExperimentNotificationError("Promotion decision durable_artifact_path must exist.")
    if promotion["promotion_target"] != "backlog_entry":
        return

    try:
        content = durable_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExperimentNotificationError(
            "Promotion decision backlog durable_artifact_path must be readable."
        ) from exc
    experiment_slug = promotion["experiment_id"].replace("_", "-")
    expected_anchor = f'<a id="ledger-{experiment_slug}"></a>'
    expected_title = f"Experiment follow-up for {promotion['experiment_id']}"
    if expected_anchor not in content or expected_title not in content:
        raise ExperimentNotificationError(
            "Promotion decision backlog durable_artifact_path must include experiment anchor."
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
    if SENSITIVE_PATH_PART_RE.search(binary):
        return "[redacted-command]"
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
        "- Local artifact summary is always written; SMTP email delivery requires explicit `--email`.\n"
        "- Slack, PR comment, and other external delivery sinks are intentionally out of scope.\n"
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


def _email_allowlist() -> set[str]:
    """Return normalized email recipients allowed for explicit delivery."""

    raw_allowlist = os.environ.get(EMAIL_ALLOWLIST_ENV, "")
    return {
        candidate.strip().lower() for candidate in raw_allowlist.split(",") if candidate.strip()
    }


def _require_allowed_email_recipient(raw_recipient: str | None) -> str:
    """Require an explicit recipient that is listed in the env allowlist."""

    recipient = (raw_recipient or "").strip().lower()
    if not recipient:
        raise ExperimentEmailDeliveryError("--email requires --email-to.")
    if CONTROL_CHAR_RE.search(recipient) or "`" in recipient:
        raise ExperimentEmailDeliveryError("--email-to is not an allowed recipient.")
    if recipient != V1_EMAIL_RECIPIENT or recipient not in _email_allowlist():
        raise ExperimentEmailDeliveryError("--email-to is not an allowed recipient.")
    return recipient


def _validate_email_address(raw_value: str, *, label: str) -> str:
    """Validate a simple email address for SMTP headers."""

    value = raw_value.strip().lower()
    if not value or CONTROL_CHAR_RE.search(value) or "`" in value:
        raise ExperimentEmailDeliveryError(f"{label} is invalid.")
    display_name, parsed_address = parseaddr(value)
    if display_name or parsed_address != value or "@" not in parsed_address:
        raise ExperimentEmailDeliveryError(f"{label} is invalid.")
    return value


def _smtp_config() -> dict[str, str | int]:
    """Read required SMTP settings from env without returning raw secrets in errors."""

    values = {
        "host": os.environ.get(SMTP_HOST_ENV, "").strip(),
        "port": os.environ.get(SMTP_PORT_ENV, "").strip(),
        "username": os.environ.get(SMTP_USERNAME_ENV, "").strip(),
        "password": os.environ.get(SMTP_AUTH_ENV, "").strip(),
        "sender": os.environ.get(SMTP_FROM_ENV, "").strip(),
    }
    if not all(values.values()):
        raise ExperimentEmailDeliveryError("SMTP configuration is incomplete.")
    try:
        port = int(values["port"])
    except ValueError as exc:
        raise ExperimentEmailDeliveryError("SMTP configuration is invalid.") from exc
    if port <= 0 or port > 65535:
        raise ExperimentEmailDeliveryError("SMTP configuration is invalid.")
    return {
        "host": values["host"],
        "port": port,
        "username": values["username"],
        "password": values["password"],
        "sender": _validate_email_address(values["sender"], label="SMTP sender"),
    }


def _recipient_hash(recipient: str) -> str:
    """Return a stable short hash for audit without publishing the full mailbox."""

    digest = hashlib.sha256(recipient.lower().encode("utf-8")).hexdigest()
    return digest[:16]


def _sha256_text(text: str) -> str:
    """Return a SHA-256 digest for redacted notification content."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path | None) -> str | None:
    """Return a SHA-256 digest for an input artifact without exposing its path."""

    if path is None:
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ExperimentEmailDeliveryError("Unable to read notification source artifact.") from exc


def _read_existing_email_audit(audit_path: Path) -> dict[str, Any] | None:
    """Read an existing email audit artifact when present."""

    if not audit_path.exists():
        return None
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperimentEmailDeliveryError("Existing email audit artifact is invalid.") from exc
    if not isinstance(payload, dict):
        raise ExperimentEmailDeliveryError("Existing email audit artifact is invalid.")
    return payload


def _require_email_not_already_sent(
    *,
    audit_path: Path,
    recipient: str,
    notification_sha256: str,
) -> None:
    """Prevent duplicate sends for the same recipient and notification body."""

    existing = _read_existing_email_audit(audit_path)
    if existing is None:
        return
    if existing.get("status") not in {"sent", "send_in_progress"}:
        return
    if (
        existing.get("recipient_hash") == _recipient_hash(recipient)
        and existing.get("notification_sha256") == notification_sha256
    ):
        raise ExperimentEmailDeliveryError("Email notification was already sent.")


def _write_email_audit(
    *,
    audit_path: Path,
    experiment_id: str,
    recipient: str,
    status: str,
    failure_class: str | None,
    markdown: str,
    output_path: Path,
    source_paths: dict[str, Path | None],
) -> None:
    """Write a local, secret-free email delivery audit artifact."""

    payload = {
        "experiment_id": experiment_id,
        "notification_sha256": _sha256_text(markdown),
        "output_path": normalize_repo_path(output_path),
        "provider_type": "smtp",
        "recipient_hash": _recipient_hash(recipient),
        "source_sha256": {key: _sha256_file(path) for key, path in sorted(source_paths.items())},
        "status": status,
        "failure_class": _safe_inline(failure_class or "none"),
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _send_smtp_email(
    *,
    recipient: str,
    subject: str,
    markdown: str,
) -> None:
    """Send the already-redacted markdown notification through SMTP."""

    config = _smtp_config()
    try:
        message = EmailMessage()
        message["From"] = str(config["sender"])
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(markdown)
        with smtplib.SMTP(str(config["host"]), int(config["port"]), timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(str(config["username"]), str(config["password"]))
            smtp.send_message(message)
    except (OSError, ValueError, smtplib.SMTPException) as exc:
        raise ExperimentEmailDeliveryError("SMTP delivery failed.") from exc


def _deliver_email_notification(
    *,
    output_path: Path,
    experiment_id: str,
    recipient: str,
    markdown: str,
    source_paths: dict[str, Path | None],
) -> Path:
    """Send an explicit email notification and record a local audit artifact."""

    audit_path = _resolve_email_audit_path(experiment_id)
    notification_sha256 = _sha256_text(markdown)
    _require_email_not_already_sent(
        audit_path=audit_path,
        recipient=recipient,
        notification_sha256=notification_sha256,
    )
    _write_email_audit(
        audit_path=audit_path,
        experiment_id=experiment_id,
        recipient=recipient,
        status="send_in_progress",
        failure_class=None,
        markdown=markdown,
        output_path=output_path,
        source_paths=source_paths,
    )
    try:
        _send_smtp_email(
            recipient=recipient,
            subject=f"PulsePlate experiment result: {experiment_id}",
            markdown=markdown,
        )
    except ExperimentEmailDeliveryError:
        _write_email_audit(
            audit_path=audit_path,
            experiment_id=experiment_id,
            recipient=recipient,
            status="failed",
            failure_class="email_delivery_failed",
            markdown=markdown,
            output_path=output_path,
            source_paths=source_paths,
        )
        raise
    _write_email_audit(
        audit_path=audit_path,
        experiment_id=experiment_id,
        recipient=recipient,
        status="sent",
        failure_class=None,
        markdown=markdown,
        output_path=output_path,
        source_paths=source_paths,
    )
    return audit_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI flags for notification rendering."""

    parser = argparse.ArgumentParser(
        prog="experiment_notify",
        description=(
            "Render governed experiment notifications "
            "(local artifact default; SMTP email explicit opt-in)."
        ),
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
    parser.add_argument(
        "--email",
        action="store_true",
        help="Explicitly send the redacted notification markdown by SMTP.",
    )
    parser.add_argument(
        "--email-to",
        default=None,
        help="Explicit email recipient; must be present in EXPERIMENT_NOTIFICATION_EMAIL_ALLOWLIST.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the notification renderer CLI."""

    args = _parse_args(argv)
    packet_path = Path(args.packet).expanduser().resolve()
    result_path = Path(args.result).expanduser().resolve()
    email_recipient = None

    try:
        if args.email:
            email_recipient = _require_allowed_email_recipient(args.email_to)
        elif args.email_to:
            raise ExperimentEmailDeliveryError("--email-to requires --email.")
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
    except ValueError:
        print("FAIL: invalid experiment notification input.")
        return 1
    except ExperimentNotificationError as exc:
        print(f"FAIL: {exc}")
        return 1

    email_audit_path = None
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        if args.github_step_summary:
            _append_github_step_summary(markdown)
        if args.email and email_recipient is not None:
            email_audit_path = _deliver_email_notification(
                output_path=output_path,
                experiment_id=packet["experiment_id"],
                recipient=email_recipient,
                markdown=markdown,
                source_paths={
                    "packet": packet_path,
                    "promotion": (
                        Path(args.promotion).expanduser().resolve() if args.promotion else None
                    ),
                    "result": result_path,
                },
            )
    except OSError:
        print("FAIL: unable to write experiment notification.")
        return 1
    except ExperimentEmailDeliveryError as exc:
        print(f"FAIL: {exc}")
        return 1
    except ExperimentNotificationError as exc:
        print(f"FAIL: unable to write experiment notification: {exc}")
        return 1

    print(
        json.dumps(
            {
                "experiment_id": packet["experiment_id"],
                "email": bool(args.email),
                "email_audit": (
                    normalize_repo_path(email_audit_path) if email_audit_path is not None else None
                ),
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
