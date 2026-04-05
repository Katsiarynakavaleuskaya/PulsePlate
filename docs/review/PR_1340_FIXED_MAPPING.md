# PR 1340 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: c12597b230ca8e558805ad7a8eca2dd317410aab
Evidence: `app/services/search_meili.py:103` (`build_meili_foods_search_headers` strips key; whitespace-only yields no `Authorization` header), `tests/test_food_search_foundation.py` (`test_meili_foods_search_helpers_match_contract_shape`)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036871644 -> c12597b230ca8e558805ad7a8eca2dd317410aab

Disposition: NOT-A-BUG
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` uses `Target PR` to track the landing PR and `Status` for implementation notes on the branch; this matches repo backlog practice and does not claim merge before CI green.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036871645

Disposition: NOT-A-BUG
Evidence: `app/services/search_meili.py` — shutdown-gate `httpx.RequestError` is raised only to stop pooled `post()` before close; minimal shape is intentional (fallback path does not inspect `request`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036860907

Disposition: NOT-A-BUG
Evidence: Non-2xx and HTTP error paths for `MeiliSearchBackend` remain exercised via existing transport/fallback tests in this module’s suite; dedicated `MockTransport` matrix is out of scope for this lifecycle PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036860910

Disposition: NOT-A-BUG
Evidence: Sourcery reviewer guide / issue comment is documentation; substantive inline threads are dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#pullrequestreview-4059474919
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#issuecomment-4188885486

Disposition: NOT-A-BUG
Evidence: CodeRabbit file-level review summary; actionable inline threads are mapped with FIXED/NOT-A-BUG above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#pullrequestreview-4059482796

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
