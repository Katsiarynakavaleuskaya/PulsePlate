# Build Equivalence Contract

**Schema version:** `release-build-equivalence.v1`
**Input schema version:** `release-build-identity.v1`
**Release-control-plane slice:** PR-4, `release/release-control-plane-pr4-build-equivalence`
**Schema:** [`BUILD_EQUIVALENCE_CONTRACT.schema.json`](BUILD_EQUIVALENCE_CONTRACT.schema.json)

## Purpose

This contract defines the internal deterministic check that compares the App
Review build identity with the production-candidate build identity before a
release can be called equivalent.

PR-4 consumes the PR-3 `release-manifest.v1` contract and does not add CI
fail-closed enforcement, App Store Connect execution, Fastlane upload mutation,
backend routes, OpenAPI changes, iOS runtime behavior, RAG behavior changes, or
product-facing behavior. CI enforcement remains scoped to PR-5.

## Input Build Identity

Each compared build identity artifact is an explicit JSON file:

```json
{
  "schema_version": "release-build-identity.v1",
  "hash_algorithm": "sha256",
  "canonicalization": "json-sorted-compact-utf8-single-trailing-newline",
  "build_identity": {
    "git_sha": "<git sha>",
    "ios_build_number": "100",
    "marketing_version": "1.0",
    "bundle_id": "app.pulseplate.PulsePlate"
  },
  "artifact_digest": "sha256:<64 lowercase hex>",
  "release_manifest_hash": "<64 lowercase hex>",
  "reviewer_identity": {},
  "ml_identity": {},
  "supply_chain_identity": {}
}
```

The `reviewer_identity`, `ml_identity`, and `supply_chain_identity` snapshots
are optional in input artifacts. When present on either side, they are compared
against both the opposite build artifact and the release manifest.

## Output Decision

The checker writes deterministic JSON:

```json
{
  "schema_version": "release-build-equivalence.v1",
  "hash_algorithm": "sha256",
  "canonicalization": "json-sorted-compact-utf8-single-trailing-newline",
  "decision": "EQUIVALENT",
  "reason_codes": [],
  "mismatch_details": [],
  "compared_fields": [
    "build_identity.git_sha",
    "build_identity.bundle_id",
    "build_identity.marketing_version",
    "build_identity.ios_build_number",
    "artifact_digest",
    "release_manifest_hash"
  ],
  "release_manifest_hash": "<64 lowercase hex>",
  "tool_version": "release-build-equivalence.v1"
}
```

`EQUIVALENT` means all required identity and digest fields match the PR-3
manifest and each other. `BLOCK` means at least one required field is missing,
malformed, unsupported, or mismatched. Reason codes and mismatch details are
sorted deterministically.

## Fail-Closed Reasons

Stable reason codes include:

- `missing_review_build_identity`
- `missing_production_candidate_identity`
- `malformed_review_build_identity`
- `malformed_production_candidate_identity`
- `invalid_release_manifest`
- `git_sha_mismatch`
- `bundle_id_mismatch`
- `marketing_version_mismatch`
- `ios_build_number_mismatch`
- `review_build_digest_mismatch`
- `release_manifest_hash_mismatch`
- `reviewer_identity_mismatch`
- `ml_identity_mismatch`
- `supply_chain_identity_mismatch`
- `unsupported_digest_format`
- `attestation_not_verified`

## CLI

Run from the repository root with explicit file paths:

```bash
python3 scripts/release/build_equivalence.py \
  --review-build artifacts/release/review_build_identity.json \
  --production-candidate artifacts/release/production_candidate_identity.json \
  --release-manifest artifacts/release/release_manifest.json \
  --output artifacts/release/build_equivalence_result.json
```

The command writes a deterministic result JSON. It exits `0` for
`EQUIVALENT`, exits nonzero for `BLOCK`, and exits nonzero with a controlled
`ERROR:` line for unreadable or malformed input.

## Boundaries

This contract does not:

- add GitHub Actions enforcement or required checks;
- run `xcodebuild`, Fastlane, Docker, `gh`, `curl`, or App Store Connect APIs;
- read signing material, App Store credentials, protected GitHub environment
  secrets, provider credentials, or deployment credentials;
- change release manifest format or create a second manifest contract;
- change RAG thresholds, runtime retrieval/generation, backend APIs, OpenAPI,
  iOS features, billing, semantic cache, GraphRAG, or product-facing behavior.
