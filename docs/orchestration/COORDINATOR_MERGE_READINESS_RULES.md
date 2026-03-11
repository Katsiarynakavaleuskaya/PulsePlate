# Coordinator: Merge Readiness and Zero-Comments Policy

**Purpose:** Canonical rules for agents (including coordinator) so that "0 comments" and "ready to merge" are never reported incorrectly. Merge is allowed **only** when both conditions below are satisfied.

**Source of truth (policy):** `AGENTS.md` (section "PR merge readiness (hard rule)", ~line 31). This doc is the **operational** checklist and script reference for the coordinator and any agent performing merge-readiness verification.

---

## 1. Hard rule (no exceptions)

- **Merge only when:**
  1. **Zero unresolved review threads** (every review thread on the PR is resolved in GitHub UI).
  2. **Zero unmapped actionable bot comments** (every bot comment that contains actionable items is listed in the canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`).

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

The canonical operator entrypoint for merge governance in this repo is:

```bash
# From repo root, for strict local parity with CI.
export GITHUB_TOKEN="..."
export GH_TOKEN="${GITHUB_TOKEN}"
python scripts/orchestration/check_merge_ready.py \
  --pr-number <PR_NUMBER> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```

Local mode semantics:
- Default local runs may stay advisory for the disposition guard when `gh` auth is unavailable.
- Add `--require-auth` only when you want strict local parity with CI.
- CI is always strict for the disposition guard and requires `GH_TOKEN`.

- **Exit 0:** Phase 2 body/artifact contract, merge-readiness checks, and disposition proof all pass → PR satisfies merge-governance policy at the time of the run.
- **Exit 1:** At least one sub-gate failed → PR must **not** be merged until fixed; wrapper prints the failing gate names and their output.

Underlying enforcement scripts remain canonical for their own domains:

- `scripts/ci/check_pr_body_phase2_gates.py`
- `scripts/ci/check_pr_merge_readiness.py`
- `scripts/orchestration/check_review_threads_disposition.py`

**CI:** The same wrapper runs with `--event-path "$GITHUB_EVENT_PATH"`. For local/agent usage, use `--pr-number` and `--repo` instead.

---

## 4. Coordinator orchestration checklist (before saying "ready to merge" or "0 comments")

1. **Run the wrapper** (section 3) for the PR.
2. **If exit code is not 0:** Do **not** report "0 comments" or "ready to merge". Report the script output (unresolved count, UNMAPPED comment URLs) and instruct to fix and re-run.
3. **If exit code is 0:** You may state that the PR satisfies the zero-comments policy **at the time of the run**. Prefer: "Orchestration merge-check passed: Phase 2, merge-readiness, and disposition proof are all green."
4. **After new bot activity:** If the user or system reports new bot comments (e.g. CodeRabbit, Sourcery), **re-run the wrapper** before any merge decision; do not assume previous pass still holds.

**Loop until zero:** Full cycle (commit → push → watch CI → new comment → fix → re-check) is in `RUNBOOK_AGENT.md` (sections "Pre-merge readiness pass" ~line 121, "Loop until zero comments (canonical cycle)" ~line 160). Repeat until script exit 0 and CI green.

---

## 5. PR body requirements (reminder)

- `## Discussion Thread Pass` with checkboxes completed.
- `### Fixed in Commit Mapping` present as a mirror section for human review.
- `## Merge Readiness` section.

Canonical review-thread mappings live in `docs/review/PR_<N>_FIXED_MAPPING.md`. The PR body no longer needs late-cycle URL→SHA duplication once the canonical artifact exists.

See `RUNBOOK_AGENT.md` (Pre-merge readiness pass ~line 121, Phase2 PR body gates).

---

## 6. References

- **Policy:** `AGENTS.md` (PR merge readiness hard rule, ~line 31).
- **Procedure:** `RUNBOOK_AGENT.md` (Pre-merge readiness pass ~line 121, Loop until zero ~line 160, Verify zero unresolved review threads).
- **Canonical operator entrypoint:** `scripts/orchestration/check_merge_ready.py`.
- **CI gate:** `scripts/ci/check_pr_merge_readiness.py` (merge-readiness sub-gate).
- **Phase2 body check:** `scripts/ci/check_pr_body_phase2_gates.py`.
