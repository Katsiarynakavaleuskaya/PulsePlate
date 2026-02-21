# Coordinator: Merge Readiness and Zero-Comments Policy

**Purpose:** Canonical rules for agents (including coordinator) so that "0 comments" and "ready to merge" are never reported incorrectly. Merge is allowed **only** when both conditions below are satisfied.

**Source of truth (policy):** `AGENTS.md` (section "PR merge readiness (hard rule)", ~line 31). This doc is the **operational** checklist and script reference for the coordinator and any agent performing merge-readiness verification.

---

## 1. Hard rule (no exceptions)

- **Merge only when:**
  1. **Zero unresolved review threads** (every review thread on the PR is resolved in GitHub UI).
  2. **Zero unmapped actionable bot comments** (every bot comment that contains actionable items is listed under `### Fixed in Commit Mapping` in the PR body as `- <comment-url> -> <commit-sha>`).

- **Do not merge when:**
  - Any review thread is unresolved.
  - Any bot (CodeRabbit, Sourcery, Cubic, etc.) has posted a comment/review that is "actionable" (e.g. "Actionable comments posted", "Potential issue", "Prompt for AI Agents") and that comment URL is **not** present in the `### Fixed in Commit Mapping` section with a commit that addresses it.

---

## 2. Why "0 unresolved threads" is not enough

- **Mistake to avoid:** Saying "0 comments" or "ready to merge" based **only** on "unresolved threads = 0".
- Threads can be marked "Resolved" in the UI before the fix is committed or before the comment is added to the mapping.
- New bot comments can appear **after** your last check; a single check is a point-in-time result.
- **Correct interpretation of "0 comments":**
  **0 unresolved threads** **and** **every actionable bot comment is mapped** (and the mapping commit actually contains the fix). Verification must be re-run after the latest bot/review activity.

---

## 3. Verification script (canonical)

The **only** authoritative check for "zero comments" in this repo is:

```bash
# From repo root, with GITHUB_TOKEN set (e.g. gh auth token or fine-grained PAT with repo read).
export GITHUB_TOKEN="..."
python scripts/ci/check_pr_merge_readiness.py --pr-number <PR_NUMBER> --repo Katsiarynakavaleuskaya/PulsePlate
```

- **Exit 0:** Zero unresolved threads and all actionable bot comments are mapped → PR satisfies "0 comments" policy.
- **Exit 1:** Either unresolved threads exist or unmapped actionable comments exist → PR must **not** be merged until fixed; script prints what is missing (e.g. `UNMAPPED: ...`).

**CI:** The same script runs in CI with `--event-path "$GITHUB_EVENT_PATH"`. For local/agent usage, use `--pr-number` and `--repo` instead.

---

## 4. Coordinator orchestration checklist (before saying "ready to merge" or "0 comments")

1. **Run the script** (section 3) for the PR.
2. **If exit code is not 0:** Do **not** report "0 comments" or "ready to merge". Report the script output (unresolved count, UNMAPPED comment URLs) and instruct to fix and re-run.
3. **If exit code is 0:** You may state that the PR satisfies the zero-comments policy **at the time of the run**. Prefer: "Merge-readiness script passed: 0 unresolved threads, all actionables mapped."
4. **After new bot activity:** If the user or system reports new bot comments (e.g. CodeRabbit, Sourcery), **re-run the script** before any merge decision; do not assume previous pass still holds.

**Loop until zero:** Full cycle (commit → push → watch CI → new comment → fix → re-check) is in `RUNBOOK_AGENT.md` (sections "Pre-merge readiness pass" ~line 121, "Loop until zero comments (canonical cycle)" ~line 160). Repeat until script exit 0 and CI green.

---

## 5. PR body requirements (reminder)

- `## Discussion Thread Pass` with checkboxes completed.
- `### Fixed in Commit Mapping` with either:
  - One line per actionable comment: `- <comment-url> -> <commit-sha>`, or
  - Exactly: `- No actionable review comments` (when there are no actionable bot comments).
- `## Merge Readiness` section.

See `RUNBOOK_AGENT.md` (Pre-merge readiness pass ~line 121, Phase2 PR body gates).

---

## 6. References

- **Policy:** `AGENTS.md` (PR merge readiness hard rule, ~line 31).
- **Procedure:** `RUNBOOK_AGENT.md` (Pre-merge readiness pass ~line 121, Loop until zero ~line 160, Verify zero unresolved review threads).
- **CI gate:** `scripts/ci/check_pr_merge_readiness.py` (exit 0/1: main() return and merge-readiness checks; same logic for CI and local/agent).
- **Phase2 body check:** `scripts/ci/check_pr_body_phase2_gates.py`.
