# PR-455 — Commit 3: Questions & Decisions Checklist

**Цель Commit 3:** Реализовать `calculate_bmi_result()` как orchestrator, который собирает `BMICalculateResult` используя helpers (Commit 1–2) и интегрирует waist risk.

**GitHub PR:** #468

---

## 🔐 Security Notes (Canonical)

### 1) Ошибки: fail-loud только для валидации, без утечек

**Политика:**
- Orchestrator (`calculate_bmi_result`) кидает **только `ValueError`** с **короткими фиксированными сообщениями**:
  - `"weight_kg must be positive"`
  - `"height_cm must be positive"`
  - `"age must be between 1 and 120"`
  - `"BMI out of valid range (10-100)"`

**Почему это безопасно:**
- сообщения **не содержат** `str(e)`, stacktrace, внутренних деталей
- API слой (router) сам локализует и формирует error envelope

✅ **Гарантия:** никаких "случайных" утечек исключений наружу через orchestrator.

---

### 2) Waist risk: fail-soft ограничен строго этим шагом

**Политика:**
- интеграция `calculate_waist_risk()` — **fail-soft**:
  - любые ошибки во время расчёта waist risk → `waist_risk=None`
- fail-soft НЕ применяется ко всему orchestrator (только к risk-интеграции)

**Почему это безопасно:**
- risk модуль может иметь дрейф сигнатуры/внутренние ошибки
- но мы не позволяем этому:
  - ломать BMI расчёт
  - приводить к падениям API
  - раскрывать детали исключений

✅ **Гарантия:** BMI результат доступен даже если risk модуль временно деградировал.

---

### 3) Локализованные тексты: только из `waist_risk.notes`

**Политика:**
- `notes` в Commit 3 наполняются **только** из `waist_risk.notes`
- orchestrator **не генерирует** user-facing строки, кроме интерпретации `category` (техническая строка)

**Почему это безопасно:**
- исключаем риск несанкционированных/непроверенных пользовательских текстов
- исключаем несогласованные i18n-строки до Commit 5

✅ **Гарантия:** все user-facing notes проходят через доменный модуль risk (где уже заложена локализация и формулировки).

---

### 4) Determinism & side effects: no I/O, no env, no time

**Политика:**
- orchestrator использует только:
  - чистые helper-функции (Commit 1–2)
  - `core.bmi.risk.calculate_waist_risk` (локальный импорт)
- **нет**:
  - файлов/сети
  - `os.environ`
  - времени/рандома
  - логирования с пользовательскими данными

✅ **Гарантия:** воспроизводимость, отсутствие скрытых каналов утечки, соответствие repo-policy.

---

### 5) Данные пользователя: минимизация и безопасные типы

**Политика:**
- работаем только с числовыми параметрами и короткими enum-like строками
- все значения нормализуются:
  - `lang` → canonical Language
  - `gender` → `male|female` (legacy parity)
- `notes` фильтруются: только `str` и только непустые

✅ **Гарантия:** защищаемся от неожиданного типа/инъекции через нестрогий ввод.

---

### 6) "Known debt" (зафиксировано и изолировано)

**Осознанно оставляем:**
- дублирование `_normalize_bool_flag` в router → **PR-456**
- возможный legacy-импорт внутри `core/bmi/risk.py` (`bmi_core`) → **не расширяем scope Commit 3**, фикс позже отдельным PR

✅ **Гарантия:** долг отмечен, но не смешивается с BMI canonical engine PR.

---

### ✅ Security Acceptance Criteria (для ревью)

Перед merge Commit 3 считаем security OK, если:

- [ ] в orchestrator нет `str(e)` / traceback в сообщениях ошибок
- [ ] fail-soft применяется **только** к waist risk интеграции
- [ ] `notes` берутся только из `waist_risk.notes`
- [ ] нет I/O, env, time, random
- [ ] все тесты зелёные + mypy/ruff зелёные

---

---

## ✅ Решения (финальные, для реализации)

### 1️⃣ Input Normalization — ✅ РЕШЕНО

**Вопрос:** Что приходит в engine и кто нормализует?

**Решение:**
- `pregnant` / `athlete`: уже приходят как `bool` (router нормализует в PR-454)
- `lang`: может быть `None` → прогоняем через `_normalize_lang(lang)` (helper принимает `Optional[str]`)
- `gender`: может быть пустым → прогоняем через `_normalize_gender(gender)` (fallback "male")
- `height_cm`: конвертируем в `height_m = height_cm / 100.0` и валидируем
- `waist_cm`: передаём в `_compute_wht_ratio()` и `calculate_waist_risk()` без падений

**Выход:** Orchestrator fail-safe, но не молчаливый (errors → ValueError).

---

### 2️⃣ Ошибки и исключения — ✅ РЕШЕНО

**Вопрос:** Как orchestrator реагирует на плохие входы?

**Решение:**
- Orchestrator **кидает `ValueError`** с коротким сообщением (без i18n)
- Router/adapter слой отвечает за user-facing i18n ошибок
- Валидация:
  - `weight_kg <= 0` → `ValueError("weight_kg must be positive")`
  - `height_cm <= 0` → `ValueError("height_cm must be positive")`
  - `age < 1 or age > 120` → `ValueError("age must be between 1 and 120")` (или использовать Pydantic bounds)
  - BMI bounds: `bmi < 10 or bmi > 100` → `ValueError("BMI out of valid range (10-100)")`

**Выход:** Unit-тесты на `ValueError` для грубой валидации.

---

### 3️⃣ BMI Calculation — ✅ РЕШЕНО

**Вопрос:** Где проверяем "реалистичные bounds" BMI (10..100)?

**Решение:**
- BMI rounding уже решён (1 decimal) → используем `_compute_bmi()`
- **BMI bounds check в orchestrator** (после `_compute_bmi()`, перед использованием BMI)
- При выходе за bounds → `ValueError("BMI out of valid range (10-100)")`

**Выход:** Тесты на bounds (BMI < 10, BMI > 100).

---

### 4️⃣ Pipeline Ordering — ✅ РЕШЕНО

**Вопрос:** В каком порядке вызываем функции?

**Решение (канонический pipeline):**

```python
def calculate_bmi_result(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    pregnant: bool,
    athlete: bool,
    waist_cm: float | None,
    lang: str,
) -> BMICalculateResult:
    # Step 1: Input validation
    if weight_kg <= 0:
        raise ValueError("weight_kg must be positive")
    if height_cm <= 0:
        raise ValueError("height_cm must be positive")
    if age < 1 or age > 120:
        raise ValueError("age must be between 1 and 120")

    # Step 2: Normalization
    lang_norm = _normalize_lang(lang)
    gender_norm = _normalize_gender(gender)
    height_m = height_cm / 100.0

    # Step 3: BMI calculation
    bmi = _compute_bmi(weight_kg, height_m)

    # Step 4: BMI bounds validation
    if bmi < 10.0 or bmi > 100.0:
        raise ValueError("BMI out of valid range (10-100)")

    # Step 5: Age band
    age_band = _age_band(age)

    # Step 6: Group determination
    group = _auto_group(
        age=age,
        gender=gender_norm,
        pregnant=pregnant,
        athlete=athlete,
        athlete_text=None,  # Commit 3: no text input yet
    )

    # Step 7: Category determination
    category = _bmi_category(bmi=bmi, age=age, group=group)

    # Step 8: Group display name
    group_display = _group_display_name(group, lang_norm)

    # Step 9: WHtR calculation (fail-soft)
    wht_ratio = _compute_wht_ratio(waist_cm, height_m)

    # Step 10: Waist risk calculation (fail-soft)
    waist_risk = None
    if waist_cm is not None:
        try:
            from core.bmi.risk import calculate_waist_risk
            waist_risk = calculate_waist_risk(
                waist_cm=waist_cm,
                height_m=height_m,
                gender=gender_norm,
                lang=lang_norm,
            )
        except Exception:
            # Fail-soft: any error → None
            waist_risk = None

    # Step 11: Notes aggregation
    notes: list[str] = []
    if waist_risk and waist_risk.notes:
        notes.extend(waist_risk.notes)
    # Commit 3: no other notes yet (Commit 5 will add i18n keys)

    # Step 12: Interpretation
    note_str = ". ".join(notes) if notes else None
    interpretation = _interpretation(category=category, note=note_str)

    # Step 13: Category string conversion
    category_str: str | None = str(category) if category else None

    # Step 14: Return result
    return BMICalculateResult(
        bmi=bmi,
        category=category_str,
        group=group,
        group_display=group_display,
        interpretation=interpretation,
        wht_ratio=wht_ratio,
        waist_risk=waist_risk,
        notes=tuple(notes),
        age_band=age_band,
    )
```

**Выход:** Один guard-test на ordering (чтобы никто не поменял порядок).

---

### 5️⃣ Notes — ✅ РЕШЕНО

**Вопрос:** Что кладём в `notes` и в каком порядке?

**Решение:**
- В Commit 3: `notes` собираем **только из `waist_risk.notes`** (если есть)
- Notes — это готовые строки из `WaistRiskResult` (уже локализованы в `core/bmi/risk.py`)
- Если `waist_risk is None` или `waist_risk.notes` пустые → `notes=()`
- Commit 5 добавит i18n ключи для других notes (athlete, disclaimer, etc.)

**Выход:** Notes deterministic, без дублирования i18n строк в core.

---

### 6️⃣ Waist Risk — ✅ РЕШЕНО: **RISK СЕЙЧАС**

**Вопрос:** Делаем risk сейчас или позже?

**Решение:** **RISK СЕЙЧАС**

**Обоснование:**
- ✅ `core/bmi/risk.py` уже существует и стабилен
- ✅ `calculate_waist_risk()` готова к использованию
- ✅ TODO checklist явно указывает на это в Commit 3 (шаг 9)
- ✅ Qoder audit рекомендует интеграцию в Commit 3
- ✅ Это часть канонического домена BMI (не расширяет scope)
- ⚠️ `core/bmi/risk.py` использует `from bmi_core import compute_wht_ratio` (legacy) — но это не критично для Commit 3, можно оставить как есть

**Реализация:**
- Вызываем `calculate_waist_risk(waist_cm, height_m, gender_norm, lang_norm)`
- Fail-soft: любые ошибки → `waist_risk = None`
- Если `waist_cm is None` → `waist_risk = None`

**Выход:** Тесты на waist risk (с waist и без).

---

### 7️⃣ BMICalculateResult — ✅ РЕШЕНО

**Вопрос:** Соответствие полям и типам?

**Решение:**
- `category`: `BMICategory | None` (из `_bmi_category`) → конвертируем в `str | None` для dataclass
- `group`: `BMIGroup` (Literal) → уже `str`
- `group_display`: `str` (из `_group_display_name`)
- `interpretation`: `str` (из `_interpretation`)
- `age_band`: `AgeBand` (Literal) → уже `str`
- `waist_risk`: `WaistRiskResult | None` (из `calculate_waist_risk`)
- `notes`: `tuple[str, ...]` (собираем из `waist_risk.notes`)

**Выход:** mypy проходит без `type: ignore`.

---

### 8️⃣ Тесты Commit 3 — ✅ РЕШЕНО

**Минимальный набор (must-have):**

1. `test_calculate_bmi_result_adult_general_happy_path()`
   - age=30, general, category="normal", group_display="General" (EN), interpretation содержит "normal"

2. `test_calculate_bmi_result_teen_category_none()`
   - age=19 → group="teen" → category=None → interpretation note-only/empty

3. `test_calculate_bmi_result_pregnant_female_group()`
   - female + pregnant=True → group="pregnant" → category=None

4. `test_calculate_bmi_result_elderly_priority_over_pregnant()`
   - age=65 + pregnant=True → group="elderly" (age priority)

5. `test_calculate_bmi_result_wht_ratio_none_when_invalid()`
   - waist present but height invalid → wht_ratio=None (fail-soft)

6. `test_calculate_bmi_result_waist_risk_present()`
   - waist_cm=95, male → waist_risk present with risk_level

7. `test_calculate_bmi_result_waist_risk_none_when_no_waist()`
   - waist_cm=None → waist_risk=None

8. `test_calculate_bmi_result_invalid_weight_raises()`
   - weight_kg=0 → ValueError

9. `test_calculate_bmi_result_invalid_height_raises()`
   - height_cm=0 → ValueError

10. `test_calculate_bmi_result_bmi_bounds_raises()`
    - BMI < 10 or BMI > 100 → ValueError

11. `test_calculate_bmi_result_notes_from_waist_risk()`
    - waist_risk with notes → notes populated in result

---

### 9️⃣ Non-goals Commit 3 — ✅ ЗАФИКСИРОВАНО

**Что НЕ делаем в Commit 3:**
- ❌ i18n ключи для categories/groups (это Commit 5)
- ❌ Правки router (уже сделано в PR-454)
- ❌ PRO/VIP логика
- ❌ Новые thresholds/формулы
- ❌ Рефактор `core/bmi/risk.py` (legacy импорт `bmi_core` оставляем как есть)
- ❌ `athlete_text` input (Commit 3: только `athlete` bool)

---

## 📋 Итоговый чек-лист для реализации

### Код (`core/bmi/engine.py`)

- [ ] Реализовать `calculate_bmi_result()` с 14 шагами (см. пункт 4)
- [ ] Input validation (weight, height, age)
- [ ] Normalization (lang, gender)
- [ ] BMI calculation + bounds check
- [ ] Age band determination
- [ ] Group determination
- [ ] Category determination
- [ ] Group display name
- [ ] WHtR calculation (fail-soft)
- [ ] Waist risk calculation (fail-soft, с try/except)
- [ ] Notes aggregation (только из waist_risk)
- [ ] Interpretation formatting
- [ ] Category string conversion
- [ ] Return `BMICalculateResult` с корректными типами

### Тесты (`tests/test_bmi_engine_commit3.py`)

- [ ] 11 тестов (см. пункт 8)
- [ ] Все тесты проходят
- [ ] mypy без ошибок
- [ ] ruff без ошибок

### Проверки перед коммитом

- [ ] `pytest -q tests/test_bmi_engine_commit3.py`
- [ ] `mypy core/bmi/engine.py`
- [ ] `ruff check core/bmi/engine.py tests/test_bmi_engine_commit3.py`
- [ ] `pytest --cov=core.bmi.engine --cov-report=term-missing` (проверка покрытия)

---

## 🎯 Commit Message

```
feat(bmi): implement calculate_bmi_result orchestrator

- Implement 14-step pipeline: validation → normalization → calculation
- Integrate waist risk from core/bmi/risk.py (fail-soft)
- Return BMICalculateResult with all fields populated
- Domain validation: BMI must be 10-100 (raise ValueError)
- Notes aggregation from waist_risk.notes only

PR-455 (GitHub #468) Commit 3
```

---

## ✅ Готово к реализации

Все вопросы решены, решения зафиксированы. Можно приступать к коду.
