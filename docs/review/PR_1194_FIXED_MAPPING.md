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

Disposition: FIXED
Commit: 424f2601
Evidence: `core/rag/vector_rag.py` now returns a precise `TableClause` type from `_user_knowledge_table()` via a `TYPE_CHECKING` import, and `tests/test_vector_rag.py` removes the unused `filtered_out_row` fixture data plus the redundant assertion that did not verify filtering behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#discussion_r2962873236 -> 424f2601
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#pullrequestreview-3978099169 -> 424f2601
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#pullrequestreview-3978158166 -> 424f2601

Disposition: FIXED
Commit: ac043839
Evidence: `core/rag/vector_rag.py` now escapes `LIKE` wildcards in `corpus_prefixes` for both Postgres and SQLite retrieval, adds `escape='\\'` to the generated predicates, and `tests/test_vector_rag.py` asserts the escaped bind values plus `ESCAPE '\\'` SQL fragments for `_` and `%` prefixes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#discussion_r2962873243 -> ac043839
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1194#pullrequestreview-3978158166 -> ac043839

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
