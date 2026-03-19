# PR 1192 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 1fcbf395
Evidence: `.env.example:28` now ships `SUBSCRIPTION_DB_ENABLED=false` with production guidance, `docker-compose.yaml:18` sets `SUBSCRIPTION_DB_ENABLED` for the production service, and `docker-compose.yaml:65` sets the dev default explicitly so the new startup guard no longer breaks repo-shipped deployment inputs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1192#discussion_r2961928851 -> 1fcbf395

Disposition: FIXED
Commit: 1fcbf395
Evidence: `app/routers/billing.py:238`-`app/routers/billing.py:286` now accept issued PRO/VIP transport keys for pre-entitlement RU/BY manual rails without consulting persisted entitlement state, and `tests/test_payment_source_contract_api.py:38` proves a production-like DB mode request with `PRO_API_KEYS` still reaches `/api/v1/pro/payments/ru-by/manual-intent` while protected `/api/v1/pro/session` remains blocked at `tests/test_payment_source_contract_api.py:61`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1192#discussion_r2961928857 -> 1fcbf395

Disposition: FIXED
Commit: 1fcbf395
Evidence: `AGENTS.md:833` and `AGENTS.md:985` now describe the current fail-closed runtime contract for `MISS`, `ERROR`, and `INVALID_TIER` under `SUBSCRIPTION_DB_ENABLED=true`, removing the stale migration-fallback wording that contradicted `app/middleware/api_tiers.py:308`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1192#discussion_r2961953817 -> 1fcbf395

Disposition: FIXED
Commit: 1fcbf395
Evidence: `tests/test_payment_source_contract_api.py:13` replaces direct private-helper invocation with a behavioral `TestClient` request that asserts the 401 integration path, and `tests/test_payment_source_contract_api.py:32` replaces the dead-env setup case with a route-level production-like scenario that actually exercises manual-route auth wiring.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1192#discussion_r2961953827 -> 1fcbf395

Disposition: FIXED
Commit: 1fcbf395
Evidence: The review-level CodeRabbit summary is fully covered by the concrete fixes above: deploy templates now ship `SUBSCRIPTION_DB_ENABLED`, the policy text matches the fail-closed DB lookup contract, and `tests/test_payment_source_contract_api.py` now uses behavioral route coverage instead of private helper calls.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1192#pullrequestreview-3977153010 -> 1fcbf395

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] Pre-commit green
