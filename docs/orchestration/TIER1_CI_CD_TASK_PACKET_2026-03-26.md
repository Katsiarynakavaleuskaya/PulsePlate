# Tier 1 CI/CD Task Packet

**Date:** 2026-03-26 (`America/New_York`)
**Status:** Active packet for the Tier 1 backend/shared CI consolidation wave.
**Wave:** stacked PRs, coordinator-first, governance-first.

## Goal

Consolidate PulsePlate backend/shared PR CI into a canonical Tier 1 execution model
without weakening current merge blockers or broadening runtime behavior.

## Scope

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

### PR-2

- canonical backend/shared PR lane in `ci.yml`
- duplicate PR-time lane deprecation plan implemented
- shared setup reuse preserved

### PR-3

- risk-based PR topology
- PR-size governance
- blocker/non-blocker split documented and enforced

### PR-4

- `scripts/ci/` metrics collector
- `ci-metrics-summary.json`
- `ci-metrics-summary.md`

## Acceptance Criteria

- One canonical backend/shared PR workflow exists after the PR series
- Duplicate PR-time coverage/security responsibilities are removed or explicitly demoted
- Current-head merge-readiness remains deterministic and wrapper-backed
- Local merge evidence remains `pre-commit run --all-files` + `make verify`
- Mandatory post-open `qa-engineer-agent -> bug-hunter` lane is recorded and used

## Validation Commands

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- `pytest -q tests/test_repo_policy_guards.py`

For non-draft PRs:

- `python scripts/orchestration/check_merge_ready.py --pr-number <N> --repo <owner/repo> --require-auth`

## Risks

- Duplicate workflow removal can create hidden required-check gaps in GitHub branch protection.
- Python 3.13 + xdist + coverage instability can regress if PR topology changes are too aggressive.
- CI/governance docs can drift again unless the backlog epic and runbook stay authoritative.

## Deferred / Follow-ups

- preview environments
- mutation testing
- full test-impact analysis
- broader CI observability platform work
