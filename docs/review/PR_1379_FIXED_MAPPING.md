# PR #1379 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056866537 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056866544 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888554 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888560 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888564 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888572 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888581 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888585 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888592 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056893790 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056893792 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056910860 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056910868 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056910886 -> e85ca81d59cb2336913e83f48513f9627c03652b
Disposition: FIXED
Commit: see mapping entries below
Evidence: `llm.py` (insight-only fallback chain, timeout floor, isolated fallback builders, provider type hint); `core/insight/llm_provider_loader.py` (insight path uses `get_insight_provider()`); `app/services/insight_runtime.py` (fallback winner propagated into tracing/provider identity); `legacy_app.py` (`/ready` fail-soft runtime enrichment); `tests/test_llm_extras.py`, `tests/test_app_insight_runtime.py`, `tests/test_api.py`, `tests/test_health_db.py`, `tests/test_insight_error_hygiene.py`, `tests/test_insight_rag_response_fields.py`, `tests/test_philosophy_validation_integration.py`, `tests/test_rag_vector_feature_flag_guard.py`; local gates green via `pre-commit run --all-files` and `make verify` on commit `e85ca81d59cb2336913e83f48513f9627c03652b`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888533 -> 62738b566
Disposition: FIXED
Commit: 62738b566
Evidence: `docs/review/PR_1379_FIXED_MAPPING.md` merge-readiness and discussion-pass checkboxes were reset to in-progress state in commit `62738b566`, so the artifact no longer claims readiness before current-head CI and GitHub thread resolution complete.

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head
