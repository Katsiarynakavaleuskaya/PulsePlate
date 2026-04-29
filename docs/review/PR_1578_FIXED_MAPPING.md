# PR #1578 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1578#discussion_r3163789209 -> eb74dce21
Disposition: FIXED
Commit: eb74dce21
Evidence: `core/ai/insight_runtime.py` now defaults null-valued speech-act and language-game route hints before string coercion; `tests/test_core_ai_insight_runtime.py` covers null fallback.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1578#discussion_r3163789216 -> eb74dce21
Disposition: FIXED
Commit: eb74dce21
Evidence: `core/rag/recursive_retrieval.py` now passes `current_query` into recursive short-circuit evaluation; `tests/test_core_ai_insight_runtime.py` covers later-hop refined query usage.

## Merge Readiness

- [ ] PR is non-draft only when truly ready for merge
- [ ] All required checks are green on latest commit with no pending rerun required
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Wait-window completed after latest bot/review activity

## Deferred / Follow-ups

- None for this PR. Out-of-scope optimization lanes remain governed by the PR-A8 packet and backlog.
