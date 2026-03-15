# PR 1176 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 50653a32d41b90ee1b563903e1da47c94c8c419c
Evidence: `requirements.txt:215` now bumps only `sentence-transformers==5.3.0`, while `requirements-lock.txt:466` mirrors the same version bump and preserves the shared CPU-neutral lock baseline without CUDA/Triton additions.
Reason: The PR now keeps the dependency update scoped to the intended `sentence-transformers` bump and removes the unconditional GPU package drift identified by cubic.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1176#discussion_r2936181724 -> 50653a32d41b90ee1b563903e1da47c94c8c419c

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1176_FIXED_MAPPING.md:8`
Reason: The review-level cubic shell only summarizes the same CUDA drift finding already dispositioned above; it does not add a second independent issue after the inline fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1176#pullrequestreview-3949650217

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
