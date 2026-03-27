# Tier 1 CI/CD PR Series Runbook

**Version:** 2026-03-26 (`America/New_York`)
**Scope:** Governance-first CI/CD consolidation wave for backend/shared PR lanes.
**Execution surface:** repo root with coordinator-first routing; no runtime product-surface mutation in PR1.

## Purpose

This runbook is the canonical operating contract for the Tier 1 CI/CD consolidation
program launched through the repo's custom agent orchestration.

It exists to keep:
- CI/governance work coordinator-led and deterministic,
- stacked PR execution synchronized with repo-local state and GitHub current-head truth,
- bug-hunter and QA review loops mandatory at the right moments,
- workflow consolidation separate from runtime feature work.

## Contract Boundaries

- This runbook owns process, merge cadence, sync points, and hard rules for the Tier 1 wave.
- [`docs/orchestration/TIER1_CI_CD_TASK_PACKET_2026-03-26.md`](./TIER1_CI_CD_TASK_PACKET_2026-03-26.md)
  owns branch-scoped routing, skill packets, deliverables, and acceptance scope.
- [`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`](./PR_ORCHESTRATION_CONTRACT_MATRIX.md)
  remains the source of truth for merge governance semantics and CI check classes.

## Packet Reuse and Versioning Policy

- This runbook is the stable process-level SoT for the Tier 1 wave.
- The dated task packet is a branch-scoped execution snapshot for the active wave.
- While the same wave remains active, update the dated packet **in place** instead
  of minting a new filename for minor routing, acceptance, or wording changes.
- Create a new dated packet only when the wave is materially re-baselined
  (for example: ownership reset, different stacked PR decomposition, or a new
  consolidation phase that would make old links misleading).
- Shared sections such as validation, deferred scope, and routing intent should
  live here first; the task packet should reference this runbook instead of
  becoming a second long-form process document.

## Source of Truth

- Coordinator workflow: `docs/orchestration/workflow.md`
- CI/governance contract matrix: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- Merge-readiness procedure: `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`
- Repo runbook: `RUNBOOK_AGENT.md`
- Root policy: `AGENTS.md`
- Skill routing: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- Backlog ledger: `docs/roadmap/BACKLOG_LEDGER.md`

## Wave Objective

Deliver a Tier 1 CI/CD consolidation program in stacked PRs that:
- defines a canonical backend/shared PR lane,
- keeps merge readiness deterministic and current-head based,
- removes duplicate PR-time CI responsibilities in PR2,
- introduces lightweight operational metrics without turning them into merge blockers.

## Current State

- PR-1 governance/bootstrap already landed in merged PR `#1240` (`24c51f85`).
- PR-2 workflow consolidation already landed on `origin/main` via PR `#1244` (`b7e029b4`).
- PR-3 risk topology already landed on `origin/main` via PR `#1253` (`3be5debf`).
- PR-4 is now the next canonical Tier 1 follow-up wave.
- Do not restart the series from PR-1; treat PR-1/PR-2/PR-3 as landed history and continue forward from PR-4.

## PR Series

### PR-1: Governance and Canonical Matrix Sync

- Create the Tier 1 task packet and this runbook.
- Align the CI/governance operating model with the existing contract matrix.
- Record the Tier 1 epic and child PR slices in `docs/roadmap/BACKLOG_LEDGER.md`.
- Resolve ledger drift where CI-classification work is already complete at the contract level.
- Status: landed in PR `#1240`; retained here as completed baseline context.

### PR-2: Workflow Consolidation

- Backend/shared PR execution is now canonicalized in `ci.yml`.
- `pr-tests.yml` and `pr-coverage.yml` are no longer active PR lanes.
- `security.yml` is a scheduled/manual audit lane, and `trivy.yml` remains a `main`/schedule/manual image-security lane; neither is a canonical PR blocker.
- Keep `build.yml`, frontend-only, and nightly-only surfaces separate.
- Workflow/governance PRs may still trigger specialized repo-level lanes such as `Frontend CI`, CodeQL, or Docker/image workflows; PR2 only makes `ci.yml` the canonical backend/shared merge-truth surface.
- Status: landed in PR `#1244`; retained here as completed baseline context.

### PR-3: Risk-Based PR Test Topology

- Open with the required reconciliation step so Tier 1 docs/backlog reflect landed PR-1 / PR-2 state before new topology work starts.
- Split PR execution into deterministic smoke, contract/risk suites, and nightly-only depth.
- Keep PR blockers focused on business-critical surfaces.
- Add PR-size governance and explicit `## Split Justification` PR-body proof for `>800` LoC cases.
- Status: landed in PR `#1253`; retained here as completed baseline context.

### PR-4: CI Metrics and Feedback Loop

- Add lightweight non-blocking CI metrics collection under `scripts/ci/`.
- Emit summary artifacts for critical-path duration, reruns, red-build rate, and xdist fallback frequency.
- Wire a weekly reporting path without changing merge blockers.
- Status: next pending canonical Tier 1 slice.

## Routing Card

- Decision question: How should PulsePlate consolidate backend/shared CI into one canonical Tier 1 lane without breaking current merge governance, runtime contracts, or stacked PR discipline?
- Primary agent: `agent-coordinator`
- Secondary agent: `backend-engineer`
- Formal reviewer path: `security-auditor`, `qa-engineer-agent`, `bug-hunter`
- Execution helper: `dev-operator`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`
- Default skills: `pulseplate-workflow`, `pulseplate-gates`
- Conditional skills:
  - `pulseplate-guards` for privileged/workflow/governance changes
  - `docs-sync` for policy/runbook/backlog edits
  - `pulseplate-openapi-sync` when API/type generation contracts are touched
  - `create-pr` only after local gates are green and the branch is ready to publish

## Sync Points

1. **PR-1 bootstrap locked**
   - task packet exists
   - runbook exists
   - backlog epic and child slices recorded
   - local governance docs are internally consistent
2. **PR-2 workflow consolidation**
   - canonical PR lane is `ci.yml`
   - duplicate PR-time lanes are retired as active PR lanes
   - required-check coverage is preserved
3. **PR-3 risk topology**
   - reconciliation step captures landed PR-1 / PR-2 evidence first
   - blocking smoke/contract lanes documented and enforced
   - nightly-only depth explicitly separated
   - PR-size governance documented and validated
4. **PR-4 metrics**
   - metrics collector exists
   - artifacts emit deterministically
   - metrics remain advisory only

## Hard Rules

- Always start with:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
- Follow coordinator-first routing.
- Run the mandatory post-open `qa-engineer-agent -> bug-hunter` pass.
- Claim merge readiness only after:
  - `pre-commit run --all-files`
  - `make verify`
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo <owner/repo> --require-auth`
- Isolate runtime/API behavior changes from PR-1 and PR-2 unless the workflow change cannot be isolated from the contract.
- Keep `build.yml` isolated as a specialized lane; do not reintroduce duplicate PR-time blockers.
- Treat Tier 1 metrics as advisory rather than merge blockers.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- `pytest -q tests/test_repo_policy_guards.py`
- workflow/tooling unit tests for any touched `scripts/ci/*` or orchestration helpers
- current-head merge wrapper for non-draft PRs

## Deferred from This Wave

- Ephemeral preview environments
- Mutation testing
- Full test-impact analysis
- AI-native self-healing CI
- Broader CI observability beyond lightweight summary artifacts
