# PR-494 — Final Scope (BMI Targets / Interpretation)

## ✅ Уточнения приняты + поправки

### Поправка A: Валидация pregnancy/male — без импорта из core.bmi.engine

**Решение:**
- Локальная нормализация gender в `app/schemas/bmi.py`
- Простая таблица маппинга (без вызова engine helpers)
- Fail-loud: ValueError → FastAPI автоматически → 422

### Поправка B: Pregnant interpretation

**Контракт (обновлён):**
- `pregnant` (без athlete) → `interpretation_v1` присутствует (`goal_direction: "medical_review"`, `target_range: "prenatal_guidelines"`)
- `pregnant + athlete` → `interpretation_v1` присутствует с дополнительными disclaimers (athlete + pregnancy)
- Только `too_young` → `interpretation_v1: null`

---

## 📋 Ответы на финальные вопросы

### 1. 422 message

**Ответ:** Стабильный текст `"Pregnancy is only applicable to females"` (английский, как в коде).
i18n ключ можно добавить позже отдельным коммитом, если потребуется.

### 2. Pregnant interpretation

**Ответ:** Подтверждаем контракт:
- `pregnant` (без athlete) → `interpretation_v1` присутствует (`goal_direction: "medical_review"`, `target_range: "prenatal_guidelines"`)
- `pregnant+athlete` → `interpretation_v1` присутствует с дополнительными disclaimers (athlete + pregnancy)
- Только `too_young` → `interpretation_v1: null`

### 3. Elderly threshold

**Ответ:** Проверено в `_age_band()`: `age >= 60` → `"elderly"`.
Выравниваем interpretation rules с этим порогом.

---

## 🧱 Финальный Scope (заморожен)

- Hybrid targets (как было)
- Athlete: maintain при норме, medical_review при экстремумах
- Child/Teen: maintain при норме, medical_review вне нормы
- Elderly (age >= 60): стабильность > снижение, increase допустим при low BMI
- API: всегда возвращаем interpretation (может быть null)
- Pregnant: всегда возвращает interpretation (с athlete или без)
- Gender+pregnant validation: локальная в схеме, без импорта из engine
- Elderly threshold: 60+ (как в `_age_band()`)

---

## 🗂️ Структура файлов (финальная)

```
core/bmi/
├─ interpretation_models.py    # dataclasses / TypedDicts
├─ interpretation_rules.py      # group-specific rules (pure functions)
├─ interpretation.py            # builder (build_interpretation)
└─ __init__.py

app/schemas/
└─ bmi.py                       # BMICalculateRequest validation + BMIInterpretationResponse

tests/
├─ test_bmi_interpretation_models.py
├─ test_bmi_interpretation_validation.py  # gender+pregnant validation
├─ test_bmi_interpretation_general.py
├─ test_bmi_interpretation_athlete.py
├─ test_bmi_interpretation_child_teen.py
├─ test_bmi_interpretation_elderly.py
├─ test_bmi_interpretation_pregnant.py
└─ test_bmi_interpretation_guards.py
```

---

## 🧾 Commit Plan (финальный)

### Commit 1: Models + Validation
- `core/bmi/interpretation_models.py`
- `app/schemas/bmi.py` — `validate_gender_pregnant()` (локальная нормализация)
- Tests: `test_male_pregnant_validation_422`, `test_female_pregnant_validation_ok`

### Commit 2: Rules
- `core/bmi/interpretation_rules.py`
- Все группы, включая pregnant+athlete

### Commit 3: Builder
- `core/bmi/interpretation.py`
- `build_interpretation(result, athlete: bool)`

### Commit 4: API
- Схемы response
- Router wiring
