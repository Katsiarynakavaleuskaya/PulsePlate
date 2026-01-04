# PR-455: Cursor TODO Checklist

**Ветка:** `feat/pr-455-bmi-engine`
**Цель:** Реализовать `core/bmi/engine.py` (не stub)

---

## Commit 1: Helper Functions (безопасный шаг)

### Файлы
- `core/bmi/engine.py`

### Задачи
- [ ] Добавить `_normalize_gender(gender: str) -> str`
  - Поддержка: "муж"/"жен"/"male"/"female"/"mujer" → "male"/"female"
  - Fallback: "male"
- [ ] Добавить `_normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool`
  - Поддержка: "yes"/"y"/"true"/"1"/"да"/"д"/"истина"/"si"/"sí" → `True`
  - Для athlete: также "спортсмен"/"спортсменка"/"атлет"/"атлетка"/"athlete"
- [ ] Добавить `_normalize_lang(lang: str) -> Language`
  - "ru"/"en"/"es" → `Language`
  - Fallback: "en"
- [ ] Добавить `_age_band(age: int) -> AgeBand`
  - `age < 12` → `"too_young"`
  - `12 <= age < 13` → `"child"`
  - `13 <= age <= 19` → `"teen"`
  - `19 < age < 60` → `"adult"`
  - `age >= 60` → `"elderly"`
- [ ] Добавить `_compute_bmi(weight_kg: float, height_m: float) -> float`
  - Формула: `weight_kg / (height_m ** 2)`
  - Округление: `round(bmi, 1)`
  - Валидация: `weight_kg > 0`, `height_m > 0`
- [ ] Добавить `_compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None`
  - Если `waist_cm is None` → `None`
  - Формула: `(waist_cm / 100.0) / height_m`
  - Округление: `round(wht_ratio, 2)`
  - Валидация: `waist_cm > 0`, `height_m > 0.5` и `height_m <= 3.0`

### Тесты (опционально, можно в Commit 2)
- [ ] `test_normalize_gender()` — все варианты
- [ ] `test_normalize_bool_flag()` — все yes-значения
- [ ] `test_age_band_boundaries()` — границы 11, 12, 13, 19, 20, 59, 60
- [ ] `test_compute_bmi()` — базовый расчёт + округление
- [ ] `test_compute_wht_ratio()` — с waist и без

### Commit message
```
feat(bmi): add helper functions for engine (normalize, age_band, compute)

- Add _normalize_gender() with ru/en/es support
- Add _normalize_bool_flag() with athlete synonyms
- Add _normalize_lang() with fallback to 'en'
- Add _age_band() with 5 age bands
- Add _compute_bmi() with rounding to 1 decimal
- Add _compute_wht_ratio() (moved from bmi_core.py)
```

---

## Commit 2: Group and Category Logic

### Файлы
- `core/bmi/engine.py`

### Задачи
- [ ] Добавить `_auto_group(age: int, gender: str, pregnant: bool, athlete: bool, lang: Language) -> str`
  - Приоритет: `age < 12` → `"too_young"`
  - Приоритет: `13 <= age <= 19` → `"teen"`
  - Приоритет: `12 <= age < 13` → `"child"`
  - Приоритет: `age >= 60` → `"elderly"`
  - Приоритет: `pregnant and gender == "female"` → `"pregnant"`
  - Иначе: `athlete` → `"athlete"`, иначе `"general"`
- [ ] Добавить `_bmi_category(bmi: float, lang: Language, age: int, group: str) -> str | None`
  - Если `group == "pregnant"` → `None`
  - Если `age_band in {"too_young", "child", "teen"}` → `None`
  - Пороги для adult: `18.5`, `25.0`, `30.0`, `35.0`, `40.0`
  - Пороги для elderly: `17.5`, `26.0`
  - Пороги для teen: `17.5`, `24.5`
  - Пороги для athlete: `27.0` (normal upper)
  - Использовать `core.i18n.t(lang, key)` для локализации
- [ ] Добавить `_group_display_name(group: str, lang: Language) -> str`
  - Таблица: `{"general": {...}, "athlete": {...}, ...}`
  - Или через `core.i18n.t()` (если ключи есть)
- [ ] Добавить `_interpretation(bmi: float, group: str, lang: Language, age: int) -> str`
  - Формат: `"{category}. {note}"` (если note есть)
  - Использовать `core.i18n.t()` для notes

### Тесты
- [ ] `test_auto_group_priority()` — все приоритеты
- [ ] `test_bmi_category_thresholds()` — все пороги
- [ ] `test_bmi_category_none()` — pregnant и youth
- [ ] `test_group_display_name()` — все группы, все языки
- [ ] `test_interpretation()` — с notes и без

### Commit message
```
feat(bmi): add group and category logic with parity to legacy

- Add _auto_group() with priority: age > pregnant > athlete
- Add _bmi_category() with group-specific thresholds
- Add _group_display_name() with localization
- Add _interpretation() with category + notes
- Use core.i18n.t() for all localized strings
```

---

## Commit 3: Main Orchestrator

### Файлы
- `core/bmi/engine.py`

### Задачи
- [ ] Реализовать `calculate_bmi_result(...) -> BMICalculateResult` (10 шагов):
  1. Валидация входных данных
  2. Нормализация: gender, pregnant, athlete, lang
  3. Расчёт BMI через `_compute_bmi()`
  4. Валидация BMI: `10 <= bmi <= 100` (raise ValueError)
  5. Определение `age_band` через `_age_band()`
  6. Определение `group` через `_auto_group()`
  7. Определение `category` через `_bmi_category()` (может быть None)
  8. Расчёт WHtR через `_compute_wht_ratio()`
  9. Расчёт waist risk через `calculate_waist_risk()` (из `core/bmi/risk.py`)
  10. Формирование `group_display`, `interpretation`, `notes`
  11. Возврат `BMICalculateResult`

### Тесты
- [ ] `test_calculate_bmi_result_basic()` — простой кейс
- [ ] `test_calculate_bmi_result_pregnant()` — category=None
- [ ] `test_calculate_bmi_result_youth()` — category=None для child/teen
- [ ] `test_calculate_bmi_result_waist_risk()` — с waist и без
- [ ] `test_calculate_bmi_result_domain_validation()` — BMI < 10, > 100

### Commit message
```
feat(bmi): implement calculate_bmi_result orchestrator

- Implement 10-step pipeline: validation → normalization → calculation
- Integrate waist risk from core/bmi/risk.py
- Return BMICalculateResult with all fields populated
- Domain validation: BMI must be 10-100 (raise ValueError)
```

---

## Commit 4: Golden Parity Tests

### Файлы
- `tests/test_bmi_engine.py`

### Задачи
- [ ] Добавить `test_parity_legacy_cases()` с 15 кейсами:
  1. `age=10, male, no, no` → `too_young`, `category=None`
  2. `age=12, female, no, no` → `child`, `category=None`
  3. `age=13, male, no, no` → `teen`, `category=None`
  4. `age=16, female, no, no` → `teen`, `category=None`
  5. `age=19, male, no, no` → `teen`, `category=None`
  6. `age=30, female, yes, no` → `pregnant`, `category=None`
  7. `age=30, male, no, yes` → `athlete`, `category=normal` (athlete threshold)
  8. `age=30, male, no, no, bmi=22` → `general`, `category=normal`
  9. `age=30, male, no, no, bmi=27` → `general`, `category=overweight`
  10. `age=30, male, no, no, bmi=32` → `general`, `category=obese_1`
  11. `age=65, female, no, no, bmi=25.5` → `elderly`, `category=normal` (elderly threshold)
  12. `age=65, male, no, yes` → `athlete`, `elderly`
  13. `age=30, male, no, no, waist=95` → `waist_risk` present
  14. `age=30, female, no, no, waist=85` → `waist_risk` present
  15. `age=14, male, no, no, bmi=17` → `teen`, `category=None` (teen threshold)

### Commit message
```
test(bmi): add golden parity tests with legacy behavior

- Add 15 test cases covering all age bands, groups, categories
- Verify category=None for pregnant and youth groups
- Verify group priority: age > pregnant > athlete
- Verify waist risk integration
```

---

## Commit 5: Localization Tests

### Файлы
- `tests/test_bmi_engine.py`

### Задачи
- [ ] Добавить `test_localization_ru_en_es()`:
  - Проверить все категории на всех языках
  - Проверить group_display на всех языках
  - Проверить interpretation на всех языках
  - Проверить notes на всех языках

### Commit message
```
test(bmi): add localization tests for RU/EN/ES

- Verify all BMI categories are localized
- Verify group_display names are localized
- Verify interpretation strings are localized
- Verify notes are localized
```

---

## Commit 6: Integration Test (endpoint не 501)

### Файлы
- `tests/test_bmi_calculate_endpoint.py`

### Задачи
- [ ] Обновить `test_bmi_calculate_returns_501_when_engine_not_implemented()`:
  - Убрать мок (engine теперь реальный)
  - Проверить, что endpoint возвращает 200 (не 501)
- [ ] Добавить реальные тесты без моков:
  - `test_bmi_calculate_real_engine()` — happy path
  - `test_bmi_calculate_pregnant()` — category=None
  - `test_bmi_calculate_youth()` — category=None

### Commit message
```
test(api): update endpoint tests to use real engine

- Remove mocks (engine is now implemented)
- Verify endpoint returns 200 (not 501)
- Add real integration tests without mocks
```

---

## Финальная проверка

### Перед push
- [ ] `ruff check .` проходит
- [ ] `pytest -q tests/test_bmi_engine.py` — все тесты зелёные
- [ ] `pytest -q tests/test_bmi_calculate_endpoint.py` — все тесты зелёные
- [ ] `pytest -q tests/test_bmi_schemas.py` — все тесты зелёные
- [ ] Endpoint `/api/v1/bmi/calculate` возвращает 200 (не 501)
- [ ] Golden parity тесты подтверждают совместимость

### После push
- [ ] CI проходит
- [ ] Coverage >= 97% для новых файлов
- [ ] Review готов

---

## Структура функций (для справки)

```python
# core/bmi/engine.py

def _normalize_gender(gender: str) -> str:
    """Normalize gender: 'муж'/'жен'/'male'/'female'/'mujer' → 'male'/'female'."""

def _normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool:
    """Normalize bool flag: 'yes'/'y'/'true'/'1'/'да'/'si' → True."""

def _normalize_lang(lang: str) -> Language:
    """Normalize language: any → 'ru'/'en'/'es' (fallback 'en')."""

def _age_band(age: int) -> AgeBand:
    """Determine age_band from age only (independent of group)."""

def _compute_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI: weight / (height ** 2), rounded to 1 decimal."""

def _compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
    """Calculate WHtR: (waist_cm / 100) / height_m, rounded to 2 decimals."""

def _auto_group(age: int, gender: str, pregnant: bool, athlete: bool, lang: Language) -> str:
    """Determine group with priority: age > pregnant > athlete."""

def _bmi_category(bmi: float, lang: Language, age: int, group: str) -> str | None:
    """Determine BMI category with group-specific thresholds."""

def _group_display_name(group: str, lang: Language) -> str:
    """Get localized group display name."""

def _interpretation(bmi: float, group: str, lang: Language, age: int) -> str:
    """Build interpretation string: '{category}. {note}'."""

def calculate_bmi_result(...) -> BMICalculateResult:
    """Main orchestrator: 10-step pipeline."""
```

---

## Порядок работы

1. **Commit 1:** Helpers (безопасный, можно тестировать по частям)
2. **Commit 2:** Group/Category (логика, требует тестов)
3. **Commit 3:** Orchestrator (главная функция)
4. **Commit 4:** Golden parity (проверка совместимости)
5. **Commit 5:** Localization (проверка i18n)
6. **Commit 6:** Integration (endpoint работает)

**Важно:** Каждый коммит должен быть рабочим (тесты проходят).
