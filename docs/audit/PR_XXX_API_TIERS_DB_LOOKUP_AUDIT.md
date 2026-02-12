# PR XXX — API Tiers DB Lookup Audit

## Scope

- Changed file: `app/middleware/api_tiers.py`
- Changed tests: `tests/test_api_tiers.py`
- Focus: tier resolution only (FREE/PRO/VIP)
- No service-layer refactor
- No cache

## Non-goals

- No TTL cache
- No migrations
- No OpenAPI contract changes

## Failure Modes and Expected Behavior

| Scenario | Expected behavior |
| --- | --- |
| DB enabled + valid key in DB | Use DB tier |
| DB enabled + key unknown in both DB and env | 403 (guard rejects after env fallback) |
| DB enabled + DB error/unavailable | Fallback to env-based tier detection |
| DB disabled | Env-only tier detection |
| Neither DB nor env resolves | 403 (guard rejects) |

## Implementation Notes

- Added DB-first resolver in `app/middleware/api_tiers.py` gated by `SUBSCRIPTION_DB_ENABLED`.
- DB lookup returns `None` on not found/errors, then code falls back to env-based resolution.
- No fail-open path introduced: unresolved keys remain forbidden by existing guard flow.
- Legacy behavior for `API_KEY`-based VIP bypass was intentionally not added to env fallback to preserve PRO guard divergence tests.

## Test Coverage Added/Updated

- `tests/test_api_tiers.py` now covers:
  - DB enabled path with DB tier results
  - DB error/miss fallback to env path
  - DB disabled env-only path
  - Unknown key rejection behavior

## DoD (Ledger 1:1)

- [x] Database lookup implemented when `SUBSCRIPTION_DB_ENABLED=true`
- [x] Fallback to env-based detection when DB unavailable
- [x] Tests cover both paths
