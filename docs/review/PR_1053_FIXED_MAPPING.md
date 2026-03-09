# PR 1053 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905404349 -> def635b9
Disposition: FIXED
Evidence: tests/test_pro_premium_contract_parity.py:254; tests/test_app_endpoints_1383_1401.py:121

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905404366 -> def635b9
Disposition: FIXED
Evidence: tests/test_app_endpoints_1383_1401.py:118; tests/test_app_endpoints_1383_1401.py:119

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905427942
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429719
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md:1461
Reason: moving `/terms` and `/privacy` out of `legacy_app.py` belongs to the existing `legacy_app.py` migration epic, not this bounded weekly-plan contract PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905427947 -> 744f16f0
Disposition: FIXED
Evidence: frontend/src/features/weekly-plan/model/adapter.ts:61; frontend/src/features/weekly-plan/__tests__/adapter.test.ts:108

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429697 -> 744f16f0
Disposition: FIXED
Evidence: app/routers/premium_week.py:275; tests/test_premium_week_router_isolated.py:55

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429714
Disposition: NOT-A-BUG
Evidence: frontend/src/api/schema.ts:3227; frontend/src/hooks/useWhoTargetsWithWeeklyPlan.ts:16
Reason: canonical `ProWeekPlanRequest` requires `lang: "ru" | "en" | "es"`, so coercing unsupported values to a supported enum preserves request validity and avoids 422 drift.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429724 -> def635b9
Disposition: FIXED
Evidence: tests/test_app_endpoints_1383_1401.py:118; tests/test_app_endpoints_1383_1401.py:119

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429729 -> def635b9
Disposition: FIXED
Evidence: tests/test_pro_premium_contract_parity.py:254; tests/test_pro_premium_contract_parity.py:256

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905746565 -> 4dea1108
Disposition: FIXED
Evidence: legacy_app.py:745; legacy_app.py:756; legacy_app.py:803

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905885722 -> f373f4f8
Disposition: FIXED
Evidence: frontend/src/features/weekly-plan/model/adapter.ts:16; frontend/src/features/weekly-plan/model/adapter.ts:179; frontend/src/features/weekly-plan/__tests__/adapter.test.ts:130

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905885731 -> f373f4f8
Disposition: FIXED
Evidence: frontend/src/features/weekly-plan/model/adapter.ts:122; frontend/src/features/weekly-plan/model/adapter.ts:156; frontend/src/features/weekly-plan/__tests__/adapter.test.ts:119

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905885748 -> f373f4f8
Disposition: FIXED
Evidence: frontend/src/features/weekly-plan/model/adapter.ts:147; frontend/src/features/weekly-plan/model/adapter.ts:174; frontend/src/features/weekly-plan/__tests__/adapter.test.ts:72

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915767054
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905746565
Reason: this review entry is a summary shell for the single child actionable comment above; the actionable thread is dispositioned separately and is the canonical proof target.

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
