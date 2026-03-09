# PR 1054 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#issuecomment-4024056533
Disposition: NOT-A-BUG
Evidence: GitHub required check `diff-coverage` passed on current head; local `make verify` reported `Coverage: 100%` for changed lines in `settings.py`, `legacy_app.py`, and `app/middleware/api_tiers.py`.
Reason: Codecov patch comment is informational-only and disagrees with the canonical merge gate for this repo (`make diff-cov` / `diff-coverage` check), which already passed on the current head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2905754667
Disposition: FIXED
Commit: 656e0239
Evidence: `settings.py:20` now prefers `ENVIRONMENT` over `APP_ENV`; `settings.py:42` keeps production-like detection fail-closed on the canonical runtime label; `tests/test_api_tiers.py:174` proves `ENVIRONMENT=production` overrides `APP_ENV=local`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2905754667 -> 656e0239

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2905783682
Disposition: FIXED
Commit: 656e0239
Evidence: `docs/deploy/VIP_API_KEYS.md:124` rewrites the migration path to require a real `API_KEY`; `docs/deploy/VIP_API_KEYS.md:186` rewrites troubleshooting to treat anonymous/dev toggles in production as a misconfiguration instead of a workaround.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2905783682 -> 656e0239

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2905783689
Disposition: FIXED
Commit: 656e0239
Evidence: `app/bootstrap/startup_guards.py:14` centralizes startup hard guards; `legacy_app.py:516` delegates to the bootstrap seam; `tests/test_app_lifespan_additional.py:90` and `tests/test_app_lifespan_additional.py:112` verify fail-closed startup behavior through the shared bootstrap seam.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2905783689 -> 656e0239

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3915807041
Disposition: FIXED
Commit: 656e0239
Evidence: `app/middleware/api_tiers.py:207` restricts developer fallbacks to `is_explicit_developer_env()`; `legacy_app.py:792` limits lenient API-key mode to explicit dev/test-like environments; `tests/test_vip_anonymous_api_key_safety.py:380` and `tests/test_vip_coverage_additional.py:130` cover preview/unknown-env fail-closed behavior; `tests/test_vip_anonymous_api_key_safety.py:17` and `tests/test_vip_coverage_additional.py:18` now use autouse `monkeypatch` fixtures instead of direct `os.environ` mutation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3915807041 -> 656e0239

## Merge Readiness
- [x] Scope tied to PR objective
- [x] Docs/runtime changes applied
- [x] Verification completed
- [ ] Required GitHub checks PASS with no pending required jobs
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] No unresolved review threads or actionable bot comments remain
- [ ] Review wait-window completed
