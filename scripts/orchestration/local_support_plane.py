"""Experimental local support-plane storage (non-canonical).

RU: Локальное key-value хранилище для операторских support-задач; не источник
истины оркестрации и не замена canonical bootstrap/reflection протоколам.

EN: Local JSON-per-key store for operator-invoked support workflows. This is
support infrastructure only — not orchestration SoT, not a second bootstrap
packet system, and not evidence of launcher or host-runtime guarantees from
repo artifacts alone (see ``docs/orchestration/AUTOMATION_READINESS_MATRIX.md``).

Mutating operations require:
- allowlist pair ``local_support_plane:artifacts_kv`` via
  ``AGENT_CONTROL_ALLOWLIST`` (or injected allowlist in tests)
- execution mode compatible with ``require_execution_mode(allow_review_required=True)``
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Final, Mapping, cast

from app.security import agent_control_plane as cp

POLICY_ACTION: Final[str] = "local_support_plane"
POLICY_TARGET: Final[str] = "artifacts_kv"
MAX_KEY_LEN: Final[int] = 128
MAX_VALUE_BYTES: Final[int] = 65_536
_KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")

SUPPORT_PLANE_ROOT_ENV = "LOCAL_SUPPORT_PLANE_ROOT"


def repo_root_from_module() -> Path:
    """Return repository root (directory containing ``app/``)."""

    return Path(__file__).resolve().parents[2]


def resolve_support_plane_root(
    *,
    repo_root: Path | None = None,
    override: Path | None = None,
) -> Path:
    """Resolve absolute directory for support-plane JSON files."""

    if override is not None:
        return override.resolve()
    env = (os.getenv(SUPPORT_PLANE_ROOT_ENV) or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    root = repo_root if repo_root is not None else repo_root_from_module()
    return (root / "artifacts" / "orchestration" / "local_support_plane").resolve()


def normalize_key(key: str) -> str:
    """Validate and return a safe single-segment key (no path components)."""

    stripped = key.strip()
    if not stripped or len(stripped) > MAX_KEY_LEN:
        raise ValueError("support_plane_key_invalid_length")
    if not _KEY_RE.match(stripped):
        raise ValueError("support_plane_key_invalid_chars")
    return stripped


def _record_path(root: Path, key: str) -> Path:
    normalized = normalize_key(key)
    return root / f"{normalized}.json"


def _ensure_under_root(path: Path, root: Path) -> None:
    """Reject paths that escape ``root`` after resolution."""

    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("support_plane_path_outside_root") from exc


def get_record(
    key: str,
    *,
    repo_root: Path | None = None,
    root_override: Path | None = None,
) -> dict[str, Any] | None:
    """Read JSON record if present; read-only (no policy gate)."""

    root = resolve_support_plane_root(repo_root=repo_root, override=root_override)
    path = _record_path(root, key)
    _ensure_under_root(path, root)
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8")
    parsed: Any = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("support_plane_record_not_object")
    return cast(dict[str, Any], parsed)


def put_record(
    key: str,
    value: Mapping[str, Any],
    *,
    allowlist: set[tuple[str, str]],
    repo_root: Path | None = None,
    root_override: Path | None = None,
    audit_secret: str | None = None,
    audit_log_path: str | Path | None = None,
    write_audit: bool = True,
) -> Path:
    """Write JSON record; policy + execution-mode gated; optional signed audit."""

    cp.require_execution_mode(allow_review_required=True)
    decision = cp.require_policy_allow(POLICY_ACTION, POLICY_TARGET, allowlist=allowlist)
    root = resolve_support_plane_root(repo_root=repo_root, override=root_override)
    root.mkdir(parents=True, exist_ok=True)
    path = _record_path(root, key)
    _ensure_under_root(path, root)
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_VALUE_BYTES:
        raise ValueError("support_plane_value_too_large")
    path.write_text(payload, encoding="utf-8")
    if write_audit:
        nk = normalize_key(key)
        metadata: dict[str, str] = {"op": "put", "key": nk}
        envelope = cp.sign_audit_envelope(decision, metadata=metadata, secret=audit_secret)
        cp.persist_audit_envelope(
            envelope,
            metadata=metadata,
            log_path=audit_log_path,
        )
    return path


def delete_record(
    key: str,
    *,
    allowlist: set[tuple[str, str]],
    repo_root: Path | None = None,
    root_override: Path | None = None,
    audit_secret: str | None = None,
    audit_log_path: str | Path | None = None,
    write_audit: bool = True,
) -> bool:
    """Delete record if it exists; returns whether a file was removed."""

    cp.require_execution_mode(allow_review_required=True)
    decision = cp.require_policy_allow(POLICY_ACTION, POLICY_TARGET, allowlist=allowlist)
    root = resolve_support_plane_root(repo_root=repo_root, override=root_override)
    path = _record_path(root, key)
    _ensure_under_root(path, root)
    existed = path.is_file()
    if existed:
        path.unlink()
    if write_audit and existed:
        nk = normalize_key(key)
        metadata = {"op": "delete", "key": nk}
        envelope = cp.sign_audit_envelope(decision, metadata=metadata, secret=audit_secret)
        cp.persist_audit_envelope(
            envelope,
            metadata=metadata,
            log_path=audit_log_path,
        )
    return existed


def default_allowlist_pair() -> tuple[str, str]:
    """Return the canonical (action, target) pair for allowlist configuration."""

    return (POLICY_ACTION, POLICY_TARGET)
