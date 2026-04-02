# PR 1306 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- [ ] Mandatory post-open bug-hunter pass completed
Notes: PR `#1306` must remain a narrow test-harness hotfix for intermittent legacy insight/RAG `429` CI failures caused by shared limiter state leakage. It must not widen into runtime rate-limit policy changes or unrelated test refactors.
