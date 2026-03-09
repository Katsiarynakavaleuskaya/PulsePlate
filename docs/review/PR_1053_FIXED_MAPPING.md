# PR 1053 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915388839 -> cf4f6381
Disposition: FIXED
Evidence: tests/test_pro_premium_contract_parity.py:254; tests/test_app_endpoints_1383_1401.py:121
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915417151 -> cf4f6381
Disposition: FIXED
Evidence: tests/test_pro_premium_contract_parity.py:254; tests/test_app_endpoints_1383_1401.py:121
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915417151 -> 36f21947
Disposition: FIXED
Evidence: tests/test_app_openapi_coverage.py:103; tests/test_weekly_plan_schema_normalization.py:38; frontend/src/api/premium/weekly-plan.ts:5; legacy_app.py:2294
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915417151
Disposition: NOT-A-BUG
Evidence: frontend/src/api/schema.ts:3227; frontend/src/hooks/useWhoTargetsWithWeeklyPlan.ts:16
Reason: canonical `ProWeekPlanRequest` requires `lang: "ru" | "en" | "es"`, so coercing unsupported values to a supported enum preserves request validity and avoids 422 drift.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915417151
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md:1355
Reason: moving `/terms` and `/privacy` out of `legacy_app.py` belongs to the existing long-tail legacy-app migration track, not this bounded weekly-plan contract PR.

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
