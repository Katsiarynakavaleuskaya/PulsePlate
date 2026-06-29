# PR 2043 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2043
Title: `docs(review): consolidate PR 2032 mapping and local verify policy`
Branch: `codex/fix-documentation-mapping-for-commits`

## Summary

This PR is the single survivor for duplicate PR 2032 mapping hygiene from
PR #2042 and PR #2043. It also updates repo-wide agent validation policy so
local agents do not run full `make verify` by default. GitHub current-head CI
owns the heavy/full signal; local agent validation uses the narrow bundle.

## Scope

- Correct PR 2032 fixed-mapping refs for `e1531a0041e0919dc4b4386d1f46eefb10f63083`
  and `011d4901626e50533c0b96be20e776b99f59aa23`.
- Add this PR 2043 fixed-mapping artifact and keep the PR body governance
  mirror aligned.
- Update root/onboarding/runbook/orchestration contract docs so local agents
  must not run full local `make verify` by default.
- Preserve GitHub current-head required CI, diff coverage, review-thread
  disposition, bot-actionable handling, and merge-readiness strictness.

## Out Of Scope

- Runtime app/backend/frontend/iOS behavior.
- Requirements, lockfile, package proxy, or dependency resolver changes.
- Weakening CI, diff coverage, review-thread, bot-actionable, Codex Security,
  or merge-readiness policy.
- Merging PR #2043 before current-head CI and strict governance pass.
- Fixing private Python package proxy timeout or lint-infra flakes that are not
  caused by this docs/governance diff.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/970b83f4014d.json`
- Branch: `codex/fix-documentation-mapping-for-commits`
- Base: `main`
- Worktree: `worktrees/pr2043-combined-local-verify-policy`
- Packet creation was treated as provenance only, not role execution.
- Dispatch manifest generated the required role order:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> architecture-specialist`.

## Experiment Runner Evidence

- Not applicable: Experiment Runner oracle-only governance reviewer did not run
  or materially shape this docs/governance consolidation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Duplicate PR #2042 / PR #2043 scope reviewed and consolidated into PR #2043.
- PR #2043 fixed-mapping artifact created.
- Local full `make verify` deferral documented as repo-wide agent policy.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass remains required on final head.
- [ ] Codex Security diff scan / finding discovery remains required when available.
- [ ] `pulseplate-pr-review` remains required.
- [ ] CodeRabbit, Sourcery, and Cubic current-head actionables must be checked after push.
- [ ] Strict merge-readiness wrapper with auth and mandatory wait-window remain required before merge.

## Fixed in Commit Mapping

- No actionable review comments

## Consolidated Fix Evidence

Disposition: FIXED
Evidence: `docs/review/PR_2032_FIXED_MAPPING.md` references resolvable commit `e1531a0041e0919dc4b4386d1f46eefb10f63083` for the Codex Security fixed mapping.
Reason: Corrects the non-resolvable PR 2032 provenance ref carried by the original PR #2043 branch.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2043

Disposition: FIXED
Evidence: `docs/review/PR_2032_FIXED_MAPPING.md` references resolvable commit `011d4901626e50533c0b96be20e776b99f59aa23` for the diff-coverage fixed mapping.
Reason: Carries over the duplicate PR #2042 mapping fix into the single survivor PR #2043.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2042
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2043

Disposition: FIXED
Evidence: `AGENTS.md`, `RUNBOOK_AGENT.md`, `docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md`, and `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md` state that local agents must not run full `make verify` by default; GitHub current-head CI is the heavy/full signal while local agents run the narrow bundle.
Reason: Prevents future agents from overheating or exceeding the operator machine budget with unsharded local full-suite runs while preserving strict CI and merge governance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2043

## Validation Plan / Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PENDING: `python3 scripts/orchestration/check_agent_consistency.py`
- PENDING: SHA checks for `e1531a0041e0919dc4b4386d1f46eefb10f63083` and
  `011d4901626e50533c0b96be20e776b99f59aa23`
- PENDING: stale-ref `rg` checks
- PENDING: `git diff --check`
- PENDING: PR body / fixed-mapping gates
- PENDING: `make validate-changed`
- PENDING: `pre-commit run --all-files`
- NOT RUN: local full `make verify`; prohibited by the repo-wide local
  full-verify budget rule unless a human explicitly overrides it for a single
  invocation.

## Merge Readiness

- Not merge-ready yet.
- Current-head GitHub CI, post-open role passes, Codex Security,
  `pulseplate-pr-review`, bot actionables, and strict merge-readiness remain
  required.
