# PR 1203 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 1377cd91
Evidence: core/ai/insight_runtime.py:49-78; core/ai/insight_runtime.py:115-185; app/services/insight_application_service.py:35-64; legacy_app.py:2251-2275; tests/test_core_ai_insight_runtime.py:76-263; tests/test_insight_application_service.py:17-137
Reason: The bounded-context seam now uses explicit `LLMProvider` typing, preserves the legacy direct-provider patchpoint via an injectable direct factory, normalizes provider loader failures into canonical bounded-context errors, rejects invalid transparency tuples fail-closed, and adds deterministic regression tests for direct-notice and missing-provider branches.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968166358
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968182664
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198519
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198522
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198527
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198529
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198533
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198535

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968166358 -> 1377cd91
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968182664 -> 1377cd91
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198519 -> 1377cd91
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198522 -> 1377cd91
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198527 -> 1377cd91
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198529 -> 1377cd91
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198533 -> 1377cd91
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2968198535 -> 1377cd91

Disposition: NOT-A-BUG
Evidence: core/ai/insight_runtime.py:49-78; core/ai/insight_runtime.py:115-185; app/services/insight_application_service.py:35-64; legacy_app.py:2251-2275; docs/roadmap/BACKLOG_LEDGER.md:1208-1215; docs/architecture/system_overview.md:98-103
Reason: The review-summary URLs aggregate the inline bot findings dispositioned above and do not add independent unresolved actions once those mapped threads are closed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#pullrequestreview-3984297653
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#pullrequestreview-3984313392
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#pullrequestreview-3984329399

Disposition: FIXED
Commit: dfbeae5d
Evidence: app/services/insight_application_service.py:31-39; app/services/insight_application_service.py:57-64; tests/test_insight_application_service.py:145-192
Reason: The shared insight service now rejects oversized prompt input with HTTP 413 before runtime preparation, preserving the legacy fail-closed contract and keeping truncation only on response text.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2969109594

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#discussion_r2969109594 -> dfbeae5d

Disposition: NOT-A-BUG
Evidence: app/services/insight_application_service.py:31-39; app/services/insight_application_service.py:57-64; tests/test_insight_application_service.py:145-192
Reason: The review-shell URL only summarizes the inline CodeRabbit finding above and does not introduce an additional unresolved action once the mapped thread is dispositioned.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#pullrequestreview-3985580981

Disposition: NOT-A-BUG
Evidence: app/services/insight_application_service.py:57-64; app/security/agent_input_guard.py:267-276; legacy_app.py:2269-2277
Reason: The shared insight service treats `input_guard` as a fail-closed validation seam, not a sanitizer. The production guard `require_safe_ai_agent_input()` returns the original text unchanged or raises a stable 400, so consuming a return value would not change runtime behavior and is not required to preserve the current legacy length contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1203#pullrequestreview-3985624764

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
