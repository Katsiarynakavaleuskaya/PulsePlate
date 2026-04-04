# PR 1331 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036113129 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: core/food_merge.py:83-101 builds `NutritionInput.nutrients` with `is_valid_nutrient_scalar`; core/off_nutrition/resolver.py:43-46
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036113132 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: core/food_merge.py:37-54 `_merge_values` filters `None`/negative; fallback micro path core/food_merge.py:117-121
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036113133 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: tests/test_food_store_service.py legacy rows and pre-parsed JSON columns; app/services/food_store.py `_normalize_food_row`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036113134 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: tests/test_unified_db_off_coverage.py asserts on `nutrition_provenance` / `nutrition_confidence` for `get_food_by_id`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036113135 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: tests/test_food_schema_provenance.py `_parse_json_inputs("not-json")`, `nutrition_confidence` coercion; app/schemas/food.py validator
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036113136 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: tests/test_off_nutrition_resolver.py normalization, auto key discovery, invalid numerics, bool rejection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036114927
Disposition: NOT-A-BUG
Evidence: core/food_merge.py:110-116
Reason: Legacy median merge for macros intentionally overrides resolver scalars; `nutrition_provenance` reflects resolver pass while emitted scalars stay backward-compatible with pre-PR1 consumers until API clients adopt per-field provenance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036114929 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: core/food_apis/unified_db.py:101-130 `nutrition_provenance` keys from `raw_nutrients` only; tests/test_unified_db_basics.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036116617
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1331_FIXED_MAPPING.md (this thread)
Reason: Comment references an unrelated PR-1326 merge script chain; no actionable change to OFF nutrition resolver scope on PR 1331.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036119916
Disposition: NOT-A-BUG
Evidence: core/off_nutrition/contracts.py:16-27
Reason: `NutritionInput`/`NutritionResolved` use immutable dataclasses with typed `Mapping[str, float]` nutrient payloads; shallow freezing matches existing contract tests and call sites.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036119917 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: core/food_apis/unified_db.py `nutrition_confidence=0.7 if raw_nutrients else 0.0`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036119918 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: core/off_nutrition/resolver.py:36-40 bool guard; tests/test_off_nutrition_resolver.py `test_is_valid_nutrient_scalar_accepts_finite_nonneg_numbers`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036119919
Disposition: NOT-A-BUG
Evidence: core/food_merge.py:110-116
Reason: Same intentional legacy macro median path as discussion_r3036114927; resolver provenance documents source priority pass, not post-override scalars.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1331#discussion_r3036119920 -> dfbc80df
Disposition: FIXED
Commit: dfbc80df
Evidence: core/food_apis/unified_db.py:127-129 provenance only for `raw_nutrients` keys

## Merge Readiness
- [ ] All required checks pass (re-verify on current head after push)
- [ ] No unresolved review threads (resolve on GitHub after reviewer ack)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
Notes: PR `#1331` adds OFF nutrition provenance resolver wiring, store/schema normalization, and USDA provenance fixes. Canonical mapping artifact must stay aligned with thread resolution on the current head before merge readiness is claimed.
