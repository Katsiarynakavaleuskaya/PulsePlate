# Release Control Plane CI Gate

Schema version: `release-control-plane-ci-gate.v1`

PR-5 adds the internal CI/release-governance gate that consumes already-produced
release evidence and emits a deterministic `ALLOW` or `BLOCK` decision.

The gate is validation-only. It does not create release artifacts, contact App
Store Connect, run Fastlane, read protected secrets, call network services, run
Docker, run Xcode, mutate deploy targets, or change product runtime behavior.

## Inputs

The checker accepts explicit file paths only:

```bash
python3 scripts/ci/check_release_control_plane.py \
  --release-manifest artifacts/release/release_manifest.json \
  --rag-gate-result artifacts/rag_eval/<experiment_id>/rag_gate_result.json \
  --build-equivalence artifacts/release/build_equivalence_result.json \
  --json-out artifacts/release/release_control_plane_ci_gate.json \
  --markdown-out artifacts/release/release_control_plane_ci_gate.md
```

Required evidence:

- `release_manifest.v1`, produced by `scripts/release/release_manifest.py`.
- `release-rag-gate-result.v1`, produced by the existing RAG release-gate runner.
- `release-build-equivalence.v1`, produced by `scripts/release/build_equivalence.py`.

Evidence source paths inside ML/RAG evidence must be relative artifact paths
under `artifacts/`. Reviewer metadata and App Store source files remain governed
by the release manifest contract and are not treated as protected CI evidence
paths by this gate.

## Output

The JSON output is stable sorted JSON with a trailing newline and contains:

- `schema_version`: `release-control-plane-ci-gate.v1`
- `decision`: `ALLOW` or `BLOCK`
- `reason_codes`: stable fail-closed reason codes
- `mismatch_details`: deterministic field-level details
- `checked_artifacts`: exact input file paths and SHA-256 file hashes
- `evidence_hashes`: SHA-256 file hashes for the consumed evidence files
- `evidence_digests`: SBOM and provenance OCI digests from the release manifest
- `release_manifest_hash`
- `build_equivalence_decision`
- `rag_gate_decision`
- `attestation_status`
- `tool_version`

The summary fields preserve the raw upstream string when malformed evidence is
present so blocked CI artifacts can show the exact bad value that caused the
failure.

Schema: [`RELEASE_CONTROL_PLANE_CI_GATE.schema.json`](RELEASE_CONTROL_PLANE_CI_GATE.schema.json).

## Allow Rule

The gate returns `ALLOW` only when all required evidence passes:

- release manifest exists, is valid, and has `release_decision == "ALLOW"`
- RAG gate result exists, is valid, and has `release_decision == "PASS"`
- build equivalence result exists, is valid, and has `decision == "EQUIVALENT"`
- release manifest hash matches the build-equivalence result
- RAG hashes and decision match the manifest `ml_identity`
- manifest build git SHA matches the RAG evidence git SHA
- SBOM and provenance digests use `sha256:<64 lowercase hex>`
- attestation status is `VERIFIED`
- artifact evidence paths stay under allowed artifact locations

## Block Reasons

Stable reason codes:

- `missing_release_manifest`
- `malformed_release_manifest`
- `invalid_release_manifest`
- `release_manifest_block`
- `missing_rag_gate_result`
- `malformed_rag_gate_result`
- `invalid_rag_gate_result`
- `rag_gate_result_not_pass`
- `missing_build_equivalence`
- `malformed_build_equivalence`
- `invalid_build_equivalence`
- `build_equivalence_not_equivalent`
- `missing_sbom_digest`
- `missing_provenance_digest`
- `attestation_not_verified`
- `unsupported_digest_format`
- `release_manifest_hash_mismatch`
- `git_sha_mismatch`
- `build_identity_mismatch`
- `evidence_path_outside_allowed_artifacts`

## CI Integration

PR-5 wires a non-secret fixture validation job into the release-control-plane CI
surface so the checker contract is exercised without requiring protected App
Store credentials or production release artifacts.

Production tag enforcement remains fail-closed at the checker level, but
protected-environment artifact wiring is a follow-up because current CI does not
yet publish real `release_manifest.json`, `rag_gate_result.json`, and
`build_equivalence_result.json` into the production deploy path. The fixture job
must not be interpreted as fake production evidence and must not be placed under
`artifacts/release/`.

Deferred protected-environment follow-up: wire real release evidence artifacts
into the production tag path before production deploy, then invoke this checker
against those real artifacts.
