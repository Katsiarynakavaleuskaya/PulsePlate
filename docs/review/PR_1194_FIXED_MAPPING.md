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

Disposition: FIXED
Commit: 39599e4e
Evidence: `core/rag/vector_rag.py` now keeps an explicit `CAST(... AS VECTOR(...))` around the bound Postgres query vector while preserving parameterized SQLAlchemy composition, and `tests/test_vector_rag.py` asserts the generated SQL still includes the vector cast.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#discussion_r2962778227 -> 39599e4e

Disposition: NOT-A-BUG
Evidence: `core/rag/vector_rag.py` already returned a precise `TableClause` type from `_user_knowledge_table()`, and `tests/test_vector_rag.py` already removed the unused `filtered_out_row` fixture data before CodeRabbit published this now-outdated nitpick. The review comment targeted an earlier snapshot, so the current implementation already satisfied the requested change at review time.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#discussion_r2962873236
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#pullrequestreview-3978099169

Disposition: FIXED
Commit: ac043839
Evidence: `core/rag/vector_rag.py` now escapes `LIKE` wildcards in `corpus_prefixes` for both Postgres and SQLite retrieval, adds `escape='\\'` to the generated predicates, and `tests/test_vector_rag.py` asserts the escaped bind values plus `ESCAPE '\\'` SQL fragments for `_` and `%` prefixes. This commit is the final code fix that closes the two actionable findings summarized in review `pullrequestreview-3978158166`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#discussion_r2962873243 -> ac043839
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#pullrequestreview-3978158166 -> ac043839

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
