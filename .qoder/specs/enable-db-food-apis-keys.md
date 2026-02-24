# Plan: Enable 4 Feature Keys (core_db, food_apis, food_apis_error_injection, unified_db)

PR #879 — continues PR #877 pattern (thin facades + gate removal).
**Keys:** 4 | **Gates removed:** 35 | **FEATURE_TODO_KEYS:** 13 -> 9

---

## Facades Needed

### 1. `core/db.py` — add 4 functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `get_db` | `() -> Generator[Session, None, None]` | delegates to `get_session()` |
| `create_tables` | `() -> None` | `Base.metadata.create_all(bind=engine)` |
| `init_database` | `() -> None` | delegates to `create_tables()` |
| `get_unified_food_db` | `() -> object \| None` | lazy-import UnifiedFoodDatabase, return instance or None |

### 2. `core/food_apis/base.py` — NEW file

- `FoodAPIBase` class (empty)
- `FoodDataProvider` class with `search_food(query) -> list`

### 3. `core/food_apis/usda.py` — NEW file (re-export)

- `from .usda_client import USDAClient` (re-export under test-expected path)

### 4. `core/food_apis/openfoodfacts.py` — NEW file (re-export)

- `from .openfoodfacts_client import OFFClient as OpenFoodFactsClient`

### 5. `core/food_apis/scheduler.py` — add 3 exports

- `FoodAPIScheduler` = alias for `DatabaseUpdateScheduler`
- `check_update_status() -> dict`
- `schedule_update() -> None`

### 6. `core/food_apis/unified_db.py` — add 4 exports

- `UnifiedFoodDB` = alias for `UnifiedFoodDatabase`
- `FoodSource` class with USDA/OPENFOODFACTS constants
- `merge_food_sources(list, list) -> list`
- `update_unified_db() -> None`

### 7. `core/food_sources/openfood_source.py` — NEW file

- `OpenFoodSource` class (thin, with optional `search()`)

### 8. `core/food_sources/usda_source.py` — NEW file

- `USDASource` class (thin, with optional `get_food_data()`)

### 9. `core/food_sources/base.py` — add 4 exports

- `FoodSourceBase` class (empty)
- `merge_food_entries(list) -> dict`
- `normalize_food_data(dict) -> dict`
- `validate_food_entry(dict) -> bool`

### 10. `core/food_categories.py` — NEW file

- `classify_food(str) -> str|None`
- `get_food_category(str) -> str|None`
- `list_categories() -> list`
- `validate_category(str) -> bool`

---

## Gate Removal (9 test files)

| File | Keys | Gates |
|------|------|-------|
| `tests/test_database_apis_coverage.py` | core_db, food_apis, unified_db | ~6 |
| `tests/test_missing_coverage_97_final.py` | core_db, food_apis | ~5 |
| `tests/test_direct_core_functions.py` | core_db, food_apis | ~2 |
| `tests/test_core_coverage_97_final.py` | food_apis, unified_db | ~4 |
| `tests/test_final_core_coverage.py` | food_apis | ~2 |
| `tests/test_simple_coverage_fixed.py` | food_apis, unified_db | ~2 |
| `tests/test_quick_coverage_boost.py` | unified_db | ~1 |
| `tests/test_final_coverage_97_boost.py` | unified_db | ~2 |
| `tests/test_food_apis_coverage_errors.py` | food_apis_error_injection | 6 |

### `tests/feature_manifest.py`

Remove 4 keys from `FEATURE_TODO_KEYS`: `core_db`, `food_apis`, `food_apis_error_injection`, `unified_db`

---

## Coverage Tests

Add `tests/test_db_food_facades_coverage.py`:
- `test_core_db_facades() -> None` — exercises get_db, create_tables, init_database, get_unified_food_db
- `test_food_apis_base_facades() -> None` — FoodAPIBase, FoodDataProvider
- `test_food_apis_reexports() -> None` — USDAClient from usda.py, OpenFoodFactsClient from openfoodfacts.py
- `test_scheduler_facades() -> None` — FoodAPIScheduler, check_update_status, schedule_update
- `test_unified_db_facades() -> None` — UnifiedFoodDB, FoodSource, merge_food_sources, update_unified_db
- `test_food_sources_facades() -> None` — OpenFoodSource, USDASource, FoodSourceBase, merge/normalize/validate
- `test_food_categories_facades() -> None` — classify_food, get_food_category, list_categories, validate_category

---

## Implementation Order

1. Add facades to core modules (6 new files + 4 existing files modified)
2. Remove 4 keys from FEATURE_TODO_KEYS
3. Remove gates from 9 test files
4. Add coverage test file
5. Run `make verify` (lint + typecheck + test-fast + diff-cov)
6. Run `pre-commit run --all-files`
7. Create branch, commit, push, open PR

---

## Verification

```bash
# 1. Smoke imports
python -c "from core.db import get_db, create_tables; print('core_db OK')"
python -c "from core.food_apis.base import FoodAPIBase; print('food_apis.base OK')"
python -c "from core.food_apis.usda import USDAClient; print('food_apis.usda OK')"
python -c "from core.food_apis.openfoodfacts import OpenFoodFactsClient; print('food_apis.off OK')"
python -c "from core.food_apis.unified_db import UnifiedFoodDB, FoodSource; print('unified_db OK')"
python -c "from core.food_categories import classify_food; print('food_categories OK')"

# 2. Guards + smoke
pytest -q tests/test_repo_policy_guards.py
make test-fast

# 3. Full verify
make verify

# 4. Pre-commit
pre-commit run --all-files
```

## Risk Notes

- `get_unified_food_db()` in core/db.py must use lazy import to avoid circular dependency
- `food_apis_error_injection` tests are async — verify pytest-asyncio handles them
- Use `**kwargs: object` not `**kwargs: Any` per project typing policy
- Tests use `hasattr()` checks — missing optional methods are tolerated
