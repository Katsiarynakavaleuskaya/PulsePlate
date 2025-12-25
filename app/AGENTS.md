# Agent instructions (scope: app/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `app/` and below.
- Key directories: `app/routers/`, `app/schemas/`, `app/models/`, `app/services/`,
  `app/middleware/`, `app/core/`, `app/dependencies.py`.

## Commands (run from repo root)
- Install: `make venv`
- Dev: `make dev`
- Test: `make test`, `make test-fast`
- Coverage: `make cov`, `make cov-check`
- Lint/format: `make lint`, `make fmt`, `make fmt-check`
- Pre-commit: `make pre-commit`

## Conventions
- FastAPI + Pydantic v2 only; prefer `model_validator`/`field_validator`.
- Keep routers thin; push business logic into `core/` or `app/services/`.
- Use dependency injection via `Depends`; keep side effects in services.
- Use `fastapi.status` for status codes and `HTTPException` for errors.
- Keep API schema changes in sync with `app/schemas/` and tests.
- Apply tier guards (`require_pro_tier`, VIP) consistently on gated endpoints.

## No duplicated business logic (app vs core)

- Routers and services must not re-implement domain logic.
- If logic is needed in multiple endpoints, put it into `core/` and call it.
- `legacy_app.py` is compatibility-only: do not add new behavior there unless it is purely shim/bridge.

## Common pitfalls
- Import Hygiene: do NOT reintroduce dynamic module loading in `app/__init__.py`
  (no `spec_from_file_location`, no `exec_module`, no sys.path hacks).
- `import app` is a PEP 562 shim: `app.app` MUST point to `legacy_app.app`, and
  missing symbols are forwarded via `__getattr__`.
- Feature flags (e.g. exports) may be evaluated at import time; tests must set
  `TESTING=true` before importing `app`/`legacy_app` (handled in `tests/conftest.py`).

## app package public surface contract
`app/__init__.py` must remain an import shim/forwarder.
It MUST NOT use dynamic module execution (spec/module_from_spec/exec_module).

If tests import symbols from `app`, update:
- `tests/test_app_public_surface.py`
- `tests/test_repo_policy_guards.py` (required exports set)

### Required symbols (forwarded via PEP 562 __getattr__)
Tests expect these symbols to exist in `app` namespace:
- `app.app` (FastAPI instance)
- `resolve_attr`
- `make_weekly_menu`
- `build_nutrition_targets`
- `get_update_scheduler`

### Quick verification
```bash
# Check what tests require from app
rg -n "from app import \(|from app import " tests -S
rg -n "app\.(build_nutrition_targets|get_update_scheduler|resolve_attr|make_weekly_menu)" tests -S

# Smoke test
python - <<'PY'
import app
need = ["resolve_attr","make_weekly_menu","build_nutrition_targets","get_update_scheduler"]
print("missing:", [n for n in need if not hasattr(app, n)])
PY
```

## Feature map

| Feature | Owner | Key paths | Entrypoints | Tests | Docs |
|--------|-------|-----------|-------------|-------|------|
| BMI/body composition | backend | `core/bmi_*.py`, `core/bmi_extras.py`, `bmi_core.py`, `bodyfat.py` | `app/routers/bmi_pro.py` | `tests/test_bmi_*.py`, `tests/test_bodyfat.py` | - |
| Nutrition logging | backend | `app/routers/nutrition_log.py`, `app/models/events.py`, `app/schemas/nutrition_log.py` | `app/routers/nutrition_log.py` | `tests/test_nutrition_log_*.py` | - |
| Meal planning | backend | `core/meal_planner.py`, `core/weekly_plan*.py`, `core/menu_engine*.py` | `app/routers/premium_week.py` | `tests/test_premium_week_*.py`, `tests/test_menu_engine_*.py` | - |
| Food database | backend | `core/food_db*.py`, `core/food_apis/`, `data/food_db.csv`, `app/services/food_store.py` | `app/routers/foods.py` | `tests/test_food_db*.py`, `tests/test_food_apis*.py` | - |
| Recipe synthesis | backend | `core/recipe_synth.py`, `core/recipe_db*.py` | `app/routers/recipes.py` | `tests/test_recipe_*.py` | - |
| Shopping lists | backend | `core/shoplist.py`, `app/routers/shopping_list_pro.py`, `app/routers/shoplist_day.py`, `app/routers/shoplist_export.py` | `app/routers/shopping_list_pro.py` | `tests/test_shopping_list_*.py`, `tests/test_shoplist_*.py` | - |
| Premium/Pro features | backend | `app/routers/*_pro.py`, `core/bmi_extras_pro.py`, `app/middleware/api_tiers.py` | `app/routers/pro.py`, `app/routers/premium_week.py`, `app/routers/vip.py` | `tests/test_*_pro*.py`, `tests/test_premium_week_*.py` | - |
| User management | backend | `app/routers/users.py`, `app/schemas/users.py`, `core/models.py` | `app/routers/users.py` | `tests/test_users_*.py` | - |
| i18n/localization | backend | `core/i18n.py`, `core/meal_i18n.py` | `core/i18n.py` | `tests/test_i18n*.py` | - |
| Bayesian analyzers | backend | `core/*_bayesian_analyzer.py`, `core/bayes/` | `app/routers/bayes_adherence.py` | `tests/test_bayes_*.py`, `tests/test_bayesian_*.py` | - |
| Export/reports | backend | `core/exports*.py`, `app/routers/plan_export.py`, `app/routers/shoplist_export.py` | `app/routers/plan_export.py` | `tests/test_exports*.py` | - |
| LLM integration | backend | `llm.py`, `core/rag/`, `providers/` | `llm.py`, `mcp_pulseplate_server.py` | `tests/test_*rag*.py` | - |

## App Import Hygiene (quick checks)
Run from repo root.

### No dynamic module loading in app package
```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- app || true
```

### app shim contract must hold
```bash
python - <<'PY'
import os
os.environ["TESTING"] = "true"
import app, legacy_app
assert app.app is legacy_app.app
print("OK: app.app is legacy_app.app")
PY
```
