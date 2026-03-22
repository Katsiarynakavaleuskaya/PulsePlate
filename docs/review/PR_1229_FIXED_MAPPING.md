# PR 1229 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: d0e43d20
Evidence: `app/main.py:125`, `app/bootstrap/direct_api_root.py:28`, `tests/test_direct_api_root_probe.py:21`, `tests/test_spanish_end_to_end_smoke.py:13`, `tests/test_spanish_end_to_end_smoke.py:103`, `tests/test_app_basic_combined.py:88`, `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md:46`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972124555
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972124557
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972124559
Disposition: FIXED
Commit: de54e75f
Evidence: `app/main.py:68`, `app/main.py:148`, `app/bootstrap/legacy_bmi_web_html.py:20`, `app/bootstrap/legacy_bmi_web_html.py:198`, `app/bootstrap/legacy_bmi_web_html.py:260`, `tests/test_direct_api_root_probe.py`, `tests/test_legacy_bmi_web_html_guard.py`, `docs/roadmap/BACKLOG_LEDGER.md`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972129621
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972135430
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972140766
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972140768
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972145442
Disposition: FIXED
Commit: a769d1d2
Evidence: `tests/test_coverage_improvement.py:42`, `tests/test_openapi_determinism.py:38`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972135433
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972135434
Disposition: FIXED
Commit: 5252261e
Evidence: `app/bootstrap/direct_api_root.py` (`DIRECT_API_ROOT_PROBE_MESSAGE`), `tests/test_direct_api_root_probe.py`, `tests/test_legacy_bmi_web_html_guard.py`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972159157
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972159163
Disposition: NOT-A-BUG
Evidence: `app/bootstrap/direct_api_root.py`, `app/bootstrap/legacy_bmi_web_html.py`, `tests/test_openapi_determinism.py` — Sourcery summary overlaps threads mapped below; bootstrap route constants and Node/.nvmrc CI gate are intentionally scoped as implemented.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#pullrequestreview-3988632955
Disposition: FIXED
Commit: de54e75f
Evidence: `app/bootstrap/legacy_bmi_web_html.py:20` (page title without stale year)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972135425
Disposition: FIXED
Commit: 81c71e64793e4ebcc22266ec668496a3bf008aaf
Evidence: `README.md` (Development & Operations bullet: BMI UI path vs apex `/` contract)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972135431
Disposition: FIXED
Commit: a769d1d2
Evidence: `tests/test_openapi_determinism.py` (CI fail-closed when Node major < `.nvmrc`)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972135438
Disposition: FIXED
Commit: de54e75f
Evidence: `app/main.py`, `app/bootstrap/legacy_bmi_web_html.py`, routing/docs batch (CodeRabbit review cycle 1)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#pullrequestreview-3988641521
Disposition: FIXED
Commit: a126a079
Evidence: `app/bootstrap/direct_api_root.py`, `tests/test_direct_api_root_probe.py`, `tests/test_legacy_bmi_web_html_guard.py` (CodeRabbit review cycles 2–3)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#pullrequestreview-3988645373
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#pullrequestreview-3988648467
Disposition: FIXED
Commit: 5252261e
Evidence: `app/bootstrap/direct_api_root.py` (`DIRECT_API_ROOT_PROBE_MESSAGE`), guard tests (Cubic P2 review)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#pullrequestreview-3988659006

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (resolve on GitHub after push)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
