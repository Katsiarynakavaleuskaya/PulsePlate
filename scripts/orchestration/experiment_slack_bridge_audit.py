"""Audit, idempotency, and rate-limit helpers for the Slack bridge."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, cast

from scripts.orchestration.experiment_slack_bridge_config import (
    _normalized_absolute_path,
    _reject_symlinked_output_components,
)
from scripts.orchestration.experiment_slack_bridge_constants import (
    RATE_LIMIT_CLAIM_MAX_ATTEMPTS,
    RATE_LIMIT_LOCK_DIR,
    REJECTED_RATE_LIMIT_LOCK_DIR,
)
from scripts.orchestration.experiment_slack_bridge_models import (
    BridgeConfig,
    OperatorCommand,
    OperatorEvent,
    SlackSocketAuditError,
    _safe_hash,
    _sha256_text,
    _utcnow,
)

PARTIAL_CLAIM_RETRY_BACKOFF_SECONDS = 0.05


def _repo_root_from_audit_dir(config: BridgeConfig, repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root
    audit_dir = cast(Path, _normalized_absolute_path(Path(config.audit_dir)))
    parts = audit_dir.parts
    for index in range(len(parts) - 1):
        if parts[index : index + 2] == ("artifacts", "orchestration"):
            return Path(*parts[:index])
    return audit_dir.parent


def _fsync_directory(directory: Path) -> None:
    directory_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _unlink_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _atomic_publish_json(path: Path, payload: dict[str, Any], *, exclusive: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
            temp_file.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        if exclusive:
            os.link(temp_path, path)
            _unlink_if_exists(temp_path)
            temp_path = None
        else:
            os.replace(temp_path, path)
            temp_path = None
        _fsync_directory(path.parent)
    finally:
        if temp_path is not None:
            _unlink_if_exists(temp_path)


def _audit_path(config: BridgeConfig, event: OperatorEvent) -> Path:
    return cast(Path, config.audit_dir / f"{_sha256_text(event.event_id)}.json")


def _read_audit(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.") from exc
    if not isinstance(payload, dict):
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
    return payload


def _audit_timestamp(audit: dict[str, Any]) -> datetime:
    timestamp_raw = audit.get("timestamp")
    if not isinstance(timestamp_raw, str):
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
    try:
        timestamp = datetime.fromisoformat(timestamp_raw)
    except ValueError as exc:
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.") from exc
    if timestamp.tzinfo is None:
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
    return timestamp.astimezone(timezone.utc)


def audit_retention_summary(
    config: BridgeConfig,
    *,
    cleanup: bool,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Report or delete expired Slack audit JSON files without exposing paths."""

    effective_repo_root = _repo_root_from_audit_dir(config, repo_root)
    mode = "cleanup" if cleanup else "report"
    _reject_symlinked_output_components(
        (config.audit_dir / "retention-check.json").absolute(),
        artifact_dir=Path(config.audit_dir).absolute(),
        repo_root=effective_repo_root,
    )
    if not config.audit_dir.exists():
        return {
            "deleted_count": 0,
            "expired_count": 0,
            "mode": mode,
            "retention_days": config.audit_retention_days,
            "status": "pass",
        }
    threshold = _utcnow() - timedelta(days=config.audit_retention_days)
    expired_paths: list[Path] = []
    try:
        audit_paths = sorted(config.audit_dir.glob("*.json"))
    except OSError as exc:
        raise SlackSocketAuditError("Unable to inspect Slack operator audit artifacts.") from exc
    for audit_path in audit_paths:
        _reject_symlinked_output_components(
            audit_path.absolute(),
            artifact_dir=Path(config.audit_dir).absolute(),
            repo_root=effective_repo_root,
        )
        audit = _read_audit(audit_path)
        if audit is None:
            continue
        if _audit_timestamp(audit) < threshold:
            expired_paths.append(audit_path)
    deleted_count = 0
    if cleanup:
        for audit_path in expired_paths:
            try:
                audit_path.unlink()
            except OSError as exc:
                raise SlackSocketAuditError(
                    "Unable to clean up Slack operator audit artifact."
                ) from exc
            deleted_count += 1
    return {
        "deleted_count": deleted_count,
        "expired_count": len(expired_paths),
        "mode": mode,
        "retention_days": config.audit_retention_days,
        "status": "pass",
    }


def _ensure_event_not_processed(
    path: Path, *, config: BridgeConfig, repo_root: Path | None = None
) -> None:
    effective_repo_root = _repo_root_from_audit_dir(config, repo_root)
    _reject_symlinked_output_components(
        path.absolute(),
        artifact_dir=Path(config.audit_dir).absolute(),
        repo_root=effective_repo_root,
    )
    existing = _read_audit(path)
    if existing is None:
        return
    if existing.get("status") in {"claimed", "dry_run", "dispatched", "failed", "rejected"}:
        raise SlackSocketAuditError("Slack operator event was already processed.")
    raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")


def _approval_prefix(config: BridgeConfig, command: OperatorCommand) -> str | None:
    """Return a truncated approval hash prefix for run-experiment commands."""

    if config.live_approval_sha256 is not None and command.kind == "run-experiment":
        return cast(str, config.live_approval_sha256[:16])
    return None


def _audit_payload(
    *,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    status: str,
    failure_class: str | None,
) -> dict[str, Any]:
    return {
        "approval_hash": _approval_prefix(config, command) or "none",
        "branch_hash": _safe_hash(command.branch_ref),
        "channel_hash": _sha256_text(event.channel_id),
        "command_kind": command.kind,
        "dispatch_mode": config.dispatch_mode,
        "event_hash": _sha256_text(event.event_id),
        "failure_class": failure_class or "none",
        "hypothesis_hash": _safe_hash(command.hypothesis),
        "provider_type": "slack_socket_mode",
        "status": status,
        "team_hash": _safe_hash(event.team_id),
        "timestamp": _utcnow().isoformat(),
        "user_hash": _sha256_text(event.user_id),
        "workflow_file": config.workflow_file,
    }


def _write_audit(
    *,
    path: Path,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    repo_root: Path | None = None,
    status: str,
    failure_class: str | None = None,
) -> None:
    effective_repo_root = _repo_root_from_audit_dir(config, repo_root)
    _reject_symlinked_output_components(
        path.absolute(),
        artifact_dir=Path(config.audit_dir).absolute(),
        repo_root=effective_repo_root,
    )
    try:
        _atomic_publish_json(
            path,
            _audit_payload(
                event=event,
                command=command,
                config=config,
                status=status,
                failure_class=failure_class,
            ),
            exclusive=False,
        )
    except OSError as exc:
        raise SlackSocketAuditError("Unable to write Slack operator audit artifact.") from exc


def _write_audit_exclusive(
    *,
    path: Path,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    repo_root: Path | None = None,
    status: str,
    failure_class: str | None = None,
) -> None:
    effective_repo_root = _repo_root_from_audit_dir(config, repo_root)
    _reject_symlinked_output_components(
        path.absolute(),
        artifact_dir=Path(config.audit_dir).absolute(),
        repo_root=effective_repo_root,
    )
    payload = _audit_payload(
        event=event,
        command=command,
        config=config,
        status=status,
        failure_class=failure_class,
    )
    try:
        _atomic_publish_json(path, payload, exclusive=True)
    except FileExistsError:
        existing = _read_audit(path)
        if existing is None:
            raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
        raise SlackSocketAuditError("Slack operator event was already processed.")
    except OSError as exc:
        raise SlackSocketAuditError("Unable to write Slack operator audit artifact.") from exc


def _claim_event(
    path: Path,
    *,
    event: OperatorEvent,
    command: OperatorCommand,
    config: BridgeConfig,
    repo_root: Path | None = None,
) -> None:
    effective_repo_root = _repo_root_from_audit_dir(config, repo_root)
    _reject_symlinked_output_components(
        path.absolute(),
        artifact_dir=Path(config.audit_dir).absolute(),
        repo_root=effective_repo_root,
    )
    payload = _audit_payload(
        event=event,
        command=command,
        config=config,
        status="claimed",
        failure_class=None,
    )
    try:
        _atomic_publish_json(path, payload, exclusive=True)
        return
    except FileExistsError:
        existing = _read_audit(path)
    except OSError as exc:
        raise SlackSocketAuditError("Unable to claim Slack operator event audit artifact.") from exc
    if existing is None or existing.get("status") not in {
        "claimed",
        "dry_run",
        "dispatched",
        "failed",
        "rejected",
    }:
        raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
    raise SlackSocketAuditError("Slack operator event was already processed.")


def _rate_limit_claim_dir(
    config: BridgeConfig, *, lock_dir_name: str = RATE_LIMIT_LOCK_DIR
) -> Path:
    return cast(Path, config.audit_dir / lock_dir_name)


def _read_rate_limit_claim(lock_dir: Path) -> datetime:
    claim_path = lock_dir / "claim.json"
    try:
        payload = json.loads(claim_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.") from exc
    if not isinstance(payload, dict):
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.")
    timestamp_raw = payload.get("timestamp")
    if not isinstance(timestamp_raw, str):
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.")
    try:
        timestamp = datetime.fromisoformat(timestamp_raw)
    except ValueError as exc:
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.") from exc
    if timestamp.tzinfo is None:
        raise SlackSocketAuditError("Existing Slack operator rate-limit claim is invalid.")
    return timestamp.astimezone(timezone.utc)


def _remove_stale_rate_limit_claim(lock_dir: Path) -> None:
    try:
        (lock_dir / "claim.json").unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clear stale Slack operator rate-limit claim."
        ) from exc
    try:
        for temp_path in lock_dir.glob(".claim.json.*.tmp"):
            if temp_path.is_file() or temp_path.is_symlink():
                temp_path.unlink()
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clear stale Slack operator rate-limit claim."
        ) from exc
    try:
        lock_dir.rmdir()
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clear stale Slack operator rate-limit claim."
        ) from exc


def _partial_rate_limit_claim_is_stale(lock_dir: Path, *, config: BridgeConfig) -> bool:
    """Return whether an incomplete rate-limit claim is old enough to clean."""

    try:
        modified_at = datetime.fromtimestamp(lock_dir.stat().st_mtime, tz=timezone.utc)
    except OSError as exc:
        raise SlackSocketAuditError("Unable to inspect Slack operator rate-limit claim.") from exc
    return cast(bool, (_utcnow() - modified_at).total_seconds() >= config.timeout_seconds)


def _cleanup_partial_rate_limit_claim(lock_dir: Path) -> None:
    claim_path = lock_dir / "claim.json"
    try:
        claim_path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clean up partial Slack operator rate-limit claim."
        ) from exc
    try:
        lock_dir.rmdir()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to clean up partial Slack operator rate-limit claim."
        ) from exc


def _claim_rate_limit(
    config: BridgeConfig,
    event: OperatorEvent,
    *,
    repo_root: Path | None = None,
    lock_dir_name: str = RATE_LIMIT_LOCK_DIR,
    remove_stale_rate_limit_claim: Callable[[Path], None] = _remove_stale_rate_limit_claim,
) -> None:
    if config.min_interval_seconds <= 0:
        return
    effective_repo_root = _repo_root_from_audit_dir(config, repo_root)
    lock_dir = _rate_limit_claim_dir(config, lock_dir_name=lock_dir_name)
    _reject_symlinked_output_components(
        (lock_dir / "claim.json").absolute(),
        artifact_dir=Path(config.audit_dir).absolute(),
        repo_root=effective_repo_root,
    )
    try:
        config.audit_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SlackSocketAuditError(
            "Unable to prepare Slack operator rate-limit claim path."
        ) from exc
    for _ in range(RATE_LIMIT_CLAIM_MAX_ATTEMPTS):
        try:
            lock_dir.mkdir()
        except FileExistsError:
            _reject_symlinked_output_components(
                (lock_dir / "claim.json").absolute(),
                artifact_dir=Path(config.audit_dir).absolute(),
                repo_root=effective_repo_root,
            )
            if not (lock_dir / "claim.json").exists():
                if _partial_rate_limit_claim_is_stale(lock_dir, config=config):
                    remove_stale_rate_limit_claim(lock_dir)
                else:
                    time.sleep(PARTIAL_CLAIM_RETRY_BACKOFF_SECONDS)
                continue
            timestamp = _read_rate_limit_claim(lock_dir)
            age_seconds = (_utcnow() - timestamp).total_seconds()
            if 0 <= age_seconds < config.min_interval_seconds:
                raise SlackSocketAuditError("Slack operator bridge rate limit is active.")
            remove_stale_rate_limit_claim(lock_dir)
            continue
        except OSError as exc:
            raise SlackSocketAuditError(
                "Unable to create Slack operator rate-limit claim."
            ) from exc
        claim = {
            "event_hash": _sha256_text(event.event_id),
            "provider_type": "slack_socket_mode",
            "status": "claimed",
            "timestamp": _utcnow().isoformat(),
        }
        try:
            _atomic_publish_json(lock_dir / "claim.json", claim, exclusive=False)
        except OSError as exc:
            _cleanup_partial_rate_limit_claim(lock_dir)
            raise SlackSocketAuditError(
                "Unable to record Slack operator rate-limit claim."
            ) from exc
        return
    raise SlackSocketAuditError("Unable to acquire Slack operator rate-limit claim.")


def _claim_rejected_event_audit_throttle(
    config: BridgeConfig,
    event: OperatorEvent,
    *,
    repo_root: Path | None = None,
    claim_rate_limit: Callable[..., None] = _claim_rate_limit,
) -> None:
    """Bound rejected audit writes without consuming the main operator throttle."""

    claim_rate_limit(
        config,
        event,
        lock_dir_name=REJECTED_RATE_LIMIT_LOCK_DIR,
        repo_root=repo_root,
    )


def _check_rate_limit(config: BridgeConfig) -> None:
    if not config.audit_dir.exists():
        return
    now = _utcnow()
    try:
        audit_paths = sorted(config.audit_dir.glob("*.json"))
    except OSError as exc:
        raise SlackSocketAuditError("Unable to inspect Slack operator audit artifacts.") from exc
    for audit_path in audit_paths:
        audit = _read_audit(audit_path)
        if audit is None or audit.get("status") not in {"dry_run", "dispatched"}:
            continue
        if config.min_interval_seconds <= 0:
            continue
        timestamp_raw = audit.get("timestamp")
        if not isinstance(timestamp_raw, str):
            raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
        try:
            timestamp = datetime.fromisoformat(timestamp_raw)
        except ValueError as exc:
            raise SlackSocketAuditError(
                "Existing Slack operator audit artifact is invalid."
            ) from exc
        if timestamp.tzinfo is None:
            raise SlackSocketAuditError("Existing Slack operator audit artifact is invalid.")
        age_seconds = (now - timestamp.astimezone(timezone.utc)).total_seconds()
        if 0 <= age_seconds < config.min_interval_seconds:
            raise SlackSocketAuditError("Slack operator bridge rate limit is active.")
