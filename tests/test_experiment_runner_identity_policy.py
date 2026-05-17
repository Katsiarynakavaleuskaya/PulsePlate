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
    assert (
        policy["git_attribution"]["co_author_trailer"]
        == "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>"
    )
    assert policy["slack_identity"]["status"] == "deferred"


def test_default_co_author_guidance_validates() -> None:
    identity_check.validate_co_author_guidance()


def test_rejects_missing_co_author_trailer() -> None:
    policy = _valid_policy()
    policy["git_attribution"].pop("co_author_trailer")

    with pytest.raises(identity_check.IdentityPolicyError, match="co_author_trailer"):
        identity_check.validate_identity_policy(policy)


def test_rejects_placeholder_co_author_guidance(tmp_path: Path) -> None:
    guidance_path = tmp_path / "AGENTS.md"
    guidance_path.write_text(
        "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        "Co-authored-by: Experiment Runner <runner@example.com>\n",
        encoding="utf-8",
    )

    with pytest.raises(identity_check.IdentityPolicyError, match="placeholder"):
        identity_check.validate_co_author_guidance((guidance_path,))


def test_rejects_placeholder_co_author_email_with_governed_name(tmp_path: Path) -> None:
    guidance_path = tmp_path / "AGENTS.md"
    guidance_path.write_text(
        "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        "Co-authored-by: PulsePlate Experiment Runner <runner@example.com>\n",
        encoding="utf-8",
    )

    with pytest.raises(identity_check.IdentityPolicyError, match="placeholder"):
        identity_check.validate_co_author_guidance((guidance_path,))


def test_rejects_placeholder_co_author_email_with_angle_whitespace(tmp_path: Path) -> None:
    guidance_path = tmp_path / "AGENTS.md"
    guidance_path.write_text(
        "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>\n"
        "Co-authored-by: PulsePlate Experiment Runner < runner@example.com >\n",
        encoding="utf-8",
    )

    with pytest.raises(identity_check.IdentityPolicyError, match="placeholder"):
        identity_check.validate_co_author_guidance((guidance_path,))


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

    with pytest.raises(identity_check.IdentityPolicyError, match="cryptographic_boundary"):
        identity_check.validate_identity_policy(policy)


def test_rejects_repo_private_key_material_with_spaced_key_name() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["private key"] = "stored"

    with pytest.raises(identity_check.IdentityPolicyError, match="cryptographic_boundary"):
        identity_check.validate_identity_policy(policy)


def test_rejects_repo_private_key_material_with_repeated_separators() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["private   key"] = "stored"

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


@pytest.mark.parametrize(
    "field_name",
    [
        "api_key",
        "access_key_id",
        "accessKeyId",
        "github_app_api_key",
        "github_app_password",
        "bot_password",
        "private.key",
        "privateSshKey",
        "privateSigningKey",
        "private ssh key",
        "signing/key",
        "pass.phrase",
    ],
)
def test_rejects_sensitive_field_names_with_punctuation(field_name: str) -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"][field_name] = "stored"

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


def test_rejects_pgp_private_key_material_under_neutral_key() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary"]["operator_note"] = (
        "-----BEGIN "
        "PGP PRIVATE KEY BLOCK-----\n"
        "abc123\n"
        "-----END "
        "PGP PRIVATE KEY BLOCK-----"
    )

    with pytest.raises(identity_check.IdentityPolicyError, match="private key material"):
        identity_check.validate_identity_policy(policy)


@pytest.mark.parametrize(
    "secret_value",
    [
        "github_pat_" + "a" * 24,
        "https://hooks.slack.com/services/" + "A" * 12 + "/" + "B" * 12 + "/" + "C" * 24,
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


def test_rejects_duplicate_json_keys_before_validation(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        '{"schema_version": "admin", "schema_version": "1.0"}',
        encoding="utf-8",
    )

    with pytest.raises(identity_check.IdentityPolicyError, match="duplicate JSON keys"):
        identity_check._read_policy(policy_path)


def test_token_shaped_json_key_error_is_redacted() -> None:
    policy = _valid_policy()
    token_value = "github_pat_" + "a" * 24
    policy["cryptographic_boundary"]["external_handles"] = {token_value: "external"}

    with pytest.raises(identity_check.IdentityPolicyError) as exc_info:
        identity_check.validate_identity_policy(policy)

    error = str(exc_info.value)
    assert token_value not in error
    assert "<redacted-key>" in error


def test_sensitive_field_name_error_is_redacted() -> None:
    policy = _valid_policy()
    sensitive_field = "secret my-real-password"
    policy["cryptographic_boundary"][sensitive_field] = "stored"

    with pytest.raises(identity_check.IdentityPolicyError) as exc_info:
        identity_check.validate_identity_policy(policy)

    error = str(exc_info.value)
    assert sensitive_field not in error
    assert "<redacted-key>" in error


def test_cli_json_failure_redacts_token_shaped_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    policy = _valid_policy()
    token_value = "github_pat_" + "a" * 24
    policy["cryptographic_boundary"]["external_handles"] = {token_value: "external"}
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    exit_code = identity_check.main(["--policy", str(policy_path), "--json"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output["status"] == "fail"
    assert token_value not in output["error"]
    assert "<redacted-key>" in output["error"]


def test_rejects_duplicate_crypto_boundary_boolean_outside_canon() -> None:
    policy = _valid_policy()
    policy["cryptographic_boundary_v2"] = {
        "private_key_material_allowed_in_repo": True,
    }

    with pytest.raises(identity_check.IdentityPolicyError, match="cryptographic_boundary"):
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


def test_authority_drift_error_redacts_secret_shaped_ancestor() -> None:
    policy = _valid_policy()
    token_value = "github_pat_" + "a" * 24
    policy[token_value] = {"merge_rights": "admin"}

    with pytest.raises(identity_check.IdentityPolicyError) as exc_info:
        identity_check.validate_identity_policy(policy)

    error = str(exc_info.value)
    assert token_value not in error
    assert "<redacted-key>" in error


def test_authority_drift_error_redacts_dotted_sensitive_ancestor() -> None:
    policy = _valid_policy()
    sensitive_key = "secret.my-real-password"
    policy[sensitive_key] = {"merge_rights": "admin"}

    with pytest.raises(identity_check.IdentityPolicyError) as exc_info:
        identity_check.validate_identity_policy(policy)

    error = str(exc_info.value)
    assert "my-real-password" not in error
    assert "<redacted-key>" in error


def test_rejects_authority_drift_with_separator_variants() -> None:
    policy = _valid_policy()
    policy["github_app_authority"] = {
        "merge-rights": "admin",
        "can resolve review threads": True,
    }

    with pytest.raises(identity_check.IdentityPolicyError, match="must not grant"):
        identity_check.validate_identity_policy(policy)


def test_rejects_authority_drift_with_camel_case_variants() -> None:
    policy = _valid_policy()
    policy["github_app_authority"] = {
        "mergeRights": "admin",
        "canResolveReviewThreads": True,
        "allowedCommitContext": "production_autonomous",
    }

    with pytest.raises(identity_check.IdentityPolicyError, match="must not grant"):
        identity_check.validate_identity_policy(policy)


def test_rejects_authority_drift_variants_inside_canonical_boundary() -> None:
    policy = _valid_policy()
    policy["authority_boundary"]["mergerights"] = "admin"

    with pytest.raises(identity_check.IdentityPolicyError, match="must not duplicate"):
        identity_check.validate_identity_policy(policy)


@pytest.mark.parametrize("authority_alias", ["merge-rights", "mergeRights"])
def test_rejects_separated_authority_drift_inside_canonical_boundary(
    authority_alias: str,
) -> None:
    policy = _valid_policy()
    policy["authority_boundary"][authority_alias] = "admin"

    with pytest.raises(identity_check.IdentityPolicyError, match="must not duplicate"):
        identity_check.validate_identity_policy(policy)


def test_rejects_duplicate_commit_context_authority_drift() -> None:
    policy = _valid_policy()
    policy["authority_boundary_v2"] = {
        "allowed_commit_context": "production_autonomous",
    }

    with pytest.raises(identity_check.IdentityPolicyError, match="authority_boundary"):
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


def test_rejects_duplicate_slack_identity_boundary() -> None:
    policy = _valid_policy()
    policy["slack_identity_v2"] = {
        "status": "active",
        "not_cryptographic_identity": False,
    }

    with pytest.raises(identity_check.IdentityPolicyError, match="duplicate slack_identity"):
        identity_check.validate_identity_policy(policy)


def test_rejects_duplicate_slack_identity_camel_case_boundary() -> None:
    policy = _valid_policy()
    policy["slackIdentity"] = {
        "status": "active",
        "not_cryptographic_identity": False,
    }

    with pytest.raises(identity_check.IdentityPolicyError, match="duplicate slack_identity"):
        identity_check.validate_identity_policy(policy)


@pytest.mark.parametrize(
    ("boundary_name", "expected_boundary"),
    [
        ("git_attribution_v2", "git_attribution"),
        ("new_git_attribution", "git_attribution"),
        ("notificationBoundaryV2", "notification_boundary"),
        ("experimental_notification_boundary", "notification_boundary"),
        ("cryptographic-boundary-v2", "cryptographic_boundary"),
        ("github_app_cryptographic_boundary", "cryptographic_boundary"),
    ],
)
def test_rejects_duplicate_non_slack_boundary_blocks(
    boundary_name: str,
    expected_boundary: str,
) -> None:
    policy = _valid_policy()
    policy[boundary_name] = {"status": "active"}

    with pytest.raises(identity_check.IdentityPolicyError, match=expected_boundary):
        identity_check.validate_identity_policy(policy)


def test_duplicate_boundary_error_redacts_secret_shaped_ancestor() -> None:
    policy = _valid_policy()
    token_value = "github_pat_" + "a" * 24
    policy[token_value] = {"git_attribution_v2": {"email": "runner@example.com"}}

    with pytest.raises(identity_check.IdentityPolicyError) as exc_info:
        identity_check.validate_identity_policy(policy)

    error = str(exc_info.value)
    assert token_value not in error
    assert "<redacted-key>" in error


def test_rejects_slack_purpose_as_crypto_identity() -> None:
    policy = _valid_policy()
    policy["slack_identity"]["purpose"] = "active_crypto_identity"

    with pytest.raises(identity_check.IdentityPolicyError, match="slack_identity.purpose"):
        identity_check.validate_identity_policy(policy)


def test_cli_json_success(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = identity_check.main(["--json"])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "co_author_trailer": "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>",
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
