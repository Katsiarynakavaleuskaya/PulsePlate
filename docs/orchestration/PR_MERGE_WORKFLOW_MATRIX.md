# PR Merge Workflow Matrix (Canonical)

**Purpose:** Single checklist for bringing PRs to green and merge. Use for every PR.

**Series rule:** Do not start the next PR in a series until the current PR has
completed open-PR review, merge, local sync, sanity, and cleanup.

**Canonical references:**

- Series-rule wording lives in `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
  under `Approved PR Series For This Wave`.
- Disposition semantics (`FIXED`, `NOT-A-BUG`, `DEFERRED`) live in `AGENTS.md`
  under `Review Governance`.

---

## 1. Local Prep

- [ ] `python3 scripts/orchestration/check_preflight.py` (in clean worktree)
- [ ] `pre-commit run --all-files`
- [ ] Agent Run Summary JSON generated (`artifacts/agent_runs/...json`) and decision is `PASS`
- [ ] (Optional) Telemetry rollup generated (`artifacts/orchestration/telemetry_rollup.json`)
- [ ] Run required local gates for the touched scope before the first PR push

---

## 2. Open PR

- [ ] Open PR with canonical body sections and create/confirm `docs/review/PR_<N>_FIXED_MAPPING.md`
- [ ] Keep draft status until scope and local evidence are stable

---

## 3. Post-Open Review Loop

- [ ] If the lane declares a mandatory post-open reviewer path, run it now
- [ ] For packets/runbooks that require it, execute `qa-engineer-agent -> bug-hunter` after PR open
- [ ] Fetch and address all review comments (Codex, Sourcery, Cubic, CodeRabbit)
- [ ] Record disposition evidence in `docs/review/PR_<N>_FIXED_MAPPING.md` before resolving any actionable review thread
- [ ] Use canonical disposition outcomes from `AGENTS.md` Review Governance: `FIXED`, `NOT-A-BUG`, or `DEFERRED`
- [ ] Fixed in Commit Mapping entries may be `- <review-url> -> <commit-sha>` or `- <review-url>` depending on disposition proof
- [ ] Resolve review threads only after the artifact contains the required disposition proof
- [ ] PR body: Discussion Thread Pass checked, mirror sections complete

---

## 4. Before Each Push

- [ ] Re-run `pre-commit run --all-files`
- [ ] Re-run the required local gates for the touched scope
- [ ] Commit hook modifications separately when hooks change files

---

## 5. Documentation & Checklist

- [ ] PR body has: Scope, Files, DoD, Discussion Thread Pass, Fixed in Commit Mapping, Merge Readiness
- [ ] Deferred / Follow-ups section with ledger links if any
- [ ] Artifact-first Phase2 validation passes: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number <PR_NUMBER>`
- [ ] Use `--body "..."` only as a local/body-only fallback when `pr_number` is unavailable

---

## 6. CI → Green

- [ ] `gh run watch <run-id> --exit-status` or wait for green
- [ ] Rerun failed jobs if transient: `gh run rerun <run-id> --failed`
- [ ] Zero unresolved threads, merge readiness gate PASS

---

## 7. Final Merge Gate

- [ ] Run `python3 scripts/orchestration/check_merge_ready.py --pr-number <PR_NUMBER> --repo <owner/repo> --require-auth` after the latest bot/review activity
- [ ] Confirm no pending required jobs remain on the current head
- [ ] Wait one review cycle after the final green state before merge

---

## 8. Merge

- [ ] `gh api repos/.../pulls/<N>/merge -X PUT -f merge_method=squash -f delete_branch_on_merge=true`
- [ ] Or: `gh pr merge <N> --squash --delete-branch`

---

## 9. Post-Merge Sync & Cleanup

- [ ] `git fetch --prune origin`
- [ ] `git checkout main && git pull origin main`
- [ ] Remove worktree: `git worktree remove worktrees/<name> --force`
- [ ] Delete local branch: `git branch -d <branch>`
- [ ] `git worktree prune`
- [ ] Remove temp outputs and local-only artifacts created by this PR lane

---

## 10. Sanity

- [ ] `make test-fast`
- [ ] `make verify` (when preparing release)

---

## 11. Ledger

- [ ] Update BACKLOG_LEDGER: mark completed items with Status, Target PR
- [ ] If merged PR closes ledger item: open docs-only follow-up PR same day

---

## 12. Next PR Gate

- [ ] Confirm sections 8-10 are complete before starting the next PR in the series
- [ ] Agree plan with user (scope, backlog, worktree)
- [ ] Create worktree: `git worktree add -b <branch> worktrees/<name> origin/main`
- [ ] Execute in worktree, push, open PR

---

**Last updated:** 2026-03-26 (Automation readiness alignment)
