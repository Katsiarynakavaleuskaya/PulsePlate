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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906058549
Disposition: FIXED
Commit: d7482420
Evidence: cubic found that `pytest.importorskip()` could silently skip the startup-guard seam. `tests/test_app_lifespan_additional.py:6` now imports `app.bootstrap.startup_guards` directly, and `tests/test_app_lifespan_additional.py:100` / `tests/test_app_lifespan_additional.py:121` inject the seam without skip-based masking.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906058549 -> d7482420

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3916112663
Disposition: FIXED
Commit: d7482420
Evidence: cubic identified the same missing fail-fast import seam in `tests/test_app_lifespan_additional.py`. The test file now uses a direct module import at `tests/test_app_lifespan_additional.py:6` and reuses `startup_guards.run_startup_guards` at `tests/test_app_lifespan_additional.py:100` / `tests/test_app_lifespan_additional.py:121`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3916112663 -> d7482420

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906102580
Disposition: FIXED
Commit: d7482420
Evidence: `tests/test_app_lifespan_additional.py:6` now imports `startup_guards` directly, and the two security regression tests wire `run_startup_guards` via `lifespan_globals` without `pytest.importorskip()`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906102580 -> d7482420

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906102591
Disposition: FIXED
Commit: d7482420
Evidence: `tests/test_vip_anonymous_api_key_safety.py:18` now pins `ALLOW_DEV_API_KEY=false` after clearing the rest of the auth env, so production-like tests no longer inherit implicit dev-key behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906102591 -> d7482420

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906102575
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-legacy-runtime-env-canonicalization`
Evidence: The remaining concern is legacy module-level env gating outside the narrow runtime hardening diff for `PR-TBD-API-KEY-TOGGLE-GUARD`. It is tracked as a dedicated follow-up item so the current PR can stay focused on fail-fast toggle enforcement without mixing a wider `legacy_app.py` env-surface refactor.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3916162189
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-legacy-runtime-env-canonicalization`
Evidence: The review summary includes three findings fixed in `d7482420` (`app/middleware/api_tiers.py`, `app/routers/vip.py`, `docs/deploy/VIP_API_KEYS.md`, and the targeted tests) plus one valid `legacy_app.py` env-surface follow-up, which is explicitly tracked in the new backlog item to avoid widening this near-ready security PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496197
Disposition: FIXED
Commit: 0f1b4f47
Evidence: `docs/deploy/VIP_API_KEYS.md:20` no longer claims `DEBUG=false` alone makes an explicit developer runtime production-like; `docs/deploy/VIP_API_KEYS.md:27` and `docs/deploy/VIP_API_KEYS.md:45` now document `ALLOW_ANONYMOUS_API_KEYS` defaulting to `false`, and the matrix/troubleshooting sections were aligned with the runtime helpers.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496197 -> 0f1b4f47

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496203
Disposition: FIXED
Commit: 0f1b4f47
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:343` now marks `ledger-p1-legacy-runtime-env-canonicalization` as the residual follow-up from PR `#1054` and links both the parent ledger item and the PR URL, making the carryover explicit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496203 -> 0f1b4f47

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496207
Disposition: FIXED
Commit: 0f1b4f47
Evidence: `tests/edges/test_vip_auth_edges.py:7` now uses an autouse `monkeypatch` fixture to reset auth env, and the edge tests use `monkeypatch.setenv()` / `delenv()` instead of process-global `os.environ` writes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496207 -> 0f1b4f47

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496213
Disposition: FIXED
Commit: 0f1b4f47
Evidence: `tests/test_vip_anonymous_api_key_safety.py:134`, `tests/test_vip_anonymous_api_key_safety.py:157`, `tests/test_vip_anonymous_api_key_safety.py:180`, and `tests/test_vip_anonymous_api_key_safety.py:294` explicitly enable `ALLOW_DEV_API_KEY=true` for dev/local/test anonymous flows and now assert `200` instead of `!= 401`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496213 -> 0f1b4f47

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#discussion_r2906496216
Disposition: NOT-A-BUG
Evidence: `app/routers/vip.py:759` shows the deprecated `/api/v1/vip/weekly-plan` alias calls the module-level `make_weekly_menu` symbol directly, not `_safe_call_with_adapter()`. `tests/test_vip_production_simple.py:78` therefore correctly monkeypatches `app.routers.vip.make_weekly_menu` to exercise the alias error path and assert the `"Weekly plan generation failed"` response.
Reason: The review comment describes the `/menu/weekly/plan` adapter path, but this test targets the deprecated `/weekly-plan` alias, which uses a different callable path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3916595868
Disposition: FIXED
Commit: 0f1b4f47
Evidence: The latest CodeRabbit review summary is now dispositioned as four concrete fixes in `0f1b4f47` (`app/middleware/api_tiers.py`, `docs/deploy/VIP_API_KEYS.md`, `docs/roadmap/BACKLOG_LEDGER.md`, `tests/edges/test_vip_auth_edges.py`, and `tests/test_vip_anonymous_api_key_safety.py`) plus one `NOT-A-BUG` clarification for the deprecated `/weekly-plan` alias path in `tests/test_vip_production_simple.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3916595868 -> 0f1b4f47

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3917624345
Disposition: FIXED
Commit: ef54e8ad
Evidence: `docs/deploy/VIP_API_KEYS.md:212` and `docs/deploy/VIP_API_KEYS.md:216` now print both `ENVIRONMENT` and `ALLOW_DEV_API_KEY`; the remaining duplicate adapter-path comment is already classified as `NOT-A-BUG` under `discussion_r2906496216` because the deprecated `/api/v1/vip/weekly-plan` alias calls `app.routers.vip.make_weekly_menu` directly.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054#pullrequestreview-3917624345 -> ef54e8ad

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
