# PR 1053 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915388839
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905404349; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905404366
Reason: this cubic review entry is a summary shell; the actionable child comments are dispositioned separately below with exact thread URLs.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915417151
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429697; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429714; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429719; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429724; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905429729
Reason: this CodeRabbit review entry is a summary shell for the actionable child threads already dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915916533
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905885722; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905885731; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905885748
Reason: this later CodeRabbit review entry is a summary shell for the follow-up actionable child threads already dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3915767054
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2905746565
Reason: this review entry is a summary shell for the single child actionable comment above; the actionable thread is dispositioned separately and is the canonical proof target.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3916090710
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906038434
Reason: cubic identified this issue in the review summary shell; the exact actionable child thread is dispositioned separately below and is the canonical proof target.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906038434 -> 56ca4c1b
Disposition: FIXED
Evidence: frontend/src/features/weekly-plan/model/adapter.ts:157; frontend/src/features/weekly-plan/__tests__/adapter.test.ts:130
Reason: preserve original `daily_menus` indices while skipping malformed entries so valid days retain the correct `day`/`dayName`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181768 -> 7995b062
Disposition: FIXED
Evidence: app/schemas/weekly_plan.py:64; tests/test_weekly_plan_schema_normalization.py:40
Reason: weekly-plan normalization now fails closed for malformed meal/day/root payloads instead of silently manufacturing DTO defaults.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181787 -> 7995b062
Disposition: FIXED
Evidence: frontend/src/features/weekly-plan/model/adapter.ts:156; frontend/src/features/weekly-plan/__tests__/adapter.test.ts:62
Reason: root payloads are now shape-guarded before dereferencing `daily_menus`, returning a safe incomplete VM for null/primitive input.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181793 -> 7995b062
Disposition: FIXED
Evidence: tests/test_premium_week_router_isolated.py:82
Reason: JSON content-type is asserted before parsing the 500-path premium router response body.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181795 -> 7995b062
Disposition: FIXED
Evidence: tests/test_pro_router.py:185
Reason: JSON content-type is asserted before parsing the 500-path PRO router response body.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181781 -> 38a5e257
Disposition: FIXED
Evidence: docs/review/PR_1053_FIXED_MAPPING.md:107; docs/review/PR_1053_FIXED_MAPPING.md:108; docs/review/PR_1053_FIXED_MAPPING.md:109
Reason: merge-readiness checklist remains unchecked until the final merge pass instead of being marked done prematurely.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#pullrequestreview-3916255202
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181768; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181781; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181787; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181793; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1053#discussion_r2906181795
Reason: this CodeRabbit review entry is a summary shell for the actionable child threads dispositioned separately below.

## Merge Readiness
- [ ] Scope tied to PR objective
- [ ] Docs/runtime changes applied
- [ ] Verification completed
- [ ] Required GitHub checks PASS with no pending required jobs
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] No unresolved review threads or actionable bot comments remain
- [ ] Review wait-window completed
