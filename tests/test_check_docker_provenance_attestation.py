"""Tests for OCI image attestation verification helper."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import scripts.ci.check_docker_provenance_attestation as verifier


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
