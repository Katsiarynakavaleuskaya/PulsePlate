# PR 1340 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 330b460675a973f61683439be58e0662930b92bc
Evidence: `app/services/search_meili.py` (`make_pooled_httpx_transport` shutdown gate raises `httpx.RequestError` with `request=httpx.Request("POST", url)` and URL in message), `tests/test_food_search_foundation.py` (`test_pooled_httpx_transport_propagates_http_status_errors`, strengthened shutdown + dispose assertions), `docs/roadmap/BACKLOG_LEDGER.md` (P2 Meili items reopened until PR #1340 merges per ledger policy)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036860907 -> 330b460675a973f61683439be58e0662930b92bc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036860910 -> 330b460675a973f61683439be58e0662930b92bc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036871645 -> 330b460675a973f61683439be58e0662930b92bc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036881197 -> 330b460675a973f61683439be58e0662930b92bc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036881199 -> 330b460675a973f61683439be58e0662930b92bc

Disposition: FIXED
Commit: c12597b230ca8e558805ad7a8eca2dd317410aab
Evidence: `app/services/search_meili.py:103` (`build_meili_foods_search_headers` strips key; whitespace-only yields no `Authorization` header), `tests/test_food_search_foundation.py` (`test_meili_foods_search_helpers_match_contract_shape`)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#discussion_r3036871644 -> c12597b230ca8e558805ad7a8eca2dd317410aab

Disposition: FIXED
Commit: 07b46ed2
Evidence: `tests/test_food_search_foundation.py` (`test_food_search_meili_client_closed_on_app_shutdown` asserts `app.state.meili_http_client` and `meili_http_shutdown_event` cleared after `TestClient` lifespan shutdown, not only `client.is_closed`)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#pullrequestreview-4059500067 -> 07b46ed2

Disposition: NOT-A-BUG
Evidence: CodeRabbit file-level review summaries; actionable inline threads are mapped with FIXED above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#pullrequestreview-4059482796
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#pullrequestreview-4059489967

Disposition: NOT-A-BUG
Evidence: Sourcery reviewer guide / issue comment is documentation; substantive inline threads are dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#pullrequestreview-4059474919
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1340#issuecomment-4188885486

## Merge Readiness

- [x] All required checks pass (verified: `gh pr checks 1340` exit 0 on current head)
- [x] No unresolved review threads (`scripts/ci/check_pr_merge_readiness.py` PASS)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] CI merge readiness gate pass
- [x] Local `make verify` PASS (`verify-env`, `lint`, `typecheck`, `test-fast`, `diff-cov` vs `origin/main`, 2026-04-05, tree at `e969a957`)
- [x] `pre-commit run --files docs/review/PR_1340_FIXED_MAPPING.md` PASS (same session)
