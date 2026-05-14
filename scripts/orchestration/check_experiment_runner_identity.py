#!/usr/bin/env python3
"""Validate the governed Experiment Runner non-human identity policy."""

from __future__ import annotations

import argparse
from email.utils import parseaddr
import json
from pathlib import Path
import re
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = (
    REPO_ROOT / "docs" / "orchestration" / "GOVERNED_NON_HUMAN_IDENTITY_POLICY.json"
)
EXPECTED_SCHEMA_VERSION = "1.0"
EXPECTED_IDENTITY_SLUG = "experiment-runner"
EXPECTED_DISPLAY_NAME = "PulsePlate Experiment Runner"
EXPECTED_EMAIL = "pulseplate@pm.me"
FORBIDDEN_EMAILS = frozenset({"runner@example.com"})
ALLOWED_SIGNING_METHODS = frozenset({"ssh", "gpg", "github_app_verified_signature"})
SENSITIVE_FIELD_RE = re.compile(
    r"(private[\s_-]*key|pass[\s_-]*phrase|secret|token|credential|signing[\s_-]*key)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_RE = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abcprs]-[A-Za-z0-9-]{10,}|xapp-[A-Za-z0-9-]{10,})",
    re.IGNORECASE,
)
AUTHORITY_FIELD_NAMES = frozenset(
    {
        "merge_rights",
        "can_claim_merge_readiness",
        "can_resolve_review_threads",
        "can_push_without_human_review",
    }
)
CANONICAL_SENSITIVE_BOOLEAN_PATHS = frozenset(
    {
        "$.cryptographic_boundary.commit_signing_required_for_autonomous_production_commits",
        "$.cryptographic_boundary.private_key_material_allowed_in_repo",
        "$.cryptographic_boundary.repo_must_not_generate_private_keys",
        "$.cryptographic_boundary.repo_must_not_store_signing_secrets",
        "$.slack_identity.requires_bot_token_secret_boundary",
    }
)


class IdentityPolicyError(ValueError):
    """Raised when the Experiment Runner identity policy is unsafe."""


def _read_policy(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityPolicyError("Unable to read Experiment Runner identity policy.") from exc
    if not isinstance(payload, dict):
        raise IdentityPolicyError("Experiment Runner identity policy must be a JSON object.")
    return payload


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise IdentityPolicyError(f"{key} must be a JSON object.")
    return value


def _require_bool(mapping: dict[str, Any], key: str, expected: bool) -> None:
    if mapping.get(key) is not expected:
        raise IdentityPolicyError(f"{key} must be {str(expected).lower()}.")


def _normalized_email(raw_email: Any) -> str:
    if not isinstance(raw_email, str):
        raise IdentityPolicyError("git_attribution.email must be a string.")
    display_name, email = parseaddr(raw_email)
    if display_name or email != raw_email or not email:
        raise IdentityPolicyError("git_attribution.email must be a bare email address.")
    if email.lower() != email:
        raise IdentityPolicyError("git_attribution.email must be lowercase.")
    if email in FORBIDDEN_EMAILS or email.endswith("@example.com"):
        raise IdentityPolicyError("Experiment Runner attribution must not use placeholder email.")
    return email


def _path_for_key(path: str, key: Any) -> str:
    if not isinstance(key, str):
        return f"{path}.<non-string-key>"
    if SENSITIVE_VALUE_RE.search(key):
        return f"{path}.<redacted-key>"
    return f"{path}.{key}"


def _normalized_policy_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")


def _reject_private_key_material(payload: Any, *, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = _path_for_key(path, key)
            if isinstance(key, str) and SENSITIVE_VALUE_RE.search(key):
                raise IdentityPolicyError(
                    f"{next_path} must not store private key material or secrets."
                )
            if SENSITIVE_FIELD_RE.search(str(key)):
                allowed_marker = isinstance(value, str) and value in {"none", "external"}
                allowed_canonical_bool = (
                    next_path in CANONICAL_SENSITIVE_BOOLEAN_PATHS and isinstance(value, bool)
                )
                if not allowed_canonical_bool and not allowed_marker:
                    raise IdentityPolicyError(
                        f"{next_path} must not store private key material or secrets."
                    )
            _reject_private_key_material(value, path=next_path)
        return
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            _reject_private_key_material(item, path=f"{path}[{index}]")
        return
    if isinstance(payload, str) and SENSITIVE_VALUE_RE.search(payload):
        raise IdentityPolicyError(f"{path} must not store private key material or secrets.")


def _reject_authority_drift(payload: Any, *, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = _path_for_key(path, key)
            if (
                path != "$.authority_boundary"
                and _normalized_policy_key(key) in AUTHORITY_FIELD_NAMES
                and value is not False
                and value != "none"
            ):
                raise IdentityPolicyError(
                    f"{next_path} must not grant Experiment Runner authority."
                )
            _reject_authority_drift(value, path=next_path)
        return
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            _reject_authority_drift(item, path=f"{path}[{index}]")


def validate_identity_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a validated identity policy or raise IdentityPolicyError."""

    _reject_authority_drift(payload)
    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise IdentityPolicyError("schema_version must be 1.0.")
    if payload.get("identity_slug") != EXPECTED_IDENTITY_SLUG:
        raise IdentityPolicyError("identity_slug must be experiment-runner.")
    if payload.get("display_name") != EXPECTED_DISPLAY_NAME:
        raise IdentityPolicyError("display_name must be PulsePlate Experiment Runner.")

    git_attribution = _require_mapping(payload, "git_attribution")
    if git_attribution.get("name") != EXPECTED_DISPLAY_NAME:
        raise IdentityPolicyError("git_attribution.name must match display_name.")
    if _normalized_email(git_attribution.get("email")) != EXPECTED_EMAIL:
        raise IdentityPolicyError("git_attribution.email must be pulseplate@pm.me.")
    if git_attribution.get("purpose") != "public_attribution_only":
        raise IdentityPolicyError("git_attribution.purpose must be public_attribution_only.")
    forbidden = git_attribution.get("forbidden_placeholder_emails")
    if not isinstance(forbidden, list) or not all(isinstance(entry, str) for entry in forbidden):
        raise IdentityPolicyError("forbidden_placeholder_emails must be a list of email strings.")
    if not FORBIDDEN_EMAILS.issubset(set(forbidden)):
        raise IdentityPolicyError("forbidden_placeholder_emails must include runner@example.com.")

    authority_boundary = _require_mapping(payload, "authority_boundary")
    if authority_boundary.get("merge_rights") != "none":
        raise IdentityPolicyError("authority_boundary.merge_rights must be none.")
    _require_bool(authority_boundary, "can_claim_merge_readiness", False)
    _require_bool(authority_boundary, "can_resolve_review_threads", False)
    _require_bool(authority_boundary, "can_push_without_human_review", False)
    if authority_boundary.get("allowed_commit_context") != "repo_local_pr_lane_only":
        raise IdentityPolicyError(
            "authority_boundary.allowed_commit_context must be repo_local_pr_lane_only."
        )

    cryptographic_boundary = _require_mapping(payload, "cryptographic_boundary")
    if cryptographic_boundary.get("status") != "operator_managed_external":
        raise IdentityPolicyError(
            "cryptographic_boundary.status must be operator_managed_external."
        )
    _require_bool(cryptographic_boundary, "verified_account_required", True)
    _require_bool(
        cryptographic_boundary,
        "commit_signing_required_for_autonomous_production_commits",
        True,
    )
    _require_bool(cryptographic_boundary, "private_key_material_allowed_in_repo", False)
    _require_bool(cryptographic_boundary, "repo_must_not_generate_private_keys", True)
    _require_bool(cryptographic_boundary, "repo_must_not_store_signing_secrets", True)
    methods = cryptographic_boundary.get("allowed_signing_methods")
    if not isinstance(methods, list) or not all(isinstance(method, str) for method in methods):
        raise IdentityPolicyError(
            "allowed_signing_methods must be a list of signing method strings."
        )
    if set(methods) != ALLOWED_SIGNING_METHODS:
        raise IdentityPolicyError("allowed_signing_methods must be ssh, gpg, and GitHub App.")

    notification_boundary = _require_mapping(payload, "notification_boundary")
    _require_bool(notification_boundary, "git_email_is_delivery_channel", False)
    if (
        notification_boundary.get("experiment_result_delivery")
        != "experiment_notify_explicit_sink_only"
    ):
        raise IdentityPolicyError(
            "notification_boundary.experiment_result_delivery must be "
            "experiment_notify_explicit_sink_only."
        )
    if notification_boundary.get("default_sink") != "local_artifact":
        raise IdentityPolicyError("notification_boundary.default_sink must be local_artifact.")
    if notification_boundary.get("v1_email_recipient") != EXPECTED_EMAIL:
        raise IdentityPolicyError(
            "notification_boundary.v1_email_recipient must be pulseplate@pm.me."
        )

    slack_identity = _require_mapping(payload, "slack_identity")
    if slack_identity.get("status") != "deferred":
        raise IdentityPolicyError("slack_identity.status must remain deferred in this policy PR.")
    if slack_identity.get("purpose") != "ops_notification_display_identity_only":
        raise IdentityPolicyError(
            "slack_identity.purpose must be ops_notification_display_identity_only."
        )
    _require_bool(slack_identity, "not_cryptographic_identity", True)
    _require_bool(slack_identity, "requires_separate_security_pr", True)
    _require_bool(slack_identity, "requires_bot_token_secret_boundary", True)
    _require_bool(slack_identity, "requires_channel_allowlist", True)
    _require_bool(slack_identity, "requires_audit_artifact", True)

    _reject_private_key_material(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH), help="Policy JSON path.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable status.")
    args = parser.parse_args(argv)

    try:
        policy = validate_identity_policy(_read_policy(Path(args.policy)))
    except IdentityPolicyError as exc:
        if args.json:
            print(json.dumps({"status": "fail", "error": str(exc)}, sort_keys=True))
        else:
            print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    result = {
        "status": "pass",
        "identity_slug": policy["identity_slug"],
        "git_email": policy["git_attribution"]["email"],
        "slack_identity": policy["slack_identity"]["status"],
    }
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            "PASS: Experiment Runner identity policy is governed, "
            "attribution-only, and externally signed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
