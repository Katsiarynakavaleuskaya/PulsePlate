# PR 1306 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No current-head review threads or actionable bot review comments were present when checked for PR `#1306` via `gh api repos/Katsiarynakavaleuskaya/PulsePlate/pulls/1306/reviews` and `gh api repos/Katsiarynakavaleuskaya/PulsePlate/pulls/1306/comments`.
- Current hotfix fix commits on this PR:
- `43896b08` — disable the canonical app-fixture limiter surfaces
- `3ef95534` — extend limiter shutdown across shared test-client helper seams
- `f53e5587` — reset leaked singleton limiter state before each test and strengthen poisoned-state guards

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- [ ] Mandatory post-open bug-hunter pass completed
Notes: PR `#1306` must remain a narrow test-harness hotfix for intermittent legacy insight/RAG `429` CI failures caused by shared limiter state leakage. It must not widen into runtime rate-limit policy changes or unrelated test refactors.
