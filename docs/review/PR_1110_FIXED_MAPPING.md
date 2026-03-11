# PR 1110 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917955375 -> eac2ebf6
Disposition: FIXED
Commit: eac2ebf6
Evidence: app/routers/vip.py:645
Reason: Legacy VIP alias now always enforces `require_vip_tier()`, removing the env-backed bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929151574 -> eac2ebf6
Disposition: FIXED
Commit: eac2ebf6
Evidence: app/routers/vip.py:645
Reason: Review summary covered the same VIP alias bypass and is fixed by the unconditional VIP-tier check.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917968517 -> eac2ebf6
Disposition: FIXED
Commit: eac2ebf6
Evidence: app/routers/vip.py:645
Reason: cubic identified the same legacy VIP alias bypass; the guard now runs regardless of DB mode.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917968531 -> eac2ebf6
Disposition: FIXED
Commit: eac2ebf6
Evidence: tests/test_subscription_activation_api.py:86
Reason: Authz expiry inputs now use `_relative_iso(...)` instead of hard-coded future timestamps.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929165943 -> eac2ebf6
Disposition: FIXED
Commit: eac2ebf6
Evidence: app/routers/vip.py:645; tests/test_subscription_activation_api.py:86
Reason: cubic review summary covered both the VIP alias bypass and hard-coded authz expiry dates; both were fixed in this commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917973544 -> eac2ebf6
Disposition: FIXED
Commit: eac2ebf6
Evidence: docs/review/PR_1110_FIXED_MAPPING.md:37
Reason: Merge-readiness checklist items were changed back to unchecked state pending final merge cycle.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929171608 -> eac2ebf6
Disposition: FIXED
Commit: eac2ebf6
Evidence: docs/review/PR_1110_FIXED_MAPPING.md:37
Reason: Review summary covered the same merge-readiness checkbox issue and is fixed in the artifact.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929270340 -> 439d41b8
Disposition: FIXED
Commit: 439d41b8
Evidence: app/routers/vip.py:642
Reason: Legacy VIP alias now applies `require_vip_tier()` to explicit keys and dev/test fallback keys, removing the anonymous bypass outside the original diff.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2918122334 -> 439d41b8
Disposition: FIXED
Commit: 439d41b8
Evidence: tests/test_vip_anonymous_api_key_safety.py:311
Reason: The anonymous-safety fixture no longer enables `VIP_API_KEYS` globally; the VIP env path is now opted into only by the test that exercises it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2918122340 -> 439d41b8
Disposition: FIXED
Commit: 439d41b8
Evidence: tests/test_vip_production_simple.py:68
Reason: Production VIP tests now set `VIP_API_KEYS` only in the cases that intentionally cover that auth path, keeping the source under test explicit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929330945 -> 439d41b8
Disposition: FIXED
Commit: 439d41b8
Evidence: tests/test_vip_anonymous_api_key_safety.py:311; tests/test_vip_production_simple.py:68
Reason: Review summary covered the same two test-fixture ambiguity fixes and is resolved by the scoped `VIP_API_KEYS` setup.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2918222586 -> 9a46c760
Disposition: FIXED
Commit: 9a46c760
Evidence: app/middleware/api_tiers.py:194
Reason: `subscriptions` is now imported inside `_lookup_tier_from_db()` so module import of `api_tiers.py` no longer pulls subscription models into OpenAPI-time import paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2918222595 -> 9a46c760
Disposition: FIXED
Commit: 9a46c760
Evidence: app/middleware/api_tiers.py:233; tests/test_api_tiers.py:317
Reason: Invalid non-datetime `expires_at` values now fail closed through `INVALID_TIER`, with a targeted regression test covering the malformed persisted state.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929437556 -> 9a46c760
Disposition: FIXED
Commit: 9a46c760
Evidence: app/middleware/api_tiers.py:194; app/middleware/api_tiers.py:233; tests/test_api_tiers.py:317
Reason: Review summary covered both api_tiers fixes: localizing the subscriptions import and denying malformed persisted expiry values.

## Merge Readiness
- [ ] python3 scripts/orchestration/check_preflight.py
- [ ] python3 scripts/orchestration/check_agent_consistency.py
- [ ] python3 scripts/orchestration/route_with_telemetry.py --domain backend --task-type "authz backend entitlements"
- [ ] pre-commit run --all-files
- [ ] make verify
- [ ] diff-cover >= 97% in PR CI
- [ ] required checks PASS
