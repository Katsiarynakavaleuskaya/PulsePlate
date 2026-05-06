# Release Control Plane Epic

**Epic title:** `epic(release): automate release control plane evidence`
**Epic slug:** `epic/release-control-plane`
**Branch namespace:** `release/release-control-plane-*`
**Date:** 2026-04-29

## Summary

This epic creates a complementary release automation line for PulsePlate. It
connects C4 release-risk context, App Store Review evidence, RAG/ML release
gates, supply-chain provenance, and a future release manifest into one
coordinator-owned control plane.

The line does not replace the colleague-owned App Store readiness epic in PR
`#1582`. It consumes that line as upstream reviewer/metadata context after the
relevant artifacts land on `main`.

## Current Repo Truth

- System architecture already has a C4-lite overview in
  `docs/architecture/system_overview.md`.
- AI/RAG ownership already has a bounded-context packet in
  `docs/architecture/C4_AI_BOUNDED_CONTEXT_PACKET_2026-03-20.md`.
- RAG release gates already have a canonical internal runner and artifact
  contract in `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md` and
  `scripts/evals/run_rag_release_gates.py`.
- Docker pushed-image provenance and SBOM attestations already have restored
  controls in `.github/workflows/build.yml`, `.github/workflows/cd.yml`, and
  `scripts/ci/check_docker_provenance_attestation.py`.
- App Store metadata, review notes, and protected-upload runbooks already exist
  under `ios/fastlane/` and `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`.
- PR `#1582` is separately owned and must not be edited by this line.

## Release Packet Contract

Later slices converge on one internal release packet. The packet must be
machine-readable and fail closed when required evidence is absent or stale.
The canonical source of truth for the PR train and field-level release packet
contract is
[`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md`](../orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md).
This epic summarizes that packet and must not redefine the train or field
format independently. Normative anchors: PR train source of truth
`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:94-106`,
release packet identity groups
`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:108-117`,
and hash/digest formats
`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:119-127`.

| Group | Fields | Purpose |
| --- | --- | --- |
| Build identity | `git_sha`, `ios_build_number`, `marketing_version`, `bundle_id` | Pins the source and iOS build under review; task-packet anchor `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:113` |
| Reviewer identity | `reviewer_notes_hash`, `appstore_metadata_hash`, attachments hash | Prevents drift between reviewer packet and submitted metadata; task-packet anchor `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:114` |
| ML identity | `rag_gate_result_hash`, `eval_artifact_hash`, optional `mlflow_run_id`, optional `model_version` | Links shipped AI behavior to evaluated release-gate evidence; task-packet anchor `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:115` |
| Supply-chain identity | `sbom_digest`, `provenance_digest`, `attestation_status` | Links release candidate to signed artifact evidence; task-packet anchor `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:116` |
| Decision | `ALLOW` or `BLOCK` plus reasons | Gives one final release-control verdict; task-packet anchor `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:117` |

`*_hash` fields use SHA-256 over canonical UTF-8 bytes and are encoded as
lowercase hexadecimal
(`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:121-122`).
`*_digest` fields preserve upstream artifact digest format when one exists, for
example OCI `sha256:<hex>` digests
(`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:123-127`).

The packet is internal policy. It is not a substitute for Apple review details,
App Store Connect protected uploads, PR merge-readiness checks, or external bot
review governance.

## PR Train

1. **PR-0: control-plane governance bootstrap**
   - Branch: `release/release-control-plane-pr0-bootstrap`
   - Add this epic, the release-risk C4 context, the task packet, and the ledger anchor.
   - No runtime, workflow, Fastlane, iOS, backend, OpenAPI, or RAG runner changes.

2. **PR-1: reviewer-packet hash contract**
   - Branch: `release/release-control-plane-pr1-reviewer-hash`
   - Define how reviewer notes, metadata, and App Store readiness artifacts are hashed after they land on `main`.
   - Consume App Store readiness outputs; do not own that PR train.
   - Contract: [`REVIEWER_PACKET_HASH_CONTRACT.md`](REVIEWER_PACKET_HASH_CONTRACT.md)
     and [`REVIEWER_PACKET_HASH_CONTRACT.schema.json`](REVIEWER_PACKET_HASH_CONTRACT.schema.json).
   - Helper: `scripts/release/reviewer_packet_hashes.py`.

3. **PR-2: RAG/ML gate result export**
   - Branch: `release/release-control-plane-pr2-rag-gate-export`
   - Export a stable gate-result JSON contract from the existing RAG release-gate runner.
   - Do not introduce a second eval source of truth or product dashboard.
   - Contract: [`RAG_GATE_RESULT_EXPORT_CONTRACT.md`](RAG_GATE_RESULT_EXPORT_CONTRACT.md)
     and [`RAG_GATE_RESULT_EXPORT_CONTRACT.schema.json`](RAG_GATE_RESULT_EXPORT_CONTRACT.schema.json).
   - Artifact: `artifacts/rag_eval/<experiment_id>/rag_gate_result.json`.

4. **PR-3: release manifest generator and validator**
   - Branch: `release/release-control-plane-pr3-release-manifest`
   - Merged as PR #1605 on 2026-04-30.
   - Generate and validate the internal release packet.
   - Fail closed on missing required identity groups.
   - Contract: [`RELEASE_MANIFEST_CONTRACT.md`](RELEASE_MANIFEST_CONTRACT.md)
     and [`RELEASE_MANIFEST_CONTRACT.schema.json`](RELEASE_MANIFEST_CONTRACT.schema.json).
   - Helper: `scripts/release/release_manifest.py`.

5. **PR-4: review build equals production candidate**
   - Branch: `release/release-control-plane-pr4-build-equivalence`
   - Active PR-4 slice.
   - Add digest/hash equivalence checks so the reviewed build and production candidate cannot silently diverge.
   - Contract: [`BUILD_EQUIVALENCE_CONTRACT.md`](BUILD_EQUIVALENCE_CONTRACT.md)
     and [`BUILD_EQUIVALENCE_CONTRACT.schema.json`](BUILD_EQUIVALENCE_CONTRACT.schema.json).
   - Helper: `scripts/release/build_equivalence.py`.

6. **PR-5: CI release decision integration**
   - Branch: `release/release-control-plane-pr5-ci-gates`
   - Add focused CI gates for release packet, RAG gate result, SBOM/provenance references, and `ALLOW` / `BLOCK` decision.
   - Deferred until PR-4 has landed; PR-4 must not add CI fail-closed enforcement.

## Boundaries

In scope:

- release evidence architecture
- PR train packet/governance
- C4 release-risk context
- future release packet schema
- future deterministic validators

Out of scope:

- editing PR `#1582` or its worktree
- App Store Connect upload execution
- Apple Server API migration
- billing rewrite
- ML platform rebuild
- product-facing eval dashboard
- Figma or Canva as source of truth
- VEX/OPA enforcement before the dedicated SBOM/VEX lane unblocks

## Security Notes

- Release decisions must fail closed on missing evidence, stale hashes, or
  digest mismatch. Enforcement contracts: release manifest validator in PR-3
  and CI decision integration in PR-5
  (`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:104-106`),
  minimum slice gates
  (`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:166-188`),
  and stop condition for unsafe release evidence
  (`docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:198-206`).
- Secrets, App Store credentials, signing keys, and reviewer credentials must
  stay in protected environments, never in release packet files. Enforcement
  anchors: protected App Store secret placement
  `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md:38-40` and release-control
  stop condition
  `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md:205`.
- RAG gate outputs are evidence artifacts, not canonical knowledge promotion;
  repo-level KPP keeps repo artifacts as source of truth (`AGENTS.md:487-493`),
  while the RAG lane keeps eval outputs in gitignored artifacts
  (`docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md:267-276`).
- Supply-chain attestations must be verified by exact digest before deploy
  claims, reusing the existing Docker provenance controls. Verifier anchors:
  exact OCI artifact URI construction
  `scripts/ci/check_docker_provenance_attestation.py:51-60` and
  provenance/SBOM attestation verification
  `scripts/ci/check_docker_provenance_attestation.py:214-262`.

## Marketing And GTM

This epic supports reviewer trust and launch discipline, but it does not create
new public claims. App Store, web, ASO, and Product Hunt copy must still remain
wellness-safe:

```text
Allowed: AI-powered wellness and nutrition planning.
Blocked: diagnosis, treatment, therapy, crisis support, guaranteed outcomes.
```

## Decision Log

1. Keep App Store readiness and release control plane as separate coordinated lines.
2. Make PR-0 governance-only to avoid scope drift.
3. Reuse existing RAG gates and Docker provenance controls.
4. Keep the release packet internal and machine-readable.
5. Defer MLflow, Hugging Face cards, VEX/OPA, and protected uploads to later explicitly scoped slices.
6. PR-1 hashes reviewer notes separately from localized App Store metadata and treats App Privacy JSON as upstream context only.
7. PR-3 keeps the release manifest internal and fail-closed, but leaves CI enforcement to PR-5 and build equivalence to PR-4.
8. PR-4 keeps build equivalence internal and deterministic, proving review-build
   and production-candidate identity through digest/hash comparison only. It
   leaves CI fail-closed enforcement to PR-5 and does not treat branch names,
   tags, or human labels as equivalence evidence.
