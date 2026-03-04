# PR Merge Workflow Matrix (Canonical)

**Purpose:** Single checklist for bringing PRs to green and merge. Use for every PR.

---

## 1. Online Review & Fixes

- [ ] Fetch and address all review comments (Codex, Sourcery, Cubic, CodeRabbit)
- [ ] Resolve all review threads (`gh api graphql` resolveReviewThread)
- [ ] Add Fixed in Commit Mapping: `- <review-url> -> <commit-sha>` for each actionable bot
- [ ] PR body: Discussion Thread Pass checked, mapping section complete

---

## 2. Documentation & Checklist

- [ ] PR body has: Scope, Files, DoD, Discussion Thread Pass, Fixed in Commit Mapping, Merge Readiness
- [ ] Deferred / Follow-ups section with ledger links if any
- [ ] `python scripts/ci/check_pr_body_phase2_gates.py --body "..."` passes

---

## 3. Gates (Before Push)

- [ ] `python3 scripts/orchestration/check_preflight.py` (in clean worktree)
- [ ] `pre-commit run --all-files`
- [ ] Agent Run Summary JSON generated (`artifacts/agent_runs/...json`) and decision is `PASS`
- [ ] (Optional) Telemetry rollup generated (`artifacts/orchestration/telemetry_rollup.json`)
- [ ] `make test-fast` (optional, CI runs it)

---

## 4. CI → Green

- [ ] `gh run watch <run-id> --exit-status` or wait for green
- [ ] Rerun failed jobs if transient: `gh run rerun <run-id> --failed`
- [ ] Zero unresolved threads, merge readiness gate PASS

---

## 5. Merge

- [ ] `gh api repos/.../pulls/<N>/merge -X PUT -f merge_method=squash -f delete_branch_on_merge=true`
- [ ] Or: `gh pr merge <N> --squash --delete-branch`

---

## 6. Post-Merge

- [ ] `git fetch --prune origin`
- [ ] `git checkout main && git pull origin main`
- [ ] Remove worktree: `git worktree remove worktrees/<name> --force`
- [ ] Delete local branch: `git branch -d <branch>`
- [ ] `git worktree prune`

---

## 7. Sanity

- [ ] `make test-fast`
- [ ] `make verify` (when preparing release)

---

## 8. Ledger

- [ ] Update BACKLOG_LEDGER: mark completed items with Status, Target PR
- [ ] If merged PR closes ledger item: open docs-only follow-up PR same day

---

## 9. Next PR Plan

- [ ] Agree plan with user (scope, backlog, worktree)
- [ ] Create worktree: `git worktree add -b <branch> worktrees/<name> origin/main`
- [ ] Execute in worktree, push, open PR

---

**Last updated:** 2026-03-05 (Agent Run Summary Artifact)
