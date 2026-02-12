# PR XXX — API Tiers DB Lookup Audit

## Scope

- Changed file: `app/middleware/api_tiers.py`
- Changed tests: `tests/test_api_tiers.py`
- Focus: tier resolution only (FREE/PRO/VIP)
- No service-layer refactor
- No cache

## Repo-truth Evidence (file:line)

- DB lookup outcome contract: `app/middleware/api_tiers.py:55`, `app/middleware/api_tiers.py:65`
- DB lookup implementation: `app/middleware/api_tiers.py:109`
- Tier guard validation flow: `app/middleware/api_tiers.py:171`
- Subscription tier inference flow: `app/middleware/api_tiers.py:298`
- DB error deny test: `tests/test_api_tiers.py:110`
- DB exception helper test: `tests/test_api_tiers.py:160`
- Invalid DB tier test: `tests/test_api_tiers.py:187`
- get_subscription_tier fail-closed test: `tests/test_api_tiers.py:355`

## Non-goals

- No TTL cache
- No migrations
- No OpenAPI contract changes

## Failure Modes and Expected Behavior

| Scenario | Expected behavior |
| --- | --- |
| DB enabled + valid key in DB | Use DB tier |
| DB enabled + key missing in DB | Env fallback allowed (migration path) |
| DB enabled + DB error/unavailable | Fail-closed for access checks; no env fallback |
| DB enabled + invalid/unparseable DB tier | Fail-closed for access checks; no env fallback |
| DB disabled | Env-only tier detection |
| Neither DB nor env resolves | 403 (guard rejects) |

## Implementation Notes

- Added DB-first resolver in `app/middleware/api_tiers.py` gated by `SUBSCRIPTION_DB_ENABLED`.
- DB lookup now returns explicit statuses (`HIT`, `MISS`, `ERROR`, `INVALID_TIER`) to avoid ambiguous `None` semantics.
- Policy: env fallback is allowed only for `MISS`; `ERROR` and `INVALID_TIER` are fail-closed in guards.
- Legacy behavior for `API_KEY`-based VIP bypass was intentionally not added to env fallback to preserve PRO guard divergence tests.

## Test Coverage Added/Updated

- `tests/test_api_tiers.py` now covers:
  - DB enabled path with DB tier results
  - DB error and invalid-tier fail-closed behavior
  - DB miss-only fallback to env path
  - DB disabled env-only path
  - Unknown key rejection behavior

## DoD (Ledger 1:1)

- [x] Database lookup implemented when `SUBSCRIPTION_DB_ENABLED=true`
- [x] Fallback to env-based detection when DB unavailable
- [x] Tests cover both paths
