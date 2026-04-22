# PR #1499 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 1067c5acd
Evidence: `app/services/insight_application_service.py:166-171` now resolves `recursive_rollout_policy` via a lazy `getattr(..., None)` fallback instead of eagerly constructing `_legacy_recursive_rollout_policy(...)`, and `tests/test_insight_application_service.py:519-590` adds a regression anchor that fails if the legacy helper runs while `prepared_runtime.recursive_rollout_policy` is already present.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158197463

Disposition: FIXED
Commit: 8152a92b6
Evidence: `app/services/insight_runtime.py:81-96` now derives the base `rag` snapshot from `recursive_rollout_policy.use_rag` when a prepared policy is injected and `use_rag` is omitted, `tests/test_remaining_modules.py:1340` adds the direct helper regression anchor, `docs/roadmap/BACKLOG_LEDGER.md:2101-2102` now names concrete `PR #1499`, `docs/orchestration/WAVE6_A7_RECURSIVE_METHODS_W1_PACKET_2026-04-22.md:24-42` and `:73-77` now carry explicit anchors, `docs/orchestration/WAVE6_A7_TASK_ANALYSIS_2026-04-22.md:57-66` adds current-head evidence pointers, and `docs/review/PR_1499_FIXED_MAPPING.md:29-35` restores unchecked merge-readiness boxes plus the required wait-window item.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158211717

Disposition: FIXED
Commit: bb22b11c0
Evidence: `app/services/insight_application_service.py:174-185` now passes `use_rag=recursive_rollout_policy.use_rag` into `generate_traced_insight(...)`, and `tests/test_insight_application_service.py:428`, `:521`, and `:608` assert that downstream `use_rag` follows the resolved recursive rollout policy on the prepared-policy, lazy-fallback, and fail-closed legacy paths.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499#pullrequestreview-4158236666

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] After latest bot/review activity, perform a final check and wait at least one review cycle before merging
- [ ] Pre-commit green on latest pushed head
  Most recent local proof: `pre-commit run --all-files` passed before pushing head `894dd6e9b8066fb5e8522931cae69233f9f39f8d`; final merge-cycle reconfirmation is still pending.
- [ ] `make verify` green on latest pushed head
  Most recent local proof: `make verify` passed earlier on branch head `3aa83b33779863e1c07d896e5398ee2a15388b49`; final merge-cycle reconfirmation is still pending.
