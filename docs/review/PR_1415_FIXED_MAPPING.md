# PR 1415 — Fixed in Commit Mapping

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

## Fixed in Commit Mapping
- Pending post-open review comments.

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
Notes: This A2 runtime PR hardens degraded retrieval and non-RAG collapse paths while preserving the existing public RAG response contract. Semantic cache, provider/quota seams, and broader reliability-control-plane work remain out of scope.
