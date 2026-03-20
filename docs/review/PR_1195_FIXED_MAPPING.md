# PR 1195 — Fixed in Commit Mapping

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 6d0b35cd
Evidence: `core/rag/philosophy_pipeline.py` now preserves Unicode and mixed health tokens such as `A1C` and `LDL-C` in query anchors, reuses per-chunk anchors instead of recomputing them per numeric range, and `tests/test_philosophy_pipeline.py` adds a regression that asserts alphanumeric medical token extraction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#issuecomment-4097730775 -> 6d0b35cd

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
