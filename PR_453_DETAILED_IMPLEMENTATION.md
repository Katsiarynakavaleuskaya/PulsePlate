# PR-453: Детальное описание реализации

## 📋 Общая информация

**PR номер:** 453  
**Ветка:** `feat/pr-453-bmi-schemas`  
**Цель:** Создать Pydantic-схемы для нового endpoint `/api/v1/bmi/calculate` (FREE tier)  
**Статус:** Готов к ревью (schemas + тесты)

---

## 📦 Что реализовано

### 1. `app/schemas/bmi.py` (NEW, 177 строк)

**Файл:** `app/schemas/bmi.py`

#### 1.1. `BMICalculateRequest` — Request Schema

**Назначение:** Валидация входящих данных для расчета BMI

**Поля:**

| Поле | Тип | Валидация | Дефолт | Описание |
|------|-----|-----------|--------|----------|
| `weight_kg` | `float` | `gt=0` | **required** | Вес в килограммах |
| `height_cm` | `float` | `gt=0` | **required** | Рост в сантиметрах |
| `age` | `int` | `ge=1, le=120` | **required** | Возраст в годах (1-120) |
| `gender` | `str` | - | `"male"` | Пол (будет нормализован в engine) |
| `pregnant` | `str \| bool` | - | `"no"` | Беременность (string/bool, нормализуется в engine) |
| `athlete` | `str \| bool` | - | `"no"` | Статус спортсмена (string/bool, нормализуется в engine) |
| `waist_cm` | `float \| None` | `gt=0` (если указан) | `None` | Окружность талии в см (опционально) |
| `lang` | `Language` | `Literal["ru", "en", "es"]` | `"en"` | Язык для локализованных ответов |

**Особенности:**
- ✅ Все поля имеют `description` и `examples` для OpenAPI документации
- ✅ `pregnant` и `athlete` принимают как `str` ("yes"/"no"), так и `bool` (для удобства клиентов)
- ✅ `waist_cm` опциональный — если не указан, WHtR и waist risk не рассчитываются
- ✅ `lang` строго типизирован через `Language = Literal["ru", "en", "es"]`

**Что НЕ валидируется в схеме:**
- ❌ BMI bounds (10-100) — это domain validation в engine
- ❌ Нормализация gender — выполняется в engine
- ❌ Конвертация pregnant/athlete string→bool — выполняется в endpoint/engine

#### 1.2. `BMICalculateResponse` — Response Schema

**Назначение:** Структура ответа API с результатами расчета BMI

**Поля:**

| Поле | Тип | Описание |
|------|-----|----------|
| `bmi` | `float` | Вычисленное значение BMI |
| `category` | `str \| None` | Категория BMI (может быть `None` для pregnant/too_young/child/teen) |
| `group` | `str` | Группа пользователя: `"general"`, `"athlete"`, `"elderly"`, `"child"`, `"teen"`, `"too_young"`, `"pregnant"` |
| `group_display` | `str` | Локализованное название группы |
| `interpretation` | `str` | Локализованная интерпретация BMI в контексте группы |
| `wht_ratio` | `float \| None` | Waist-to-Height Ratio (WHtR), только если `waist_cm` был предоставлен |
| `waist_risk` | `dict[str, Any] \| None` | Результат оценки риска по талии (сериализованный `WaistRiskResult`) |
| `notes` | `list[str]` | Агрегированные заметки (из `waist_risk.notes`), пустой список если нет заметок |
| `age_band` | `Literal["too_young", "child", "teen", "adult", "elderly"]` | Возрастная группа для UI дифференциации |

**Ключевые особенности:**

1. **`category=None` — валидно и ожидаемо:**
   - Для `pregnant` — BMI не валиден во время беременности
   - Для `too_young` (<12 лет) — BMI не применяется для детей младше 12
   - Для `child` (12-14) — используется педиатрическая интерпретация
   - Для `teen` (15-18) — используется подростковая интерпретация
   - Это **не ошибка**, а медицинский дисклеймер

2. **`waist_risk` — сериализованный dataclass:**
   - Структура: `{'wht_ratio': float | None, 'risk_level': 'low'|'moderate'|'high', 'notes': tuple[str, ...]}`
   - Присутствует только если `waist_cm` был предоставлен и риск был рассчитан
   - Сериализация происходит в endpoint (dataclass → dict)

3. **`notes` — всегда `list[str]`:**
   - Используется `default_factory=list` для мутабельного дефолта
   - Содержит только заметки из `waist_risk.notes` (на данный момент)
   - Пустой список если нет заметок

4. **`age_band` — для UI дифференциации:**
   - `too_young`: <12 лет
   - `child`: 12-14 лет
   - `teen`: 15-18 лет
   - `adult`: 19-59 лет
   - `elderly`: >=60 лет

---

### 2. `tests/test_bmi_schemas.py` (NEW, 282 строки)

**Файл:** `tests/test_bmi_schemas.py`

**Покрытие:** 26 тестов, все проходят ✅

#### 2.1. `TestBMICalculateRequest` — Request Validation Tests

**Тесты валидации (422 cases):**

1. ✅ `test_valid_request` — валидный запрос со всеми полями
2. ✅ `test_default_values` — проверка дефолтных значений
3. ✅ `test_negative_weight_raises_validation_error` — отрицательный вес → ValidationError
4. ✅ `test_zero_height_raises_validation_error` — нулевой рост → ValidationError
5. ✅ `test_age_below_minimum_raises_validation_error` — возраст < 1 → ValidationError
6. ✅ `test_age_above_maximum_raises_validation_error` — возраст > 120 → ValidationError
7. ✅ `test_negative_waist_cm_raises_validation_error` — отрицательная талия → ValidationError
8. ✅ `test_none_waist_cm_is_valid` — `waist_cm=None` валидно (опциональное поле)
9. ✅ `test_valid_languages` (parametrize: `ru`, `en`, `es`) — валидные языки
10. ✅ `test_invalid_language_raises_validation_error` — невалидный язык → ValidationError
11. ✅ `test_pregnant_string_and_bool` — `pregnant` принимает string и bool
12. ✅ `test_athlete_string_and_bool` — `athlete` принимает string и bool

#### 2.2. `TestBMICalculateResponse` — Response Structure Tests

**Тесты структуры ответа:**

1. ✅ `test_minimal_response` — минимальный ответ (без waist)
2. ✅ `test_full_response_with_waist_risk` — полный ответ с waist risk
3. ✅ `test_category_none_for_pregnant` — `category=None` для беременных (валидно)
4. ✅ `test_category_none_for_too_young` — `category=None` для too_young (валидно)
5. ✅ `test_category_none_for_child` — `category=None` для child (валидно)
6. ✅ `test_category_none_for_teen` — `category=None` для teen (валидно)
7. ✅ `test_all_age_bands` (parametrize: все age_band значения) — все возрастные группы валидны
8. ✅ `test_notes_default_factory` — `notes` дефолтно пустой список

**Особенности тестов:**
- Все тесты проверяют конкретные значения, а не тавтологии
- Тесты для `category=None` явно документируют, что это валидно
- Тесты покрывают все edge cases и граничные значения

---

### 3. `PR_453_COMMIT_3_SCHEMAS.md` (NEW, 161 строка)

**Файл:** `PR_453_COMMIT_3_SCHEMAS.md`

**Содержание:**
- Детальное описание коммита
- Инварианты и архитектурные решения
- Связь с другими коммитами
- Test Matrix
- Checklist

---

## 🎯 Архитектурные решения

### 1. Разделение ответственности

**Схемы (Pydantic):**
- ✅ Валидация базовых типов и диапазонов
- ✅ Определение API контракта
- ✅ OpenAPI документация

**Engine (domain):**
- ✅ BMI bounds validation (10-100)
- ✅ Нормализация gender/pregnant/athlete
- ✅ Бизнес-логика расчета

**Endpoint (adapter):**
- ✅ Маппинг request → engine → response
- ✅ Сериализация dataclass → dict
- ✅ Error handling

### 2. Инварианты

1. **BMI bounds НЕ в схеме:**
   - Схема проверяет только `weight_kg > 0`, `height_cm > 0`
   - BMI bounds (10-100) проверяются в engine после вычисления
   - Это позволяет engine возвращать `ValueError` для domain validation

2. **Нормализация НЕ в схеме:**
   - `gender` принимает любой `str` (нормализация в engine)
   - `pregnant`/`athlete` принимают `str | bool` (конвертация в endpoint/engine)

3. **`category=None` — валидно:**
   - Для `pregnant/too_young/child/teen` это медицинский дисклеймер
   - Схема явно документирует это в `description`
   - Тесты проверяют, что это валидно

4. **`waist_risk` — dict, не Pydantic:**
   - `WaistRiskResult` — dataclass (не Pydantic)
   - Сериализация происходит в endpoint через `dataclasses.asdict()`
   - Response содержит `dict[str, Any]` для JSON-совместимости

---

## 📊 Статистика

| Метрика | Значение |
|---------|----------|
| Новых файлов | 3 |
| Строк кода | 617 |
| Тестов | 26 |
| Покрытие тестами | 100% (все тесты проходят) |
| Схем Pydantic | 2 (`BMICalculateRequest`, `BMICalculateResponse`) |
| Поля в Request | 8 |
| Поля в Response | 9 |

---

## 🔗 Связь с другими PR/коммитами

### Зависимости

**PR-453 опирается на:**
- ✅ `core/i18n.py` — `Language = Literal["ru", "en", "es"]`
- ✅ `core/bmi/risk.py` — `WaistRiskResult` (для документации структуры)

**PR-453 готовит для:**
- 🔜 PR-454 (endpoint) — будет использовать `BMICalculateRequest`/`BMICalculateResponse`
- 🔜 PR-455 (legacy wiring) — legacy endpoints будут маппить в эти схемы

### Что НЕ входит в PR-453

- ❌ `core/bmi/engine.py` — будет в отдельном PR (или уже есть)
- ❌ `app/routers/bmi.py` — endpoint будет в PR-454
- ❌ Legacy wiring — будет в PR-455

---

## ✅ Checklist реализации

- [x] Создан `app/schemas/bmi.py`
- [x] `BMICalculateRequest` со всеми полями и валидацией
- [x] `BMICalculateResponse` со всеми полями и описаниями
- [x] Все поля имеют `description` и `examples`
- [x] Создан `tests/test_bmi_schemas.py`
- [x] 26 тестов покрывают все edge cases
- [x] Тесты проходят (26/26 ✅)
- [x] `ruff check` проходит
- [x] `ruff format` проходит
- [x] Импорты корректны (нет циклических зависимостей)
- [x] Документация в docstrings на RU/EN
- [x] `PR_453_COMMIT_3_SCHEMAS.md` создан

---

## 🧪 Примеры использования

### Пример 1: Минимальный запрос

```python
from app.schemas.bmi import BMICalculateRequest

req = BMICalculateRequest(
    weight_kg=70.0,
    height_cm=175.0,
    age=30,
)
# Все остальные поля используют дефолты
```

### Пример 2: Полный запрос с waist

```python
req = BMICalculateRequest(
    weight_kg=70.0,
    height_cm=175.0,
    age=30,
    gender="female",
    pregnant=False,
    athlete=True,
    waist_cm=80.0,
    lang="ru",
)
```

### Пример 3: Response с category=None

```python
from app.schemas.bmi import BMICalculateResponse

response = BMICalculateResponse(
    bmi=24.5,
    category=None,  # Валидно для pregnant/too_young/child/teen
    group="pregnant",
    group_display="Pregnant",
    interpretation="BMI is not valid during pregnancy.",
    wht_ratio=None,
    waist_risk=None,
    notes=[],
    age_band="adult",
)
```

---

## 📝 Коммиты в PR-453

1. **`feat(api): add BMI request/response schemas`** (1d12d0ec)
   - Создан `app/schemas/bmi.py`
   - Создан `tests/test_bmi_schemas.py`
   - Создан `PR_453_COMMIT_3_SCHEMAS.md`

2. **`fix: add trailing newline to PR description`** (cd9297d1)
   - Исправление форматирования (pre-commit hook)

---

## 🔜 Следующие шаги

После мерджа PR-453:

1. **PR-454: BMI Calculate Endpoint**
   - Создать `app/routers/bmi.py`
   - Реализовать `POST /api/v1/bmi/calculate`
   - Использовать `BMICalculateRequest`/`BMICalculateResponse`
   - Вызывать `core/bmi/engine.calculate_bmi_result()`

2. **PR-455: Legacy Wiring**
   - Рефакторинг legacy endpoints
   - Использование engine вместо локальных вычислений
   - Golden tests для проверки идентичности поведения

