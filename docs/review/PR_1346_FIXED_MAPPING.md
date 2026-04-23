<!-- markdownlint-disable MD034 -->
# PR 1346 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: c2323037
Evidence: app/schemas/food.py (bool guard in `_parse_json_float_dict`); app/services/food_store.py:156 (`_coerce_nutrient_confidence_map`); scripts/build_food_db.py:332 (explicit `INSERT INTO foods (...)`); app/routers/foods.py:48 (`_coerce_hit_nutrition_confidence`); tests in `tests/test_food_schema_provenance.py`, `tests/test_food_store_service.py`, `tests/test_foods_router_coverage_boost.py` (`test_list_foods_coerces_bad_nutrition_confidence_safely` uses `monkeypatch.setattr` per Python 3.12+/xdist policy)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037264392 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037266604 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037266605 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037267255 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037267261 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037267264 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037271378 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037271380 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#pullrequestreview-4059773871 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#pullrequestreview-4059775943 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#pullrequestreview-4059778783 -> c2323037
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#discussion_r3037302271 -> 1c8af78a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#pullrequestreview-4059801671 -> 1c8af78a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1346#pullrequestreview-4059802357 -> 1c8af78a

## Merge Readiness

- [ ] All required checks pass (re-check on current head before merge)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] `pre-commit run --all-files` green on pushed head
- [x] `make verify` green locally vs `origin/main` before marking ready

Notes: Checkbox thread (r3037271380) was previously marked addressed in e2e78f6; included here for a single mapping pass with the nutrition-confidence fix commit c2323037. Re-resolve threads on GitHub after push if needed.

## Split Justification

Single feature PR: wire aggregate and per-nutrient confidence through food list/detail, SQLite builder, and normalization. Elevated line count is from deterministic tests (router coercion matrix, schema/store bool guards) and explicit SQL column list — not mixed product scope.

<!-- markdownlint-enable MD034 -->
