# PR-455: BMI Engine Implementation Plan

**Цель:** Реализовать `core/bmi/engine.py` (не stub), чтобы `/api/v1/bmi/calculate` перестал возвращать 501.

**Основа:** Qoder Audit Report (`PR_455_QODER_AUDIT_REPORT.md`)

---

## Инварианты (не нарушать)

- ✅ One BMI Engine: вся математика только в `core/bmi/*`
- ✅ Free BMI = расширенный скрининг (groups, age_bands, waist risk)
- ✅ child ≠ teen (отдельная логика)
- ✅ category=None для youth и pregnant (медицинский дисклеймер)

---

## Что берём из legacy (parity-важно)

### Приоритеты group
- **age > pregnant > athlete** (строгий порядок)
- Примеры:
  - `age=12, pregnant=yes, female` → `group="child"` (age приоритетнее)
  - `age=30, pregnant=yes, female` → `group="pregnant"` (pregnant приоритетнее athlete)
  - `age=65, athlete=yes` → `group="athlete"`, но `age_band="elderly"`

### Нормализации
- **gender:** "муж"/"жен"/"male"/"female"/"mujer" → "male"/"female"
- **pregnant/athlete:** "yes"/"y"/"true"/"1"/"да"/"д"/"истина"/"si"/"sí" → `True`
- **athlete:** также "спортсмен"/"спортсменка"/"атлет"/"атлетка"/"athlete" → `True`
- **lang:** любой → "ru"/"en"/"es" (fallback "en")

### Пороги категорий
- **Adult:** `18.5`, `25.0`, `30.0`, `35.0`, `40.0`
- **Elderly:** `17.5`, `26.0` (underweight, normal upper)
- **Teen:** `17.5`, `24.5` (underweight, normal upper)
- **Athlete:** `27.0` (normal upper, Config.ATHLETE_BMI_MAX)

### Локализация
- Использовать `core.i18n.t(lang, key)` для всех строк
- Ключи: `bmi_underweight`, `bmi_normal`, `bmi_overweight`, `bmi_obese_1/2/3`, `advice_athlete_bmi`, `bmi_not_valid_during_pregnancy`, `risk_elderly_note`, `risk_child_note`, `risk_teen_note`

---

## Что меняем (канон сильнее legacy)

### category = None для youth
- **Legacy:** не возвращает `category=None` для детей/подростков
- **Канон:** `category=None` для `age_band in {"too_young", "child", "teen"}`
- **Причина:** медицинский дисклеймер (BMI категории не применимы для youth)

### age_band определяется только возрастом
- `age_band` не зависит от `pregnant`/`athlete`
- Пример: `age=30, pregnant=yes` → `age_band="adult"`, `group="pregnant"`

---

## Структура `core/bmi/engine.py`

**Важно:** Всё в одном файле (без новых модулей), чтобы PR был маленьким.

```python
# core/bmi/engine.py

# 1. Imports
from dataclasses import dataclass
from typing import Literal
from core.bmi.risk import calculate_waist_risk, WaistRiskResult
from core.i18n import t, Language

# 2. Types
AgeBand = Literal["too_young", "child", "teen", "adult", "elderly"]

# 3. Dataclass (уже есть)
@dataclass(frozen=True)
class BMICalculateResult:
    bmi: float
    category: str | None
    group: str
    group_display: str
    interpretation: str
    wht_ratio: float | None
    waist_risk: WaistRiskResult | None
    notes: tuple[str, ...]
    age_band: AgeBand

# 4. Helper functions (внутри файла)
def _normalize_gender(gender: str) -> str:
    """Normalize gender to 'male'/'female'."""

def _normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool:
    """Normalize pregnant/athlete flags (ru/en/es support)."""

def _normalize_lang(lang: str) -> Language:
    """Normalize language to 'ru'/'en'/'es'."""

def _age_band(age: int) -> AgeBand:
    """Determine age_band from age only."""

def _auto_group(age: int, gender: str, pregnant: bool, athlete: bool, lang: Language) -> str:
    """Determine group with priority: age > pregnant > athlete."""

def _compute_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI: weight / (height ** 2), rounded to 1 decimal."""

def _compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
    """Calculate WHtR: (waist_cm / 100) / height_m, rounded to 2 decimals."""

def _bmi_category(bmi: float, lang: Language, age: int, group: str) -> str | None:
    """Determine BMI category with group-specific thresholds."""

def _group_display_name(group: str, lang: Language) -> str:
    """Get localized group display name."""

def _interpretation(bmi: float, group: str, lang: Language, age: int) -> str:
    """Build interpretation string (category + notes)."""

# 5. Main orchestrator
def calculate_bmi_result(...) -> BMICalculateResult:
    """10-step pipeline as per Qoder audit."""
```

---

## Тест-пакет PR-455

**Файл:** `tests/test_bmi_engine.py`

### Обязательный минимум

1. **Базовый расчёт:**
   - `test_bmi_calculation_basic()` — простой расчёт
   - `test_bmi_rounding()` — округление до 1 знака
   - `test_bmi_domain_validation()` — проверка `10 <= bmi <= 100`

2. **Age bands:**
   - `test_age_band_too_young()` — `age=11`
   - `test_age_band_child()` — `age=12`
   - `test_age_band_teen()` — `age=13, 16, 19`
   - `test_age_band_adult()` — `age=20, 30, 59`
   - `test_age_band_elderly()` — `age=60, 65`

3. **Group priority:**
   - `test_group_priority_age_over_pregnant()` — `age=12, pregnant=yes, female` → `group="child"`
   - `test_group_priority_pregnant_over_athlete()` — `age=30, pregnant=yes, female` → `group="pregnant"`
   - `test_group_athlete_elderly()` — `age=65, athlete=yes` → `group="athlete"`, `age_band="elderly"`

4. **Category None:**
   - `test_category_none_pregnant()` — `pregnant=True` → `category=None`
   - `test_category_none_youth()` — `age_band in {"too_young", "child", "teen"}` → `category=None`

5. **Waist risk integration:**
   - `test_waist_risk_with_waist()` — `waist_cm=90` → `waist_risk` present
   - `test_waist_risk_without_waist()` — `waist_cm=None` → `waist_risk=None`

6. **Golden parity (15 кейсов):**
   - `test_parity_legacy_cases()` — все кейсы из Qoder audit

7. **Локализация:**
   - `test_localization_ru_en_es()` — проверка всех языков

---

## Что НЕ делаем в PR-455

- ❌ Не удаляем legacy BMI math (`legacy_app.py:calc_bmi()`)
- ❌ Не трогаем другие endpoints (`/api/v1/bmi`, `/bmi`)
- ❌ Не делаем guard-test (отдельный PR)
- ❌ Не рефакторим `bmi_core.py`

---

## Порядок реализации (Cursor)

1. Реализовать helpers в `core/bmi/engine.py`
2. Реализовать `calculate_bmi_result()` orchestrator
3. Написать тесты в `tests/test_bmi_engine.py`
4. Проверить, что endpoint не возвращает 501
5. Запустить golden parity тесты

---

## Критерии готовности PR-455

- ✅ `calculate_bmi_result()` не выбрасывает `NotImplementedError`
- ✅ Endpoint `/api/v1/bmi/calculate` возвращает 200 (не 501)
- ✅ Все тесты проходят (минимум 20 тестов)
- ✅ Golden parity тесты подтверждают совместимость с legacy
- ✅ Локализация работает (RU/EN/ES)
- ✅ `category=None` для youth и pregnant
