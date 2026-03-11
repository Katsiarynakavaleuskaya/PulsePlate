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

Disposition: FIXED
Commit: see mapping entries below
Evidence: `ee5aa57a` stores actual recursive-path execution in `core/rag/orchestration.py:49` and propagates it through `core/insight/philosophical_runtime.py:414` and `core/insight/philosophical_runtime.py:649`, while also tightening the NOT-A-BUG evidence wording in `docs/review/PR_1114_FIXED_MAPPING.md:20` so the later CodeRabbit follow-up is closed on the latest head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918352786 -> ee5aa57a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918352789 -> ee5aa57a

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1114_FIXED_MAPPING.md:28` and `docs/review/PR_1114_FIXED_MAPPING.md:29` already map the second CodeRabbit wave's actionable inline comments to `ee5aa57a`, so the aggregate review-status URL below is a mirror of those same items rather than a separate unresolved change request.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#pullrequestreview-3929582286

Disposition: FIXED
Commit: see mapping entries below
Evidence: `eb7c861e` corrects the stale line anchors in `docs/review/PR_1114_FIXED_MAPPING.md:32` so the second CodeRabbit-wave mirror evidence now points at the actual mapped entries.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918541088 -> eb7c861e

Disposition: FIXED
Commit: see mapping entries below
Evidence: `e186feca` preserves recursive-path fail-safe metadata in `core/rag/orchestration.py:60` and `core/rag/orchestration.py:186`, surfaces `rag_recursive_path` for executed recursive retrieval even when no usable chunks survive in `core/insight/philosophical_runtime.py:651`, and adds regressions in `tests/test_rag_orchestration.py:74`, `tests/test_rag_orchestration.py:573`, and `tests/test_philosophical_runtime.py:653`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918541100 -> e186feca
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#discussion_r2918541108 -> e186feca

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1114_FIXED_MAPPING.md:40`, `docs/review/PR_1114_FIXED_MAPPING.md:46`, and `docs/review/PR_1114_FIXED_MAPPING.md:47` already capture the actionable cubic items from the latest wave, so the aggregate cubic review URL below is a mirror summary rather than a separate unresolved change request.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1114#pullrequestreview-3929794699
