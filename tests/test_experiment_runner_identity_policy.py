"""Tests for governed Experiment Runner identity policy validation."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.orchestration import check_experiment_runner_identity as identity_check


def _valid_policy() -> dict[str, Any]:
    return deepcopy(identity_check._read_policy(identity_check.DEFAULT_POLICY_PATH))


def test_default_policy_validates() -> None:
    policy = identity_check.validate_identity_policy(_valid_policy())

    assert policy["identity_slug"] == "experiment-runner"
    assert policy["git_attribution"]["email"] == "pulseplate@pm.me"
    assert policy["slack_identity"]["status"] == "deferred"


def test_rejects_placeholder_runner_email() -> None:
    policy = _valid_policy()
    policy["git_attribution"]["email"] = "runner@example.com"

    with pytest.raises(identity_check.IdentityPolicyError, match="placeholder email"):
        identity_check.validate_identity_policy(policy)


def test_rejects_non_allowlisted_git_email() -> None:
    policy = _valid_policy()
    policy["git_attribution"]["email"] = "ops@pulseplate.app"

    with pytest.raises(identity_check.IdentityPolicyError, match="pulseplate@pm.me"):
        identity_check.validate_identity_policy(policy)


def test_rejects_repo_private_key_material() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["private" + "_key"] = "stored"

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


def test_rejects_repo_private_key_material_with_spaced_key_name() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["private key"] = "stored"

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


def test_rejects_repo_private_key_material_with_repeated_separators() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["private   key"] = "stored"

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


def test_rejects_sensitive_field_object_without_type_error() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["private_key"] = {"stored": True}

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


def test_rejects_private_key_material_under_neutral_key() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["operator_note"] = (
        "-----BEGIN " "PRIVATE KEY-----\n" "abc123\n" "-----END " "PRIVATE KEY-----"
    )

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


@pytest.mark.parametrize(
    "secret_value",
    [
        "github_pat_" + "a" * 24,
        "xapp-" + "b" * 24,
        "xoxc-" + "c" * 24,
    ],
)
def test_rejects_current_token_prefixes_under_neutral_key(secret_value: str) -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["operator_note"] = secret_value

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


def test_rejects_token_shaped_json_key() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["external_handles"] = {"github_pat_" + "a" * 24: "external"}

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


def test_rejects_missing_external_signing_requirement() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"][
        "commit_signing_required_for_autonomous_production_commits"
    ] = False

    with pytest.raises(identity_check.IdentityPolicyError, match="commit_signing"):
        identity_check.validate_identity_policy(policy)


def test_rejects_malformed_forbidden_placeholder_email_entries() -> None:
    policy = _valid_policy()
    policy["git_attribution"]["forbidden_placeholder_emails"] = ["runner@example.com", {}]

    with pytest.raises(identity_check.IdentityPolicyError, match="email strings"):
        identity_check.validate_identity_policy(policy)


def test_rejects_malformed_allowed_signing_method_entries() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["allowed_signing_methods"] = [
        "ssh",
        "gpg",
        {"provider": "github_app_verified_signature"},
    ]

    with pytest.raises(identity_check.IdentityPolicyError, match="signing method strings"):
        identity_check.validate_identity_policy(policy)


def test_rejects_autonomous_commit_context_drift() -> None:
    policy = _valid_policy()
    policy["authority_boundary"]["allowed_commit_context"] = "production_autonomous"

    with pytest.raises(identity_check.IdentityPolicyError, match="allowed_commit_context"):
        identity_check.validate_identity_policy(policy)


def test_rejects_authority_drift_outside_main_boundary() -> None:
    policy = _valid_policy()
    policy["github_app_authority"] = {
        "merge_rights": "admin",
        "can_resolve_review_threads": True,
    }

    with pytest.raises(identity_check.IdentityPolicyError, match="must not grant"):
        identity_check.validate_identity_policy(policy)


def test_rejects_notification_delivery_drift() -> None:
    policy = _valid_policy()
    policy["notification_boundary"]["experiment_result_delivery"] = "smtp_email"

    with pytest.raises(identity_check.IdentityPolicyError, match="experiment_result_delivery"):
        identity_check.validate_identity_policy(policy)


def test_rejects_slack_as_active_crypto_identity() -> None:
    policy = _valid_policy()
    policy["slack_identity"]["status"] = "active"

    with pytest.raises(identity_check.IdentityPolicyError, match="slack_identity.status"):
        identity_check.validate_identity_policy(policy)


def test_rejects_slack_purpose_as_crypto_identity() -> None:
    policy = _valid_policy()
    policy["slack_identity"]["purpose"] = "active_crypto_identity"

    with pytest.raises(identity_check.IdentityPolicyError, match="slack_identity.purpose"):
        identity_check.validate_identity_policy(policy)


def test_cli_json_success(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = identity_check.main(["--json"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "git_email": "pulseplate@pm.me",
        "identity_slug": "experiment-runner",
        "slack_identity": "deferred",
        "status": "pass",
    }


def test_cli_json_failure_is_sanitized(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    policy = _valid_policy()
    policy["git_attribution"]["email"] = "runner@example.com"
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    exit_code = identity_check.main(["--policy", str(policy_path), "--json"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["status"] == "fail"
    assert "runner@example.com" not in output["error"]
