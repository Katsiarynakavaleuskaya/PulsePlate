"""GitHub App private-pilot capability report contract.

The report is a local, read-only evidence artifact. It describes already
observed GitHub App permissions; this module never mints tokens, calls GitHub,
mutates app settings, dispatches workflows, or persists secrets.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
from typing import Any

SCHEMA_VERSION = "1.0"
REPORT_ARTIFACT_TYPE = "github_app_private_pilot_capability_report"
POLICY_VERSION = "github-app-private-pilot-capability-report"

REPORT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "policy_version",
        "generated_at_utc",
        "repository",
        "permissions",
        "capabilities",
        "workflow_dispatch",
        "authority",
        "sanitized",
    }
)
PERMISSION_KEYS = frozenset(
    {
        "metadata",
        "pull_requests",
        "checks",
        "contents",
        "actions",
        "workflows",
        "administration",
        "organization_administration",
        "members",
        "secrets",
    }
)
CAPABILITY_KEYS = frozenset(
    {
        "pull_requests_read",
        "checks_read",
        "metadata_read",
        "contents_read",
        "actions_read",
        "workflow_dispatch",
    }
)
WORKFLOW_DISPATCH_KEYS = frozenset({"enabled", "label"})
AUTHORITY_KEYS = frozenset(
    {
        "read_pull_requests",
        "read_checks",
        "read_metadata",
        "read_contents",
        "read_actions",
        "workflow_dispatch",
        "write_pull_requests",
        "write_checks",
        "write_contents",
        "write_workflows",
        "write_repository_settings",
        "admin_repository",
        "read_secrets",
        "mint_installation_tokens",
        "modify_github_app",
    }
)
REPORT_STATE_KEYS = frozenset(
    {
        "status",
        "report_present",
        "missing_permissions",
        "read_only",
        "workflow_dispatch_label",
        "authority",
    }
)
READ_ONLY_STATE_KEYS = frozenset(
    {
        "pull_requests_read",
        "checks_read",
        "metadata_read",
        "contents_read",
        "actions_read",
    }
)

ACTION_PERMISSION_LEVELS = frozenset({"none", "write"})
READ_ONLY_PERMISSION_LEVELS = frozenset({"none", "read"})
NONE_PERMISSION_LEVELS = frozenset({"none"})
ADMIN_NONE_PERMISSION_KEYS = frozenset(
    {"workflows", "administration", "organization_administration", "members", "secrets"}
)
REQUIRED_READ_PERMISSIONS = ("pull_requests:read", "checks:read")
CAPABILITY_STATUSES = frozenset(
    {
        "manual_only",
        "read_only_capable",
        "read_only_with_workflow_dispatch",
        "missing_required_read_permissions",
    }
)
WORKFLOW_DISPATCH_LABELS = frozenset(
    {"not_checked", "manual_only", "workflow_dispatch_actions_write_optional"}
)

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[psoru]_[A-Za-z0-9_.-]{12,}|github_pat_|"
    r"xox[abprs]-|authorization:\s*bearer|private[_ -]?key|api[_ -]?key|"
    r"GH_TOKEN|GITHUB_TOKEN)",
    re.IGNORECASE,
)
LEAK_TEXT_RE = re.compile(
    r"(diff --git|^\+\+\+ |^--- |@@ |candidate\.patch|candidate_patch|"
    r"raw[_ -]?(body|prompt|response|context|patch|review|pr)|"
    r"review[_ -]?thread[_ -]?body|pull[_ -]?request[_ -]?body|"
    r"chain[_ -]?of[_ -]?thought|provider[_ -]?payload|"
    r"oracle[_ -]?(stdout|stderr|output)|file://|"
    r"/(?:Users|home|private/var|var/folders|tmp|etc|opt|usr|Volumes|mnt|root|"
    r"workspace|workspaces)(?:/|$)|~[/\\]|[A-Za-z]:[\\/]|\.venv/|\.git/|"
    r"worktrees([:/._-]|$)|merge[-_ ]?ready|ready to merge|mergeable)",
    re.IGNORECASE | re.MULTILINE,
)
UNSAFE_KEY_RE = re.compile(
    r"(?i)(^raw|raw_|_raw|body$|_body$|body_text|body_html|patch_text|raw_patch|"
    r"prompt_text|raw_prompt|provider_payload|oracle_stdout|oracle_stderr|"
    r"secret_value|token_value|access_token|api_key|private_key)"
)


class GithubAppPrivatePilotCapabilityError(ValueError):
    """Raised when a GitHub App capability report violates the contract."""


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise GithubAppPrivatePilotCapabilityError(
                f"github-app capability JSON has duplicate key: {_diagnostic_key(key)}"
            )
        seen.add(key)
        payload[key] = value
    return payload


def _diagnostic_key(key: Any) -> str:
    if not isinstance(key, str):
        return "<non-string-key>"
    if SECRET_RE.search(key) or LEAK_TEXT_RE.search(key) or UNSAFE_KEY_RE.search(key):
        return "<redacted-key>"
    return key


def reject_unsafe_report_value(value: Any, *, label: str) -> None:
    """Reject values that could persist secrets, raw bodies, patches, or local paths."""

    if isinstance(value, str):
        if SECRET_RE.search(value) or LEAK_TEXT_RE.search(value):
            raise GithubAppPrivatePilotCapabilityError(
                f"{label} contains unsafe GitHub App capability text."
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_unsafe_report_value(item, label=f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if UNSAFE_KEY_RE.search(key):
                raise GithubAppPrivatePilotCapabilityError(
                    f"{label}.{key} is an unsupported raw/private field."
                )
            reject_unsafe_report_value(item, label=f"{label}.{key}")


def read_github_app_private_pilot_capability_report(path: str | Path) -> dict[str, Any]:
    """Read and validate a capability report while rejecting duplicate JSON keys."""

    report_path = Path(path)
    _reject_symlink_components(report_path)
    try:
        payload = json.loads(
            report_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object_keys,
        )
    except GithubAppPrivatePilotCapabilityError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GithubAppPrivatePilotCapabilityError(
            "Unable to read GitHub App capability report JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise GithubAppPrivatePilotCapabilityError(
            "GitHub App capability report must be a JSON object."
        )
    return validate_github_app_private_pilot_capability_report(payload)


def _reject_symlink_components(path: Path) -> None:
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current_path = current_path / part
        if current_path.is_symlink():
            raise GithubAppPrivatePilotCapabilityError(
                "capability report path must not traverse symlinks."
            )


def _require_exact_keys(
    payload: Mapping[str, Any], expected: frozenset[str], *, label: str
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise GithubAppPrivatePilotCapabilityError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )
    if extra:
        extra_text = ", ".join(_diagnostic_key(key) for key in extra)
        raise GithubAppPrivatePilotCapabilityError(f"{label} has unsupported fields: {extra_text}")


def _require_const(payload: Mapping[str, Any], key: str, expected: Any, *, label: str) -> Any:
    value = payload.get(key)
    if value != expected:
        raise GithubAppPrivatePilotCapabilityError(f"{label}.{key} must equal {expected!r}.")
    return value


def _require_bool(
    payload: Mapping[str, Any], key: str, *, expected: bool | None, label: str
) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise GithubAppPrivatePilotCapabilityError(f"{label}.{key} must be a boolean.")
    if expected is not None and value is not expected:
        raise GithubAppPrivatePilotCapabilityError(f"{label}.{key} must be {expected}.")
    return value


def _require_id(payload: Mapping[str, Any], key: str, *, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise GithubAppPrivatePilotCapabilityError(f"{label}.{key} must be a string.")
    normalized = value.strip()
    if not normalized or not ID_RE.fullmatch(normalized):
        raise GithubAppPrivatePilotCapabilityError(f"{label}.{key} must be a safe identifier.")
    reject_unsafe_report_value(normalized, label=f"{label}.{key}")
    return normalized


def _require_timestamp(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise GithubAppPrivatePilotCapabilityError(f"{label} must be a UTC timestamp.")
    return value


def _require_repository(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not REPOSITORY_RE.fullmatch(value):
        raise GithubAppPrivatePilotCapabilityError(f"{label} must be an owner/repo slug.")
    reject_unsafe_report_value(value, label=label)
    return value


def _normalize_permission_level(
    payload: Mapping[str, Any],
    key: str,
    *,
    allowed: frozenset[str],
    label: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise GithubAppPrivatePilotCapabilityError(f"{label}.{key} must be a string.")
    normalized = value.strip().lower()
    if normalized not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise GithubAppPrivatePilotCapabilityError(f"{label}.{key} must be one of: {allowed_text}.")
    return normalized


def _expected_capabilities(
    permissions: Mapping[str, str],
    *,
    dispatch_enabled: bool,
) -> dict[str, bool]:
    return {
        "pull_requests_read": permissions["pull_requests"] == "read",
        "checks_read": permissions["checks"] == "read",
        "metadata_read": permissions["metadata"] == "read",
        "contents_read": permissions["contents"] == "read",
        "actions_read": permissions["actions"] == "write",
        "workflow_dispatch": permissions["actions"] == "write" and dispatch_enabled,
    }


def _normalize_permissions(raw_permissions: Any) -> dict[str, str]:
    if not isinstance(raw_permissions, Mapping):
        raise GithubAppPrivatePilotCapabilityError("permissions must be a JSON object.")
    _require_exact_keys(raw_permissions, PERMISSION_KEYS, label="permissions")
    permissions = {
        "metadata": _normalize_permission_level(
            raw_permissions, "metadata", allowed=frozenset({"read"}), label="permissions"
        ),
        "pull_requests": _normalize_permission_level(
            raw_permissions,
            "pull_requests",
            allowed=READ_ONLY_PERMISSION_LEVELS,
            label="permissions",
        ),
        "checks": _normalize_permission_level(
            raw_permissions, "checks", allowed=READ_ONLY_PERMISSION_LEVELS, label="permissions"
        ),
        "contents": _normalize_permission_level(
            raw_permissions,
            "contents",
            allowed=NONE_PERMISSION_LEVELS,
            label="permissions",
        ),
        "actions": _normalize_permission_level(
            raw_permissions, "actions", allowed=ACTION_PERMISSION_LEVELS, label="permissions"
        ),
    }
    for key in sorted(ADMIN_NONE_PERMISSION_KEYS):
        permissions[key] = _normalize_permission_level(
            raw_permissions, key, allowed=frozenset({"none"}), label="permissions"
        )
    return dict(sorted(permissions.items()))


def _normalize_workflow_dispatch(raw_dispatch: Any) -> dict[str, Any]:
    if not isinstance(raw_dispatch, Mapping):
        raise GithubAppPrivatePilotCapabilityError("workflow_dispatch must be a JSON object.")
    _require_exact_keys(raw_dispatch, WORKFLOW_DISPATCH_KEYS, label="workflow_dispatch")
    enabled = _require_bool(raw_dispatch, "enabled", expected=None, label="workflow_dispatch")
    label = _require_id(raw_dispatch, "label", label="workflow_dispatch")
    expected = "workflow_dispatch_actions_write_optional" if enabled else "manual_only"
    if label != expected:
        raise GithubAppPrivatePilotCapabilityError(
            f"workflow_dispatch.label must equal {expected!r}."
        )
    return {"enabled": enabled, "label": label}


def _normalize_capabilities(
    raw_capabilities: Any,
    *,
    expected: Mapping[str, bool],
) -> dict[str, bool]:
    if not isinstance(raw_capabilities, Mapping):
        raise GithubAppPrivatePilotCapabilityError("capabilities must be a JSON object.")
    _require_exact_keys(raw_capabilities, CAPABILITY_KEYS, label="capabilities")
    normalized = {
        key: _require_bool(raw_capabilities, key, expected=None, label="capabilities")
        for key in sorted(CAPABILITY_KEYS)
    }
    if normalized != dict(sorted(expected.items())):
        raise GithubAppPrivatePilotCapabilityError(
            "capabilities must match the normalized permission set."
        )
    return normalized


def _expected_authority(capabilities: Mapping[str, bool]) -> dict[str, bool]:
    authority = {key: False for key in sorted(AUTHORITY_KEYS)}
    authority.update(
        {
            "read_actions": capabilities["actions_read"],
            "read_checks": capabilities["checks_read"],
            "read_contents": capabilities["contents_read"],
            "read_metadata": capabilities["metadata_read"],
            "read_pull_requests": capabilities["pull_requests_read"],
            "workflow_dispatch": capabilities["workflow_dispatch"],
        }
    )
    return dict(sorted(authority.items()))


def _normalize_authority(raw_authority: Any, *, expected: Mapping[str, bool]) -> dict[str, bool]:
    if not isinstance(raw_authority, Mapping):
        raise GithubAppPrivatePilotCapabilityError("authority must be a JSON object.")
    _require_exact_keys(raw_authority, AUTHORITY_KEYS, label="authority")
    normalized = {
        key: _require_bool(raw_authority, key, expected=None, label="authority")
        for key in sorted(AUTHORITY_KEYS)
    }
    if normalized != dict(sorted(expected.items())):
        raise GithubAppPrivatePilotCapabilityError(
            "authority must match the normalized permission set."
        )
    return normalized


def _validate_actions_write_boundary(
    *, permissions: Mapping[str, str], workflow_dispatch: Mapping[str, Any]
) -> None:
    if permissions["actions"] == "write" and not workflow_dispatch["enabled"]:
        raise GithubAppPrivatePilotCapabilityError(
            "permissions.actions write is allowed only for optional workflow_dispatch."
        )
    if permissions["actions"] != "write" and workflow_dispatch["enabled"]:
        raise GithubAppPrivatePilotCapabilityError(
            "workflow_dispatch requires permissions.actions write."
        )


def validate_github_app_private_pilot_capability_report(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and normalize a strict GitHub App capability report."""

    _require_exact_keys(payload, REPORT_KEYS, label="github_app_capability_report")
    _require_const(payload, "schema_version", SCHEMA_VERSION, label="github_app_capability_report")
    _require_const(
        payload,
        "artifact_type",
        REPORT_ARTIFACT_TYPE,
        label="github_app_capability_report",
    )
    _require_const(payload, "policy_version", POLICY_VERSION, label="github_app_capability_report")
    permissions = _normalize_permissions(payload["permissions"])
    workflow_dispatch = _normalize_workflow_dispatch(payload["workflow_dispatch"])
    _validate_actions_write_boundary(
        permissions=permissions,
        workflow_dispatch=workflow_dispatch,
    )
    expected_capabilities = _expected_capabilities(
        permissions,
        dispatch_enabled=bool(workflow_dispatch["enabled"]),
    )
    capabilities = _normalize_capabilities(
        payload["capabilities"],
        expected=expected_capabilities,
    )
    expected_authority = _expected_authority(capabilities)
    authority = _normalize_authority(payload["authority"], expected=expected_authority)
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": REPORT_ARTIFACT_TYPE,
        "policy_version": POLICY_VERSION,
        "generated_at_utc": _require_timestamp(
            payload["generated_at_utc"],
            label="github_app_capability_report.generated_at_utc",
        ),
        "repository": _require_repository(
            payload["repository"], label="github_app_capability_report.repository"
        ),
        "permissions": permissions,
        "capabilities": capabilities,
        "workflow_dispatch": workflow_dispatch,
        "authority": authority,
        "sanitized": _require_bool(
            payload, "sanitized", expected=True, label="github_app_capability_report"
        ),
    }
    reject_unsafe_report_value(normalized, label="github_app_capability_report")
    return normalized


def missing_required_read_permissions(report: Mapping[str, Any]) -> list[str]:
    """Return required read permissions missing from a normalized report."""

    capabilities = report["capabilities"]
    missing: list[str] = []
    if not capabilities["pull_requests_read"]:
        missing.append("pull_requests:read")
    if not capabilities["checks_read"]:
        missing.append("checks:read")
    return sorted(missing)


def default_github_app_capability_state() -> dict[str, Any]:
    """Return the non-blocking state used when no report is supplied."""

    return {
        "status": "manual_only",
        "report_present": False,
        "missing_permissions": [],
        "read_only": {
            "pull_requests_read": False,
            "checks_read": False,
            "metadata_read": False,
            "contents_read": False,
            "actions_read": False,
        },
        "workflow_dispatch_label": "not_checked",
        "authority": {key: False for key in sorted(AUTHORITY_KEYS)},
    }


def github_app_capability_state_from_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a normalized report into the state summary embedded in pilot state."""

    normalized_report = validate_github_app_private_pilot_capability_report(report)
    missing = missing_required_read_permissions(normalized_report)
    if missing:
        status = "missing_required_read_permissions"
    elif normalized_report["capabilities"]["workflow_dispatch"]:
        status = "read_only_with_workflow_dispatch"
    else:
        status = "read_only_capable"
    return {
        "status": status,
        "report_present": True,
        "missing_permissions": missing,
        "read_only": {
            key: normalized_report["capabilities"][key] for key in sorted(READ_ONLY_STATE_KEYS)
        },
        "workflow_dispatch_label": normalized_report["workflow_dispatch"]["label"],
        "authority": dict(normalized_report["authority"]),
    }


def normalize_github_app_capability_state(payload: Any) -> dict[str, Any]:
    """Validate and normalize the capability summary stored in pilot state."""

    if not isinstance(payload, Mapping):
        raise GithubAppPrivatePilotCapabilityError("github_app_capability must be a JSON object.")
    _require_exact_keys(payload, REPORT_STATE_KEYS, label="github_app_capability")
    status = _require_id(payload, "status", label="github_app_capability")
    if status not in CAPABILITY_STATUSES:
        raise GithubAppPrivatePilotCapabilityError("github_app_capability.status is unsupported.")
    report_present = _require_bool(
        payload, "report_present", expected=None, label="github_app_capability"
    )
    missing_raw = payload["missing_permissions"]
    if not isinstance(missing_raw, list):
        raise GithubAppPrivatePilotCapabilityError(
            "github_app_capability.missing_permissions must be a list."
        )
    missing = [
        _require_id({"permission": permission}, "permission", label="github_app_capability")
        for permission in missing_raw
    ]
    if missing != sorted(missing):
        raise GithubAppPrivatePilotCapabilityError(
            "github_app_capability.missing_permissions must be sorted."
        )
    if any(permission not in REQUIRED_READ_PERMISSIONS for permission in missing):
        raise GithubAppPrivatePilotCapabilityError(
            "github_app_capability.missing_permissions has unsupported entries."
        )
    read_only_raw = payload["read_only"]
    if not isinstance(read_only_raw, Mapping):
        raise GithubAppPrivatePilotCapabilityError(
            "github_app_capability.read_only must be a JSON object."
        )
    _require_exact_keys(
        read_only_raw,
        READ_ONLY_STATE_KEYS,
        label="github_app_capability.read_only",
    )
    read_only = {
        key: _require_bool(
            read_only_raw, key, expected=None, label="github_app_capability.read_only"
        )
        for key in sorted(READ_ONLY_STATE_KEYS)
    }
    dispatch_label = _require_id(payload, "workflow_dispatch_label", label="github_app_capability")
    if dispatch_label not in WORKFLOW_DISPATCH_LABELS:
        raise GithubAppPrivatePilotCapabilityError(
            "github_app_capability.workflow_dispatch_label is unsupported."
        )
    authority = _normalize_authority(
        payload["authority"],
        expected={
            **{key: False for key in sorted(AUTHORITY_KEYS)},
            "read_actions": read_only["actions_read"],
            "read_checks": read_only["checks_read"],
            "read_contents": read_only["contents_read"],
            "read_metadata": read_only["metadata_read"],
            "read_pull_requests": read_only["pull_requests_read"],
            "workflow_dispatch": dispatch_label == "workflow_dispatch_actions_write_optional",
        },
    )
    if not report_present and (
        status != "manual_only"
        or missing
        or any(read_only.values())
        or dispatch_label != "not_checked"
        or any(authority.values())
    ):
        raise GithubAppPrivatePilotCapabilityError(
            "github_app_capability not-checked state must be manual-only."
        )
    if report_present:
        if read_only["contents_read"]:
            raise GithubAppPrivatePilotCapabilityError(
                "github_app_capability contents read is not part of the private-pilot gate."
            )
        if (
            read_only["actions_read"]
            and dispatch_label != "workflow_dispatch_actions_write_optional"
        ):
            raise GithubAppPrivatePilotCapabilityError(
                "github_app_capability actions read is allowed only for workflow dispatch."
            )
        if dispatch_label == "not_checked":
            raise GithubAppPrivatePilotCapabilityError(
                "github_app_capability.workflow_dispatch_label must be checked when report is present."
            )
        if (
            dispatch_label == "workflow_dispatch_actions_write_optional"
            and not read_only["actions_read"]
        ):
            raise GithubAppPrivatePilotCapabilityError(
                "github_app_capability workflow dispatch requires actions read/write capability."
            )
        expected_missing = []
        if not read_only["pull_requests_read"]:
            expected_missing.append("pull_requests:read")
        if not read_only["checks_read"]:
            expected_missing.append("checks:read")
        expected_missing = sorted(expected_missing)
        if missing != expected_missing:
            raise GithubAppPrivatePilotCapabilityError(
                "github_app_capability.missing_permissions must match read booleans."
            )
        expected_status = (
            "missing_required_read_permissions"
            if missing
            else (
                "read_only_with_workflow_dispatch"
                if dispatch_label == "workflow_dispatch_actions_write_optional"
                else "read_only_capable"
            )
        )
        if status != expected_status:
            raise GithubAppPrivatePilotCapabilityError(
                f"github_app_capability.status must equal {expected_status!r}."
            )
    normalized = {
        "status": status,
        "report_present": report_present,
        "missing_permissions": missing,
        "read_only": read_only,
        "workflow_dispatch_label": dispatch_label,
        "authority": authority,
    }
    reject_unsafe_report_value(normalized, label="github_app_capability")
    return normalized
