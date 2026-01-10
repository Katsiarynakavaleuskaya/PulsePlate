# PR-508: Фактические куски кода для проверки

**Дата:** 2026-01-09
**Цель:** Проверка фактов перед финальным планом PR-508

---

## 1) Legacy endpoints (legacy_app.py)

### A) `/api/v1/premium/targets` (строка 4687)

```python
@app.post(
    "/api/v1/premium/targets",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=WHOTargetsResponse,
)
async def api_who_targets(payload: Dict[str, Any] = Body(...)) -> WHOTargetsResponse:
    """Calculate WHO-aligned nutrition targets for premium clients.

    Normal FastAPI route usage with Body(...) and dependency injection.
    For direct test calls, use _generate_who_targets_response directly.
    """
    try:
        req = WHOTargetsRequest.model_validate(payload)
    except ValidationError as exc:
        from fastapi.encoders import jsonable_encoder

        raise HTTPException(status_code=422, detail=jsonable_encoder(exc.errors())) from exc

    return _generate_who_targets_response(req)
```

**✅ Факт:** Endpoint существует, POST, использует `WHOTargetsRequest`/`WHOTargetsResponse`

---

### B) `/api/v1/premium/plate` (строка 3982)

```python
@app.post(
    "/api/v1/premium/plate",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=PlateResponse,
)
async def api_premium_plate(req: PlateRequest) -> PlateResponse:
    """
    RU: Генерирует «Мою Тарелку» под цель/дефицит/активность.
    EN: Generates 'My Plate' for goal/deficit/activity.

    Enhanced Plate API with visual sectors and hand/cup portions:
    - Visual plate layout with 4 sectors + 2 bowls
    - Precise deficit/surplus percentage control
    - Hand/cup portion method for real-world application
    - Diet flags support (VEG, GF, DAIRY_FREE, LOW_COST)
    - Macro-balanced meal suggestions
    """
    # Feature flag check BEFORE snapshot to allow tests to set FEATURE_PREMIUM_NUTRITION
    if str(os.getenv("FEATURE_PREMIUM_NUTRITION", "")).strip().lower() not in {
        "1",
        "true",
        "on",
        "yes",
    }:
        raise HTTPException(status_code=503, detail="Enhanced plate feature not available")

    try:
        # Resolve through multiple module candidates to respect tests patching 'app.*'
        # ... (дальше логика генерации plate)
```

**✅ Факт:** Endpoint существует, POST, использует `PlateRequest`/`PlateResponse`, есть feature flag

---

### C) `/api/v1/premium/plan/week` (строка 4709)

```python
@app.post(
    "/api/v1/premium/plan/week",
    dependencies=[Depends(_get_api_key_dynamic)],
    response_model=WeeklyMenuResponse,
)
async def api_premium_plan_week(...) -> WeeklyMenuResponse:
    # ... (реализация)
```

**✅ Факт:** Endpoint существует, POST, использует `WeeklyMenuResponse`

---

## 2) Канонические endpoints (app/routers/pro.py)

### A) `/api/v1/pro/nutrition/daily` (строка 365)

```python
@router.get(
    "/nutrition/daily",
    response_model=DailyNutritionResponse,
    dependencies=[Depends(require_pro_tier)],
    summary="Get daily nutrition data (PRO tier)",
    description="""
    Get daily nutrition tracking data for Plate view based on WHO targets.

    RU: Получить данные по питанию за день для визуализации тарелки на основе таргетов ВОЗ.
    EN: Get daily nutrition tracking data for Plate view based on WHO targets.

    Requires: PRO tier API key in X-API-Key header

    Features:
    - WHO/USDA-based personalized targets
    - Plate segment visualization
    - Overall progress tracking

    Query Parameters:
    - date: Date in YYYY-MM-DD format (required)
    - sex: Biological sex (required)
    - age: Age in years (required)
    - height_cm: Height in centimeters (required)
    - weight_kg: Weight in kilograms (required)
    - activity: Activity level (optional, default: moderate)
    - goal: Nutrition goal (optional, default: maintain)
    - lang: Language for localized segment names (optional, default: en)

    Note: Current consumption values (current_value) are 0.0 until meal logging is implemented.
    """,
)
async def get_daily_nutrition(
    date_str: str = Query(
        ...,
        alias="date",
        description="Date in ISO 8601 format (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    # RU: Обязательные параметры профиля пользователя
    # EN: Required user profile parameters
    sex: Literal["female", "male"] = Query(..., description="Biological sex"),
    age: int = Query(..., ge=10, le=100, description="Age in years (10-100 inclusive)"),
    height_cm: float = Query(..., gt=100, lt=250, description="Height in centimeters"),
    weight_kg: float = Query(..., gt=30, lt=300, description="Weight in kilograms"),
    # RU: Опциональные параметры с разумными дефолтами
    # EN: Optional parameters with sensible defaults
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = Query(
        "moderate", description="Activity level"
    ),
    goal: Literal["loss", "maintain", "gain"] = Query("maintain", description="Nutrition goal"),
    # RU: Язык интерфейса для локализованных названий сегментов
    # EN: Interface language for localized segment names
    lang: Language = Query("en", description="Language for localized content"),
) -> DailyNutritionResponse:
    """Get daily nutrition data for Plate visualization using WHO targets engine.

    RU: Получить данные питания за день с использованием WHO/USDA таргетов.
    EN: Get daily nutrition data using WHO/USDA targets engine.

    Args:
        date_str: Date string in YYYY-MM-DD format
        sex: Biological sex (female/male)
        age: Age in years (10-100 inclusive)
        height_cm: Height in centimeters (100-250)
        weight_kg: Weight in kilograms (30-300)
        activity: Activity level (sedentary/light/moderate/active/very_active)
        goal: Nutrition goal (loss/maintain/gain)
        lang: Language for localized segment names (en/ru/es)

    Returns:
        DailyNutritionResponse with WHO-based targets and segments

    Raises:
        HTTPException: 400 if date format is invalid or profile validation fails

    Note:
        Current intake values (current_value, total_progress) are 0.0 until
        meal logging/HealthKit integration is implemented. Targets are calculated
        using WHO/USDA/EFSA evidence-based recommendations.
    """
    # Validate date format
    # RU: Валидация формата даты
    # EN: Validate date format
    try:
        Date.fromisoformat(date_str)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid date format: {date_str}. Expected YYYY-MM-DD"
        ) from e

    # Build user profile for WHO targets calculation
    # ... (дальше логика)
```

**✅ Факт:** Endpoint существует, GET с Query параметрами, возвращает `DailyNutritionResponse`

---

### B) `/api/v1/pro/meal/weekly` (строка 241)

```python
@router.post(
    "/meal/weekly",
    response_model=WeekPlanResponse,
    dependencies=[Depends(require_pro_tier)],
    summary="Generate weekly meal plan (PRO tier)",
    description="""
    Generate weekly meal plan with PRO tier features.

    RU: Генерация недельного плана питания с функциями PRO уровня.
    EN: Generate weekly meal plan with PRO tier features.

    Requires: PRO tier API key in X-API-Key header

    Features:
    - WHO-based nutrition targets
    - Macro and micronutrient planning
    - Dietary restrictions support
    - Weekly shopping list
    - Cost estimation
    """,
)
async def generate_week_plan(req: WeekPlanRequest) -> Union[WeekPlanResponse, JSONResponse]:
    """Generate weekly meal plan with PRO tier features.

    Args:
        req: WeekPlanRequest with targets or user profile

    Returns:
        WeekPlanResponse with daily menus, coverage, shopping list, and metrics

    Raises:
        HTTPException: 400 if profile data is missing or invalid
    """
    # Get cached database instances
    fooddb = get_food_db()
    recipedb = get_recipe_db()

    # Get targets (treat partial/empty targets as "missing" and fall back to profile derivation)
    targets_from_request: Dict[str, Any] = (
        req.targets.model_dump(exclude_none=True) if req.targets is not None else {}
    )

    if _is_complete_targets(targets_from_request):
        targets: Dict[str, Any] = targets_from_request
    else:
        # Fallback: derive from profile, otherwise 400 (DRY error messages with helper)
        if req.sex is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("sex"))
        if req.age is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("age"))
        if req.height_cm is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("height_cm"))
        if req.weight_kg is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("weight_kg"))
        # activity/goal have defaults but can be explicitly set to null
        if req.activity is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("activity"))
        if req.goal is None:
            raise HTTPException(status_code=400, detail=_missing_profile_detail("goal"))

        # After all None checks above, types are narrowed to non-None
        targets = estimate_targets_minimal(
            sex=req.sex,
            age=req.age,
            height_cm=float(req.height_cm),
            weight_kg=float(req.weight_kg),
            activity=req.activity,
            goal=req.goal,
        )

    # Hard guard: never pass None/malformed targets to core
    if not isinstance(targets, dict):
        raise HTTPException(status_code=400, detail="Unable to derive targets")
    if not _is_complete_targets(targets):
        raise HTTPException(status_code=400, detail="Unable to derive targets")

    # Build week (generation stage) + postprocess (pipeline with ordering guard)
    from core.menu_engine_new import PlateDayTargets

    # Wrap WeekPlanResponse constructor to match postprocess_fn signature
    def _postprocess_week(week: Dict[str, Any]) -> WeekPlanResponse:
        return WeekPlanResponse(**week)

    result = run_weekly_pipeline_guarded(
        generation_fn=build_week,
        postprocess_fn=_postprocess_week,
        generation_kwargs={
            "targets": cast(PlateDayTargets, targets),
            "diet_flags": req.diet_flags,
            "lang": req.lang,
            "fooddb": fooddb,
            "recipedb": recipedb,
        },
        postprocess_kwargs={},
        generation_map_error=lambda _e: ("weekly_generation_failed", "Failed to generate plan"),
        generation_default_code="weekly_generation_failed",
        postprocess_map_error=lambda _e: (
            "weekly_postprocess_failed",
            "Failed to build weekly plan response",
        ),
        postprocess_default_code="weekly_postprocess_failed",
        generation_debug_ctx={
            "router": "pro",
            "path": "/api/v1/pro/meal/weekly",
        },
        postprocess_debug_ctx={
            "router": "pro",
            "path": "/api/v1/pro/meal/weekly",
        },
    )

    # Pipeline returns either error envelope or postprocess result
    if isinstance(result, dict) and result.get("status") == "error":
        # IMPORTANT: bypass response_model validation
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=result)

    if not isinstance(result, WeekPlanResponse):
        raise TypeError(
            "Expected WeekPlanResponse from weekly pipeline, "
            f"got type={type(result).__name__} value={result!r}"
        )
    return result
```

**✅ Факт:** Endpoint существует, POST, использует `WeekPlanRequest`/`WeekPlanResponse`

---

### C) `/api/v1/pro/nutrition/targets` — проверка

```bash
$ grep -n "@router\.(post|get).*nutrition.*targets\|/nutrition/targets" app/routers/pro.py
12:- /api/v1/pro/nutrition/targets - WHO-based nutrition goals
```

**❌ Факт:** Endpoint НЕ существует, только упоминание в комментарии (строка 12)

---

## 3) OpenAPI generation pipeline

### A) frontend/package.json — скрипт generate-types

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ci": "vitest run --environment jsdom --testTimeout=30000 --reporter=verbose --reporter=junit --outputFile=test-results/junit.xml",
    "test:coverage": "vitest run --coverage",
    "test:accessibility": "vitest run --environment jsdom --testTimeout=30000 --reporter=verbose src/**/__tests__/*Accessibility.test.tsx",
    "generate-types": "openapi-typescript src/api/openapi.json --output src/api/schema.ts"
  }
}
```

**✅ Факт:** Скрипт существует, использует `openapi-typescript`

---

### B) frontend/src/api/schema.ts — существование

```bash
$ test -f frontend/src/api/schema.ts && echo "EXISTS" || echo "NOT_EXISTS"
EXISTS
```

**✅ Факт:** Файл существует

---

## Итоговые факты

| Endpoint | Метод | Существует | Расположение |
|----------|-------|------------|--------------|
| `/api/v1/premium/targets` | POST | ✅ Да | `legacy_app.py:4687` |
| `/api/v1/premium/plate` | POST | ✅ Да | `legacy_app.py:3982` |
| `/api/v1/premium/plan/week` | POST | ✅ Да | `legacy_app.py:4709` |
| `/api/v1/pro/nutrition/daily` | GET | ✅ Да | `app/routers/pro.py:365` |
| `/api/v1/pro/meal/weekly` | POST | ✅ Да | `app/routers/pro.py:241` |
| `/api/v1/pro/nutrition/targets` | POST | ❌ Нет | Только комментарий в `pro.py:12` |

---

## Выводы

1. **Legacy endpoints существуют** — все три (`/premium/targets`, `/premium/plate`, `/premium/plan/week`)
2. **Канонические endpoints частично реализованы:**
   - ✅ `/pro/nutrition/daily` (GET) — есть
   - ✅ `/pro/meal/weekly` (POST) — есть
   - ❌ `/pro/nutrition/targets` (POST) — нет
3. **OpenAPI pipeline работает** — скрипт и schema.ts существуют
4. **Проблема:** `/premium/plate` (POST) и `/pro/nutrition/daily` (GET) — разные методы, нужен compatibility alias

---

## Ответы на быстрые вопросы

1. **PR-508 строго baseline без прод-кода?** → **ДА** (вариант 508A)
2. **Compat слой `/premium/*` на 3 месяца — железно?** → **ДА**
3. **OpenAPI включает legacy aliases или только канон?** → **ОБА** (legacy помечены `deprecated=True`)
