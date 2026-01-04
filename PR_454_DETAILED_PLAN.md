# PR-454: BMI Calculate Endpoint (Commit 4)

## 🎯 Цель PR

Создать **тонкий API endpoint** `POST /api/v1/bmi/calculate` (FREE tier), который:
- Принимает `BMICalculateRequest` (Pydantic валидация)
- Вызывает `core/bmi/engine.calculate_bmi_result()` (доменная логика)
- Возвращает `BMICalculateResponse` (сериализация)

**Важно**: Endpoint — **только адаптер**, никакой бизнес-логики.

---

## ✅ Что УЖЕ ЕСТЬ в проекте

### 1. **`app/routers/bmi.py`** ✅ СОЗДАН
- **Статус**: Файл существует, endpoint реализован
- **Endpoint**: `POST /api/v1/bmi/calculate`
- **Функциональность**:
  - ✅ Валидация входа через `BMICalculateRequest` (Pydantic)
  - ✅ Нормализация `pregnant`/`athlete` (string → bool) через `_normalize_bool_flag()`
  - ✅ Вызов `calculate_bmi_result()` из engine
  - ✅ Маппинг `BMICalculateResult` → `BMICalculateResponse`
  - ✅ Сериализация `WaistRiskResult` (dataclass → `WaistRiskResultSchema`)
  - ✅ Error handling: 422 (Pydantic), 400 (ValueError), 500 (default), 501 (engine not available)

**Проблема**: Router **НЕ зарегистрирован** в `legacy_app.py`

### 2. **`core/bmi/engine.py`** ✅ СОЗДАН (STUB)
- **Статус**: Файл существует, но это заглушка
- **Содержимое**:
  - ✅ `BMICalculateResult` dataclass (правильные типы)
  - ✅ `calculate_bmi_result()` функция (выбрасывает `NotImplementedError`)
  - ✅ Правильные типы для всех параметров

**Проблема**: Engine **не реализован** (будет в PR-453 Commit 2 или отдельном PR)

### 3. **`app/schemas/bmi.py`** ✅ СОЗДАН (из PR-453)
- **Статус**: Полностью реализован в PR-453
- **Содержимое**:
  - ✅ `BMICalculateRequest` (8 полей, валидация)
  - ✅ `BMICalculateResponse` (9 полей, описания)
  - ✅ `WaistRiskResultSchema` (строгая типизация)

### 4. **`tests/test_bmi_schemas.py`** ✅ СОЗДАН (из PR-453)
- **Статус**: 27 тестов, все проходят
- **Покрытие**: Схемы, валидация, edge cases

### 5. **`core/bmi/risk.py`** ✅ СОЗДАН (из PR-452)
- **Статус**: Полностью реализован
- **Содержимое**:
  - ✅ `WaistRiskResult` dataclass
  - ✅ `calculate_waist_risk()` функция

---

## ❌ Что НУЖНО СДЕЛАТЬ

### 1. **Превратить legacy endpoint в shim** 🔴 КРИТИЧНО

**Проблема:**
- В `legacy_app.py:2195` уже есть `@app.post("/api/v1/bmi/calculate")` который регистрируется при загрузке модуля
- Просто "зарегистрировать router перед legacy" **не работает** — FastAPI может использовать legacy endpoint первым
- Нужно **устранить конфликт маршрута** детерминированно

**Решение (Shim Pattern):**
1. **Оставить legacy endpoint** на месте (не удаляем, чтобы не ломать клиентов)
2. **Превратить его в thin-proxy** — внутри вызывать новый handler из `app/routers/bmi.py`
3. **Добавить `bmi_calculate_handler()`** в `app/routers/bmi.py` — вынести логику endpoint в отдельную функцию
4. **Зарегистрировать router** (для структуры проекта, но shim будет работать и без этого)

**Патч для `legacy_app.py`:**
```python
# Строка 2195-2198: заменить на shim
@app.post("/api/v1/bmi/calculate")
async def bmi_calculate_legacy(req: BMIRequestV1) -> Dict[str, Any]:
    """
    RU: Shim endpoint. Исторически этот путь жил в legacy_app.py.
    Теперь это тонкий прокси в новый Free BMI handler (app/routers/bmi.py),
    чтобы не было двух реализаций и чтобы API/клиенты не расходились.

    EN: Shim endpoint. This path historically lived in legacy_app.py.
    Now it is a thin proxy to the new Free BMI handler (app/routers/bmi.py)
    to avoid duplicate implementations and client divergence.
    """
    # Local import to avoid import cycles on app startup.
    from app.routers.bmi import bmi_calculate_handler  # type: ignore

    # Delegate to the canonical Free BMI handler.
    # Keep request/response shape stable for clients.
    return await bmi_calculate_handler(req)
```

**Патч для `app/routers/bmi.py`:**
- Вынести логику из `calculate_bmi()` в `bmi_calculate_handler(req: Any) -> dict[str, Any]`
- `calculate_bmi()` вызывает `bmi_calculate_handler()` и возвращает `BMICalculateResponse`
- `bmi_calculate_handler()` принимает `BMIRequestV1` или `BMICalculateRequest`, конвертирует и возвращает `dict`

**Регистрация router (опционально, для структуры):**
```python
# После строки 5425 (после bmi_pro_router)
from app.routers.bmi import router as bmi_router
app.include_router(bmi_router)
```

**Примечание**: Router можно зарегистрировать, но shim будет работать и без этого (legacy endpoint уже зарегистрирован).

### 2. **Создать `tests/test_bmi_calculate_endpoint.py`** 🔴 КРИТИЧНО

**Требования:**
- Тесты для endpoint (не схем)
- Покрытие всех сценариев из плана

**Test Matrix:**

#### Успешные запросы:
- ✅ Adult normal (`age=30, bmi=22.5`) → `category="normal"`, `age_band="adult"`
- ✅ Pregnant (`age=28, pregnant=True`) → `category=None`, `group="pregnant"`
- ✅ Child (`age=13`) → `category=None`, `age_band="child"`
- ✅ Teen (`age=16`) → `category=None`, `age_band="teen"`
- ✅ With waist (`waist_cm=90`) → `wht_ratio` calculated, `waist_risk` present
- ✅ Without waist (`waist_cm=None`) → `wht_ratio=None`, `waist_risk=None`
- ✅ Все языки (RU/EN/ES)

#### Error cases:
- ✅ Invalid weight (`weight_kg=-10`) → 422 (Pydantic)
- ✅ Invalid age (`age=0`) → 422 (Pydantic)
- ✅ BMI < 10 → 400 (ValueError from engine)
- ✅ BMI > 100 → 400 (ValueError from engine)
- ✅ Engine not available → 501 (NotImplementedError)

**Проблема**: Engine пока stub, поэтому тесты будут падать на `NotImplementedError`

**Решение**: 
- Вариант A: Мокировать `calculate_bmi_result` в тестах
- Вариант B: Оставить тесты, но пометить как `@pytest.mark.skip` до реализации engine
- **Рекомендация**: Вариант A (мокировать)

### 3. **Обновить `core/bmi/__init__.py`** 🟡 ОПЦИОНАЛЬНО

**Текущее состояние:**
```python
from core.bmi.risk import WaistRiskResult, calculate_waist_risk
__all__ = ["WaistRiskResult", "calculate_waist_risk"]
```

**Нужно добавить:**
```python
from core.bmi.engine import BMICalculateResult, calculate_bmi_result, AgeBand
__all__ = [
    "WaistRiskResult", 
    "calculate_waist_risk",
    "BMICalculateResult",
    "calculate_bmi_result",
    "AgeBand",
]
```

**Примечание**: Это можно сделать позже, когда engine будет реализован.

---

## 🔒 Инварианты (должны соблюдаться)

### 1. **Тонкий адаптер**
- Endpoint **не содержит** бизнес-логики
- Вся логика в `core/bmi/engine.py`
- Endpoint только: валидация → вызов engine → маппинг → сериализация

### 2. **Error handling (Free tier)**
- **422** — Pydantic validation (автоматически)
- **400** — domain validation errors (`ValueError` → `HTTPException(400)`)
- **500** — FastAPI default (не используем `safe_call` для Free BMI)
- **501** — engine not available (`NotImplementedError`)

**Важно**: `safe_call` используется только для PRO/VIP endpoints, не для Free.

### 3. **Сериализация `waist_risk`**
- `WaistRiskResult` — dataclass (не Pydantic)
- Сериализация через `WaistRiskResultSchema` (Pydantic model)
- `notes: tuple[str, ...]` → сохраняется как tuple (Pydantic автоматически сериализует)

### 4. **Нормализация флагов**
- `pregnant: str | bool` → `bool` (в endpoint, перед вызовом engine)
- `athlete: str | bool` → `bool` (в endpoint, перед вызовом engine)
- Engine принимает уже нормализованные `bool`

### 5. **Shim Pattern для legacy endpoint**
- В `legacy_app.py:2195` есть `@app.post("/api/v1/bmi/calculate")`
- **Решение**: Превратить legacy endpoint в shim, который делегирует в новый handler
- **Преимущества**:
  - Нет конфликта маршрутов (один endpoint, одна реализация)
  - Клиенты не ломаются (путь остаётся тот же)
  - Legacy реально становится thin-proxy уже сейчас
  - PR-455 упрощается (не нужно мигрировать клиентов)

---

## 📝 Детали реализации

### Нормализация `pregnant`/`athlete` ✅ УЖЕ РЕАЛИЗОВАНО

```python
def _normalize_bool_flag(value: str | bool) -> bool:
    """Convert string/bool to bool (fail-soft)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        return s in {"yes", "y", "да", "true", "1"}
    return False
```

### Маппинг engine → response ✅ УЖЕ РЕАЛИЗОВАНО

```python
result = calculate_bmi_result(...)  # BMICalculateResult (dataclass)

# Сериализация waist_risk
waist_risk_schema = None
if result.waist_risk:
    waist_risk_schema = WaistRiskResultSchema(
        wht_ratio=result.waist_risk.wht_ratio,
        risk_level=result.waist_risk.risk_level,
        notes=result.waist_risk.notes,
    )

return BMICalculateResponse(
    bmi=result.bmi,
    category=result.category,  # Already str | None
    group=result.group,
    group_display=result.group_display,
    interpretation=result.interpretation,
    wht_ratio=result.wht_ratio,
    waist_risk=waist_risk_schema,
    notes=list(result.notes),  # Ensure list[str]
    age_band=result.age_band,
)
```

---

## 🧪 Test Matrix (детально)

### Успешные запросы

| Case | Input | Expected Response |
|------|-------|------------------|
| Adult normal | `age=30, weight_kg=70, height_cm=175` | `category="normal"`, `age_band="adult"`, `group="general"` |
| Adult overweight | `age=30, weight_kg=90, height_cm=175` | `category="overweight"`, `age_band="adult"` |
| Pregnant | `age=28, pregnant=True` | `category=None`, `group="pregnant"`, `age_band="adult"` |
| Child | `age=13` | `category=None`, `age_band="child"`, `group="child"` |
| Teen | `age=16` | `category=None`, `age_band="teen"`, `group="child"` |
| Elderly | `age=65` | `category="normal"`, `age_band="elderly"`, `group="elderly"` |
| Athlete | `age=30, athlete=True` | `group="athlete"` |
| With waist | `waist_cm=90, height_cm=175` | `wht_ratio=0.514`, `waist_risk` present |
| Without waist | `waist_cm=None` | `wht_ratio=None`, `waist_risk=None` |
| Language RU | `lang="ru"` | Все тексты на русском |
| Language EN | `lang="en"` | Все тексты на английском |
| Language ES | `lang="es"` | Все тексты на испанском |

### Error cases

| Case | Input | Expected Status | Expected Detail |
|------|-------|----------------|-----------------|
| Invalid weight | `weight_kg=-10` | 422 | Pydantic validation error |
| Invalid height | `height_cm=0` | 422 | Pydantic validation error |
| Invalid age | `age=0` | 422 | Pydantic validation error |
| BMI < 10 | `weight_kg=10, height_cm=200` | 400 | Domain validation error |
| BMI > 100 | `weight_kg=200, height_cm=100` | 400 | Domain validation error |
| Engine not available | (mock engine=None) | 501 | "BMI engine is not available" |

---

## ✅ Checklist реализации

### Код
- [x] `app/routers/bmi.py` создан и реализован
- [ ] Добавлен `bmi_calculate_handler()` в `app/routers/bmi.py`
- [ ] Legacy endpoint превращён в shim (вызывает `bmi_calculate_handler`)
- [ ] Router зарегистрирован в `legacy_app.py` (опционально, для структуры)
- [x] Нормализация `pregnant`/`athlete` реализована
- [x] Маппинг `BMICalculateResult` → `BMICalculateResponse` реализован
- [x] Сериализация `waist_risk` реализована
- [x] Error handling реализован

### Тесты
- [ ] `tests/test_bmi_calculate_endpoint.py` создан
- [ ] Тесты для успешных запросов (все группы, языки)
- [ ] Тесты для error cases (422, 400, 501)
- [ ] Тесты для сериализации `waist_risk`
- [ ] Тесты для shim (legacy endpoint вызывает handler)
- [ ] Моки для `calculate_bmi_result` (пока engine stub)

### Документация
- [ ] `PR_454_DETAILED_PLAN.md` создан (этот файл)
- [ ] Commit message готов

### Проверки
- [ ] `ruff check` проходит
- [ ] `ruff format` проходит
- [ ] `pytest` проходит (с моками)
- [ ] `mypy` проходит (если включен)

---

## 📝 Commit Message

```
feat(api): add POST /api/v1/bmi/calculate endpoint (shim pattern)

- Add bmi_calculate_handler() in app/routers/bmi.py (reusable handler)
- Convert legacy endpoint to shim (delegates to new handler)
- Endpoint uses core/bmi/engine.calculate_bmi_result() for domain logic
- Returns BMICalculateResponse with unified contract
- Normalize pregnant/athlete flags (string → bool)
- Serialize WaistRiskResult via WaistRiskResultSchema
- Error handling: 422 (Pydantic), 400 (ValueError), 500 (default), 501 (engine unavailable)
- Add comprehensive endpoint tests with mocks
- Register BMI router in legacy_app.py (FREE tier, no API key)
- Shim pattern eliminates route conflict deterministically
```

---

## 🔜 Следующий PR

**PR-455: Legacy Endpoints as Shims**

- Рефакторинг `legacy_app.py` endpoints (`bmi_endpoint`, `bmi_endpoint_v1`, `bmi_calculate_legacy`)
- Использование `calculate_bmi_result()` вместо локальных вычислений
- Сохранение формата ответа для обратной совместимости
- Удаление legacy endpoint `/api/v1/bmi/calculate` после миграции

---

## ⚠️ Известные проблемы

### 1. Engine пока stub
- `calculate_bmi_result()` выбрасывает `NotImplementedError`
- **Решение**: Использовать моки в тестах
- **После**: Когда engine будет реализован, убрать моки

### 2. Конфликт с legacy endpoint (решён через shim)
- В `legacy_app.py:2195` есть `@app.post("/api/v1/bmi/calculate")`
- **Решение**: Превратить legacy endpoint в shim (вызывает новый handler)
- **Преимущества**: Нет конфликта маршрутов, клиенты не ломаются, детерминированно
- **После PR-455**: Можно удалить legacy endpoint, если все клиенты мигрированы

### 3. Документация
- Много markdown файлов в корне проекта
- **Рекомендация**: Включить только `PR_454_DETAILED_PLAN.md` в PR
- Остальные документы оставить локально или заархивировать

---

## 📊 Статистика

| Метрика | Значение |
|---------|----------|
| Новых файлов | 1 (`tests/test_bmi_calculate_endpoint.py`) |
| Изменённых файлов | 2 (`legacy_app.py`, возможно `core/bmi/__init__.py`) |
| Строк кода | ~200-300 (тесты) |
| Тестов | ~15-20 |
| Покрытие | 100% endpoint логики |

