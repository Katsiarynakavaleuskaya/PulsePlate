# Release Manifest Contract

**Schema version:** `release-manifest.v1`
**Release-control-plane slice:** PR-3, `release/release-control-plane-pr3-release-manifest`
**Schema:** [`RELEASE_MANIFEST_CONTRACT.schema.json`](RELEASE_MANIFEST_CONTRACT.schema.json)

## Purpose

This contract defines the internal release manifest that joins build identity,
reviewer packet identity, RAG/ML gate identity, supply-chain identity, and one
fail-closed release-control decision.

PR-3 adds a generator and validator only
(`scripts/release/release_manifest.py:143`,
`scripts/release/release_manifest.py:375`, `tests/test_release_manifest.py:99`).
It does not add CI release gating, review-build versus production-candidate
equivalence checks, App Store Connect uploads, backend APIs, OpenAPI changes, or
product runtime behavior; PR-4 and PR-5 remain the scoped train entries for
build equivalence and CI release gates
(`docs/release/RELEASE_CONTROL_PLANE_EPIC.md:100`,
`docs/release/RELEASE_CONTROL_PLANE_EPIC.md:104`).

## Generator And Validator

The deterministic helper is:

```text
scripts/release/release_manifest.py
```

It supports:

- `generate`: consumes current App Store reviewer hash artifacts through
  `scripts/release/reviewer_packet_hashes.py`, consumes an existing
  `rag_gate_result.json`, accepts explicit build and supply-chain identity
  values, and writes a release manifest JSON file.
- `validate`: reads an existing manifest and fails closed on schema-version,
  hash, digest, path, identity, or release-decision mismatches.

Generated manifest paths must be repo-relative or run-dir-relative. Absolute
local filesystem paths are invalid.

## Hash And Digest Fields

| Field | Source | Format |
| --- | --- | --- |
| `release_manifest_hash` | Canonical JSON manifest payload excluding this self-hash | SHA-256 lowercase hex, no prefix |
| `reviewer_notes_hash` | PR-1 reviewer packet hash contract | SHA-256 lowercase hex, no prefix |
| `appstore_metadata_hash` | PR-1 reviewer packet hash contract | SHA-256 lowercase hex, no prefix |
| `rag_gate_result_hash` | PR-2 RAG gate export contract | SHA-256 lowercase hex, no prefix |
| `eval_artifact_hash` | PR-2 RAG safe artifact manifest hash | SHA-256 lowercase hex, no prefix |
| `sbom_digest` | Upstream supply-chain evidence | OCI `sha256:<hex>` digest |
| `provenance_digest` | Upstream supply-chain evidence | OCI `sha256:<hex>` digest |

JSON canonicalization uses sorted keys, compact separators, UTF-8 bytes, and
exactly one trailing LF.

## Contract Payload

The manifest contains:

```json
{
  "schema_version": "release-manifest.v1",
  "hash_algorithm": "sha256",
  "canonicalization": "json-sorted-compact-utf8-single-trailing-newline",
  "release_manifest_hash": "<64 lowercase hex>",
  "build_identity": {
    "git_sha": "<git sha>",
    "ios_build_number": "1",
    "marketing_version": "1.0",
    "bundle_id": "app.pulseplate.PulsePlate"
  },
  "reviewer_identity": {
    "schema_version": "release-reviewer-packet-hashes.v1",
    "reviewer_notes_hash": "<64 lowercase hex>",
    "appstore_metadata_hash": "<64 lowercase hex>",
    "source_artifacts": [
      {
        "kind": "reviewer_notes",
        "path": "ios/fastlane/metadata/review_information/notes.txt",
        "hash": "<64 lowercase hex>"
      }
    ]
  },
  "ml_identity": {
    "schema_version": "release-rag-gate-result.v1",
    "rag_gate_result_hash": "<64 lowercase hex>",
    "eval_artifact_hash": "<64 lowercase hex>",
    "release_decision": "PASS",
    "source_artifacts": [
      {
        "kind": "rag_gate_result",
        "path": "artifacts/rag_eval/release/rag_gate_result.json",
        "hash": "<64 lowercase hex>"
      }
    ]
  },
  "supply_chain_identity": {
    "sbom_digest": "sha256:<64 lowercase hex>",
    "provenance_digest": "sha256:<64 lowercase hex>",
    "attestation_status": "VERIFIED"
  },
  "release_decision": "ALLOW",
  "decision_reasons": []
}
```

Optional ML identity fields `mlflow_run_id` and `model_version` are copied only
when the PR-2 RAG gate export supplies them.

## Release Decision

The validator recomputes the release-control decision.

`ALLOW` requires all of the following:

- required build, reviewer, ML, and supply-chain identity groups are present;
- RAG gate result decision is `PASS`;
- `sbom_digest` and `provenance_digest` use OCI `sha256:<hex>` format;
- `attestation_status` is `VERIFIED`;
- `release_manifest_hash` matches the canonical payload.

Any missing or invalid required evidence results in `BLOCK` with deterministic
`decision_reasons`, such as `rag_gate_result_not_pass`,
`attestation_not_verified`, `invalid_sbom_digest`, or
`invalid_provenance_digest`.

## Boundaries

This PR-3 contract does not:

- change App Store metadata, reviewer notes, screenshots, privacy payloads, or
  Fastlane upload lanes; reviewer assets are consumed through the PR-1 hash
  helper only (`scripts/release/reviewer_packet_hashes.py:78`,
  `scripts/release/release_manifest.py:158`);
- change RAG thresholds, retrieval, generation, or product runtime behavior;
  PR-3 reads the PR-2 export as an input artifact only
  (`scripts/release/release_manifest.py:159`,
  `scripts/release/release_manifest.py:164`);
- read App Store Connect credentials, signing material, provider credentials,
  protected GitHub environment secrets, or deployment credentials; CLI inputs are
  explicit build/supply-chain identifiers only
  (`scripts/release/release_manifest.py:351`,
  `scripts/release/release_manifest.py:357`);
- verify review-build versus production-candidate equivalence;
- add CI release-decision enforcement.

Those behaviors remain scoped to the App Store readiness train, PR-4, and PR-5.
