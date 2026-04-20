<!-- markdownlint-disable MD034 -->
# PR #1483 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:47-57`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e8a689710
Evidence: `app/services/insight_application_service.py:32-33`, `app/services/insight_application_service.py:65-91`, `tests/test_remaining_modules.py`
Reason: Best-effort promotion is now bounded by an explicit async timeout so slow or stalled awaitable stores degrade to logging instead of request-path latency.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3109939655 -> e8a689710

Disposition: FIXED
Commit: e8a689710
Evidence: `core/insight/philosophical_runtime.py:86-98`, `core/insight/philosophical_runtime.py:560-580`, `tests/test_philosophical_runtime.py`
Reason: The retriever seam now caches signature support, forwards `knowledge_policy` to `**kwargs`-compatible retrievers, and fails closed toward forward-compatible passing when signature introspection is opaque.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3109959617 -> e8a689710

Disposition: FIXED
Commit: e8a689710
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:1639-1643`
Reason: The PR-K1 ledger entry now reflects active implementation status instead of staying in planned state while this slice is in flight.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3109959623 -> e8a689710

Disposition: FIXED
Commit: e8a689710
Evidence: `core/insight/philosophical_runtime.py:86-98`, `core/insight/philosophical_runtime.py:592-600`, `core/knowledge/store.py:99-102`, `tests/test_knowledge_contracts.py`
Reason: The Sourcery review surfaced three real high-level issues and the current head now addresses all of them: the route-factual policy flag is enforced, retriever signature introspection is cached, and `InMemoryKnowledgeStore` exposes a stable `all_records()` seam for tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#pullrequestreview-4139123418 -> e8a689710

Disposition: NOT-A-BUG
Evidence: `core/knowledge/store.py:20-27` already allows awaitable `promote(...)` returns, while the remaining actionable inline findings from the wrapper are fixed above as `#discussion_r3109959617` and `#discussion_r3109959623`.
Reason: The CodeRabbit wrapper review does not introduce a separate standalone defect once the stale protocol nitpick is checked against current code and the concrete inline issues are dispositioned.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#pullrequestreview-4139178116

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:38-45`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: GitHub checks for PR #1483 current head.
- [ ] Required checks complete (no pending jobs)
  Evidence: GitHub checks for PR #1483 current head.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: Current known review-thread URLs are dispositioned above; re-check GitHub thread state on current head before merge.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: Current known bot review URLs are mapped above; re-check current head before merge for any new activity.
- [ ] Pre-commit green on latest pushed head
  Evidence: local pre-push hooks passed before `origin/codex/pr-k1-knowledge-promotion` push.
- [ ] `make verify` green on latest pushed head
  Evidence: local `make verify` / `make diff-cov` did not complete in this environment because repeated runs were terminated externally with `make: *** [diff-cov] Terminated: 15`; GitHub current-head CI remains the heavy gate for this draft PR.
<!-- markdownlint-enable MD034 -->
