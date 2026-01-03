# PR-453 Commit 3: Add BMI Request/Response Schemas

## 🎯 Цель

Создать **Pydantic схемы** для нового endpoint `/api/v1/bmi/calculate` (FREE tier), которые определяют **API контракт** между клиентом и сервером.

**Важно**: Это **только API-слой** (Pydantic), без логики. Вся доменная логика уже в `core/bmi/engine.py` (PR-453 Commit 2).

---

## ✅ Что сделано

### 1. Создан `app/schemas/bmi.py` (NEW)

Две схемы:

- **`BMICalculateRequest`** — валидация входящих данных
- **`BMICalculateResponse`** — структура ответа API

### 2. `BMICalculateRequest` — детали

**Поля:**
- `weight_kg: float` (required, `gt=0`)
- `height_cm: float` (required, `gt=0`)
- `age: int` (required, `ge=1`, `le=120`)
- `gender: str` (default `"male"`)
- `pregnant: str | bool` (default `"no"`)
- `athlete: str | bool` (default `"no"`)
- `waist_cm: float | None` (optional, `gt=0` if provided)
- `lang: Language` (default `"en"`)

**Валидация:**
- Базовые типы и диапазоны (`gt=0`, `ge=1`, `le=120`)
- BMI bounds (10-100) **НЕ в схеме** — проверяются в engine (domain validation)
- Gender normalization **НЕ в схеме** — выполняется в engine
- Pregnant/athlete string→bool **НЕ в схеме** — конвертация в engine

### 3. `BMICalculateResponse` — детали

**Поля:**
- `bmi: float` — вычисленное значение BMI
- `category: str | None` — категория BMI (может быть `None` для pregnant/too_young/child/teen)
- `group: str` — группа пользователя (`general`, `athlete`, `elderly`, `child`, `teen`, `too_young`, `pregnant`)
- `group_display: str` — локализованное название группы
- `interpretation: str` — локализованная интерпретация BMI
- `wht_ratio: float | None` — Waist-to-Height Ratio (если `waist_cm` был предоставлен)
- `waist_risk: dict[str, Any] | None` — результат оценки риска по талии (сериализованный `WaistRiskResult`)
- `notes: list[str]` — агрегированные заметки (из `waist_risk.notes`)
- `age_band: Literal["too_young", "child", "teen", "adult", "elderly"]` — возрастная группа для UI

**Важно:**
- `category=None` — **валидно** для беременных и детей/подростков (медицинский дисклеймер)
- `waist_risk` — сериализованный dataclass (`WaistRiskResult.model_dump()`)
- `notes` — всегда `list[str]` (даже если пустой)

### 4. Тесты: `tests/test_bmi_schemas.py` (NEW)

Покрывает:
- ✅ Schema validation (422 cases): отрицательные значения, возраст вне диапазона
- ✅ Default values: проверка дефолтных значений
- ✅ Language validation: только `ru`/`en`/`es`
- ✅ Response structure: структура ответа (golden tests)
- ✅ Category None: валидность `category=None` для беременных/детей

---

## 🚫 Что намеренно НЕ сделано

- ❌ Логика расчета BMI (в engine)
- ❌ Валидация BMI bounds в схеме (в engine)
- ❌ Нормализация gender/pregnant/athlete в схеме (в engine)
- ❌ API endpoint (Commit 4)
- ❌ Legacy wiring (Commit 5)

---

## 🔗 Связь с другими коммитами

### Commit 2 (engine) → Commit 3 (schemas)
- Engine возвращает `BMICalculateResult` (dataclass)
- Schemas определяют API контракт (Pydantic)
- Маппинг происходит в Commit 4 (endpoint)

### Commit 3 (schemas) → Commit 4 (endpoint)
- Endpoint использует `BMICalculateRequest` для валидации
- Endpoint возвращает `BMICalculateResponse` для сериализации JSON

---

## 📊 Отличия от существующих схем

| Схема | Высота | Gender | Waist | Premium | Chart |
|-------|--------|--------|-------|---------|-------|
| `BMIRequest` (legacy) | `height_m` | `gender` | Optional | ✅ | ✅ |
| `BMIRequestV1` (legacy) | `height_cm` | `gender` | Optional | ❌ | ❌ |
| `BMIProRequest` (PRO) | `height_cm` | `sex` (Literal) | **Required** | ❌ | ❌ |
| **`BMICalculateRequest` (NEW)** | `height_cm` | `gender` | Optional | ❌ | ❌ |

---

## 🧪 Test Matrix

### Request Validation (422 cases)

| Case | Input | Expected |
|------|-------|----------|
| Valid | `weight_kg=70, height_cm=175, age=30` | ✅ |
| Negative weight | `weight_kg=-10` | ❌ ValidationError |
| Zero height | `height_cm=0` | ❌ ValidationError |
| Age < 1 | `age=0` | ❌ ValidationError |
| Age > 120 | `age=121` | ❌ ValidationError |
| Negative waist | `waist_cm=-10` | ❌ ValidationError |
| None waist | `waist_cm=None` | ✅ (optional) |

### Response Structure

| Case | `category` | `waist_risk` | `notes` |
|------|------------|-------------|---------|
| Adult normal | `"normal"` | `None` | `[]` |
| Pregnant | `None` | `None` | `[]` |
| Child | `None` | `None` | `[]` |
| With waist risk | `"overweight"` | `{...}` | `["Increased waist-related risk"]` |

---

## ✅ Checklist

- [x] Создан `app/schemas/bmi.py`
- [x] `BMICalculateRequest` со всеми полями и валидацией
- [x] `BMICalculateResponse` со всеми полями и описаниями
- [x] Создан `tests/test_bmi_schemas.py`
- [x] Тесты покрывают: validation, defaults, language, response structure, category=None
- [x] Импорты корректны (нет циклических зависимостей)
- [x] Документация в docstrings на RU/EN

---

## 📝 Commit Message

```
feat(api): add BMI request/response schemas

- Create app/schemas/bmi.py with BMICalculateRequest/Response
- Request: weight_kg, height_cm, age, gender, pregnant, athlete, waist_cm, lang
- Response: bmi, category, group, group_display, interpretation, wht_ratio, waist_risk, notes, age_band
- Validation: basic type/range checks (BMI bounds validated in engine)
- Support category=None for pregnant/too_young/child/teen (medical disclaimer)
- Add comprehensive schema validation tests
```

---

## 🔜 Следующий PR

**Commit 4 — BMI Calculate Endpoint**

- `app/routers/bmi.py` (NEW)
- `POST /api/v1/bmi/calculate`
- Использует `BMICalculateRequest` / `BMICalculateResponse`
- Вызывает `core/bmi/engine.calculate_bmi_result()`

