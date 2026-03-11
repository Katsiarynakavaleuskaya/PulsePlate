# PR 1110 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917955375 -> eac2ebf6
  Disposition: FIXED
  Evidence: app/routers/vip.py:645
  Reason: Legacy VIP alias now always enforces `require_vip_tier()`, removing the env-backed bypass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929151574 -> eac2ebf6
  Disposition: FIXED
  Evidence: app/routers/vip.py:645
  Reason: Review summary covered the same VIP alias bypass and is fixed by the unconditional VIP-tier check.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917968517 -> eac2ebf6
  Disposition: FIXED
  Evidence: app/routers/vip.py:645
  Reason: cubic identified the same legacy VIP alias bypass; the guard now runs regardless of DB mode.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917968531 -> eac2ebf6
  Disposition: FIXED
  Evidence: tests/test_subscription_activation_api.py:86
  Reason: Authz expiry inputs now use `_relative_iso(...)` instead of hard-coded future timestamps.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929165943 -> eac2ebf6
  Disposition: FIXED
  Evidence: app/routers/vip.py:645; tests/test_subscription_activation_api.py:86
  Reason: cubic review summary covered both the VIP alias bypass and hard-coded authz expiry dates; both were fixed in this commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#discussion_r2917973544 -> eac2ebf6
  Disposition: FIXED
  Evidence: docs/review/PR_1110_FIXED_MAPPING.md:37
  Reason: Merge-readiness checklist items were changed back to unchecked state pending final merge cycle.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1110#pullrequestreview-3929171608 -> eac2ebf6
  Disposition: FIXED
  Evidence: docs/review/PR_1110_FIXED_MAPPING.md:37
  Reason: Review summary covered the same merge-readiness checkbox issue and is fixed in the artifact.

## Merge Readiness
- [ ] python3 scripts/orchestration/check_preflight.py
- [ ] python3 scripts/orchestration/check_agent_consistency.py
- [ ] python3 scripts/orchestration/route_with_telemetry.py --domain backend --task-type "authz backend entitlements"
- [ ] pre-commit run --all-files
- [ ] make verify
- [ ] diff-cover >= 97% in PR CI
- [ ] required checks PASS
