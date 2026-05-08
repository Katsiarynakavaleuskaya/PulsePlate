# Release Control Plane Task Packet

**Packet ID:** `release-control-plane-2026-04-29`
**Epic:** `epic/release-control-plane`
**Created:** 2026-04-29
**Branch namespace:** `release/release-control-plane-*`
**Ledger:** [`ledger-p1-release-control-plane`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-release-control-plane)

## Task Summary

Bootstrap a coordinator-owned complementary release automation line for the
documented C4, App Store Review, ML gate, and supply-chain control-plane work.
This line complements colleague-owned App Store readiness work in PR `#1582`
and must not edit `release/appstore-readiness-pr0-bootstrap` or
`worktrees/appstore-readiness-pr0`.

The PR-0 slice is governance-only. It creates the epic, release-risk C4
context, backlog anchor, and PR train contract for later implementation.

## Scope

PR-0 may touch only:

- `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md`
- `docs/release/RELEASE_CONTROL_PLANE_EPIC.md`
- `docs/architecture/C4_RELEASE_CONTROL_PLANE_CONTEXT.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_<N>_FIXED_MAPPING.md` after PR open for mandatory review-governance mapping

PR-0 must not change:

- iOS runtime or Fastlane behavior
- App Store metadata or privacy payloads
- backend endpoints, schemas, OpenAPI, or billing transport
- RAG runner behavior
- Docker/GitHub Actions workflows
- colleague-owned PR `#1582` branch or worktree

## Role Order

The coordinator-owned train uses this role order unless a later slice packet
narrows it with explicit rationale:

1. `agent-coordinator`
2. `architecture-specialist`
3. `ml-engineer-agent`
4. `data-scientist-agent`
5. `security-auditor`
6. `app-store-release-agent`
7. `backend-engineer`
8. `frontend-engineer`
9. `dev-operator`
10. `qa-engineer-agent`
11. `bug-hunter`

For iOS-specific release surfaces, `frontend-engineer` is the canonical platform
surface owner per the routing graph until a dedicated `ios-engineer-agent` slug
exists in the agent inventory.

Mandatory post-open review lane:

```text
qa-engineer-agent -> bug-hunter -> premortem-facilitator
```

## Recommended Skills

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-ledger`
- `pulseplate-pr-review`
- `pulseplate-app-store-release`
- `pulseplate-agent-product`
- `pulseplate-graphmap`

Conditional skills:

- `pulseplate-backend-endpoints` only if a later slice changes backend API or runtime contracts
- `pulseplate-openapi-sync` only if a later slice changes OpenAPI
- `pulseplate-playwright-e2e` only for browser proof
- `pulseplate-ai-reports` only for research or market appendix work
- `pulseplate-design-launch-system` only for diagram or launch-asset governance

External plugins are evidence helpers only. GitHub and CodeRabbit may provide
PR/review evidence; Build iOS Apps may validate iOS slices; Browser Use and
Computer Use may capture runtime evidence; Figma and Canva may render diagrams;
Hugging Face and Life Science Research may support bounded ML/research intake.
None of them replaces repo source of truth, coordinator routing, fixed-mapping
governance, or local gates.

## PR Train

The canonical PR train and release packet contract source of truth is this task
packet. The epic, C4 context, and ledger entry summarize or link back to this
packet; later slices must update this packet first if the train or contract
changes.

| PR | Branch | Primary outcome | Blocking proof |
| --- | --- | --- | --- |
| PR-0 | `release/release-control-plane-pr0-bootstrap` | Epic, packet, C4 release-risk context, ledger anchor | docs/ledger validation and repo policy guards |
| PR-1 | `release/release-control-plane-pr1-reviewer-hash` | Reviewer-packet hash contract consuming App Store readiness artifacts | reviewer hash schema tests and Fastlane artifact-name discovery |
| PR-2 | `release/release-control-plane-pr2-rag-gate-export` | RAG/ML gate result export contract over the existing eval runner | gate-result schema tests |
| PR-3 | `release/release-control-plane-pr3-release-manifest` | Release manifest generator and validator, merged as PR #1605 | manifest validator tests |
| PR-4 | `release/release-control-plane-pr4-build-equivalence` | Merged review build equals production-candidate equivalence check in PR #1679 | equivalence tests |
| PR-5 | `release/release-control-plane-pr5-ci-gates` | Merged CI integration for release packet, gate result, build equivalence, SBOM/provenance references, and fail-closed decision in PR #1682 | focused CI/workflow contract tests |
| PR-6 | `release/release-control-plane-pr6-production-artifact-wiring` | Merged production tag wiring for real release-control-plane evidence artifacts in PR #1688 | production workflow contract tests |
| Post-#1692 | `ci/release-control-plane-evidence-publication` | Merged governed manual publication workflow for the production evidence artifact required by CD in PR #1699 | evidence publication workflow contract tests |
| Post-#1699 | `ci/release-control-plane-source-producers` | Merged governed source producers for `Release Manifest Evidence` and `Build Equivalence Evidence` in PR #1703 | source producer workflow contract tests |

## Release Packet Contract

Later slices must converge on one machine-readable release packet with these
identity groups:

- build identity: `git_sha`, `ios_build_number`, `marketing_version`, `bundle_id`
- reviewer identity: `reviewer_notes_hash`, `appstore_metadata_hash`, optional attachments hash
- ML identity: `rag_gate_result_hash`, `eval_artifact_hash`, optional `mlflow_run_id` and `model_version`
- supply-chain identity: `sbom_digest`, `provenance_digest`, `attestation_status`
- release decision: `ALLOW` or `BLOCK`

Hash and digest format contract:

- `*_hash` fields use SHA-256 over canonical UTF-8 bytes and are encoded as
  lowercase hexadecimal without a `sha256:` prefix.
- `*_digest` fields preserve the upstream artifact digest format when one
  exists, for example OCI digests as `sha256:<hex>`.
- If a non-OCI artifact lacks an upstream digest format, later slices must use
  SHA-256 lowercase hexadecimal and document the canonical byte serialization
  next to the producing validator.

PR-0 defines the contract only. It does not generate, validate, or publish the
packet.

### PR-1 Reviewer Packet Hash Contract

PR-1 defines the reviewer identity fields without changing App Store metadata,
reviewer notes, Fastlane upload behavior, or protected App Store credentials.
The machine-readable schema and field contract live in
[`docs/release/REVIEWER_PACKET_HASH_CONTRACT.md`](../release/REVIEWER_PACKET_HASH_CONTRACT.md)
and
[`docs/release/REVIEWER_PACKET_HASH_CONTRACT.schema.json`](../release/REVIEWER_PACKET_HASH_CONTRACT.schema.json).

Canonical upstream artifact names consumed from landed App Store readiness work:

- `ios/fastlane/metadata/review_information/notes.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/name.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/subtitle.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/description.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/keywords.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/promotional_text.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/release_notes.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/privacy_url.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/support_url.txt`
- `ios/fastlane/metadata/{en-US,ru-RU,es-ES}/marketing_url.txt`
- `ios/fastlane/app_privacy_details.json` as upstream context only

`reviewer_notes_hash` hashes only reviewer notes. `appstore_metadata_hash`
hashes a canonical JSON manifest of localized metadata file hashes and excludes
`review_information/**` plus App Privacy JSON. Text artifacts are decoded as
UTF-8, line endings are normalized to LF, exactly one trailing LF is enforced,
all other whitespace is preserved, and the resulting canonical UTF-8 bytes are
hashed with SHA-256 lowercase hexadecimal.

### PR-2 RAG Gate Result Export Contract

PR-2 defines the ML identity export without changing RAG thresholds, retrieval,
generation, product runtime, backend APIs, or final release decision logic. The
machine-readable schema and field contract live in
[`docs/release/RAG_GATE_RESULT_EXPORT_CONTRACT.md`](../release/RAG_GATE_RESULT_EXPORT_CONTRACT.md)
and
[`docs/release/RAG_GATE_RESULT_EXPORT_CONTRACT.schema.json`](../release/RAG_GATE_RESULT_EXPORT_CONTRACT.schema.json).

The existing RAG release-gates runner emits
`artifacts/rag_eval/<experiment_id>/rag_gate_result.json` beside the current
artifact pack. The export contains `rag_gate_result_hash`,
`eval_artifact_hash`, existing `PASS` / `NO-GO` eval decision fields, gate
checks, threshold rows, strict violations, runtime warnings, dataset identity,
sample size, git SHA, and retriever/generator modes. It reserves optional
`mlflow_run_id` and `model_version` fields for future explicitly scoped ML
identity integrations.

### PR-3 Release Manifest Contract

PR-3 defines the internal release manifest generator and fail-closed validator
without adding CI release gating, build-equivalence enforcement, App Store
uploads, backend APIs, OpenAPI changes, or product runtime behavior. The
machine-readable schema and field contract live in
[`docs/release/RELEASE_MANIFEST_CONTRACT.md`](../release/RELEASE_MANIFEST_CONTRACT.md)
and
[`docs/release/RELEASE_MANIFEST_CONTRACT.schema.json`](../release/RELEASE_MANIFEST_CONTRACT.schema.json).

The deterministic helper is `scripts/release/release_manifest.py`. It consumes
the PR-1 reviewer packet hash helper, an existing PR-2 `rag_gate_result.json`,
explicit build identity values, and explicit supply-chain digest/attestation
values. `release_manifest_hash` is SHA-256 lowercase hexadecimal over canonical
JSON bytes excluding the self-hash. `release_decision` is `ALLOW` only when
required identity groups are complete, RAG gate result is `PASS`, supply-chain
digests are valid OCI `sha256:<hex>` values, and `attestation_status` is
`VERIFIED`; otherwise it is `BLOCK` with deterministic `decision_reasons`.

### PR-4 Build Equivalence Contract

PR-4 defines an internal deterministic checker that compares App Review build
identity and production-candidate build identity against the PR-3
`release-manifest.v1` contract. The machine-readable schema and field contract
live in
[`docs/release/BUILD_EQUIVALENCE_CONTRACT.md`](../release/BUILD_EQUIVALENCE_CONTRACT.md)
and
[`docs/release/BUILD_EQUIVALENCE_CONTRACT.schema.json`](../release/BUILD_EQUIVALENCE_CONTRACT.schema.json).

The deterministic helper is `scripts/release/build_equivalence.py`. It consumes
explicit review-build identity, production-candidate identity, and release
manifest JSON paths. It compares build identity, artifact digest,
`release_manifest_hash`, and optional reviewer, ML, and supply-chain identity
snapshots when present. It returns `EQUIVALENT` only when all required fields
match; otherwise it returns `BLOCK` with deterministic `reason_codes` and
`mismatch_details`. PR-4 does not add GitHub Actions enforcement, protected App
Store upload automation, Fastlane mutation, runtime behavior, OpenAPI changes,
RAG behavior changes, semantic cache, or product-facing behavior. PR-5 owns the
focused CI fail-closed enforcement slice.

### PR-5 Release Control Plane CI Gate

PR-5 defines a deterministic CI checker that consumes the PR-3 release manifest,
PR-2 RAG gate result, PR-4 build-equivalence result, and supply-chain identity
references. The machine-readable schema and field contract live in
[`docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md`](../release/RELEASE_CONTROL_PLANE_CI_GATE.md)
and
[`docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json`](../release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json).

The deterministic helper is `scripts/ci/check_release_control_plane.py`. It
returns `ALLOW` only when the release manifest is `ALLOW`, the RAG gate result
is `PASS`, the build-equivalence decision is `EQUIVALENT`, supply-chain digests
are valid, attestation is `VERIFIED`, and evidence hashes/identity fields match.
Otherwise it returns `BLOCK` with deterministic reason codes. The workflow
integration is a non-secret fixture validation job because protected production
artifact wiring is not available in this slice. PR-5 does not add App Store
Connect execution, Fastlane upload mutation, runtime/API/OpenAPI/iOS changes,
RAG behavior changes, semantic cache, GraphRAG, or product-facing behavior.

### PR-6 Production Release Evidence Wiring

PR-6 wires real production release-control-plane evidence artifacts into the
production tag path before deploy. The machine-readable operator contract lives
in
[`docs/release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md`](../release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md).

The CD workflow resolves `RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID` and
`RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME` from production environment or
repository Actions variables when production deploy is active. It downloads the
named artifact from the named run and requires this layout:

```text
release-control-plane/
  release_manifest.json
  rag_gate_result.json
  build_equivalence_result.json
```

The production evidence job invokes `scripts/ci/check_release_control_plane.py`
against those real artifacts and uploads
`release_control_plane_ci_gate.json` plus `release_control_plane_ci_gate.md` as
workflow evidence. Production deploy depends on this gate when deploy is active.

PR-6 does not create fake production evidence, does not use fixtures in the
production tag path, does not add App Store Connect execution, does not mutate
Fastlane protected upload behavior, and does not change runtime/API/OpenAPI/iOS,
RAG, billing, semantic cache, GraphRAG, or product-facing behavior.

### Post-PR-1692 Governed Evidence Publication

After PR #1692, production tags fail closed until protected Actions variables
point CD at a real release-control-plane evidence artifact. The
`ci/release-control-plane-evidence-publication` follow-up adds the manual
governed workflow that publishes that artifact. The slice-specific packet lives
in
[`RELEASE_CONTROL_PLANE_EVIDENCE_PUBLICATION_PACKET_2026-05-07.md`](RELEASE_CONTROL_PLANE_EVIDENCE_PUBLICATION_PACKET_2026-05-07.md).

The publication workflow must arrange this canonical layout:

```text
release-control-plane/
  release_manifest.json
  rag_gate_result.json
  build_equivalence_result.json
```

Source evidence must come from successful `workflow_dispatch` runs for the same
git SHA and must be validated with `scripts/ci/check_release_control_plane.py`
before upload. The workflow publishes governed evidence only; it does not
create release truth, use fixtures as production evidence, perform App Store
Connect execution, mutate Fastlane protected upload behavior, or change
runtime/API/iOS, RAG, billing, semantic cache, GraphRAG, or product-facing
behavior.

### Post-PR-1699 Governed Source Producers

After PR #1699, the publisher had a governed manual publication lane but still
needed repo-owned source producers for release manifest and build-equivalence
evidence. PR #1703 merged the `ci/release-control-plane-source-producers`
follow-up and added:

- `Release Manifest Evidence` at `.github/workflows/release-manifest-evidence.yml`
- `Build Equivalence Evidence` at `.github/workflows/build-equivalence-evidence.yml`

`RAG Release Gates` remains the existing RAG/ML producer. The source producers
are `workflow_dispatch` only, validate source run provenance and matching
`git_sha`, reject fixtures/placeholders/fallbacks, publish stable root artifact
paths (`release_manifest.json` and `build_equivalence_result.json`), and avoid
App Store Connect execution, Fastlane upload mutation, runtime/API/iOS, RAG
behavior, billing, semantic cache, GraphRAG, or product-facing behavior.
Build-equivalence publication keeps App Review and production-candidate
artifact digests as explicit protected dispatch inputs; this slice must not
self-certify those App Store build identities from Docker image digests.
Release-manifest publication similarly requires one governed same-SHA
supply-chain source object pointing to the `release-control-plane-build-sources`
artifact root, emitted by the `Docker Build and Push` publish lane only after
exact-digest provenance/SBOM attestation verification passes. That artifact must
contain `sbom_digest.txt`, `provenance_digest.txt`, and
`attestation_status.txt`.

### PR #1703 Closeout

PR #1703 completed the release-control-plane evidence plumbing through governed
RAG release gates, governed source producers, the governed publisher, and the
production CD gate. No further release-control-plane evidence-plumbing PR is
currently required. Broader App Store Connect execution, Fastlane protected
upload mutation, protected upload automation, and final App Store readiness
remain separate deferred release/App Store work.

## Bootstrap Commands

Run from synced root before each slice:

```bash
git fetch --prune origin
git checkout main
git merge --ff-only origin/main
git rev-list --left-right --count HEAD...origin/main
git worktree add worktrees/release-control-plane-pr<N> -b release/release-control-plane-pr<N>-<slug> origin/main
```

Run inside the slice worktree before edits:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py \
  --goal "Release control plane slice <N>: <goal>" \
  --task-class Orchestration \
  --pr-phase pre_open \
  --requested-agent agent-coordinator \
  --requested-agent architecture-specialist \
  --requested-agent ml-engineer-agent \
  --requested-agent data-scientist-agent \
  --requested-agent security-auditor \
  --requested-agent app-store-release-agent \
  --requested-agent backend-engineer \
  --requested-agent frontend-engineer \
  --requested-agent dev-operator \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

## Gates

Minimum every slice:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make verify
```

Focused gates by future slice:

- reviewer hash: Fastlane metadata/reviewer-note validators
- reviewer packet hash contract:
  `pytest -q tests/test_release_reviewer_packet_hashes.py`
- RAG gate export: `pytest -q tests/test_rag_release_gates_runner.py`
- release manifest: `pytest -q tests/test_release_manifest.py`
- build equivalence: `pytest -q tests/test_build_equivalence.py`
- supply chain: `pytest -q tests/test_check_docker_provenance_attestation.py tests/test_python_supply_chain_controls.py`

Full `make verify` remains the default before readiness claims unless the
operator explicitly approves the repo's machine-heavy exception and the PR body
documents the deferral.

## Decisions

1. PR `#1582` remains the upstream App Store readiness baseline and is not owned by this line.
2. PR-0 is docs/governance only.
3. The release packet is internal policy, not an Apple-required public artifact.
4. Existing RAG gates and Docker provenance controls are reused instead of duplicated.
5. MLflow, Hugging Face cards, VEX, OPA, and protected uploads are future opt-in integrations, not PR-0 requirements.

## Stop Conditions

Stop and report before editing more files if:

- the worktree or branch does not match the current release-control-plane slice
- a change would edit PR `#1582` files or worktree directly
- a slice needs runtime/API/workflow changes outside its declared scope
- a release packet field would require secrets or protected App Store credentials in repo
- a gate result is treated as `ALLOW` without deterministic local or current-head CI evidence
