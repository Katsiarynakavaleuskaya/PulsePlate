---
name: PR-11 BMI Canonical Engine
overview: Создать единый BMI engine как source of truth, заменить дублирование calc_bmi() и legacy логики на канонический orchestrator, добавить новый endpoint /api/v1/bmi/calculate с единым контрактом.
todos:
  - id: commit1_risk
    content: Extract waist_risk to core/bmi/risk.py with WaistRiskResult dataclass
    status: pending
  - id: commit2_engine
    content: Create core/bmi/engine.py orchestrator with calculate_bmi_result() pipeline
    status: pending
    dependencies:
      - commit1_risk
  - id: commit3_schemas
    content: Add app/schemas/bmi.py with BMICalculateRequest/Response DTOs
    status: pending
  - id: commit4_endpoint
    content: Add POST /api/v1/bmi/calculate endpoint using engine
    status: pending
    dependencies:
      - commit2_engine
      - commit3_schemas
  - id: commit5_legacy_shims
    content: Refactor legacy endpoints to use engine (preserve response format)
    status: pending
    dependencies:
      - commit2_engine
  - id: commit6_remove_duplicates
    content: Mark calc_bmi() as deprecated alias (soft cleanup, preserve compatibility)
    status: pending
    dependencies:
      - commit5_legacy_shims
---

# PR-1

1: BMI Canonical Engine + Single Endpoint

## Цель

Создать единый source of truth для BMI расчетов, устранить дублирование `calc_bmi()` в 3 местах, обеспечить единый контракт для сайта и iOS через `/api/v1/bmi/calculate`.

## Архитектура

```javascript
bmi_core.py                    # Domain primitives (math + rules)
  ├── bmi_value()
  ├── bmi_category()
  ├── auto_group()
  ├── compute_wht_ratio()
  └── interpret_group()

core/bmi/
  ├── __init__.py              # Package exports
  ├── engine.py                 # Orchestrator (source of truth)
  └── risk.py                   # Waist risk assessment

app/schemas/bmi.py              # Request/Response DTO (API contract)
app/routers/bmi.py              # POST /api/v1/bmi/calculate

legacy_app.py                   # Legacy endpoints (shims → engine)
```



## Commit 1: Extract waist risk to core/bmi/risk.py

**Файлы:**

- `core/bmi/__init__.py` (NEW)
- `core/bmi/risk.py` (NEW)

**Изменения:**

- Перенести `waist_risk()` из `legacy_app.py:1583` в `core/bmi/risk.py`
- Преобразовать в структурированный результат:
  ```python
      @dataclass(frozen=True)
      class WaistRiskResult:
          wht_ratio: float | None
          risk_level: Literal["unknown", "low", "moderate", "high"]
          notes: list[str]
  ```




- Использовать `compute_wht_ratio()` из `bmi_core.py` для WHtR
- Пороги: male (94/102), female (80/88) - без изменений (golden test)

**Тесты:**

- `tests/test_bmi_risk.py` (NEW) - golden tests для старого поведения
- Матрица: (waist_cm, gender, lang) → ожидаемая строка/risk_level

**Commit message:**

```javascript
refactor(bmi): extract waist risk to core/bmi/risk.py

- Move waist_risk() from legacy_app.py to core/bmi/risk.py
- Convert to structured WaistRiskResult dataclass
- Use compute_wht_ratio() from bmi_core.py
- Add golden tests to preserve legacy behavior
```

---

## Commit 2: Create BMI engine orchestrator

**Файлы:**

- `core/bmi/engine.py` (NEW)
- `core/bmi/__init__.py` (UPDATE - export engine)

**Изменения:**

- Создать функцию `calculate_bmi_result()`:
  ```python
      def calculate_bmi_result(
          weight_kg: float,
          height_cm: float,
          age: int,
          gender: str,
          pregnant: str | bool,
          athlete: str | bool,
          waist_cm: float | None,
          lang: str,
      ) -> BMICalculateResult:
  ```




- Pipeline:

1. Validate inputs (weight > 0, height_cm > 0, age in range)
2. Convert height_cm → height_m
3. Calculate BMI: `bmi_value(weight_kg, height_m)`
4. Determine group: `auto_group(age, gender, pregnant, athlete, lang)`
5. Get category: `bmi_category(bmi, lang, age, group)`
6. Get interpretation: `interpret_group(bmi, group, lang, age)`
7. Calculate WHtR: `compute_wht_ratio(waist_cm, height_m)` (optional)
8. Get waist risk: `calculate_waist_risk(waist_cm, height_m, gender, lang)` (optional)
9. Assemble result DTO

**Зависимости:**

- Импортирует из `bmi_core`: `bmi_value`, `bmi_category`, `auto_group`, `interpret_group`, `compute_wht_ratio`
- Импортирует из `core.bmi.risk`: `calculate_waist_risk`

**Тесты:**

- `tests/test_bmi_engine.py` (NEW)
- Матрица групп: general/athlete/elderly/teen/child/pregnant/too_young
- Матрица языков: RU/EN/ES
- WHtR fail-soft (waist_cm=None → wht_ratio=None, risk=None)
- Edge cases: беременность (category=None), too_young

**Commit message:**

```javascript
feat(core): add BMI engine orchestrator

- Create core/bmi/engine.py with calculate_bmi_result()
- Pipeline: validate → convert → bmi_value → auto_group → category → interpret → wht_ratio → risk
- Uses bmi_core primitives (no duplication)
- Optional waist risk assessment via core/bmi/risk.py
```

---

## Commit 3: Add BMI schemas (API contract)

**Файлы:**

- `app/schemas/bmi.py` (NEW)

**Изменения:**

- `BMICalculateRequest`:
  ```python
      class BMICalculateRequest(BaseModel):
          weight_kg: float = Field(..., gt=0)
          height_cm: float = Field(..., gt=0)
          age: int = Field(..., ge=1, le=120)
          gender: str = Field(default="male")
          pregnant: str | bool = Field(default="no")
          athlete: str | bool = Field(default="no")
          waist_cm: float | None = Field(None, gt=0)
          lang: Language = Field(default="en")
  ```




- `BMICalculateResponse`:
  ```python
      class BMICalculateResponse(BaseModel):
          bmi: float
          category: str | None
              # None for pregnant/too_young - not an error, medical disclaimer
              # BMI is not valid during pregnancy or for children <12
          group: str
          group_display: str
          interpretation: str
          wht_ratio: float | None
          waist_risk: dict[str, Any] | None  # WaistRiskResult serialized
          notes: list[str]
  ```


**Валидация:**

- BMI bounds: 10-100 (как в BMIRequestV1)
- Gender normalization (male/female/unknown)
- Pregnant/athlete string→bool conversion

**Тесты:**

- `tests/test_bmi_schemas.py` (NEW)
- Schema validation: 422 cases (negative weight, invalid age, etc.)
- Golden tests: request → response structure

**Commit message:**

```javascript
feat(api): add BMI request/response schemas

- Create app/schemas/bmi.py with BMICalculateRequest/Response
- Request: weight_kg, height_cm, age, gender, pregnant, athlete, waist_cm, lang
- Response: bmi, category, group, interpretation, wht_ratio, waist_risk, notes
- Validation: BMI bounds 10-100, gender normalization, string→bool conversion
```

---

## Commit 4: Add POST /api/v1/bmi/calculate endpoint

**Файлы:**

- `app/routers/bmi.py` (NEW)

**Изменения:**

- Создать router:
  ```python
      router = APIRouter(prefix="/api/v1/bmi", tags=["bmi"])

      @router.post("/calculate", response_model=BMICalculateResponse)
      async def calculate_bmi(req: BMICalculateRequest) -> BMICalculateResponse:
          result = calculate_bmi_result(
              weight_kg=req.weight_kg,
              height_cm=req.height_cm,
              age=req.age,
              gender=req.gender,
              pregnant=req.pregnant,
              athlete=req.athlete,
              waist_cm=req.waist_cm,
              lang=req.lang,
          )
          return BMICalculateResponse(**result.model_dump())
  ```




- Error handling:
  - 422 — Pydantic validation (автоматически)
  - 400 — domain validation errors (ValueError → HTTPException(400))
  - 500 — FastAPI default (не использовать safe_call для Free BMI)

**Интеграция:**

- Зарегистрировать router в `app/main.py` или `legacy_app.py` (где регистрируются роутеры)

**Тесты:**

- `tests/test_bmi_calculate_endpoint.py` (NEW)
- API integration: все группы, языки, с/без waist_cm
- Error cases: 422 (invalid input), 400 (validation)

**Commit message:**

```javascript
feat(api): add POST /api/v1/bmi/calculate endpoint

- Create app/routers/bmi.py with calculate endpoint
- Uses core/bmi/engine.calculate_bmi_result()
- Returns BMICalculateResponse with unified contract
- No API key required (FREE tier)
```

---

## Commit 5: Legacy endpoints as shims

**Файлы:**

- `legacy_app.py` (UPDATE - bmi_endpoint, bmi_endpoint_v1, bmi_calculate_legacy)

**Изменения:**

- Заменить локальные вычисления на вызов `calculate_bmi_result()`:
  ```python
      # Вместо:
      bmi = calc_bmi(req.weight_kg, req.height_m)
      category = bmi_category(bmi, req.lang, req.age, ...)

      # Использовать:
      from core.bmi.engine import calculate_bmi_result
      result = calculate_bmi_result(
          weight_kg=req.weight_kg,
          height_cm=req.height_m * 100,  # convert
          age=req.age,
          gender=req.gender,
          pregnant=req.pregnant,
          athlete=req.athlete,
          waist_cm=req.waist_cm,
          lang=req.lang,
      )
      # Map result to legacy response format
  ```




- Заменить локальные функции на вызовы engine:
  - `calc_bmi()` → использовать `bmi_value()` из `bmi_core` (через engine)
  - `normalize_flags()` → использовать `auto_group()` из `bmi_core` (через engine)
  - `waist_risk()` → использовать `calculate_waist_risk()` из `core.bmi.risk` (через engine)

**Важно:** Сначала заменить логику на engine, потом (в Commit 6) пометить старые функции как deprecated

**Обратная совместимость:**

- Legacy response format сохраняется (для существующих клиентов)
- Добавить комментарий: "DEPRECATED: Use /api/v1/bmi/calculate"

**Тесты:**

- `tests/test_bmi_legacy_shims.py` (NEW)
- Golden tests: legacy endpoints возвращают те же значения BMI/category/group что и новый engine
- Проверка: `bmi_endpoint()` → `calculate_bmi_result()` → одинаковые результаты

**Commit message:**

```javascript
refactor(api): route legacy BMI endpoints through engine

- Replace local calc_bmi/normalize_flags/waist_risk with engine calls
- Legacy endpoints become thin shims over core/bmi/engine
- Preserve legacy response format for backward compatibility
- Mark calc_bmi/normalize_flags as deprecated (use bmi_core/engine)
```

---

## Commit 6: Remove calc_bmi duplicates

**Файлы:**

- `app/routers/bmi_pro.py` (UPDATE)
- `legacy_app.py` (UPDATE - удалить локальный calc_bmi если не используется)

**Изменения:**

- В `app/routers/bmi_pro.py`: заменить локальный `calc_bmi()` на импорт:
  ```python
      from bmi_core import bmi_value as calc_bmi
  ```




- В `legacy_app.py`: удалить `calc_bmi()` (или оставить как deprecated alias)

**Проверка:**

- `grep -r "def calc_bmi"` → должен найти только в `bmi_core.py` (или deprecated alias)

**Тесты:**

- Существующие тесты должны проходить (поведение не меняется)

**Commit message:**

```javascript
refactor(bmi): remove calc_bmi() duplicates

- Replace local calc_bmi() in app/routers/bmi_pro.py with bmi_core.bmi_value
- Remove calc_bmi() from legacy_app.py (use bmi_core.bmi_value)
- Ensure single source of truth: bmi_core.bmi_value()
```

---

## Тесты (обязательные для всех коммитов)

### Unit tests

- `tests/test_bmi_risk.py` - waist risk logic
- `tests/test_bmi_engine.py` - engine orchestrator (все группы, языки, edge cases)
- `tests/test_bmi_schemas.py` - request/response validation

### Integration tests

- `tests/test_bmi_calculate_endpoint.py` - новый endpoint
- `tests/test_bmi_legacy_shims.py` - legacy endpoints через engine

### Golden tests (фиксируют поведение)

- Матрица: (group, lang, age, waist_cm) → ожидаемый результат
- Проверка: legacy endpoints = engine results

---

## Правила импорта (важно)

1. `core/bmi/engine.py` импортирует:

- `bmi_core`: `bmi_value`, `bmi_category`, `auto_group`, `interpret_group`, `compute_wht_ratio`
- `core.bmi.risk`: `calculate_waist_risk`

2. `bmi_core.py` НЕ импортирует:

- Ничего из `core.bmi.*`
- Ничего из `app/*`

3. `app/routers/*` импортирует:

- `core.bmi.engine` (для нового endpoint)
- `bmi_core.bmi_value` (только если нужен напрямую, иначе через engine)

---

## Риски и митигация

1. **Циклические импорты**: Следовать правилам выше, тесты на import-time
2. **Регрессии в legacy**: Golden tests фиксируют поведение
3. **Coverage drop**: Добавить тесты для всех веток engine
4. **Frontend/iOS breakage**: Legacy endpoints сохраняют формат ответа

---

## Non-goals (не в этом PR)

- Изменение порогов риска (waist_risk thresholds)
- PRO/VIP features (остаются в app/routers/bmi_pro.py)
- Weekly plan integration (отдельный PR)
- Frontend/iOS changes (только backend contract)

---

## Файлы для ревью (минимальный набор)

1. `bmi_core.py` (уже есть, не меняем)
2. `core/bmi/__init__.py` (NEW)
3. `core/bmi/engine.py` (NEW)
4. `core/bmi/risk.py` (NEW)
5. `app/schemas/bmi.py` (NEW)
6. `app/routers/bmi.py` (NEW)
7. `legacy_app.py` (UPDATE - shims)

---

## Уточнения к плану (внесены по фидбеку)

### Commit 1: `calculate_waist_risk()` сигнатура

- Функция возвращает `WaistRiskResult | None`
- Если `waist_cm is None` → вернуть `None` (не `unknown`)
- `unknown` используется только если данные есть, но риск не определим

### Commit 2: `BMICalculateResult` как dataclass

- Использовать внутренний `@dataclass(frozen=True)` (не Pydantic)
- Маппинг в Pydantic происходит в Commit 3/4 (API layer)

### Commit 4: Error handling без safe_call

- 422 — Pydantic validation (автоматически)
- 400 — domain validation errors
- 500 — FastAPI default
- safe_call не используется для Free BMI (это PRO/VIP уровень)

### Commit 6: Deprecated alias вместо удаления

- В `legacy_app.py` создать deprecated alias с `warnings.warn()`
- Полное удаление — в PR-12
- Сохранить обратную совместимость для существующих импортов
