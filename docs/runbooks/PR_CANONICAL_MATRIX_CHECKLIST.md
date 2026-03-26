# PR Canonical Matrix Checklist

## Purpose

Single operational checklist so context is never lost during PR execution.

## Canonical Flow (Strict Order)

1. Matrix and scope lock
   - Define IN/OUT scope.
   - Confirm work package type (runtime/docs/security/etc.).
   - Start with coordinator-first routing.
2. Audit and brainstorming
   - Quick audit of touched surfaces and risks.
   - Brainstorm alternatives, choose one path, record rationale.
3. Plan and implementation
   - Create concrete step plan.
   - Implement in narrow scope only.
4. Local quality gates
   - Run relevant tests/lint/build for changed scope.
   - Fix failures before commit.
5. Commits and PR creation
   - Logical commits with canonical messages.
   - Open PR with required body sections and mapping.
6. Post-open review lane
   - If the packet/runbook for this lane requires a post-open reviewer path, run it only after the PR exists.
   - `qa-engineer-agent -> bug-hunter` is a post-open loop, not a pre-PR substitute.
7. Online CI watch
   - Monitor checks until stable pass.
   - Rerun only when transient failures are confirmed.
8. Bot and review loop
   - Answer all actionable bot comments (CodeRabbit/Sourcery/etc.).
   - Record disposition evidence in the canonical artifact before resolving any actionable review thread.
   - Resolve review threads only after FIXED / NOT-A-BUG / DEFERRED proof is present.
9. Merge gate
   - Merge only when:
     - required CI is green,
     - no unresolved review threads,
     - no actionable bot comments remain,
     - the final strict merge-wrapper pass and wait-window are complete.
10. Post-merge closure
   - Sync the local repo back to `origin/main`.
   - Remove merged branches, worktrees, and temporary artifacts for this lane.
1. Post-merge sanity
   - Run the required sanity checks after sync/cleanup.
   - Only after sanity passes is the lane considered closed.
1. Next PR start gate
   - Start the next PR in a series only after post-merge closure and post-merge sanity are complete.
1. Ledger and follow-up closure
   - Update backlog ledger for deferred/completed items.
   - Add follow-up docs-only ledger closure PR when policy requires.

## Hard Merge Conditions

- No unresolved review threads.
- Required checks are PASS.
- No unaddressed actionable bot comments.
- Final strict merge-wrapper pass completed.
- Wait-window after the final green state is complete.
- PR scope stays within declared matrix.

## Operator Notes

- Never skip matrix/audit/plan stages.
- Never mark "ready" before full gate closure.
- Canonical series-rule wording lives in `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`.
- Canonical disposition semantics live in `AGENTS.md` under `Review Governance`.
- Never begin PR2 while PR1 is still in review, merge, sync, sanity, or cleanup.
- If context drifts, return to this checklist and restart at step 1.
