# PR-455 Commit 1: Helper Functions - Риски и Тонкие Места

**Canonical: PR-455 (BMI Engine Implementation)**
**GitHub PR: #468**
**Дата:** 2026-01-04  
**Статус:** Pre-implementation review

---

## 🎯 Общая оценка Commit 1

**Безопасность:** ✅ Высокая (изолированные helpers, легко тестировать)  
**Риски:** 🟡 Средние (несколько тонких мест требуют внимания)  
**Готовность:** ✅ Можно начинать после учёта рисков

---

## 🔴 Критичные риски (обязательно учесть)

### 1. `_normalize_gender()` — неполная совместимость с legacy

**Проблема:**
Legacy использует `g.startswith("жен")` / `g.startswith("mujer")`, а не точное совпадение.

**Legacy код (`bmi_core.py:146-149`):**
```python
(lang == "ru" and g.startswith("жен") and p in yes_vals)
or (lang == "en" and g == "female" and p in yes_vals)
or (lang == "es" and g.startswith("mujer") and p in yes_vals)
```

**Риск:**
Если engine использует только точные совпадения (`"жен"`, `"mujer"`), то варианты типа `"женский"`, `"mujeres"` не распознаются.

**Решение:**
```python
def _normalize_gender(gender: str) -> str:
    g = (gender or "").strip().lower()
    
    # Russian: "жен", "женский", "женщина" → "female"
    if g.startswith("жен"):
        return "female"
    # Spanish: "mujer", "mujeres" → "female"
    if g.startswith("mujer"):
        return "female"
    # English: exact match
    if g == "female":
        return "female"
    # Male variants
    if g.startswith("муж") or g == "male":
        return "male"
    
    # Fallback: "male" (как в legacy)
    return "male"
```

**⚠️ Важно:** Это должно совпадать с логикой в `_auto_group()` (Commit 2), иначе parity нарушится.

---

### 2. `_normalize_bool_flag()` — athlete synonyms и regex

**Проблема:**
Legacy использует **regex** для athlete: `r"спортсмен(ка)?|атлет(ка)?"`

**Legacy код (`bmi_core.py:131-133`):**
```python
athlete_pattern_match = re.search(r"спортсмен(ка)?", a_raw) or re.search(r"атлет(ка)?", a_raw)
if not is_athlete and a_raw and athlete_pattern_match:
    is_athlete = True
```

**Риск:**
Если в Commit 1 сделать только `in {"спортсмен", ...}`, то варианты типа `"я спортсмен"` не распознаются.

**Решение:**
```python
def _normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        
        # Standard yes values
        if yes_values:
            if s in yes_values:
                return True
        else:
            # Default yes values
            if s in {"yes", "y", "true", "1", "да", "д", "истина", "si", "sí"}:
                return True
        
        # For athlete: also check regex patterns
        if yes_values is None:  # Default mode
            import re
            athlete_pattern = re.search(r"спортсмен(ка)?|атлет(ка)?", s)
            if athlete_pattern:
                return True
    
    return False
```

**⚠️ Альтернатива:** Если в Commit 1 не делать regex, то в Commit 2 (`_auto_group`) нужно будет добавить regex-проверку для athlete. Это создаст дублирование логики.

**Рекомендация:** В Commit 1 сделать базовую версию без regex, а regex добавить в Commit 2 в `_auto_group()` (там он и нужен).

---

### 3. `_normalize_lang()` — использовать существующую функцию

**Проблема:**
В `core/i18n.py` уже есть `normalize_lang()`, которая делает сложную нормализацию с locale fallbacks.

**Риск:**
Если написать свою `_normalize_lang()`, то:
- Дублирование логики
- Несоответствие с остальным кодом
- Потеря locale fallback логики

**Решение:**
```python
from core.i18n import normalize_lang, Language

def _normalize_lang(lang: str) -> Language:
    """Normalize language using core.i18n.normalize_lang()."""
    return normalize_lang(lang)
```

**⚠️ Важно:** Не дублировать логику, использовать существующую функцию.

---

### 4. `_age_band()` — граница age=19 (inclusive vs exclusive)

**Проблема:**
В чеклисте написано:
- `13 <= age <= 19` → `"teen"` (age 19 включительно)
- `19 < age < 60` → `"adult"` (age 19 исключительно)

**Legacy (`bmi_core.py:138`):**
```python
if Config.TEEN_MIN_AGE <= age <= Config.TEEN_MAX_AGE:  # 13 <= age <= 19
    return "teen"
```

**Риск:**
Если сделать `19 < age < 60` для adult, то age=19 попадёт в teen (правильно), но нужно убедиться, что границы не пересекаются.

**Проверка:**
- `age < 12` → `too_young` ✅
- `12 <= age < 13` → `child` ✅
- `13 <= age <= 19` → `teen` ✅ (age 19 включительно)
- `19 < age < 60` → `adult` ✅ (age 20-59)
- `age >= 60` → `elderly` ✅

**⚠️ Важно:** Age 19 должен быть в `teen`, а не в `adult`. Проверить, что условие `19 < age` корректно (age 20 и выше).

---

### 5. `_compute_bmi()` — точность округления и edge cases

**Legacy (`bmi_core.py:44-45`):**
```python
bmi = weight_kg / (height_m**2)
return round(bmi, 1)
```

**Риски:**
1. **Округление:** `round(24.95, 1)` → `25.0` (может пересечь порог)
2. **Edge case:** `weight_kg = 0.1`, `height_m = 0.5` → `bmi = 0.4` (ниже 10, но валидно по формуле)
3. **Precision:** Python float может дать `24.9999999` вместо `25.0`

**Решение:**
```python
def _compute_bmi(weight_kg: float, height_m: float) -> float:
    if weight_kg <= 0:
        raise ValueError("Weight must be positive")
    if height_m <= 0:
        raise ValueError("Height must be positive")
    
    bmi = weight_kg / (height_m ** 2)
    # Round to 1 decimal (legacy parity)
    return round(bmi, 1)
```

**⚠️ Важно:** Domain validation (10 <= bmi <= 100) будет в orchestrator (Commit 3), не здесь.

---

### 6. `_compute_wht_ratio()` — формула и валидация

**Legacy (`bmi_core.py:263`):**
```python
return round((waist_cm / 100.0) / height_m, 2)
```

**Legacy валидация (`bmi_core.py:253-260`):**
```python
if height_m <= 0.5 or height_m > 3.0:
    return None
if waist_cm <= 0:
    return None
if waist_cm > Config.MAX_WAIST_CM:  # 300.0
    return None
```

**Риски:**
1. **Формула:** `(waist_cm / 100.0) / height_m` = `waist_cm / (100.0 * height_m)` — это правильно
2. **Валидация height:** `height_m > 3.0` — это 300 см, разумно
3. **Валидация waist:** `waist_cm > Config.MAX_WAIST_CM` — нужно проверить, что это 300.0

**Решение:**
```python
def _compute_wht_ratio(waist_cm: float | None, height_m: float) -> float | None:
    if waist_cm is None:
        return None
    
    # Height validation (legacy parity)
    if height_m <= 0.5 or height_m > 3.0:
        return None
    
    # Waist validation (legacy parity)
    if waist_cm <= 0:
        return None
    if waist_cm > 300.0:  # Config.MAX_WAIST_CM
        return None
    
    try:
        wht_ratio = (waist_cm / 100.0) / height_m
        return round(wht_ratio, 2)
    except (ZeroDivisionError, OverflowError):
        return None
```

**⚠️ Важно:** Использовать `try-except` для безопасности (как в legacy).

---

## 🟡 Средние риски (желательно учесть)

### 7. `_normalize_bool_flag()` — параметр `yes_values`

**Проблема:**
В чеклисте указан параметр `yes_values: set[str] | None = None`, но не ясно, когда его использовать.

**Риск:**
Если в Commit 2 `_auto_group()` будет вызывать `_normalize_bool_flag()` с разными `yes_values` для `pregnant` и `athlete`, то логика может разойтись.

**Рекомендация:**
В Commit 1 сделать базовую версию:
```python
def _normalize_bool_flag(value: str | bool) -> bool:
    """Normalize bool flag with default yes values."""
    # Базовые yes-значения
    # Regex для athlete будет в Commit 2 в _auto_group()
```

А в Commit 2 добавить перегрузку или отдельную функцию для athlete с regex.

---

### 8. Типы возвращаемых значений

**Проблема:**
- `_normalize_lang()` должна возвращать `Language` (Literal["ru", "en", "es"])
- `_age_band()` должна возвращать `AgeBand` (Literal["too_young", "child", "teen", "adult", "elderly"])

**Риск:**
Если использовать `str` вместо `Literal`, то mypy будет ругаться, и потеряется type safety.

**Решение:**
```python
from typing import Literal

Language = Literal["ru", "en", "es"]
AgeBand = Literal["too_young", "child", "teen", "adult", "elderly"]

def _normalize_lang(lang: str) -> Language:
    ...

def _age_band(age: int) -> AgeBand:
    ...
```

**⚠️ Важно:** Использовать типы из `core/i18n.py` и `core/bmi/engine.py` (если уже определены).

---

## 🟢 Низкие риски (можно исправить позже)

### 9. Документация функций

**Рекомендация:**
Добавить docstrings с примерами:
```python
def _normalize_gender(gender: str) -> str:
    """
    Normalize gender string to 'male' or 'female'.
    
    Supports:
    - Russian: "муж", "мужской" → "male"; "жен", "женский" → "female"
    - English: "male" → "male"; "female" → "female"
    - Spanish: "mujer", "mujeres" → "female"
    
    Args:
        gender: Gender string (any case)
    
    Returns:
        Normalized gender: "male" or "female" (default: "male")
    
    Examples:
        >>> _normalize_gender("жен")
        'female'
        >>> _normalize_gender("MALE")
        'male'
        >>> _normalize_gender("unknown")
        'male'  # fallback
    """
```

---

### 10. Импорты и зависимости

**Риск:**
Если в Commit 1 добавить `import re` для athlete regex, но не использовать его, то линтер может ругаться.

**Решение:**
Либо не добавлять regex в Commit 1 (оставить для Commit 2), либо добавить `# noqa: F401` если импорт нужен для будущего.

---

## ✅ Чеклист перед началом Commit 1

- [ ] Проверить, что `_normalize_gender()` использует `startswith()` для RU/ES (parity с legacy)
- [ ] Решить: regex для athlete в Commit 1 или Commit 2?
- [ ] Использовать `core.i18n.normalize_lang()` вместо дублирования
- [ ] Проверить границы `_age_band()` (age 19 в teen, не в adult)
- [ ] Добавить `try-except` в `_compute_wht_ratio()` для безопасности
- [ ] Использовать правильные типы (`Language`, `AgeBand`)
- [ ] Добавить docstrings с примерами

---

## 🎯 Рекомендации по порядку реализации

1. **Сначала:** `_normalize_lang()` (просто обёртка над `normalize_lang`)
2. **Потом:** `_compute_bmi()` и `_compute_wht_ratio()` (простые вычисления)
3. **Потом:** `_age_band()` (проверить границы)
4. **Потом:** `_normalize_gender()` (проверить `startswith()`)
5. **В конце:** `_normalize_bool_flag()` (базовая версия, без regex)

**Тесты:** Можно писать параллельно или сразу после каждой функции.

---

## 📝 Итоговый вердикт

**Commit 1 безопасен для реализации** после учёта рисков выше.

**Критичные правки:**
1. `_normalize_gender()` — использовать `startswith()` для RU/ES
2. `_normalize_lang()` — использовать `core.i18n.normalize_lang()`
3. `_age_band()` — проверить границу age=19

**Остальное:** Можно реализовать по чеклисту, риски низкие.

