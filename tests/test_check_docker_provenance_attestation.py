"""Tests for OCI image attestation verification helper."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import scripts.ci.check_docker_provenance_attestation as verifier


def _synthetic_private_index_url() -> str:
    """Return runtime-only secret-shaped test data without a static finding."""

    return "".join(
        (
            "https://",
            "ci-user",
            ":",
            "TOKEN",
            "_FOR",
            "_TEST",
            "@private.invalid/simple",
        )
    )


def _completed_process(payload: object) -> subprocess.CompletedProcess[str]:
    """Return a completed process with JSON stdout."""

    return subprocess.CompletedProcess(
        args=["gh", "attestation", "verify"],
        returncode=0,
        stdout=json.dumps(payload),
        stderr="",
    )


def _verified_payload(predicate_type: str) -> list[dict[str, object]]:
    """Return a minimal successful verification payload."""

    return [
        {
            "verificationResult": {
                "statement": {
                    "predicateType": predicate_type,
                }
            }
        }
    ]


def test_build_artifact_uri_uses_exact_digest() -> None:
    assert (
        verifier.build_artifact_uri("ghcr.io/katsiarynakavaleuskaya/pulseplate", "sha256:abc123")
        == "oci://ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:abc123"
    )


@pytest.mark.parametrize(
    ("image_name", "digest", "error"),
    (
        ("", "sha256:abc123", "image_name"),
        ("oci://ghcr.io/test/image", "sha256:abc123", "oci://"),
        ("ghcr.io/test/image", "latest", "sha256"),
    ),
)
def test_build_artifact_uri_rejects_invalid_inputs(
    image_name: str,
    digest: str,
    error: str,
) -> None:
    with pytest.raises(RuntimeError, match=error):
        verifier.build_artifact_uri(image_name, digest)


def test_verify_attestations_runs_provenance_and_sbom_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        predicate_type = verifier.PROVENANCE_PREDICATE_TYPE
        if "--predicate-type" in args:
            predicate_type = args[args.index("--predicate-type") + 1]
        return _completed_process(_verified_payload(predicate_type))

    monkeypatch.setattr(verifier, "_run_gh", fake_run_gh)

    bundle = verifier.verify_attestations(
        image_name="ghcr.io/katsiarynakavaleuskaya/pulseplate",
        digest="sha256:abc123",
        repo="Katsiarynakavaleuskaya/PulsePlate",
        signer_workflow="Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml",
        source_ref="refs/heads/main",
    )

    assert bundle.passed is True
    assert bundle.artifact_uri == "oci://ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:abc123"
    assert bundle.provenance.attestation_count == 1
    assert bundle.sbom.attestation_count == 1
    assert len(calls) == 2

    provenance_call, sbom_call = calls
    assert provenance_call[0:3] == [
        "attestation",
        "verify",
        "oci://ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:abc123",
    ]
    assert "--repo" in provenance_call
    assert "--signer-workflow" in provenance_call
    assert "--source-ref" in provenance_call
    assert "--bundle-from-oci" in provenance_call
    assert "--deny-self-hosted-runners" in provenance_call
    assert "--predicate-type" not in provenance_call

    assert "--predicate-type" in sbom_call
    assert sbom_call[sbom_call.index("--predicate-type") + 1] == "https://spdx.dev/Document/v2.3"


def test_verify_attestations_fails_closed_on_missing_attestations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def fake_run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls["count"] += 1
        if calls["count"] == 1:
            return _completed_process(_verified_payload(verifier.PROVENANCE_PREDICATE_TYPE))
        return _completed_process([])

    monkeypatch.setattr(verifier, "_run_gh", fake_run_gh)

    with pytest.raises(RuntimeError, match="at least one attestation"):
        verifier.verify_attestations(
            image_name="ghcr.io/katsiarynakavaleuskaya/pulseplate",
            digest="sha256:abc123",
            repo="Katsiarynakavaleuskaya/PulsePlate",
            signer_workflow="Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml",
            source_ref="refs/heads/main",
        )


def test_parser_accepts_wrapped_verification_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub CLI format drift should stay debuggable but fail closed."""

    calls = {"count": 0}

    def fake_run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls["count"] += 1
        predicate_type = verifier.PROVENANCE_PREDICATE_TYPE
        if "--predicate-type" in args:
            predicate_type = args[args.index("--predicate-type") + 1]
        return _completed_process({"verifications": _verified_payload(predicate_type)})

    monkeypatch.setattr(verifier, "_run_gh", fake_run_gh)

    bundle = verifier.verify_attestations(
        image_name="ghcr.io/katsiarynakavaleuskaya/pulseplate",
        digest="sha256:abc123",
        repo="Katsiarynakavaleuskaya/PulsePlate",
        signer_workflow="Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml",
        source_ref="refs/heads/main",
    )

    assert calls["count"] == 2
    assert bundle.provenance.attestation_count == 1
    assert bundle.sbom.attestation_count == 1


def test_parser_redacts_raw_attestation_build_arguments() -> None:
    secret_index_url = _synthetic_private_index_url()
    raw_statement = {
        "predicateType": verifier.PROVENANCE_PREDICATE_TYPE,
        "predicate": {
            "buildDefinition": {
                "externalParameters": {"build-arg:PULSEPLATE_PYTHON_INDEX_URL": secret_index_url}
            }
        },
    }
    payload = [{"verificationResult": {"statement": raw_statement}}]

    parsed = verifier._parse_verification_output(
        stdout=json.dumps(payload),
        predicate_type=verifier.PROVENANCE_PREDICATE_TYPE,
        label="provenance",
    )

    serialized = json.dumps(parsed, sort_keys=True)
    assert secret_index_url not in serialized
    assert "TOKEN_FOR_TEST" not in serialized
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in serialized
    assert "redacted_statement_summary_sha256" in serialized
    assert verifier._canonical_json_sha256(raw_statement) not in serialized
    assert parsed[0]["verificationResult"]["statement"]["predicateType"] == (
        verifier.PROVENANCE_PREDICATE_TYPE
    )


@pytest.mark.parametrize(
    "payload",
    (
        {"verificationResult": {"statement": {}}},
        {"verificationResult": {"statement": {"predicateType": 123}}},
    ),
)
def test_redacted_verification_summary_fails_closed_on_missing_predicate_type(
    payload: dict[str, object],
) -> None:
    with pytest.raises(RuntimeError, match="predicateType"):
        verifier._redacted_verification_summary(payload, index=0)


def test_failure_diagnostics_redact_attestation_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_index_url = _synthetic_private_index_url()
    json_out = tmp_path / "attestation.json"
    markdown_out = tmp_path / "attestation.md"

    def fake_verify_attestations(**_: object) -> verifier.VerificationBundle:
        raise RuntimeError(
            f"verification failed for PULSEPLATE_PYTHON_INDEX_URL={secret_index_url}"
        )

    monkeypatch.setattr(verifier, "verify_attestations", fake_verify_attestations)

    exit_code = verifier.main(
        [
            "--image-name",
            "ghcr.io/katsiarynakavaleuskaya/pulseplate",
            "--digest",
            "sha256:abc123",
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--signer-workflow",
            "Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml",
            "--source-ref",
            "refs/heads/main",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert exit_code == 1
    stderr = capsys.readouterr().err
    failure_payload = json.loads(json_out.read_text(encoding="utf-8"))
    failure_markdown = markdown_out.read_text(encoding="utf-8")
    serialized = json.dumps(failure_payload, sort_keys=True) + failure_markdown + stderr
    assert secret_index_url not in serialized
    assert "TOKEN_FOR_TEST" not in serialized
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in serialized
    assert "[redacted-build-arg]" in serialized


def test_failure_diagnostics_redact_common_secret_shapes() -> None:
    token_key = "GITHUB" + "_" + "TOKEN"
    credential_key = "REGISTRY" + "_CREDENTIAL"
    raw_detail = " ".join(
        (
            f"{token_key}=ghs_example_token_value",
            "Bearer " + "eyJ" + ".example.token",
            f"{credential_key}=pw-12345",
            "plain text stays",
        )
    )

    redacted = verifier._redact_sensitive_text(raw_detail)

    assert "ghs_example_token_value" not in redacted
    assert "eyJ.example.token" not in redacted
    assert "pw-12345" not in redacted
    assert "[redacted-build-arg]" in redacted
    assert "Bearer [redacted-token]" in redacted
    assert f"{credential_key}=[redacted-secret]" in redacted
    assert "plain text stays" in redacted


def test_run_gh_redacts_subprocess_failure_output(monkeypatch: pytest.MonkeyPatch) -> None:
    secret_index_url = _synthetic_private_index_url()

    def fake_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["gh", "attestation", "verify"],
            output=f"stdout PULSEPLATE_PYTHON_INDEX_URL={secret_index_url}",
            stderr=f"stderr PULSEPLATE_PYTHON_INDEX_URL={secret_index_url}",
        )

    monkeypatch.setattr(verifier.shutil, "which", lambda _: "/usr/bin/gh")
    monkeypatch.setattr(verifier.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as exc_info:
        verifier._run_gh(["attestation", "verify", "oci://example@sha256:abc"])

    message = str(exc_info.value)
    assert secret_index_url not in message
    assert "TOKEN_FOR_TEST" not in message
    assert "PULSEPLATE_PYTHON_INDEX_URL" not in message
    assert "[redacted-build-arg]" in message


def test_parser_reports_unexpected_shape_with_trimmed_stdout() -> None:
    oversized_stdout = json.dumps({"unexpected": "x" * 600})

    with pytest.raises(RuntimeError, match="unexpected JSON shape"):
        verifier._parse_verification_output(
            stdout=oversized_stdout,
            predicate_type=verifier.PROVENANCE_PREDICATE_TYPE,
            label="provenance",
        )


def test_gh_timeout_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(verifier.GH_TIMEOUT_SECONDS_ENV, "240")

    assert verifier._gh_timeout_seconds() == 240


def test_gh_timeout_falls_back_on_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(verifier.GH_TIMEOUT_SECONDS_ENV, "not-an-int")

    assert verifier._gh_timeout_seconds() == verifier.GH_TIMEOUT_SECONDS_DEFAULT


def test_main_writes_failure_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_out = tmp_path / "attestation.json"
    markdown_out = tmp_path / "attestation.md"

    def fake_verify_attestations(**_: object) -> verifier.VerificationBundle:
        raise RuntimeError("verification failed")

    monkeypatch.setattr(verifier, "verify_attestations", fake_verify_attestations)

    exit_code = verifier.main(
        [
            "--image-name",
            "ghcr.io/katsiarynakavaleuskaya/pulseplate",
            "--digest",
            "sha256:abc123",
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--signer-workflow",
            "Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml",
            "--source-ref",
            "refs/heads/main",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert exit_code == 1
    failure_payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert failure_payload["passed"] is False
    assert failure_payload["error"] == "verification failed"
    assert "Passed: `false`" in markdown_out.read_text(encoding="utf-8")


def test_main_writes_failure_artifacts_for_invalid_artifact_uri(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    json_out = tmp_path / "attestation.json"
    markdown_out = tmp_path / "attestation.md"

    def fake_verify_attestations(**_: object) -> verifier.VerificationBundle:
        raise RuntimeError("image_name must not include the oci:// prefix.")

    monkeypatch.setattr(verifier, "verify_attestations", fake_verify_attestations)

    exit_code = verifier.main(
        [
            "--image-name",
            "oci://ghcr.io/katsiarynakavaleuskaya/pulseplate",
            "--digest",
            "sha256:abc123",
            "--repo",
            "Katsiarynakavaleuskaya/PulsePlate",
            "--signer-workflow",
            "Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml",
            "--source-ref",
            "refs/heads/main",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )

    assert exit_code == 1
    failure_payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert failure_payload["artifact_uri"] is None
    assert "Passed: `false`" in markdown_out.read_text(encoding="utf-8")
