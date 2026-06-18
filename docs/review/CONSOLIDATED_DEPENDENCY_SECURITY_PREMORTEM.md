# Consolidated Dependency Security PR Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/ad85012276cf.json` (local, gitignored)
Date: 2026-06-18

## Summary

Plan: land one consolidated dependency-security PR that patches frontend npm
alert floors, disables vulnerable tracked RAGAS/DiskCache eval deps, splits
Python dependency submission by profile, and keeps torch optional-vector risk
explicitly upstream-blocked.

Failure frame: it is 48 hours from now, the PR merged, and Dependabot/security
debt got worse because the lane either hid real alerts, broke offline eval
tooling, or produced misleading dependency graph data.

## Most Likely Failure

The most likely failure is a false-green dependency graph: the workflow looks
more structured, but the submitted snapshot still mixes optional/manual
profiles into CI-lite or omits a relevant lockfile. That would leave stale
alerts open or hide real optional-surface findings until the next security
cycle.

Disposition: FIXED in this diff by splitting Python dependency submission into
runtime, eval/data, and RAG/vector temp roots with unique correlators, plus
focused tests in `tests/test_python_supply_chain_controls.py` and
`tests/guards/test_security_devtooling_regression_guards.py`.

## Most Dangerous Failure

The most dangerous failure is treating no-patch advisories as ordinary version
bumps. RAGAS/DiskCache and torch have different risk shapes: RAGAS/DiskCache
can be removed from tracked eval deps now, while torch remains only in optional
RAG/vector profiles and needs advisory/private-index agreement before a bump.

Disposition: FIXED/DEFERRED in this diff. `requirements-evals.in` and
`requirements-evals.txt` remove vulnerable RAGAS/DiskCache roots; docs and tests
record the disabled state. Torch remains deferred under
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`
with refreshed advisory wording.

## Hidden Assumption

The hidden assumption is that Dependabot alert count and `npm audit` are the
same surface. They are not: `ws` was no longer an open Dependabot alert, but
local audit still reported the already-ledgered Storybook `ws` finding.

Disposition: FIXED in this diff by including `ws@8.21.0`, updating the existing
Node/toolchain guard, and keeping the scope tied to the existing P1 backlog
item rather than silent frontend churn.

## Revised Plan

- Keep the PR consolidated, but only across dependency-security surfaces already
  evidenced by current alerts, audit output, or existing backlog.
- Do not change backend routes, OpenAPI, product runtime, semantic cache,
  provider behavior, or RAG runtime.
- Document the operator-approved local `make verify` deferral in the PR body and
  fixed mapping; use focused local gates plus current-head CI parity.
- After merge, refresh dependency graph workflows from `main` before judging
  which alerts are actually closed.

## Pre-Merge Checklist

- Focused Python guards pass:
  `pytest -q tests/test_frontend_dependency_guards.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py tests/test_ci_workflow_pr_size_governance_contract.py`.
- Frontend package checks pass: `npm audit --package-lock-only
  --audit-level=moderate`, `npm run build`, `npm run test:ci`, and
  `npm run build-storybook`.
- Eval runner remains importable without native RAGAS deps:
  `python -m evals.ragas.run_ragas_eval --help` and focused RAGAS tests pass.
- `make validate-changed` and `pre-commit run --all-files` pass.
- PR body and `docs/review/PR_<N>_FIXED_MAPPING.md` record the machine-heavy
  local `make verify` deferral and all review/premortem dispositions.
- Current-head CI and strict merge-readiness wrapper pass after the latest bot
  or review activity.

## Decision

`proceed with changes`

The plan is sound only with the implemented changes above: include the audit
active `ws` floor, disable rather than waive RAGAS/DiskCache, split Python
dependency submission by profile, and keep torch as explicit upstream-blocked
optional-vector debt.
