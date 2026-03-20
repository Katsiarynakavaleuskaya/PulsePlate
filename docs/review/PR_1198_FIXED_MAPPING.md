# PR 1198 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 37cea0a5
Evidence: core/judgment.py:188-224; tests/test_judgment_core.py:155-261
Reason: The canonical judgment builder now fails closed on scalar `source_ids`, rejects impossible supported/contradicted evidence records at the constructor boundary, and the negative tests now use explicit boundary casts instead of inline `# type: ignore`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966948957 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989317 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989393 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2967102359 -> 37cea0a5

Disposition: FIXED
Commit: 37cea0a5
Evidence: docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md:7-18; docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md:54-146; docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md:7-26; docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md:72-184; scripts/orchestration/task_bootstrap.py:59-68; scripts/orchestration/task_bootstrap.py:409-458; tests/test_task_bootstrap.py:73-113; tests/test_philosophy_pipeline.py:489-507
Reason: The governed docs now carry explicit `file:line` anchors for canonical enums, role ownership, rollout semantics, and dev-only boundaries; the bootstrap packet restores `max_provider_calls=0`, recognizes underscore trigger terms, and the cohort-specific philosophy regression test now exercises an actual cohort split.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989346 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989349 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989355 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989388 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989399 -> 37cea0a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2967102367 -> 37cea0a5

Disposition: NOT-A-BUG
Evidence: core/judgment.py:236-244
Reason: The current head already clamps `NaN`, `+inf`, and `-inf` into bounded probabilities, so the missing-`NaN` behavior described in the earlier cubic note is not present anymore on the reviewed branch.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966934382

Disposition: NOT-A-BUG
Evidence: core/judgment.py:216-223; tests/test_judgment_core.py:225-235
Reason: The canonical builder now rejects non-boolean `conflict_flag` inputs and preserves boolean semantics, so this thread does not require an additional follow-up change on the current head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966934387

Disposition: NOT-A-BUG
Evidence: core/judgment.py:236-244
Reason: The judgment contract intentionally sanitizes non-finite uncertainty inputs into bounded values instead of raising; the branch already enforces the bounded output invariant that this review note was concerned about.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989323

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md:7225-7236
Evidence: core/rag/philosophy_pipeline.py:108-117; core/rag/philosophy_pipeline.py:499-531
Reason: Query-bound cohort/cadence anchors are a valid follow-up, but changing the stopword/disambiguation model safely requires a broader regression sweep than this near-ready judgment-contract PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966948949

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md:7211-7222
Evidence: core/rag/philosophy_pipeline.py:454-460; core/rag/philosophy_pipeline.py:522-531
Reason: Expanding numeric context disambiguators for units and measurement systems is a bounded enhancement, but it needs an explicit false-positive review and additional regression coverage before widening the current token set.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989340

Disposition: FIXED
Commit: f4efaa39
Evidence: docs/roadmap/BACKLOG_LEDGER.md:7196-7239; tests/test_philosophy_pipeline.py:489-497
Reason: The new deferred ledger items now expose explicit structured `Priority` fields, and the cohort-specific protein regression test now varies only cohort while keeping the per-meal units identical across both chunks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2967271810 -> f4efaa39

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md:7241-7256
Evidence: scripts/orchestration/task_bootstrap.py:59-70; scripts/orchestration/task_bootstrap.py:122-137; scripts/orchestration/route_with_telemetry.py:1-5; scripts/orchestration/routing_graph_loader.py:1-24
Reason: Replacing the bootstrap-local judgment trigger vocabulary with a canonical routing/config source changes shared orchestration behavior and bootstrap tests, so it is tracked as a dedicated follow-up instead of being rushed into this near-ready PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2967271824

Disposition: NOT-A-BUG
Evidence: docs/review/PR_1197_FIXED_MAPPING.md:45-49
Reason: The referenced PR 1197 artifact now keeps every merge-readiness checkbox unchecked on the current head, so this historical nitpick does not require an additional standalone change beyond the current artifact state.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#discussion_r2966989363

Disposition: NOT-A-BUG
Evidence: core/judgment.py:188-244; scripts/orchestration/task_bootstrap.py:59-70; docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md:7-18; docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md:7-26; docs/roadmap/BACKLOG_LEDGER.md:7196-7256; tests/test_philosophy_pipeline.py:489-507
Reason: These review-summary URLs aggregate inline findings that are explicitly dispositioned above; once the mapped thread URLs are closed, the review-level summaries do not introduce independent unresolved actions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#pullrequestreview-3982838510
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#pullrequestreview-3982859156
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#pullrequestreview-3982874893
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#pullrequestreview-3982920585
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#pullrequestreview-3983058550
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1198#pullrequestreview-3983267538

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
