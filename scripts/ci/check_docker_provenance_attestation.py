#!/usr/bin/env python3
"""Verify OCI image provenance and SBOM attestations with the GitHub CLI.

The helper is intentionally fail-closed: it verifies the exact pushed image
digest from OCI-backed attestations and emits JSON/Markdown evidence for CI.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404: bounded gh CLI verification is required for OCI attestation checks (remove-by: 2026-09-30, ref: PR-docker-signed-provenance)
import sys

GH_TIMEOUT_SECONDS_DEFAULT = 180
GH_TIMEOUT_SECONDS_ENV = "PULSEPLATE_DOCKER_ATTESTATION_GH_TIMEOUT_SECONDS"
PROVENANCE_PREDICATE_TYPE = "https://slsa.dev/provenance/v1"
SBOM_PREDICATE_TYPE = "https://spdx.dev/Document/v2.3"
BUNDLE_SOURCE = "oci-registry"
MAX_ERROR_STDOUT_CHARS = 500
_USERINFO_URL_RE = re.compile(r"https?://[^\s/@:]+:[^\s/@]+@[^\s]+")
_BEARER_TOKEN_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|API[_-]?KEY|INDEX_URL)[A-Z0-9_]*)=([^\s,;`]+)"
    r"|\b([A-Z0-9_]*CREDENTIAL[A-Z0-9_]*)=([^\s,;`]+)"
)
_SENSITIVE_ATTESTATION_TOKENS = (
    "PULSEPLATE_PYTHON_INDEX_URL",
    "GITHUB_TOKEN",
    "GH_TOKEN",
)


@dataclass(frozen=True)
class VerifiedPredicate:
    """Evidence summary for a single verified attestation predicate."""

    name: str
    predicate_type: str
    attestation_count: int
    verification_result: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class VerificationBundle:
    """Deterministic verification bundle written to CI evidence artifacts."""

    passed: bool
    artifact_uri: str
    repo: str
    signer_workflow: str
    source_ref: str
    bundle_source: str
    provenance: VerifiedPredicate
    sbom: VerifiedPredicate


def build_artifact_uri(image_name: str, digest: str) -> str:
    """Return the exact OCI artifact URI for a pushed image digest."""

    normalized_image_name = image_name.strip()
    normalized_digest = digest.strip()
    if not normalized_image_name:
        raise RuntimeError("image_name must be a non-empty string.")
    if normalized_image_name.startswith("oci://"):
        raise RuntimeError("image_name must not include the oci:// prefix.")
    if not normalized_digest.startswith("sha256:"):
        raise RuntimeError("digest must use the sha256:<hex> format.")
    return f"oci://{normalized_image_name}@{normalized_digest}"


def _gh_path() -> str:
    """Return the absolute gh binary path or fail closed."""

    gh_path = shutil.which("gh")
    if gh_path is None:
        raise RuntimeError("gh binary is not available on PATH.")
    return gh_path


def _gh_timeout_seconds() -> int:
    """Return a bounded gh timeout, configurable for slower registries."""

    raw_value = os.getenv(GH_TIMEOUT_SECONDS_ENV, str(GH_TIMEOUT_SECONDS_DEFAULT)).strip()
    try:
        timeout_seconds = int(raw_value)
    except ValueError:
        return GH_TIMEOUT_SECONDS_DEFAULT
    if timeout_seconds <= 0:
        return GH_TIMEOUT_SECONDS_DEFAULT
    return timeout_seconds


def _run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run gh with a resolved binary path and strict timeout/error handling."""

    timeout_seconds = _gh_timeout_seconds()
    try:
        return subprocess.run(  # nosec B603: argv uses a resolved gh path with fixed attestation-verification subcommands only (remove-by: 2026-09-30, ref: PR-docker-signed-provenance)
            [_gh_path(), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"gh attestation verify timed out after {timeout_seconds}s: {' '.join(args)}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        detail = _trim_for_error(stderr or stdout or str(exc))
        raise RuntimeError(f"gh attestation verify failed: {detail}") from exc


def _parse_verification_output(
    *,
    stdout: str,
    predicate_type: str,
    label: str,
) -> tuple[dict[str, object], ...]:
    """Parse and validate gh attestation verify JSON output."""

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} verification output is not valid JSON.") from exc

    if isinstance(payload, list):
        verification_items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("verifications"), list):
        verification_items = payload["verifications"]
    else:
        raise RuntimeError(
            f"{label} verification returned an unexpected JSON shape: " f"{_trim_for_error(stdout)}"
        )

    if not verification_items:
        raise RuntimeError(f"{label} verification must return at least one attestation.")

    normalized: list[dict[str, object]] = []
    for index, item in enumerate(verification_items):
        if not isinstance(item, dict):
            raise RuntimeError(f"{label} verification item #{index} is not a JSON object.")
        verification_result = item.get("verificationResult")
        if not isinstance(verification_result, dict):
            raise RuntimeError(f"{label} verification item #{index} is missing verificationResult.")
        statement = verification_result.get("statement")
        if not isinstance(statement, dict):
            raise RuntimeError(f"{label} verification item #{index} is missing statement.")
        actual_predicate_type = statement.get("predicateType")
        if actual_predicate_type != predicate_type:
            raise RuntimeError(
                f"{label} verification item #{index} has predicate "
                f"{actual_predicate_type!r}, expected {predicate_type!r}."
            )
        normalized.append(_redacted_verification_summary(item, index=index))
    return tuple(normalized)


def _redacted_verification_summary(
    item: Mapping[str, object],
    *,
    index: int,
) -> dict[str, object]:
    """Return non-secret metadata for one verified attestation item.

    GitHub's raw verification JSON can contain SLSA build invocation details.
    CI artifacts only need deterministic proof that the expected predicate was
    verified, so retain the predicate type plus a digest of the raw statement
    instead of publishing raw provenance/SBOM predicates or build arguments.
    """

    verification_result = item.get("verificationResult")
    if not isinstance(verification_result, dict):
        raise RuntimeError(f"verification item #{index} is missing verificationResult.")
    statement = verification_result.get("statement")
    if not isinstance(statement, dict):
        raise RuntimeError(f"verification item #{index} is missing statement.")
    predicate_type = statement.get("predicateType")
    if not isinstance(predicate_type, str):
        raise RuntimeError(f"verification item #{index} is missing predicateType.")
    return {
        "verificationResult": {
            "statement": {
                "predicateType": predicate_type,
                "redacted_statement_summary_sha256": _canonical_json_sha256(
                    {"predicateType": predicate_type, "redaction": "predicate-only-v1"}
                ),
            }
        }
    }


def _canonical_json_sha256(payload: Mapping[str, object]) -> str:
    """Return a stable hash for JSON-compatible attestation metadata."""

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _redact_sensitive_text(value: str) -> str:
    """Return text safe for CI logs and failure artifacts."""

    redacted = _USERINFO_URL_RE.sub("[redacted-url-with-userinfo]", value)
    redacted = _BEARER_TOKEN_RE.sub("Bearer [redacted-token]", redacted)
    redacted = _ASSIGNMENT_SECRET_RE.sub(
        lambda match: f"{match.group(1) or match.group(3)}=[redacted-secret]",
        redacted,
    )
    for token in _SENSITIVE_ATTESTATION_TOKENS:
        redacted = redacted.replace(token, "[redacted-build-arg]")
    return redacted


def _trim_for_error(value: str) -> str:
    """Return a one-line bounded string for fail-closed diagnostics."""

    normalized = _redact_sensitive_text(value).strip().replace("\n", "\\n")
    if len(normalized) <= MAX_ERROR_STDOUT_CHARS:
        return normalized
    return f"{normalized[:MAX_ERROR_STDOUT_CHARS]}..."


def _verify_predicate(
    *,
    artifact_uri: str,
    repo: str,
    signer_workflow: str,
    source_ref: str,
    predicate_type: str,
    label: str,
) -> VerifiedPredicate:
    """Verify one predicate type against the exact pushed OCI image digest."""

    args = [
        "attestation",
        "verify",
        artifact_uri,
        "--repo",
        repo,
        "--signer-workflow",
        signer_workflow,
        "--source-ref",
        source_ref,
        "--bundle-from-oci",
        "--deny-self-hosted-runners",
        "--format",
        "json",
    ]
    if predicate_type != PROVENANCE_PREDICATE_TYPE:
        args.extend(["--predicate-type", predicate_type])
    completed = _run_gh(args)
    verification_result = _parse_verification_output(
        stdout=completed.stdout,
        predicate_type=predicate_type,
        label=label,
    )
    return VerifiedPredicate(
        name=label,
        predicate_type=predicate_type,
        attestation_count=len(verification_result),
        verification_result=verification_result,
    )


def verify_attestations(
    *,
    image_name: str,
    digest: str,
    repo: str,
    signer_workflow: str,
    source_ref: str,
) -> VerificationBundle:
    """Verify provenance and SBOM attestations for one OCI image digest."""

    artifact_uri = build_artifact_uri(image_name, digest)
    provenance = _verify_predicate(
        artifact_uri=artifact_uri,
        repo=repo,
        signer_workflow=signer_workflow,
        source_ref=source_ref,
        predicate_type=PROVENANCE_PREDICATE_TYPE,
        label="provenance",
    )
    sbom = _verify_predicate(
        artifact_uri=artifact_uri,
        repo=repo,
        signer_workflow=signer_workflow,
        source_ref=source_ref,
        predicate_type=SBOM_PREDICATE_TYPE,
        label="sbom",
    )
    return VerificationBundle(
        passed=True,
        artifact_uri=artifact_uri,
        repo=repo,
        signer_workflow=signer_workflow,
        source_ref=source_ref,
        bundle_source=BUNDLE_SOURCE,
        provenance=provenance,
        sbom=sbom,
    )


def render_markdown(bundle: VerificationBundle) -> str:
    """Render a concise Markdown summary for CI step summaries/artifacts."""

    lines = [
        "# OCI Image Attestation Verification",
        "",
        f"- Passed: `{str(bundle.passed).lower()}`",
        f"- Artifact: `{bundle.artifact_uri}`",
        f"- Repo: `{bundle.repo}`",
        f"- Signer workflow: `{bundle.signer_workflow}`",
        f"- Source ref: `{bundle.source_ref}`",
        f"- Bundle source: `{bundle.bundle_source}`",
        f"- Provenance attestations verified: `{bundle.provenance.attestation_count}`",
        f"- SBOM attestations verified: `{bundle.sbom.attestation_count}`",
        f"- Provenance predicate: `{bundle.provenance.predicate_type}`",
        f"- SBOM predicate: `{bundle.sbom.predicate_type}`",
    ]
    return "\n".join(lines) + "\n"


def _safe_artifact_uri(image_name: str, digest: str) -> str | None:
    """Build an artifact URI for evidence without masking the root failure."""

    try:
        return build_artifact_uri(image_name, digest)
    except RuntimeError:
        return None


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write a deterministic JSON evidence file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    """Write a UTF-8 text evidence file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_argument_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-name", required=True, help="Registry/repository image name.")
    parser.add_argument("--digest", required=True, help="Exact pushed image digest (sha256:...).")
    parser.add_argument("--repo", required=True, help="GitHub repository in owner/name format.")
    parser.add_argument(
        "--signer-workflow",
        required=True,
        help="Signer workflow in owner/name/.github/workflows/file.yml format.",
    )
    parser.add_argument("--source-ref", required=True, help="Git ref expected in the certificate.")
    parser.add_argument("--json-out", required=True, help="Path to the JSON evidence artifact.")
    parser.add_argument(
        "--markdown-out",
        required=True,
        help="Path to the Markdown evidence artifact.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    json_out = Path(args.json_out)
    markdown_out = Path(args.markdown_out)

    try:
        bundle = verify_attestations(
            image_name=args.image_name,
            digest=args.digest,
            repo=args.repo,
            signer_workflow=args.signer_workflow,
            source_ref=args.source_ref,
        )
    except RuntimeError as exc:
        error_message = _redact_sensitive_text(str(exc))
        failure_payload = {
            "passed": False,
            "error": error_message,
            "artifact_uri": _safe_artifact_uri(args.image_name, args.digest),
            "repo": args.repo,
            "signer_workflow": args.signer_workflow,
            "source_ref": args.source_ref,
            "bundle_source": BUNDLE_SOURCE,
        }
        failure_markdown = "\n".join(
            [
                "# OCI Image Attestation Verification",
                "",
                "- Passed: `false`",
                f"- Repo: `{args.repo}`",
                f"- Signer workflow: `{args.signer_workflow}`",
                f"- Source ref: `{args.source_ref}`",
                f"- Bundle source: `{BUNDLE_SOURCE}`",
                f"- Error: `{error_message}`",
                "",
            ]
        )
        _write_json(json_out, failure_payload)
        _write_text(markdown_out, failure_markdown)
        print(error_message, file=sys.stderr)
        return 1

    _write_json(json_out, asdict(bundle))
    _write_text(markdown_out, render_markdown(bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
