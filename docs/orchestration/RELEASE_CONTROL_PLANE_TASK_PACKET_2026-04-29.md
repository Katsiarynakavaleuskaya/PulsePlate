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
6. `appstore-release-agent`
7. `backend-engineer-agent`
8. `ios-engineer-agent`
9. `dev-operator`
10. `qa-engineer-agent`
11. `bug-hunter`

Mandatory post-open review lane:

```text
qa-engineer-agent -> bug-hunter
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

| PR | Branch | Primary outcome | Blocking proof |
| --- | --- | --- | --- |
| PR-0 | `release/release-control-plane-pr0-bootstrap` | Epic, packet, C4 release-risk context, ledger anchor | docs/ledger validation and repo policy guards |
| PR-1 | `release/release-control-plane-pr1-reviewer-hash` | Reviewer-packet hash contract consuming App Store readiness artifacts | reviewer hash schema tests |
| PR-2 | `release/release-control-plane-pr2-rag-gate-export` | RAG/ML gate result export contract over the existing eval runner | gate-result schema tests |
| PR-3 | `release/release-control-plane-pr3-release-manifest` | Release manifest generator and validator | manifest validator tests |
| PR-4 | `release/release-control-plane-pr4-build-equivalence` | Review build equals production-candidate equivalence check | equivalence tests |
| PR-5 | `release/release-control-plane-pr5-ci-gates` | CI integration for release packet, gate result, SBOM/provenance references, and fail-closed decision | focused CI/workflow contract tests |

## Release Packet Contract

Later slices must converge on one machine-readable release packet with these
identity groups:

- build identity: `git_sha`, `ios_build_number`, `marketing_version`, `bundle_id`
- reviewer identity: `reviewer_notes_hash`, `appstore_metadata_hash`, optional attachments hash
- ML identity: `rag_gate_result_hash`, `eval_artifact_hash`, optional `mlflow_run_id` and `model_version`
- supply-chain identity: `sbom_digest`, `provenance_digest`, `attestation_status`
- release decision: `ALLOW` or `BLOCK`

PR-0 defines the contract only. It does not generate, validate, or publish the
packet.

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
  --requested-agent appstore-release-agent \
  --requested-agent backend-engineer-agent \
  --requested-agent ios-engineer-agent \
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
- RAG gate export: `pytest -q tests/test_rag_release_gates_runner.py`
- release manifest: manifest schema and failure-mode tests
- build equivalence: review/prod digest mismatch tests
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
