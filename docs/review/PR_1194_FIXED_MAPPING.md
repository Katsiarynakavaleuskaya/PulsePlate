# PR 1194 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ae161d1c
Evidence: `core/rag/vector_rag.py`, `core/rag/orchestration.py`, and `tests/test_vector_rag.py` now share one `user_knowledge` table descriptor, reuse the labeled similarity expression in the Postgres ordering path, realign the orchestration docstring bullet, and assert tenant-scoping SQL fragments in the SQLite corpus-filtering regression test.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#discussion_r2962757968 -> ae161d1c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#pullrequestreview-3978037938 -> ae161d1c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#pullrequestreview-3978046252 -> ae161d1c

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
