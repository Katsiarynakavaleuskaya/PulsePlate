# PR-455: Qoder Audit Report (BMI Engine Implementation)

**Дата:** 2026-01-04
**Статус:** Аудит завершён, готов к реализации engine

---

## A) Карта текущего состояния

### 1. BMI-математика вне `core/bmi/*` (нарушения канона)

#### 🔴 Критичные нарушения:

**`legacy_app.py` (строка 1547-1548):**
```python
def calc_bmi(weight_kg: StrictFloat, height_m: float) -> float:
    return round(float(weight_kg) / (height_m**2), 1)
```
- **Использование:** `bmi_endpoint`, `bmi_endpoint_v1`, `plan_endpoint`
- **Статус:** Должна быть удалена после миграции на engine

**`app/routers/bmi_pro.py` (строка 16-17):**
```python
def calc_bmi(weight_kg: float, height_m: float) -> float:
    return round(weight_kg / (height_m**2), 1)
```
- **Использование:** PRO endpoint `/api/v1/bmi/pro`
- **Статус:** Отдельный PRO модуль, не относится к Free BMI (можно оставить пока)

**`bmi_core.py` (строка 24-45):**
```python
def bmi_value(weight_kg: float, height_m: float) -> float:
    bmi = weight_kg / (height_m**2)
    return round(bmi, 1)
```
- **Статус:** ✅ Это legacy core, будет заменён на `core/bmi/engine.py`

**`legacy_app.py` (строка 1466, 1440):**
```python
bmi = self.weight_kg / (self.height_m**2)  # Валидация BMIRequestV1
```
- **Статус:** Валидация в Pydantic model, не критично (можно оставить)

**`app/routers/bodyfat.py` (строка 52-53):**
```python
if req.bmi is None and req.weight_kg is not None and req.height_m is not None:
    data["bmi"] = req.weight_kg / (req.height_m**2)
```
- **Статус:** Вспомогательный расчёт для bodyfat, не относится к Free BMI

#### ✅ Правильные места (в `core/bmi/*`):

- `core/bmi/risk.py` — waist risk (уже канонично)
- `core/bmi/engine.py` — stub (будет реализован)

---

### 2. BMI Endpoints (карта маршрутов)

| Путь | Файл | Функция | Контракт | Статус |
|------|------|---------|----------|--------|
| `/bmi` | `legacy_app.py:2026` | `bmi_endpoint` | `BMIRequest` | Legacy, будет shim |
| `/api/v1/bmi` | `legacy_app.py:2139` | `bmi_endpoint_v1` | `BMIRequestV1` | Legacy, будет shim |
| `/api/v1/bmi/calculate` | `legacy_app.py:2196` | `bmi_calculate_legacy` | `BMIRequestV1` | ✅ Shim (PR-454) |
| `/api/v1/bmi/calculate` | `app/routers/bmi.py:163` | `calculate_bmi` | `BMICalculateRequest` | ✅ Новый (PR-454) |
| `/api/v1/bmi/pro` | `app/routers/bmi_pro.py:45` | `bmi_pro` | `BMIProRequest` | PRO (отдельно) |
| `/plan` | `legacy_app.py:2088` | `plan_endpoint` | `BMIRequest` | Legacy, не относится |

**Приоритет миграции:**
1. ✅ `/api/v1/bmi/calculate` — уже shim (PR-454)
2. 🔄 `/api/v1/bmi` — нужно сделать shim (PR-455 или позже)
3. 🔄 `/bmi` — нужно сделать shim (PR-455 или позже)

---

### 3. `BMIRequestV1` vs `BMICalculateRequest` (сравнение)

| Поле | BMIRequestV1 | BMICalculateRequest | Различия |
|------|--------------|---------------------|----------|
| `weight_kg` | `StrictFloat`, `gt=0` | `float`, `gt=0` | ✅ Совместимо |
| `height_cm` | `float`, `gt=0` | `float`, `gt=0` | ✅ Совместимо |
| `age` | `int`, `default=30`, `ge=0`, `le=120` | `int`, `ge=1`, `le=120` | ⚠️ Разные defaults |
| `gender` | `str`, `default="male"` | `str`, `default="male"` | ✅ Совместимо |
| `pregnant` | `Union[str, bool]`, `default="no"` | `str \| bool`, `default="no"` | ✅ Совместимо |
| `athlete` | `Union[str, bool]`, `default="no"` | `str \| bool`, `default="no"` | ✅ Совместимо |
| `waist_cm` | `Optional[float]`, `gt=0` | `float \| None`, `gt=0` | ✅ Совместимо |
| `lang` | `Language`, `default="en"` | `Language`, `default="en"` | ✅ Совместимо |
| `group` | `str`, `default="general"` | ❌ Нет | ⚠️ Legacy поле (игнорируется) |

**Вывод:** Конвертация через `model_dump()` работает корректно (PR-454 уже реализовал).

---

## B) Parity и риск расхождения

### 4. Правила `group` и `age_band` в legacy

**Источник:** `bmi_core.py:auto_group()` (строка 117-153)

**Правила определения `group`:**

1. **too_young:** `age < 12`
2. **teen:** `13 <= age <= 19` (Config.TEEN_MIN_AGE = 13, TEEN_MAX_AGE = 19)
3. **child:** `12 <= age < 13` (pre-teen)
4. **elderly:** `age >= 60` (Config.ELDERLY_AGE = 60)
5. **pregnant:**
   - Только для `gender == "female"` (проверка через `g.startswith("жен")` / `g == "female"` / `g.startswith("mujer")`)
   - `pregnant in yes_vals` (да/yes/y/true/1/да/д/истина/si/sí)
   - Проверяется **ПОСЛЕ** age checks (приоритет: age > pregnant)
6. **athlete:**
   - `athlete in yes_vals` ИЛИ
   - `athlete in {"спорт", "спортсмен", "спортсменка", "атлет", "атлетка", "athlete"}` ИЛИ
   - Regex match: `r"спортсмен(ка)?|атлет(ка)?"`
7. **general:** По умолчанию (если не athlete)

**Правила определения `age_band` (для engine):**

- **too_young:** `age < 12`
- **child:** `12 <= age < 13` (или `12 <= age < TEEN_MIN_AGE`)
- **teen:** `13 <= age <= 19` (или `TEEN_MIN_AGE <= age <= TEEN_MAX_AGE`)
- **adult:** `19 < age < 60` (или `TEEN_MAX_AGE < age < ELDERLY_AGE`)
- **elderly:** `age >= 60`

**⚠️ Критично:** В legacy `group` и `age_band` могут не совпадать:
- `age=12, gender=female, pregnant=yes` → `group="pregnant"`, но `age_band="child"`
- `age=65, athlete=yes` → `group="athlete"`, но `age_band="elderly"`

**Решение для engine:** `age_band` определяется **только по возрасту**, `group` учитывает все факторы (age, pregnant, athlete).

---

### 5. Правила `category` и когда она `None`

**Источник:** `bmi_core.py:bmi_category()` (строка 71-109) + legacy endpoints

**Правила определения `category`:**

1. **Пороги (общие):**
   - `underweight`: `bmi < 18.5` (или `17.5` для elderly/teen)
   - `normal`: `18.5 <= bmi < 25.0` (или `24.5` для teen, `26.0` для elderly, `27.0` для athlete)
   - `overweight`: `25.0 <= bmi < 30.0`
   - `obese_1`: `30.0 <= bmi < 35.0`
   - `obese_2`: `35.0 <= bmi < 40.0`
   - `obese_3`: `bmi >= 40.0`

2. **Специальные пороги:**
   - **elderly:** `underweight < 17.5`, `normal < 26.0`
   - **teen:** `underweight < 17.5`, `normal < 24.5`
   - **athlete:** `normal < 27.0` (Config.ATHLETE_BMI_MAX)

3. **Когда `category = None`:**

   **В legacy (`legacy_app.py:2031-2049, 2148-2161`):**
   - ✅ `pregnant == True` → `category = None` (медицинский дисклеймер)
   - ❌ **НЕТ** `category = None` для `too_young`, `child`, `teen` в legacy endpoints

   **В новом API (`app/schemas/bmi.py:131-140`):**
   - ✅ `pregnant == True` → `category = None`
   - ✅ `age_band in {"too_young", "child", "teen"}` → `category = None` (медицинский дисклеймер)

   **⚠️ Расхождение:** Legacy **НЕ** возвращает `category = None` для детей/подростков, но новый API должен (по канону).

**Решение:** Engine должен возвращать `category = None` для:
- `pregnant == True`
- `age_band in {"too_young", "child", "teen"}`

---

### 6. Локализация RU/EN/ES для BMI интерпретаций

**Источник:** `core/i18n.py` (TRANSLATIONS dict)

**Ключи локализации (важно не потерять):**

**BMI Categories:**
- `bmi_underweight` (RU: "Недостаточная масса", EN: "Underweight", ES: "Bajo peso")
- `bmi_normal` (RU: "Норма", EN: "Normal weight", ES: "Peso normal")
- `bmi_overweight` (RU: "Избыточная масса", EN: "Overweight", ES: "Sobrepeso")
- `bmi_obese_1` (RU: "Ожирение I степени", EN: "Obese Class I", ES: "Obesidad Clase I")
- `bmi_obese_2` (RU: "Ожирение II степени", EN: "Obese Class II", ES: "Obesidad Clase II")
- `bmi_obese_3` (RU: "Ожирение III степени", EN: "Obese Class III", ES: "Obesidad Clase III")

**Group Notes:**
- `advice_athlete_bmi` (RU: "У спортсменов BMI может завышать жировую массу", EN: "For athletes, BMI may overestimate body fat due to muscle mass", ES: "Para atletas, el IMC puede sobreestimar la grasa corporal")
- `bmi_not_valid_during_pregnancy` (RU: "BMI не применим при беременности", EN: "BMI is not valid during pregnancy", ES: "El IMC no es válido durante el embarazo")
- `risk_elderly_note` (RU: "У пожилых ИМТ может занижать долю жира (саркопения).", EN: "In older adults, BMI can underestimate body fat (sarcopenia).", ES: "En adultos mayores, el IMC puede subestimar la grasa...")
- `risk_child_note` (RU: "Для подростков используйте возрастные центильные таблицы.", EN: "Use BMI-for-age percentiles for youth.", ES: "Utilice percentiles de IMC para la edad en jóvenes.")
- `risk_teen_note` (RU: "Подростковый возраст: учитывайте этап полового созревания.", EN: "Teenage years: consider pubertal development stage.", ES: "Años adolescentes: considere la etapa de desarrollo puberal.")

**Group Display Names:**
- Хардкод в `bmi_core.py:group_display_name()` (строка 181-195):
  - `general`: {"ru": "общая", "en": "general", "es": "general"}
  - `athlete`: {"ru": "спортсмен", "en": "athlete", "es": "atleta"}
  - `pregnant`: {"ru": "беременная", "en": "pregnant", "es": "embarazada"}
  - `elderly`: {"ru": "пожилой", "en": "elderly", "es": "anciano"}
  - `child`: {"ru": "ребёнок", "en": "child", "es": "niño"}
  - `teen`: {"ru": "подросток", "en": "teenager", "es": "adolescente"}
  - `too_young`: {"ru": "слишком юный", "en": "too young", "es": "muy joven"}

**Интерпретации:**
- `interpret_group()` в `bmi_core.py:156-178` формирует строку: `"{category}. {note}"`

**⚠️ Важно:** Engine должен использовать `core.i18n.t()` для всех локализованных строк, не хардкодить.

---

## C) Предохранители (anti-duplication)

### 7. Guard-test стратегия "No BMI math outside core/bmi"

**Что считать "математикой":**
- Формула BMI: `weight / (height ** 2)` или `weight / height**2` или `weight / (height_m * height_m)`
- Пороги BMI: `18.5`, `25.0`, `30.0`, `35.0`, `40.0` (в контексте BMI категорий)
- Пороги WHtR: `0.5`, `0.6` (если не в `core/bmi/risk.py`)
- Пороги waist: `80.0`, `88.0`, `94.0`, `102.0` (если не в `core/bmi/risk.py`)

**Исключения (не считать нарушением):**
- `core/bmi/*` — разрешено
- `bmi_core.py` — legacy, будет удалён после миграции
- `core/bmi_extras*.py` — PRO модули (отдельный трек)
- `tests/*` — тесты могут содержать формулы для проверки
- `app/routers/bodyfat.py` — вспомогательный расчёт для bodyfat API

**Patterns для поиска:**
```python
# Regex patterns для guard-test:
patterns = [
    r'weight.*/.*height.*\*\*',  # weight / height**
    r'weight.*/.*\(.*height',      # weight / (height
    r'bmi\s*=\s*.*weight.*height', # bmi = ... weight ... height
    r'18\.5|25\.0|30\.0|35\.0|40\.0',  # Пороги (в контексте BMI)
]
```

**Стратегия реализации:**
1. Создать `tests/test_bmi_math_guard.py`
2. Использовать `ast` для парсинга Python файлов
3. Искать паттерны в `app/*`, `legacy_app.py` (исключая разрешённые)
4. CI должен падать, если найдены нарушения

**Пример guard-test:**
```python
def test_no_bmi_math_outside_core_bmi():
    """Guard: No BMI math outside core/bmi/*"""
    violations = scan_for_bmi_math(["app/", "legacy_app.py"], exclude=["core/bmi/", "tests/"])
    assert violations == [], f"Found BMI math outside core/bmi: {violations}"
```

---

### 8. Golden parity тесты (10-15 кейсов)

**Матрица тестов для parity с legacy:**

| # | Возраст | Пол | Pregnant | Athlete | Waist | BMI | Ожидаемый group | Ожидаемый age_band | Ожидаемый category |
|---|---------|-----|----------|---------|-------|-----|-----------------|-------------------|-------------------|
| 1 | 10 | male | no | no | None | 20.0 | `too_young` | `too_young` | `None` |
| 2 | 12 | female | no | no | None | 20.0 | `child` | `child` | `None` |
| 3 | 13 | male | no | no | None | 20.0 | `teen` | `teen` | `None` |
| 4 | 16 | female | no | no | None | 22.0 | `teen` | `teen` | `None` |
| 5 | 19 | male | no | no | None | 24.0 | `teen` | `teen` | `None` |
| 6 | 30 | female | yes | no | None | 22.0 | `pregnant` | `adult` | `None` |
| 7 | 30 | male | no | yes | None | 26.0 | `athlete` | `adult` | `normal` (athlete threshold) |
| 8 | 30 | male | no | no | None | 22.0 | `general` | `adult` | `normal` |
| 9 | 30 | male | no | no | None | 27.0 | `general` | `adult` | `overweight` |
| 10 | 30 | male | no | no | None | 32.0 | `general` | `adult` | `obese_1` |
| 11 | 65 | female | no | no | None | 25.5 | `elderly` | `elderly` | `normal` (elderly threshold) |
| 12 | 65 | male | no | yes | None | 28.0 | `athlete` | `elderly` | `normal` (athlete threshold) |
| 13 | 30 | male | no | no | 95.0 | 22.0 | `general` | `adult` | `normal` + waist_risk |
| 14 | 30 | female | no | no | 85.0 | 22.0 | `general` | `adult` | `normal` + waist_risk |
| 15 | 14 | male | no | no | None | 17.0 | `teen` | `teen` | `None` (teen threshold) |

**Дополнительные edge cases:**
- Границы порогов: `18.49`, `18.5`, `24.99`, `25.0`, `29.99`, `30.0`
- Языки: RU, EN, ES (проверка локализации)
- Нормализация gender: "муж", "жен", "male", "female", "mujer"
- Нормализация athlete: "спортсмен", "athlete", "yes", True

---

## D) План реализации engine

### 9. Детальный план `core/bmi/engine.py`

**Структура модулей:**

```
core/bmi/
├── __init__.py          # Экспорты
├── engine.py            # Главный orchestrator (calculate_bmi_result)
├── group.py             # auto_group логика (опционально, можно в engine)
├── category.py          # bmi_category логика (опционально, можно в engine)
├── risk.py              # ✅ Уже есть (waist risk)
└── i18n_helpers.py      # Хелперы для локализации (опционально)
```

**Порядок вычислений в `calculate_bmi_result()`:**

1. **Валидация входных данных:**
   - `weight_kg > 0`, `height_cm > 0`, `age >= 1`, `age <= 120`
   - Нормализация `gender` → "male"/"female"
   - Нормализация `pregnant` → `bool`
   - Нормализация `athlete` → `bool`
   - Нормализация `lang` → "ru"/"en"/"es"

2. **Расчёт BMI:**
   - `height_m = height_cm / 100.0`
   - `bmi = weight_kg / (height_m ** 2)`
   - `bmi = round(bmi, 1)`
   - Валидация: `10 <= bmi <= 100` (domain validation)

3. **Определение `age_band`:**
   - `age < 12` → `too_young`
   - `12 <= age < 13` → `child`
   - `13 <= age <= 19` → `teen`
   - `19 < age < 60` → `adult`
   - `age >= 60` → `elderly`

4. **Определение `group` (через `_auto_group`):**
   - Приоритет: `too_young` > `child` > `teen` > `elderly` > `pregnant` > `athlete` > `general`
   - Использовать логику из `bmi_core.py:auto_group()` (перенести в engine)

5. **Определение `category`:**
   - Если `pregnant == True` → `category = None`
   - Если `age_band in {"too_young", "child", "teen"}` → `category = None`
   - Иначе: вызвать `_bmi_category(bmi, lang, age, group)` с порогами:
     - Общие: `18.5`, `25.0`, `30.0`, `35.0`, `40.0`
     - Elderly: `17.5`, `26.0`
     - Teen: `17.5`, `24.5`
     - Athlete: `27.0` (верхняя граница normal)

6. **Определение `group_display` и `interpretation`:**
   - `group_display = _group_display_name(group, lang)` (использовать `core.i18n.t()` или хардкод из `bmi_core.py`)
   - `interpretation = _interpret_group(bmi, group, lang, age)` (использовать `core.i18n.t()`)

7. **Расчёт WHtR:**
   - Если `waist_cm is not None`:
     - `wht_ratio = compute_wht_ratio(waist_cm, height_m)` (из `bmi_core.py` или перенести в `core/bmi/`)
   - Иначе: `wht_ratio = None`

8. **Расчёт waist risk:**
   - Если `waist_cm is not None`:
     - `waist_risk = calculate_waist_risk(waist_cm, height_m, gender, lang)` (из `core/bmi/risk.py`)
   - Иначе: `waist_risk = None`

9. **Формирование `notes`:**
   - Собрать notes из `waist_risk.notes` (если есть)
   - Добавить athlete note (если `group == "athlete"`)

10. **Возврат `BMICalculateResult`:**
    - Все поля заполнены, типы корректны

**Подключение `core/bmi/risk.py`:**

- ✅ Уже есть `calculate_waist_risk()` в `core/bmi/risk.py`
- ✅ Использует `compute_wht_ratio()` из `bmi_core.py` (можно перенести в `core/bmi/` или оставить импорт)
- ✅ Нет циклов зависимостей

**Импорты (без циклов):**
```python
# core/bmi/engine.py
from core.bmi.risk import calculate_waist_risk, WaistRiskResult
from core.i18n import t, Language
from bmi_core import compute_wht_ratio  # Временно, потом перенести
```

---

### 10. Список тестов для engine

**Файл:** `tests/test_bmi_engine.py`

**Группы тестов:**

1. **Базовые расчёты:**
   - `test_bmi_calculation_basic()` — простой расчёт BMI
   - `test_bmi_rounding()` — округление до 1 знака
   - `test_bmi_domain_validation()` — проверка `10 <= bmi <= 100`

2. **Age bands:**
   - `test_age_band_too_young()` — `age < 12`
   - `test_age_band_child()` — `12 <= age < 13`
   - `test_age_band_teen()` — `13 <= age <= 19`
   - `test_age_band_adult()` — `19 < age < 60`
   - `test_age_band_elderly()` — `age >= 60`

3. **Groups:**
   - `test_group_pregnant()` — беременность
   - `test_group_athlete()` — спортсмен
   - `test_group_elderly()` — пожилой
   - `test_group_priority()` — приоритеты (age > pregnant > athlete)

4. **Category:**
   - `test_category_none_pregnant()` — `category = None` для беременных
   - `test_category_none_youth()` — `category = None` для too_young/child/teen
   - `test_category_thresholds()` — пороги для adult
   - `test_category_elderly_thresholds()` — пороги для elderly
   - `test_category_teen_thresholds()` — пороги для teen
   - `test_category_athlete_thresholds()` — пороги для athlete

5. **Waist risk:**
   - `test_waist_risk_integration()` — интеграция с `core/bmi/risk.py`
   - `test_waist_risk_none()` — без waist_cm

6. **Локализация:**
   - `test_localization_ru()` — русский
   - `test_localization_en()` — английский
   - `test_localization_es()` — испанский

7. **Golden parity:**
   - `test_parity_legacy_cases()` — все 15 кейсов из секции C.8

8. **Edge cases:**
   - `test_gender_normalization()` — нормализация пола
   - `test_athlete_normalization()` — нормализация athlete
   - `test_pregnant_normalization()` — нормализация pregnant

**Минимум для PR-455:** Тесты 1-4 + 7 (golden parity) = ~20 тестов.

---

## Итоговые рекомендации

### ✅ Что делать в PR-455:

1. Реализовать `core/bmi/engine.py` по плану из секции D.9
2. Добавить тесты из секции D.10 (минимум: базовые + age_bands + groups + category + golden parity)
3. Убедиться, что endpoint `/api/v1/bmi/calculate` перестаёт возвращать 501
4. Проверить parity с legacy (golden tests)

### ⚠️ Что НЕ делать в PR-455:

- Не удалять `legacy_app.py:calc_bmi()` (это отдельный PR)
- Не мигрировать `/api/v1/bmi` и `/bmi` endpoints (это отдельный PR)
- Не создавать guard-test (это отдельный PR)
- Не рефакторить `bmi_core.py` (это отдельный PR)

### 🔜 Следующие PR после PR-455:

- PR-456: Guard-test "No BMI math outside core/bmi"
- PR-457: Миграция остальных legacy endpoints на shim
- PR-458: Удаление `bmi_core.py` и `legacy_app.py:calc_bmi()`

---

**Конец отчёта Qoder Audit**
