# Tier 1 CI/CD Task Packet

**Date:** 2026-03-26 (`America/New_York`)
**Status:** Landed PR-4 packet retained as baseline evidence after merged PR `#1286`.
**Wave:** stacked PRs, coordinator-first, governance-first.

## Goal

Consolidate PulsePlate backend/shared PR CI into a canonical Tier 1 execution model
without weakening current merge blockers or broadening runtime behavior.

## Relationship to the Runbook

- [`docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`](./TIER1_CI_CD_PR_SERIES_RUNBOOK.md)
  is the canonical process/runbook SoT for this wave.
- This packet keeps only branch-scoped execution details: scope, critical
  surfaces, routing, PR-by-PR deliverables, and acceptance criteria.
- Shared process sections such as hard rules, validation baseline, deferred
  scope, and packet versioning are inherited from the runbook and are only
  summarized here when a branch-local reminder is useful.

## Scope

### Active execution state

- PR-1 governance/bootstrap is already landed in PR `#1240` (`24c51f85`).
- PR-2 workflow consolidation is already landed on `origin/main` in PR `#1244` (`b7e029b4`).
- PR-3 risk topology is already landed on `main` in PR `#1253` (`3be5debf`).
- PR-4 advisory CI metrics is already landed on `main` in PR `#1286` (`a9bf2781`).
- This packet is retained as the landed execution record for the original Tier 1 PR1-PR4 wave; follow-up work should open new backlog-scoped packets instead of treating PR-4 as still active.

### In scope

- CI/governance docs and runbooks
- backlog/epic tracking for the Tier 1 program
- backend/shared PR workflow consolidation
- risk-based PR test topology for business-critical surfaces
- lightweight CI metrics artifacts

### Out of scope

- frontend-only CI redesign
- iOS CI redesign beyond shared-governance references
- ephemeral preview environments
- mutation testing
- full test-impact analysis
- runtime API/product behavior changes unrelated to CI/governance

## Critical Surfaces

Blocking surfaces for Tier 1 PR-lane decisions:
- billing verification and manual reconciliation
- entitlement/tier routing
- VIP insight / AI runtime entrypoints
- OpenAPI determinism and generated client sync
- merge-readiness and review-governance scripts

## Routing

- Primary: `agent-coordinator`
- Secondary: `backend-engineer`
- Reviewer: `security-auditor`
- Additional review lane: `qa-engineer-agent -> bug-hunter`
- Execution helper: `dev-operator`

## Skill Packet

### Always

- `pulseplate-workflow`
- `pulseplate-gates`

### Conditional

- `pulseplate-guards` for workflow/governance/privileged surfaces
- `docs-sync` for docs/runbook/backlog edits
- `pulseplate-openapi-sync` for generated API/type contract drift
- `create-pr` only after local readiness

## Deliverables by PR

### PR-1

- Tier 1 runbook
- Tier 1 task packet
- backlog epic + child slices
- governance/runbook cross-links
- Status: landed baseline (`#1240`)

### PR-2

- canonical backend/shared PR lane in `ci.yml`
- `pr-tests.yml` and `pr-coverage.yml` retired as active PR lanes
- `security.yml` demoted to scheduled/manual audit lane; `trivy.yml` kept as `main`/schedule/manual image-security lane
- `build.yml` kept as a specialized release/image lane
- specialized repo-level PR workflows may still attach on workflow/governance diffs, but they stay outside canonical backend/shared merge truth unless branch protection promotes them
- Status: landed baseline (`#1244`)

### PR-3

- Tier 1 reconciliation pre-step for landed PR-1 / PR-2 evidence
- risk-based PR topology
- PR-size governance with explicit `## Split Justification` PR-body proof for `>800` LoC cases
- blocker/non-blocker split documented and enforced
- Status: landed baseline (`#1253`)

### PR-4

- `scripts/ci/` metrics collector
- `ci-metrics-summary.json`
- `ci-metrics-summary.md`
- `ci-metrics.yml` advisory schedule/manual workflow
- `GITHUB_STEP_SUMMARY` publication path
- Status: landed baseline (`#1286`)

## Acceptance Criteria

- PR2's canonical backend/shared PR lane in `ci.yml` remains the only backend/shared merge-truth surface
- PR3 makes the PR path explicit as critical smoke plus contract/risk suites, while keeping nightly/regression depth outside normal PR blocking flow
- PR3 adds documented and enforced PR-size governance for `<300`, `300-800`, and `>800` LoC cases
- PR4 keeps metrics advisory-only and publishes artifact + step summary without widening merge blockers
- Current-head merge-readiness remains deterministic and wrapper-backed
- Local merge evidence remains `pre-commit run --all-files` + `make verify`
- Mandatory post-open `qa-engineer-agent -> bug-hunter` lane remains recorded and used for this slice

## Validation Commands

Canonical validation baseline is inherited from the Tier 1 runbook. Use the
commands below as the branch-local execution reminder for this packet:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- `pytest -q tests/test_repo_policy_guards.py`

For non-draft PRs:

- `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo <owner/repo> --require-auth`

## Risks

- Duplicate workflow removal can create hidden required-check gaps in GitHub branch protection.
- Python 3.13 + xdist + coverage instability can regress if PR topology changes are too aggressive.
- CI/governance docs can drift again unless the backlog epic and runbook stay authoritative.
- Advisory metrics can become noisy if the collector treats missing log data as hard failure; unknown states must stay non-blocking.

## Deferred / Follow-ups

Deferred scope is governed by the Tier 1 runbook. For this packet, the active
carry-forward list is:

- preview environments
- mutation testing
- full test-impact analysis
- broader CI observability platform work beyond the weekly artifact/summary loop
