# PR 1114 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `c97d0a16` moves runtime reason-code assembly outside the Phase 1/2 gate in `core/insight/philosophical_runtime.py:474`, scopes the strict rewrite threshold to actual RAG-backed paths in `core/insight/philosophical_runtime.py:595`, mirrors the verification-first fallback gate for falsifiability in `core/insight/philosophical_runtime.py:624`, adds non-RAG and phase12-disabled regressions in `tests/test_philosophical_runtime.py:519` and `tests/test_philosophical_runtime.py:616`, and adds an explicit JSON content-type assertion in `tests/test_insight_rag_response_fields.py:356`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918257469 -> c97d0a16
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918257475 -> c97d0a16
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918260780 -> c97d0a16
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918260792 -> c97d0a16
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918260807 -> c97d0a16
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#pullrequestreview-3929480272 -> c97d0a16

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1114_FIXED_MAPPING.md:4` and `docs/review/PR_1114_FIXED_MAPPING.md:5` already had the required artifact-level discussion-pass boxes checked on head `35e9b983`, so the later checkbox suggestion was stale rather than still actionable.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918260796
