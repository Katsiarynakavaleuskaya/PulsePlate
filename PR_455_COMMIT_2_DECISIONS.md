# PR-455 Commit 2: Group & Category Logic - Decisions & Answers

**Canonical: PR-455 (BMI Engine Implementation)**
**GitHub PR: #468**
**Дата:** 2026-01-04
**Статус:** Pre-implementation decisions (зафиксировано ДО кода)

---

## 🎯 Цель Commit 2

Реализовать **group + category + interpretation** логику, строго по домену и Qoder audit, без самодеятельности.

---

## 1️⃣ `_auto_group()` — приоритеты (ЖЁСТКО)

### ✅ Окончательный порядок приоритетов (подтверждено Qoder audit):

```
1. age < 12           → "too_young"    (высший приоритет)
2. 12 <= age < 13     → "child"        (высший приоритет)
3. 13 <= age <= 19    → "teen"         (высший приоритет)
4. age >= 60          → "elderly"      (высший приоритет)
5. pregnant == true AND gender == "female" → "pregnant"  (средний приоритет)
6. athlete == true    → "athlete"      (низкий приоритет)
7. else               → "general"      (default)
```

### ❓ Вопрос: **pregnant может переопределять elderly или нет?**

**✅ Ответ:** НЕТ. Age-based groups (too_young, child, teen, elderly) имеют **высший приоритет** и проверяются ПЕРВЫМИ.

**Примеры:**
- `age=65, gender=female, pregnant=true` → `group="elderly"` (age приоритетнее)
- `age=30, gender=female, pregnant=true` → `group="pregnant"` (pregnant приоритетнее athlete)
- `age=12, gender=female, pregnant=true` → `group="child"` (age приоритетнее pregnant)

**Источник:** Qoder audit, `bmi_core.py:auto_group()` (строки 136-143) — age checks идут ПЕРЕД pregnant.

---

## 2️⃣ Athlete detection — где именно логика?

### ✅ Решение: **в `_auto_group()` напрямую**

**Где:** Внутри `_auto_group()`, не в отдельной функции (чтобы не плодить helpers без необходимости).

**Логика athlete detection:**

1. **Проверка через `_normalize_bool_flag()`:**
   - Если `athlete` уже `bool` и `True` → athlete
   - Если `athlete` строка и входит в `_DEFAULT_YES_VALUES` → athlete

2. **Проверка через точные совпадения:**
   ```python
   athlete_strings = {"спортсмен", "спортсменка", "атлет", "атлетка", "athlete"}
   # ВАЖНО: "спорт" НЕ входит в список (слишком общее)
   if athlete_str in athlete_strings:
       return True
   ```

3. **Проверка через regex (legacy parity):**
   ```python
   import re
   athlete_pattern = re.search(r"спортсмен(ка)?|атлет(ка)?", athlete_str)
   if athlete_pattern:
       return True
   ```

**❓ Вопрос: Regex строгий или расширенный?**

**✅ Ответ:** **Строгий regex** `r"спортсмен(ка)?|атлет(ка)?"` (как в legacy).

**Что НЕ считается athlete:**
- `"спорт"` (слишком общее, не в legacy)
- `"тренируюсь"` (не в legacy)
- `"спортивный"` (не в legacy)

**Что считается athlete (regex найдёт внутри строки):**
- `"я спортсмен"` → regex найдёт "спортсмен" → athlete ✅
- `"он атлетка"` → regex найдёт "атлетка" → athlete ✅

**Источник:** Qoder audit, `bmi_core.py:131-133` — используется именно этот regex.

---

## 3️⃣ `_bmi_category()` — пороги (НЕ ТРОГАТЬ)

### ✅ Пороги зафиксированы (из Qoder audit):

**Adult (default):**
- `underweight`: `bmi < 18.5`
- `normal`: `18.5 <= bmi < 25.0`
- `overweight`: `25.0 <= bmi < 30.0`
- `obese_1`: `30.0 <= bmi < 35.0`
- `obese_2`: `35.0 <= bmi < 40.0`
- `obese_3`: `bmi >= 40.0`

**Elderly:**
- `underweight`: `bmi < 17.5`
- `normal`: `17.5 <= bmi < 26.0`
- остальные пороги как у adult

**Teen:**
- `underweight`: `bmi < 17.5`
- `normal`: `17.5 <= bmi < 24.5`
- остальные пороги как у adult

**Athlete:**
- `underweight`: `bmi < 18.5` (как adult)
- `normal`: `18.5 <= bmi < 27.0` (верхняя граница выше)
- остальные пороги как у adult

### ❓ Вопрос 1: Для `elderly + athlete` — какие пороги?

**✅ Ответ:** Используем пороги **elderly** (age приоритетнее athlete для порогов).

**Логика:**
- Если `age >= 60` → `age_band="elderly"` → используем elderly пороги
- `group` может быть `"athlete"`, но пороги берём по `age_band`

**Пример:**
- `age=65, athlete=true, bmi=25.5` → `group="athlete"`, `age_band="elderly"`, `category="normal"` (elderly threshold 26.0)

**Источник:** Qoder audit — пороги определяются по `age` и `group`, но `age_band` имеет приоритет.

### ❓ Вопрос 2: Для `athlete` есть ли `underweight`?

**✅ Ответ:** ДА, `underweight` есть для athlete (порог `18.5`, как у adult).

**Логика:**
- `bmi < 18.5` → `underweight` (для всех групп, кроме elderly/teen, где `17.5`)
- `18.5 <= bmi < 27.0` → `normal` (для athlete)
- `bmi >= 27.0` → `overweight` и выше

**Источник:** `bmi_core.py:bmi_category()` (строки 79-94) — athlete использует `ATHLETE_BMI_MAX=27.0` только для верхней границы normal.

---

## 4️⃣ `category = None` — финальный список

### ✅ Строгий список (подтверждено Qoder audit):

1. `too_young` → `category = None` ✅
2. `child` → `category = None` ✅
3. `teen` → `category = None` ✅
4. `pregnant` → `category = None` ✅

### ❓ Вопрос: Есть ли ещё группы, где category должна быть None?

**✅ Ответ:** НЕТ. Только эти 4 случая.

**Логика:**
- `elderly` → category определяется (с особыми порогами)
- `athlete` → category определяется (с особыми порогами)
- `general` → category определяется (стандартные пороги)

**Источник:** Qoder audit, `app/schemas/bmi.py:131-140` — только эти 4 случая.

---

## 5️⃣ `_group_display_name()` — i18n или таблица?

### ✅ Решение: **таблица в Commit 2, i18n в Commit 5** (канон)

**Подход для Commit 2:** Использовать **локальную таблицу** (как в legacy), без новых i18n ключей.

**Причина:**
- Commit 2 должен быть "domain parity & logic", а не "i18n migration"
- Иначе рискуем сломать CI из-за отсутствующих ключей в RU/EN/ES
- i18n ключи добавим в Commit 5 (i18n keys)

**Таблица для Commit 2:**
```python
GROUP_DISPLAY_NAMES = {
    "general": {"ru": "общая", "en": "general", "es": "general"},
    "athlete": {"ru": "спортсмен", "en": "athlete", "es": "atleta"},
    "pregnant": {"ru": "беременная", "en": "pregnant", "es": "embarazada"},
    "elderly": {"ru": "пожилой", "en": "elderly", "es": "anciano"},
    "child": {"ru": "ребёнок", "en": "child", "es": "niño"},
    "teen": {"ru": "подросток", "en": "teenager", "es": "adolescente"},
    "too_young": {"ru": "слишком юный", "en": "too young", "es": "muy joven"},
}
```

**В Commit 5:** Добавим i18n ключи и переведём на `core.i18n.t()`.

**Источник:** Qoder audit — `bmi_core.py:group_display_name()` (строки 181-195) использует таблицу.

---

## 6️⃣ `_interpretation()` — структура строки

### ✅ Формат (из TODO):

```
"{category}. {note}"
```

**Если `category=None`:**
- Возвращаем **только note** (без префикса "None. ")
- Если note нет → возвращаем пустую строку `""`

**Если `category` есть:**
- Формат: `"{category}. {note}"` (если note есть)
- Формат: `"{category}"` (если note нет)

### ❓ Вопрос 1: Если `category=None` — что возвращаем?

**✅ Ответ:** **Только note** (медицинский дисклеймер).

**Примеры:**
- `pregnant, category=None` → `interpretation = t(lang, "bmi_not_valid_during_pregnancy")`
- `too_young, category=None` → `interpretation = t(lang, "risk_child_note")`
- `teen, category=None` → `interpretation = t(lang, "risk_teen_note")`

**Источник:** Qoder audit — notes используются для медицинских дисклеймеров.

### ❓ Вопрос 2: Может ли быть несколько notes?

**✅ Ответ:** НЕТ, в Commit 2 только **один note** на группу.

**Логика:**
- Каждая группа имеет **один основной note** (через i18n ключ)
- Если нужно несколько notes → это будет в Commit 3 (orchestrator собирает notes из разных источников)

**Порядок notes (если будет несколько в будущем):**
- Сначала group note (athlete, elderly, etc.)
- Потом waist risk notes (если есть)
- Склеиваем через `. ` (точка + пробел)

**Источник:** Qoder audit — в `BMICalculateResult.notes` может быть tuple, но в `interpretation` — одна строка.

---

## 7️⃣ Языки (важно для Commit 2)

### ✅ Подтверждено:

- **RU / EN / ES** — обязательны для всех локализованных строк
- **Fallback** — через `core.i18n.normalize_lang()` (уже реализовано)
- **Никаких строк "напрямую"** в коде — только через `core.i18n.t()`

### ❓ Вопрос: Допускаем ли временно отсутствие ключа в одном языке?

**✅ Ответ:** **НЕТ**, тесты должны падать, если ключ отсутствует.

**Логика:**
- `core.i18n.t()` уже имеет fallback логику (если ключ не найден, возвращает ключ)
- Но для Commit 2 мы должны **гарантировать**, что все ключи существуют в RU/EN/ES
- Если ключа нет → это баг, тест должен упасть

**Проверка:**
- В тестах проверить все 3 языка для каждого ключа
- Если ключ отсутствует → тест падает с понятной ошибкой

---

## 8️⃣ Тесты Commit 2 — минимальный набор

### ✅ Зафиксированный список тестов:

1. **`test_auto_group_priority()`**
   - Проверить все приоритеты: age > pregnant > athlete
   - Edge cases: age=12, age=13, age=19, age=60

2. **`test_auto_group_pregnant_vs_athlete()`**
   - `pregnant=true, athlete=true` → `group="pregnant"` (pregnant приоритетнее)
   - `pregnant=false, athlete=true` → `group="athlete"`

3. **`test_auto_group_athlete_detection()`**
   - Regex: `"спортсмен"`, `"атлетка"`, `"я спортсмен"` → `group="athlete"`
   - Не athlete: `"спорт"`, `"тренируюсь"` → `group="general"`

4. **`test_bmi_category_adult_thresholds()`**
   - Пороги: 18.5, 25.0, 30.0, 35.0, 40.0
   - Edge cases: 18.49, 18.5, 24.99, 25.0, 29.99, 30.0

5. **`test_bmi_category_elderly_thresholds()`**
   - Пороги: 17.5, 26.0
   - Edge cases: 17.49, 17.5, 25.99, 26.0

6. **`test_bmi_category_teen_thresholds()`**
   - Пороги: 17.5, 24.5
   - Edge cases: 17.49, 17.5, 24.49, 24.5

7. **`test_bmi_category_athlete_thresholds()`**
   - Пороги: 18.5, 27.0
   - Edge cases: 18.49, 18.5, 26.99, 27.0

8. **`test_bmi_category_none_for_youth_and_pregnant()`**
   - `too_young` → `None`
   - `child` → `None`
   - `teen` → `None`
   - `pregnant` → `None`

9. **`test_group_display_name_all_languages()`**
   - Все группы, все языки (RU/EN/ES)
   - Проверка, что ключи существуют

10. **`test_interpretation_with_and_without_notes()`**
    - С category и note: `"{category}. {note}"`
    - С category без note: `"{category}"`
    - Без category с note: `"{note}"`
    - Без category без note: `""`

11. **`test_auto_group_elderly_pregnant_is_elderly()`**
    - `age=65, gender=female, pregnant=true` → `group="elderly"` (age приоритетнее pregnant)
    - Закрепляет invariant: "pregnant не переопределяет elderly"

---

## 📌 Итоговые решения для Commit 2

### ✅ Зафиксировано:

1. **Приоритеты:** age > pregnant > athlete (age-based группы имеют высший приоритет)
2. **Athlete detection:** в `_auto_group()` с regex `r"спортсмен(ка)?|атлет(ка)?"`
3. **Пороги:** строго по Qoder audit (не менять)
4. **category=None:** только для too_young, child, teen, pregnant
5. **group_display_name:** через таблицу в Commit 2, i18n ключи в Commit 5
6. **interpretation:** `"{category}. {note}"` или только note, если category=None
7. **Языки:** RU/EN/ES обязательны, тесты падают при отсутствии ключей
8. **Тесты:** 10 минимальных тестов (см. список выше)

---

## 🚀 Готовность к реализации

**Все решения зафиксированы ДО кода.**

**Следующий шаг:** Реализация Commit 2 по этим решениям.

