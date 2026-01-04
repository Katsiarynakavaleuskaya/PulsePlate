# PR-453: BMI Calculate Schemas (API Contract)

## 🎯 Цель

Добавить **Pydantic-схемы** для нового public endpoint `/api/v1/bmi/calculate` (FREE tier). Это **только API-контракт**: валидация входа и форма ответа. Доменная логика остаётся в `core/bmi/engine.py` (будет в следующем PR).

## ✅ Что сделано

- ✅ `app/schemas/bmi.py` (NEW)
  - `BMICalculateRequest` — валидация входящих данных
  - `BMICalculateResponse` — структура ответа API
- ✅ `tests/test_bmi_schemas.py` (NEW)
  - 26 тестов: validation (422), defaults, lang RU/EN/ES, response structure, `category=None`
- ✅ `PR_453_COMMIT_3_SCHEMAS.md` — описание коммита/контракта

## 🔒 Инварианты

- **BMI bounds (10..100)** — НЕ в схеме; это **domain validation** в engine
- **Никакой логики в схемах**: нормализация `gender/pregnant/athlete` происходит в engine/endpoint mapping
- `category=None` — валидно для `pregnant/too_young/child/teen` (дисклеймер, не ошибка)
- `waist_risk` — **dict[str, Any] | None** (сериализация dataclass в endpoint), не Pydantic модель

## 📝 Детали

### BMICalculateRequest
- Поля: `weight_kg`, `height_cm`, `age`, `gender`, `pregnant`, `athlete`, `waist_cm`, `lang`
- Валидация: базовые типы (`gt=0`, `ge=1`, `le=120`)
- Дефолты: `gender="male"`, `pregnant="no"`, `athlete="no"`, `lang="en"`

### BMICalculateResponse
- Поля: `bmi`, `category` (может быть `None`), `group`, `group_display`, `interpretation`, `wht_ratio`, `waist_risk`, `notes`, `age_band`
- `category=None` — валидно для беременных/детей/подростков (медицинский дисклеймер)
- `waist_risk` — сериализованный `WaistRiskResult` (dict)

## 🧪 Тесты

- ✅ Schema validation (422 cases): отрицательные значения, возраст вне диапазона
- ✅ Default values: проверка дефолтных значений
- ✅ Language validation: только `ru`/`en`/`es`
- ✅ Response structure: структура ответа (golden tests)
- ✅ Category None: валидность `category=None` для беременных/детей

## ✅ Checklist

- [x] Создан `app/schemas/bmi.py`
- [x] `BMICalculateRequest` со всеми полями и валидацией
- [x] `BMICalculateResponse` со всеми полями и описаниями
- [x] Создан `tests/test_bmi_schemas.py`
- [x] Тесты покрывают: validation, defaults, language, response structure, category=None
- [x] `ruff check` и `ruff format` проходят
- [x] `pytest tests/test_bmi_schemas.py` проходит (26/26)
- [x] Импорты корректны (нет циклических зависимостей)
- [x] Документация в docstrings на RU/EN

## 🔜 Следующий PR

**PR-454: BMI Calculate Endpoint**
- `app/routers/bmi.py` (NEW)
- `POST /api/v1/bmi/calculate`
- Использует `BMICalculateRequest` / `BMICalculateResponse`
- Вызывает `core/bmi/engine.calculate_bmi_result()`

## 📊 Отличия от существующих схем

| Схема | Высота | Gender | Waist | Premium | Chart |
|-------|--------|--------|-------|---------|-------|
| `BMIRequest` (legacy) | `height_m` | `gender` | Optional | ✅ | ✅ |
| `BMIRequestV1` (legacy) | `height_cm` | `gender` | Optional | ❌ | ❌ |
| `BMIProRequest` (PRO) | `height_cm` | `sex` (Literal) | **Required** | ❌ | ❌ |
| **`BMICalculateRequest` (NEW)** | `height_cm` | `gender` | Optional | ❌ | ❌ |
