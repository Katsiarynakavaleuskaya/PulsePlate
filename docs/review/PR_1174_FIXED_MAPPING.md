# PR 1174 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 94c7233880b637e6ddaf01f1052cd315b55ed885
Evidence: `requirements-dev.in:11` bumps `faker` only in the testing lane, `requirements-dev.txt:60` pins `faker==40.11.0`, and `requirements-lock.txt:65` keeps the lock update scoped to the same test dependency without introducing runtime CUDA/Triton packages.
Reason: The PR now keeps the testing-group bump limited to `faker` and removes the unrelated `requirements.txt` CUDA/Triton drift called out by cubic.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1174#discussion_r2936178966 -> 94c7233880b637e6ddaf01f1052cd315b55ed885

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1174_FIXED_MAPPING.md:8`
Reason: The review-level cubic shell only summarizes the same runtime-drift finding already mapped above; it does not add a second independent defect once the inline comment is fixed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1174#pullrequestreview-3949030175

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
