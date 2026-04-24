# PR #1447 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact tracks the fresh-worktree merge-ready recovery for PR #1447.
Code/test remediation landed first in commit `e89c8db56`, which reconciles
dual-row VIP quota migration state into the canonical counter before consume,
centralizes tier constants, and adds deterministic regression coverage for both
legacy-only and dual-row migration scenarios.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e89c8db56
Evidence: `app/security/llm_monthly_quota.py:27-29`; `app/security/llm_monthly_quota.py:122-184`; `tests/test_insight_vip_monthly_quota_api.py:20-25`; `tests/test_insight_vip_monthly_quota_api.py:149-247`
Reason: The Sourcery review body asked for centralized VIP tier constants and for the legacy fingerprint test path to reuse shared helpers instead of duplicating the hashing logic inline. Commit `e89c8db56` implements both changes while also tightening the quota migration logic that those comments discussed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1447#pullrequestreview-4131511568 -> e89c8db56

Disposition: FIXED
Commit: e89c8db56
Evidence: `app/security/llm_monthly_quota.py:122-184`; `app/security/llm_monthly_quota.py:224-236`; `tests/test_insight_vip_monthly_quota_api.py:201-247`
Reason: The Codex inline finding identified a real bypass when legacy and canonical rows both existed. Commit `e89c8db56` reconciles both counters into the canonical row before consumption and the dual-row regression test proves the fail-closed behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1447#discussion_r3102743446 -> e89c8db56

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1447#discussion_r3102743446`
Reason: The Codex review shell is an aggregate wrapper around the single actionable inline quota-migration thread dispositioned immediately above and does not add a separate unresolved obligation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1447#pullrequestreview-4131513701

Disposition: NOT-A-BUG
Evidence: `app/security/llm_monthly_quota.py:165-177`; `tests/test_insight_vip_monthly_quota_api.py:201-247`
Reason: The CodeRabbit review suggests an optional explanatory comment about the idempotent UPSERT, not a correctness or merge-safety defect. The concurrency-safe behavior is already enforced by the monotonic `CASE` update and covered by the dual-row fail-closed regression test.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1447#pullrequestreview-4154143839

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: current-head GitHub checks after push.
- [ ] Required checks complete (no pending jobs)
  Evidence: current-head GitHub checks after push.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: `gh api graphql` review-thread snapshot after disposition sync.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: this artifact plus current PR timeline after push.
- [ ] Pre-commit green on latest pushed head
  Evidence: local `pre-commit run --all-files` on fresh-worktree branch head.
- [ ] `make verify` green on latest pushed head
  Evidence: local `make verify` on fresh-worktree branch head.
