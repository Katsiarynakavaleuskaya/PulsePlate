# PR-453 Commit 4: Add POST /api/v1/bmi/calculate Endpoint

## 🎯 Цель

Создать **тонкий API endpoint** `/api/v1/bmi/calculate` (FREE tier), который:
- Принимает `BMICalculateRequest` (Pydantic валидация)
- Вызывает `core/bmi/engine.calculate_bmi_result()` (доменная логика)
- Возвращает `BMICalculateResponse` (сериализация)

**Важно**: Endpoint — **только адаптер**, никакой бизнес-логики.

---

## ✅ Что сделано

### 1. `app/routers/bmi.py` (NEW)

**Endpoint**: `POST /api/v1/bmi/calculate`

**Функциональность:**
- Валидация входа через `BMICalculateRequest` (Pydantic)
- Нормализация `pregnant`/`athlete` (string → bool)
- Вызов `calculate_bmi_result()` из engine
- Маппинг `BMICalculateResult` → `BMICalculateResponse`
- Сериализация `WaistRiskResult` (dataclass → dict)
- Error handling: 422 (Pydantic), 400 (ValueError), 500 (FastAPI default)

**Регистрация:**
- Router регистрируется в `legacy_app.py` рядом с `bmi_pro_router`

### 2. `tests/test_bmi_calculate_endpoint.py` (NEW)

**Покрытие:**
- ✅ Успешные запросы (все группы, языки RU/EN/ES)
- ✅ С `waist_cm` и без
- ✅ `category=None` для pregnant/too_young/child/teen
- ✅ Error cases: 422 (invalid input), 400 (domain validation)
- ✅ Сериализация `waist_risk` (dict с tuple → list)

---

## 🔒 Инварианты

### 1. **Тонкий адаптер**
- Endpoint **не содержит** бизнес-логики
- Вся логика в `core/bmi/engine.py`
- Endpoint только: валидация → вызов engine → маппинг → сериализация

### 2. **Error handling (Free tier)**
- **422** — Pydantic validation (автоматически)
- **400** — domain validation errors (`ValueError` → `HTTPException(400)`)
- **500** — FastAPI default (не используем `safe_call` для Free BMI)

**Важно**: `safe_call` используется только для PRO/VIP endpoints, не для Free.

### 3. **Сериализация `waist_risk`**
- `WaistRiskResult` — dataclass (не Pydantic)
- Сериализация через `dataclasses.asdict()`
- `notes: tuple[str, ...]` → `list[str]` для JSON

### 4. **Нормализация флагов**
- `pregnant: str | bool` → `bool` (в endpoint, перед вызовом engine)
- `athlete: str | bool` → `bool` (в endpoint, перед вызовом engine)
- Engine принимает уже нормализованные `bool`

---

## 📝 Детали реализации

### Нормализация `pregnant`/`athlete`

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

### Маппинг engine → response

```python
result = calculate_bmi_result(...)  # BMICalculateResult (dataclass)

# Сериализация waist_risk
waist_risk_dict = None
if result.waist_risk:
    waist_risk_dict = dataclasses.asdict(result.waist_risk)
    # Convert tuple to list for JSON
    waist_risk_dict["notes"] = list(waist_risk_dict["notes"])

return BMICalculateResponse(
    bmi=result.bmi,
    category=result.category,  # Already str | None
    group=result.group,
    group_display=result.group_display,
    interpretation=result.interpretation,
    wht_ratio=result.wht_ratio,
    waist_risk=waist_risk_dict,
    notes=list(result.notes),  # Ensure list[str]
    age_band=result.age_band,
)
```

---

## 🧪 Test Matrix

### Успешные запросы

| Case | Input | Expected Response |
|------|-------|------------------|
| Adult normal | `age=30, bmi=22.5` | `category="normal"`, `age_band="adult"` |
| Pregnant | `age=28, pregnant=True` | `category=None`, `group="pregnant"` |
| Child | `age=13` | `category=None`, `age_band="child"` |
| Teen | `age=16` | `category=None`, `age_band="teen"` |
| With waist | `waist_cm=90` | `wht_ratio` calculated, `waist_risk` present |
| Without waist | `waist_cm=None` | `wht_ratio=None`, `waist_risk=None` |

### Error cases

| Case | Input | Expected Status |
|------|-------|----------------|
| Invalid weight | `weight_kg=-10` | 422 (Pydantic) |
| Invalid age | `age=0` | 422 (Pydantic) |
| BMI < 10 | `weight_kg=10, height_cm=200` | 400 (ValueError) |
| BMI > 100 | `weight_kg=200, height_cm=100` | 400 (ValueError) |

---

## ✅ Checklist

- [x] Создан `app/routers/bmi.py`
- [x] Endpoint `POST /api/v1/bmi/calculate` реализован
- [x] Нормализация `pregnant`/`athlete` (string → bool)
- [x] Маппинг `BMICalculateResult` → `BMICalculateResponse`
- [x] Сериализация `waist_risk` (dataclass → dict, tuple → list)
- [x] Error handling: 422, 400, 500
- [x] Router зарегистрирован в `legacy_app.py`
- [x] Создан `tests/test_bmi_calculate_endpoint.py`
- [x] Тесты покрывают: успешные запросы, error cases, сериализацию
- [x] `ruff check` и `ruff format` проходят
- [x] `pytest` проходит

---

## 📝 Commit Message

```
feat(api): add POST /api/v1/bmi/calculate endpoint

- Create app/routers/bmi.py with calculate endpoint
- Uses core/bmi/engine.calculate_bmi_result() for domain logic
- Returns BMICalculateResponse with unified contract
- Normalize pregnant/athlete flags (string → bool)
- Serialize WaistRiskResult (dataclass → dict, tuple → list)
- Error handling: 422 (Pydantic), 400 (ValueError), 500 (default)
- No API key required (FREE tier)
- Add comprehensive endpoint tests
```

---

## 🔜 Следующий PR

**Commit 5 — Legacy Endpoints as Shims**

- Рефакторинг `legacy_app.py` endpoints (`bmi_endpoint`, `bmi_endpoint_v1`, `bmi_calculate_legacy`)
- Использование `calculate_bmi_result()` вместо локальных вычислений
- Сохранение формата ответа для обратной совместимости

