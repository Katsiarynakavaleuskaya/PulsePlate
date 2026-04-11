# PR #1389 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 5199ad601
Evidence: `core/rag/vector_rag.py` now accepts generic non-string `Sequence` inputs, rejects boolean embedding elements fail-closed, and `core/rag/orchestration.py` collapses non-string formatted/redacted context to the non-RAG fail-safe path. Coverage in `tests/test_vector_rag.py` and `tests/test_rag_orchestration.py` was expanded in the same commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#discussion_r3067158270 -> 5199ad601
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#discussion_r3067162837 -> 5199ad601
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#pullrequestreview-4092907452 -> 5199ad601
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#pullrequestreview-4092912806 -> 5199ad601
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#pullrequestreview-4092917113 -> 5199ad601

Disposition: FIXED
Commit: 74f0c0ede
Evidence: `tests/test_vector_rag.py` drops the synthetic non-finite-similarity test that only reached the guard by monkeypatching `vector_rag._cosine_similarity`; the remaining stored-embedding finiteness coverage preserves the fail-closed contract without violating the repo guard against monkeypatching core compute helpers.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#discussion_r3067287563 -> 74f0c0ede
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#discussion_r3067403589 -> 74f0c0ede
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#pullrequestreview-4093037095 -> 74f0c0ede
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#pullrequestreview-4093178566 -> 74f0c0ede

Disposition: FIXED
Commit: 65a4a4c4b
Evidence: `core/rag/simple_rag.py` now keeps scanning ranked candidates until it fills the requested limit with non-empty redacted chunks, so lower-ranked safe chunks backfill when earlier results redact to empty; `tests/test_rag_orchestration.py` covers the backfill path at `max_chunks=1`, and `tests/test_vector_rag.py` adds direct `_normalize_similarity()` assertions for `nan`/`inf`/`-inf`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#discussion_r3067155700 -> 65a4a4c4b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1389#pullrequestreview-4093250775 -> 65a4a4c4b

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green on latest pushed head
- [x] `make verify` green on latest pushed head
