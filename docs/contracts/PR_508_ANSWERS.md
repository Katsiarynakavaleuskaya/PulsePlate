# PR-508: Детальные ответы на архитектурные вопросы

**Дата:** 2026-01-09
**Версия:** 1.0
**Статус:** ✅ Готово к реализации

---

## 0) Главный вопрос: Что является "истиной" по контрактам?

### ✅ Рекомендация: **Вариант A + временный compatibility слой**

**Решение:**
- **OpenAPI из backend** (`app.main.app.openapi()`) — канонический источник истины
- Frontend + iOS строго генерируют типы из OpenAPI
- Legacy `/api/v1/premium/*` остаётся как compatibility alias на `/api/v1/pro/*` (deprecated, но работает)

**Обоснование:**

```python
# app/main.py — канонический entrypoint
from legacy_app import app as _legacy_app
from app.bootstrap.metrics import register_metrics

app: FastAPI = _legacy_app
register_metrics(app)

# OpenAPI генерируется из app.main.app
# ✅ Это единственный источник истины
```

**Почему не вариант B (ручные типы):**
- Дублирование кода
- Риск рассинхронизации
- Нет автоматической валидации

**Почему не вариант C (legacy как канон):**
- Legacy endpoints уже помечены как deprecated
- Миграция на `/pro/*` — это направление развития
- Нужен compatibility слой, но не как канон

**Фиксация решения:**
- Создать `docs/contracts/API_CANONICAL_MAP.md` с явным указанием канонических endpoints
- OpenAPI генерируется из `app.main.app.openapi()`
- Legacy endpoints — это aliases, не канон

---

## 1) Версионирование и политика совместимости

### 1.1 Сохраняем `/api/v1/premium/*` как alias/compat?

**✅ Да, сохраняем на 3 месяца (до 2026-04-09) с явным deprecation warning**

**Обоснование:**
- iOS приложение может быть в App Store без обновления
- Web-клиенты могут кэшировать endpoints
- Плавная миграция снижает риск регрессий

**Минимальный набор legacy endpoints (обязаны жить):**

```python
# legacy_app.py — compatibility aliases
@app.post("/api/v1/premium/bmr", deprecated=True)
async def premium_bmr_alias(req: BMRRequest) -> BMRResponse:
    """DEPRECATED: Use /api/v1/premium/bmr (same endpoint, no change needed)."""
    return await api_premium_bmr(req)

@app.post("/api/v1/premium/targets", deprecated=True)
async def premium_targets_alias(req: TargetsRequest) -> TargetsResponse:
    """DEPRECATED: Use /api/v1/pro/nutrition/targets instead."""
    # Redirect to pro endpoint
    return await pro_nutrition_targets(req)

@app.post("/api/v1/premium/plate", deprecated=True)
async def premium_plate_alias(req: PlateRequest) -> PlateResponse:
    """DEPRECATED: Use GET /api/v1/pro/nutrition/daily instead."""
    # Convert POST to GET with query params
    return await pro_nutrition_daily_get(...)

@app.post("/api/v1/premium/plan/week", deprecated=True)
async def premium_plan_week_alias(req: WeekPlanRequest) -> WeekPlanResponse:
    """DEPRECATED: Use /api/v1/pro/meal/weekly instead."""
    return await pro_meal_weekly(req)
```

**Что запрещено добавлять в legacy:**
- ❌ Новые endpoints (только aliases на `/pro/*`)
- ❌ Изменение контрактов (request/response схемы)
- ❌ Новая бизнес-логика (только делегирование)

**Где фиксируется политика:**
- `docs/contracts/API_COMPAT.md` — политика совместимости
- `docs/contracts/API_CANONICAL_MAP.md` — карта канонических endpoints
- `app/AGENTS.md` — правила для разработчиков

---

## 2) Карта фич (вертикальные слайсы)

### F1 — Targets (калории/макросы/микро-таргеты)

#### 2.1 Канонический endpoint: POST или GET?

**✅ POST** — входные параметры (user profile) в body

**Обоснование:**
```python
# app/routers/pro.py — НЕТ endpoint /nutrition/targets!
# Но есть функция estimate_targets_minimal() внутри /meal/weekly

# ПРОБЛЕМА: Фронтенд ожидает /api/v1/premium/targets
# Бэкенд НЕ предоставляет отдельный endpoint для targets
```

**Решение:**
1. **Endpoint `/api/v1/premium/targets` уже существует** (legacy_app.py:4687)
2. **Создать канонический endpoint `/api/v1/pro/nutrition/targets` (POST)**
3. Использовать существующую функцию `estimate_targets_minimal()` из `pro.py`
4. **Legacy endpoint остаётся как alias** (deprecated, но работает)

**Код решения:**

```python
# app/routers/pro.py — добавить endpoint

@router.post(
    "/nutrition/targets",
    response_model=TargetsResponse,
    dependencies=[Depends(require_pro_tier)],
    summary="Get WHO-based nutrition targets (PRO tier)",
)
async def get_nutrition_targets(req: TargetsRequest) -> TargetsResponse:
    """Get WHO-based nutrition targets from user profile.

    RU: Получить таргеты питания на основе профиля пользователя (ВОЗ).
    EN: Get WHO-based nutrition targets from user profile.

    Args:
        req: TargetsRequest with user profile (sex, age, height, weight, activity, goal)

    Returns:
        TargetsResponse with kcal, macros, micros, water, activity targets
    """
    # Validate required fields
    if req.sex is None or req.age is None or req.height_cm is None or req.weight_kg is None:
        raise HTTPException(status_code=400, detail="Missing required profile fields")

    # Use existing function
    targets_dict = estimate_targets_minimal(
        sex=req.sex,
        age=req.age,
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        activity=req.activity or "moderate",
        goal=req.goal or "maintain",
    )

    # Convert to response model
    return TargetsResponse(**targets_dict)
```

**Схема запроса (совпадает с фронтендом?):**

```typescript
// Фронтенд (premium/types.ts)
type TargetsRequest = {
  sex: 'male' | 'female';
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';
  goal: 'loss' | 'maintain' | 'gain';
  lang?: 'ru' | 'en' | 'es';
};
```

```python
# Бэкенд (legacy_app.py использует WHOTargetsRequest)
# Нужно проверить структуру WHOTargetsRequest
# И создать каноническую схему в app/schemas/targets.py
class TargetsRequest(BaseModel):
    sex: Literal["female", "male"]
    age: int = Field(..., ge=10, le=100)
    height_cm: float = Field(..., gt=100, lt=250)
    weight_kg: float = Field(..., gt=30, lt=300)
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = "moderate"
    goal: Literal["loss", "maintain", "gain"] = "maintain"
    lang: Language = "en"
```

**⚠️ Требует проверки:** Нужно сравнить `WHOTargetsRequest` (legacy) с фронтенд-типом

**Схема ответа:**

```python
# app/schemas/targets.py — создать
class TargetsResponse(BaseModel):
    """WHO-based nutrition targets response."""
    kcal_daily: int = Field(..., description="Daily calorie target")
    macros: Dict[str, float] = Field(..., description="Macronutrients (protein_g, fat_g, carbs_g, fiber_g)")
    water_ml: int = Field(..., description="Daily water target (ml)")
    priority_micros: Dict[str, float] = Field(..., description="Priority micronutrients (iron, calcium, vitamin_c, etc.)")
    activity_weekly: Dict[str, float] = Field(..., description="Weekly activity targets")
    calculation_date: str = Field(..., description="ISO 8601 date when targets were calculated")
    warnings: List[Dict[str, str]] = Field(default_factory=list, description="Warnings (e.g., age out of range)")
```

**Обязательные поля (не меняются без версии):**
- ✅ `kcal_daily` — обязателен
- ✅ `macros` — обязателен (dict с ключами: `protein_g`, `fat_g`, `carbs_g`, `fiber_g`)
- ✅ `water_ml` — обязателен
- ✅ `priority_micros` — обязателен (dict с ключами: `iron`, `calcium`, `vitamin_c`, и т.д.)
- ✅ `activity_weekly` — обязателен (dict с ключами: `moderate_aerobic_min`, `vigorous_aerobic_min`, `strength_sessions`, `steps_daily`)
- ✅ `calculation_date` — обязателен (ISO 8601 string)
- ⚠️ `warnings` — опционален (list of dict)

**Типизация warnings:**

```python
# app/schemas/targets.py
class TargetWarning(BaseModel):
    """Structured warning for nutrition targets."""
    code: str = Field(..., description="Warning code (e.g., 'age_out_of_range')")
    message: str = Field(..., description="Human-readable warning message")
    severity: Literal["info", "warning", "error"] = Field(default="warning")

class TargetsResponse(BaseModel):
    # ...
    warnings: List[TargetWarning] = Field(default_factory=list)
```

**✅ Рекомендация: типизировать warnings** (code/message/severity)

---

### F2 — Daily / Plate (дневной рацион/порции/лейаут)

#### 2.1 `/api/v1/pro/nutrition/daily` — GET или POST?

**✅ GET с query parameters** (уже реализовано в бэкенде!)

**Обоснование:**
```python
# app/routers/pro.py:396 — уже реализовано как GET
@router.get("/nutrition/daily", ...)
async def get_daily_nutrition(
    date_str: str = Query(..., alias="date"),
    sex: Literal["female", "male"] = Query(...),
    age: int = Query(...),
    # ...
) -> DailyNutritionResponse:
```

**Почему GET, а не POST:**
- Stateless: параметры в query, не в body
- Кэшируемо (если добавить Cache-Control)
- RESTful: GET для получения данных

**Проблема:** Фронтенд ожидает POST `/api/v1/premium/plate`

**Решение:**
1. **Backend compatibility alias:** POST `/api/v1/premium/plate` → конвертирует в GET `/api/v1/pro/nutrition/daily`
2. **Frontend миграция:** использовать GET с query params

**Код compatibility alias:**

```python
# legacy_app.py — добавить
@app.post("/api/v1/premium/plate", deprecated=True)
async def premium_plate_alias(req: PlateRequest) -> DailyNutritionResponse:
    """DEPRECATED: Use GET /api/v1/pro/nutrition/daily instead.

    This alias converts POST body to GET query parameters for backward compatibility.
    """
    from app.routers.pro import get_daily_nutrition

    # Convert POST body to GET query params
    return await get_daily_nutrition(
        date_str=req.date,
        sex=req.sex,
        age=req.age,
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        activity=req.activity or "moderate",
        goal=req.goal or "maintain",
        lang=req.lang or "en",
    )
```

#### 2.2 Layout — backend или frontend responsibility?

**✅ Backend отдаёт структурированные данные, frontend строит layout**

**Обоснование:**
```python
# app/routers/pro.py:118-127
class NutritionSegmentData(BaseModel):
    name: str  # "Vegetables", "Protein", etc.
    current_value: float  # servings consumed
    target_value: float  # target servings
    percentage: float  # 0-100, для визуализации
    color: str  # "green", "red", etc.
    icon: str  # SF Symbol name

class DailyNutritionResponse(BaseModel):
    segments: List[NutritionSegmentData]  # ✅ Backend структурирует
    total_progress: float
    daily_goals: DailyGoals
```

**Backend ответственность:**
- ✅ Структурированные данные (segments с percentage)
- ✅ Цвета и иконки (для консистентности)
- ✅ Процент заполнения (percentage)

**Frontend ответственность:**
- ✅ Визуализация (круг, тарелка, график)
- ✅ Анимации
- ✅ Адаптивность под экран

**✅ Текущая реализация правильная** — backend структурирует, frontend визуализирует

#### 2.3 Стабильные ключи для `day_micros` и `meals`?

**⚠️ Проблема:** `DailyNutritionResponse` не содержит `day_micros` и `meals`!

**Текущая структура:**
```python
class DailyNutritionResponse(BaseModel):
    date: str
    segments: List[NutritionSegmentData]  # Порции (servings)
    total_progress: float
    daily_goals: DailyGoals  # Цели (servings)
    # ❌ НЕТ day_micros
    # ❌ НЕТ meals
```

**Фронтенд ожидает:**
```typescript
type PlateApiResponse = {
  kcal: number;
  macros: Record<string, number>;
  portions: Portion;  // ✅ Есть (daily_goals)
  layout: LayoutItem[];  // ✅ Есть (segments)
  meals: Meal[];  // ❌ НЕТ в бэкенде
  day_micros?: Record<string, number>;  // ❌ НЕТ в бэкенде
  meals_per_day: number;  // ❌ НЕТ в бэкенде
};
```

**Решение:**
1. **Расширить `DailyNutritionResponse`** (если нужны meals/micros)
2. **Или адаптировать фронтенд** под текущую структуру

**Рекомендация:** Адаптировать фронтенд под текущую структуру бэкенда (segments + daily_goals достаточно для Plate view)

---

### F3 — Weekly plan (недельный план/покрытие/шоплист)

#### 3.1 Контрактный ответ совпадает с фронтендом?

**Проверка:**

```python
# Бэкенд (app/routers/pro.py:108-115)
class WeekPlanResponse(BaseModel):
    daily_menus: List[Dict]  # ⚠️ List[Dict], не типизировано!
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float
    adherence_score: float
```

```typescript
// Фронтенд (features/weekly-plan/model/types.ts)
interface RawWeekPlanResponse {
  daily_menus: Array<Record<string, unknown>>;  // ✅ Совпадает
  weekly_coverage: Record<string, unknown>;  // ⚠️ unknown vs float
  shopping_list: Record<string, unknown>;  // ⚠️ unknown vs float
  total_cost: number;  // ✅ Совпадает
  adherence_score: number;  // ✅ Совпадает
}
```

**Проблемы:**
1. `daily_menus` — `List[Dict]` в бэкенде, нужно типизировать
2. `weekly_coverage` — `Dict[str, float]` в бэкенде, но фронтенд ожидает `Record<string, unknown>`
3. `shopping_list` — аналогично

**Решение:**
1. **Типизировать `daily_menus`** в бэкенде (создать `DayMenu` модель)
2. **Оставить `Dict[str, float]`** в бэкенде (это правильно)
3. **Адаптер во фронтенде** конвертирует `float` → `number` (это автоматически)

**Код типизации:**

```python
# app/schemas/weekly_plan.py — создать
class MealRecipe(BaseModel):
    id: str
    name: str
    portions: int

class DayMeal(BaseModel):
    meal_type: str  # "breakfast", "lunch", etc.
    recipes: List[MealRecipe]
    totals: Dict[str, float]  # kcal, protein_g, fat_g, carbs_g, fiber_g

class DayMenu(BaseModel):
    day: int  # 1-7
    meals: List[DayMeal]
    daily_totals: Dict[str, float]

class WeekPlanResponse(BaseModel):
    daily_menus: List[DayMenu]  # ✅ Типизировано
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float
    adherence_score: float
```

#### 3.2 `shopping_list` — PRO или VIP?

**✅ PRO включает базовый shopping_list (ингредиенты + количества)**

**Обоснование:**
- PRO tier должен включать базовый список покупок
- VIP tier добавляет: цены, сравнение магазинов, экспорт

**Текущая реализация:**
```python
# app/routers/pro.py:108-115
class WeekPlanResponse(BaseModel):
    shopping_list: Dict[str, float]  # ✅ Есть в PRO
```

**✅ Правильно** — shopping_list в PRO, расширенный функционал в VIP

#### 3.3 `total_cost` — что возвращать для BY/RU?

**✅ Возвращать `0.0` или `null` (опциональное поле)**

**Обоснование:**
- Цены доступны только для VIP tier (региональные каталоги)
- PRO tier возвращает `0.0` или `null`

**Решение:**
```python
class WeekPlanResponse(BaseModel):
    total_cost: Optional[float] = Field(default=0.0, description="Total cost (VIP only, 0.0 for PRO)")
```

**✅ Рекомендация:** `Optional[float]` с default `0.0`

#### 3.4 Deprecated `/premium/plan/week` — что делать?

**✅ Alias на `/api/v1/pro/meal/weekly` с deprecation warning**

**Код:**
```python
# legacy_app.py
@app.post("/api/v1/premium/plan/week", deprecated=True)
async def premium_plan_week_alias(req: WeekPlanRequest) -> WeekPlanResponse:
    """DEPRECATED: Use /api/v1/pro/meal/weekly instead."""
    from app.routers.pro import generate_week_plan
    return await generate_week_plan(req)
```

---

## 3) OpenAPI: генерация, обновление, CI-гейт

### 3.1 Источник OpenAPI

**✅ `app.main.app.openapi()`** (канонический источник)

**Обоснование:**
```python
# app/main.py
from legacy_app import app as _legacy_app
from app.bootstrap.metrics import register_metrics

app: FastAPI = _legacy_app
register_metrics(app)  # Регистрирует middleware + /metrics

# app.main.app — это тот же объект, что legacy_app.app
# Но через app.main мы гарантируем, что bootstrap применён
```

**Проверка:**
```python
# ✅ Правильно
from app.main import app
schema = app.openapi()

# ❌ Неправильно (может не иметь bootstrap)
from legacy_app import app
schema = app.openapi()
```

### 3.2 Генерация OpenAPI

**Текущее состояние:**
- ❌ Ручное обновление `frontend/src/api/openapi.json`
- ❌ Нет автоматизации

**Решение:**
```bash
# scripts/generate_openapi.py — создать
#!/usr/bin/env python3
"""Generate OpenAPI schema from backend and update frontend/openapi.json"""

import json
import sys
from pathlib import Path

# Ensure we're in repo root
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from app.main import app

schema = app.openapi()
output_path = repo_root / "frontend" / "src" / "api" / "openapi.json"

with open(output_path, "w") as f:
    json.dump(schema, f, indent=2)

print(f"✅ OpenAPI schema generated: {output_path}")
```

**Makefile target:**
```makefile
# Makefile
openapi: ## Generate OpenAPI schema from backend
	python3 scripts/generate_openapi.py
	cd frontend && npm run generate-types

.PHONY: openapi
```

### 3.3 CI-гейт

**Решение:**
```yaml
# .github/workflows/openapi-sync.yml
name: OpenAPI Sync Check

on:
  pull_request:
    paths:
      - 'app/**/*.py'
      - 'frontend/src/api/openapi.json'

jobs:
  check-openapi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Generate OpenAPI
        run: |
          python3 scripts/generate_openapi.py > /tmp/generated.json
      - name: Check OpenAPI sync
        run: |
          if ! diff -q frontend/src/api/openapi.json /tmp/generated.json; then
            echo "❌ OpenAPI schema is out of sync!"
            echo "Run: make openapi"
            exit 1
          fi
      - name: Check TypeScript types
        run: |
          cd frontend && npm ci && npm run generate-types
          if ! git diff --quiet src/api/schema.ts; then
            echo "❌ TypeScript types are out of sync!"
            echo "Run: cd frontend && npm run generate-types"
            exit 1
          fi
```

### 3.4 Запрет ручных типов

**✅ Да, запрещаем ручные типы в `premium/types.ts`**

**Правило:**
- ❌ Запрещено: `export type BmrRequest = { ... }` (ручной тип)
- ✅ Разрешено: `export type BmrRequest = components['schemas']['BMRRequest']` (из OpenAPI)
- ✅ Разрешено: Zod-схемы для runtime-валидации (в отдельном файле)

**Код миграции:**
```typescript
// premium/types.ts — ДО
export type BmrRequest = {
  sex: 'male' | 'female';
  // ...
};

// premium/types.ts — ПОСЛЕ
import type { components } from '../schema';
export type BmrRequest = components['schemas']['BMRRequest'];
export type BmrApiResponse = components['schemas']['BMRResponse'];
```

---

## 4) FE и iOS: "тонкие клиенты" или "толстые адаптеры"?

### 4.1 Где держать compatibility/адаптацию?

**✅ Вариант A: максимум совместимости в backend, клиенты тонкие**

**Обоснование:**
- Backend контролирует контракты
- Клиенты остаются простыми
- Легче поддерживать

**Распределение ответственности:**

| Слой | Ответственность |
|------|----------------|
| **Backend** | Compatibility aliases, нормализация ответов, версионирование |
| **Frontend** | Минимальный адаптер (только для UI-специфичных преобразований) |
| **iOS** | Минимальный адаптер (только для Swift-специфичных преобразований) |

**Пример:**
```python
# Backend — compatibility alias
@app.post("/api/v1/premium/plate", deprecated=True)
async def premium_plate_alias(req: PlateRequest) -> DailyNutritionResponse:
    # Конвертация POST → GET
    return await pro_nutrition_daily_get(...)
```

```typescript
// Frontend — тонкий клиент
export const getPlate = (params: PlateParams) =>
  api<DailyNutritionResponse>(`/api/v1/pro/nutrition/daily?${new URLSearchParams(params)}`);
```

### 4.2 iOS типы

**✅ Генерировать Swift Decodable модели из OpenAPI**

**Инструменты:**
- `openapi-generator` (поддерживает Swift)
- Или ручные Decodable модели (если генератор не подходит)

**Рекомендация:**
- Использовать `openapi-generator` для автоматической генерации
- Хранить сгенерированные модели в `ios/Models/Generated/`
- Обновлять при изменении OpenAPI

---

## 5) Definition of Done для каждой фичи

### F1 — Targets: Definition of Done

- [ ] **Backend:**
  - [ ] Endpoint `/api/v1/pro/nutrition/targets` (POST) создан
  - [ ] Схемы `TargetsRequest` и `TargetsResponse` в `app/schemas/targets.py`
  - [ ] Compatibility alias `/api/v1/premium/targets` → `/api/v1/pro/nutrition/targets`
  - [ ] Тесты backend contract tests
- [ ] **OpenAPI:**
  - [ ] Схема обновлена (`make openapi`)
  - [ ] Типы сгенерированы (`cd frontend && npm run generate-types`)
- [ ] **Frontend:**
  - [ ] Клиент использует `/api/v1/pro/nutrition/targets`
  - [ ] Типы из `schema.ts` (не ручные)
  - [ ] Адаптер минимальный/явный
  - [ ] Integration tests на mock
- [ ] **iOS:**
  - [ ] Модели соответствуют OpenAPI
  - [ ] Endpoint вызывается корректно
- [ ] **Документация:**
  - [ ] `API_CANONICAL_MAP.md` обновлён
  - [ ] `API_COMPAT.md` обновлён

### F2 — Daily / Plate: Definition of Done

- [ ] **Backend:**
  - [ ] Endpoint `/api/v1/pro/nutrition/daily` (GET) работает
  - [ ] Compatibility alias `/api/v1/premium/plate` (POST) → GET
  - [ ] Тесты backend contract tests
- [ ] **OpenAPI:**
  - [ ] Схема обновлена
  - [ ] Типы сгенерированы
- [ ] **Frontend:**
  - [ ] Клиент использует GET `/api/v1/pro/nutrition/daily`
  - [ ] Типы из `schema.ts`
  - [ ] Адаптер под текущую структуру (segments + daily_goals)
  - [ ] Integration tests
- [ ] **iOS:**
  - [ ] Модели соответствуют OpenAPI
  - [ ] Endpoint вызывается корректно
- [ ] **Документация:**
  - [ ] `API_CANONICAL_MAP.md` обновлён

### F3 — Weekly Plan: Definition of Done

- [ ] **Backend:**
  - [ ] Endpoint `/api/v1/pro/meal/weekly` (POST) работает
  - [ ] `WeekPlanResponse` типизирован (`DayMenu`, `DayMeal`, etc.)
  - [ ] Compatibility alias `/api/v1/premium/plan/week` → `/api/v1/pro/meal/weekly`
  - [ ] Тесты backend contract tests
- [ ] **OpenAPI:**
  - [ ] Схема обновлена
  - [ ] Типы сгенерированы
- [ ] **Frontend:**
  - [ ] Клиент использует `/api/v1/pro/meal/weekly`
  - [ ] Типы из `schema.ts`
  - [ ] Адаптер обновлён под типизированную структуру
  - [ ] Integration tests
- [ ] **iOS:**
  - [ ] Модели соответствуют OpenAPI
  - [ ] Endpoint вызывается корректно
- [ ] **Документация:**
  - [ ] `API_CANONICAL_MAP.md` обновлён

---

## Предложение: PR-508 структура

### ✅ Рекомендация: **Contract-first подход**

**PR-508 = "Contract-first: API alignment baseline"**

**Scope (узкий):**
1. Документ канона: `docs/contracts/API_CANONICAL_MAP.md`
2. Скрипт генерации OpenAPI: `scripts/generate_openapi.py`
3. Make-таргет: `make openapi`
4. CI check: OpenAPI sync validation
5. Документ совместимости: `docs/contracts/API_COMPAT.md`

**Что НЕ входит:**
- ❌ Миграция endpoints во фронтенде
- ❌ Рефактор типов
- ❌ Runtime Zod-валидация

**Почему:**
- PR-508 — это "земля под ногами"
- Дальше PR-509/510/511 — вертикальные фичи (Targets/Daily/Weekly)

**Готовые куски для PR-508:**

1. **`docs/contracts/API_CANONICAL_MAP.md`** — таблица фич → endpoints
2. **`scripts/generate_openapi.py`** — генерация OpenAPI
3. **`Makefile`** — target `openapi`
4. **`.github/workflows/openapi-sync.yml`** — CI check
5. **`docs/contracts/API_COMPAT.md`** — политика совместимости

---

## Итоговое решение

**✅ PR-508 = Contract-first baseline**

**Следующие PR:**
- PR-509: F1 — Targets (вертикальная фича)
- PR-510: F2 — Daily/Plate (вертикальная фича)
- PR-511: F3 — Weekly Plan (вертикальная фича)

**Готов начать реализацию PR-508?** 🚀
