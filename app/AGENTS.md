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

## Common pitfalls
- Dual Base issue: avoid relying on module identity across import paths
  (`app/__init__.py` uses `spec.loader.exec_module`).

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
