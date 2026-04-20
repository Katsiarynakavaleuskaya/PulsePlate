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

Disposition: FIXED
Commit: a7acaff6d
Evidence: `tests/test_remaining_modules.py:303-341`, `tests/test_remaining_modules.py:459-479`
Reason: The fast-lane helper seams now carry explicit return annotations and a typed `supersedes` parameter, matching repo typing requirements for modified Python helpers.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110020760 -> a7acaff6d

Disposition: FIXED
Commit: a7acaff6d
Evidence: `tests/test_remaining_modules.py:769-780`
Reason: The pgvector-missing smoke test no longer patches `builtins.__import__`; it now simulates the missing module through `monkeypatch` + `sys.modules`, which stays within repo test policy.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110020770 -> a7acaff6d

Disposition: NOT-A-BUG
Evidence: `core/rag/orchestration.py:295-304`
Reason: Current head no longer marks knowledge candidates canonical unconditionally; promotion is allowed only when the philosophy path ran without recursion and without a degraded retrieval reason, so the bot comment is stale relative to current code.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110038251

Disposition: NOT-A-BUG
Evidence: `core/insight/philosophical_runtime.py:86-98`, `core/insight/philosophical_runtime.py:572-580`
Reason: Current head already supports retrievers that accept `**kwargs` and falls back safely when signature introspection is opaque, so the strict-forwarding concern is stale on this head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110038254

Disposition: FIXED
Commit: a7acaff6d
Evidence: `tests/test_remaining_modules.py:303-341`, `tests/test_remaining_modules.py:459-479`, `tests/test_remaining_modules.py:769-780`
Reason: The current CodeRabbit review wrapper is fully covered by the two actionable current-head findings fixed in `a7acaff6d`: helper type hints were tightened and the forbidden `builtins.__import__` patch was replaced with a `monkeypatch`-based module-missing simulation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#pullrequestreview-4139245059 -> a7acaff6d

Disposition: NOT-A-BUG
Evidence: `core/rag/orchestration.py:295-304`, `core/insight/philosophical_runtime.py:86-98`, `core/insight/philosophical_runtime.py:572-580`
Reason: The Cubic wrapper review only aggregates the two inline findings already dispositioned above; on current head the promotion-canonical guard and `**kwargs` retriever forwarding are already correct, so the wrapper itself does not represent a separate unresolved defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#pullrequestreview-4139263200

Disposition: FIXED
Commit: 7eec5d903
Evidence: `app/services/insight_application_service.py:76-97`, `tests/test_remaining_modules.py:655-690`
Reason: Sync knowledge-store promotion is now offloaded via `asyncio.to_thread(...)` and bounded by the same timeout contract as awaitable stores, so slow synchronous persistence can no longer stall the response path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110157635 -> 7eec5d903

Disposition: FIXED
Commit: 7eec5d903
Evidence: `core/insight/philosophical_runtime.py:85-96`, `tests/test_philosophical_runtime.py:628-637`
Reason: `_retriever_accepts_knowledge_policy(...)` no longer uses `@lru_cache`, so callable retriever instances do not need to be hashable and the helper cannot accumulate an unbounded per-callable cache.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110157643 -> 7eec5d903

Disposition: FIXED
Commit: 7eec5d903
Evidence: `app/services/insight_application_service.py:76-97`, `core/insight/philosophical_runtime.py:85-96`, `tests/test_remaining_modules.py:655-690`, `tests/test_philosophical_runtime.py:628-637`
Reason: The latest CodeRabbit wrapper is fully covered by the current-head fixes for sync promotion timeout handling and removal of the unsafe retriever-signature cache.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#pullrequestreview-4139390601 -> 7eec5d903

Disposition: FIXED
Commit: 7eec5d903
Evidence: `core/insight/philosophical_runtime.py:85-96`, `tests/test_philosophical_runtime.py:628-637`
Reason: The cubic inline request is satisfied by removing the cache decorator entirely, which resolves both the unhashable-callable failure mode and the unbounded-cache-growth concern.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110174850 -> 7eec5d903

Disposition: FIXED
Commit: 7eec5d903
Evidence: `core/insight/philosophical_runtime.py:85-96`, `tests/test_philosophical_runtime.py:628-637`
Reason: The helper no longer maintains any cache state, so there is no remaining unbounded `lru_cache(maxsize=None)` growth path on current head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#discussion_r3110174851 -> 7eec5d903

Disposition: FIXED
Commit: 7eec5d903
Evidence: `core/insight/philosophical_runtime.py:85-96`, `tests/test_philosophical_runtime.py:628-637`
Reason: The latest cubic wrapper is fully covered by the same current-head cache-removal fix mapped above; no separate unresolved defect remains beyond those inline comments.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1483#pullrequestreview-4139408489 -> 7eec5d903

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
