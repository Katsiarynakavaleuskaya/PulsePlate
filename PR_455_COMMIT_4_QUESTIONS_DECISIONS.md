# PR-455 — Commit 4: Questions & Decisions Checklist

**Цель Commit 4:** Зафиксировать golden parity tests (legacy vs engine) и добавить anti-duplication guard test.

**GitHub PR:** #468

---

## ✅ Решения (финальные, для реализации)

### 1️⃣ Legacy Reference — ✅ РЕШЕНО

**Вопрос:** Какой entrypoint у legacy используем для сравнения?

**Решение:** **`bmi_core.py` как oracle**

**Обоснование:**
- `bmi_core.py` — чистая доменная логика без FastAPI зависимостей
- Содержит функции: `bmi_value()`, `bmi_category()`, `waist_risk()`
- Легко использовать в unit-тестах без поднятия всего приложения
- `legacy_app.py` использует `bmi_core.bmi_category` внутри, так что это тот же источник истины

**Функции для parity:**
- `bmi_core.bmi_value(weight_kg, height_m)` → BMI (round 1 decimal)
- `bmi_core.bmi_category(bmi, lang, age, group)` → category string or None
- `bmi_core.waist_risk(waist_cm, gender_male, lang)` → risk string or None
- `bmi_core` group logic (athlete/pregnant/elderly detection)

**Выход:** Helper функция `_legacy_calculate_bmi(inputs) -> dict` в тестах, которая вызывает `bmi_core` функции.

---

### 2️⃣ Golden Matrix — ✅ РЕШЕНО

**Вопрос:** Какие кейсы обязательны?

**Решение:** **12–15 golden cases** (баланс между coverage и скоростью)

**Обязательные кейсы:**

1. **Age boundaries:**
   - `age=11` → `too_young`, `category=None`
   - `age=12` → `child`, `category=None`
   - `age=13` → `teen`, `category=None`
   - `age=19` → `teen`, `category=None`
   - `age=20` → `adult`, `category=normal`
   - `age=60` → `elderly`, `category=normal` (elderly threshold)

2. **Groups:**
   - `pregnant=True, female, age=30` → `pregnant`, `category=None`
   - `athlete=True, age=30` → `athlete`, `category=normal` (athlete threshold)
   - `elderly+pregnant` → `elderly` (age priority)

3. **BMI categories:**
   - `bmi=18.4, adult` → `underweight`
   - `bmi=22.0, adult` → `normal`
   - `bmi=27.0, adult` → `overweight`
   - `bmi=32.0, adult` → `obesity_1`
   - `bmi=25.5, elderly` → `normal` (elderly threshold < 26.0)
   - `bmi=26.9, athlete` → `normal` (athlete threshold < 27.0)

4. **Waist risk:**
   - `waist_cm=95, male` → `waist_risk` present
   - `waist_cm=85, female` → `waist_risk` present
   - `waist_cm=None` → `waist_risk=None`

5. **Languages:**
   - `lang="ru"` → category localized
   - `lang="en"` → category localized
   - `lang="es"` → category localized
   - `lang="en-US"` → normalized to "en"

**Выход:** Таблица кейсов в `test_bmi_engine_golden_parity.py` с параметризацией.

---

### 3️⃣ Strict vs Semantic Comparison — ✅ РЕШЕНО

**Вопрос:** Что сравниваем строго, а что семантически?

**Решение:**

**Strict comparison (exact match):**
- `bmi`: exact float with 1 decimal
- `group`: exact string match
- `category`: exact string or None
- `wht_ratio`: exact float with 2 decimals or None
- `age_band`: exact string match

**Semantic comparison (presence/meaning):**
- `waist_risk.risk_level`: compare presence and level code (low/moderate/high)
- `notes`: compare "not empty" and key substrings (if texts differ)
- `interpretation`: check that contains category string (if category not None)

**Helper functions:**
```python
def assert_strict_fields_equal(engine_result, legacy_result):
    """Compare strict fields: bmi, group, category, wht_ratio, age_band."""
    assert engine_result.bmi == legacy_result["bmi"]
    assert engine_result.group == legacy_result["group"]
    assert engine_result.category == legacy_result.get("category")
    # ... etc

def assert_semantic_fields_ok(engine_result, legacy_result):
    """Compare semantic fields: waist_risk, notes, interpretation."""
    # waist_risk presence and risk_level
    # notes presence and key substrings
    # interpretation contains category
```

**Выход:** Helper asserts в `tests/_helpers/parity_asserts.py` или inline в тестах.

---

### 4️⃣ Parity Implementation — ✅ РЕШЕНО

**Вопрос:** Как избежать хрупкости тестов?

**Решение:** **Legacy-as-oracle pattern**

**Паттерн:**
1. В тесте вычисляем legacy результат через `bmi_core` функции
2. Вычисляем engine результат через `calculate_bmi_result()`
3. Сравниваем по strict subset полей

**Преимущества:**
- Меньше ручных expected значений
- Любые изменения в legacy сразу подсветят divergence
- Тесты не "подстраиваются" под engine

**Выход:** Функция `_legacy_calculate_bmi()` внутри тестового файла.

---

### 5️⃣ Anti-duplication Guard Test — ✅ РЕШЕНО

**Вопрос:** Что считать "BMI math" и где запрещено?

**Решение:**

**Whitelist путей:**
- `core/bmi/**` ✅ (canonical location)
- `tests/**` ✅ (test code allowed)
- `legacy_app.py` ✅ (temporary, until PR-456)
- `docs/**` ✅ (documentation formulas OK)
- `bmi_core.py` ✅ (legacy reference, temporary)

**Forbidden patterns (regex):**
1. BMI formula: `weight_kg\s*/\s*\(\s*height(_m|_cm)?\s*\*\*\s*2`
2. BMI thresholds: `\b18\.5\b|\b25\.0\b|\b30\.0\b|\b35\.0\b|\b40\.0\b|\b17\.5\b|\b26\.0\b|\b27\.0\b|\b24\.5\b`
3. WHtR formula: `waist(_cm)?\s*/\s*100(\.0)?\s*/\s*height_m` or `wht(r|_ratio)`

**Guard test behavior:**
- Scan all `.py` files (except whitelist)
- Report matches with file:line
- Fail with readable message
- Not too strict: allow comments/docs

**Выход:** `tests/test_no_bmi_math_outside_core.py` с regex patterns и whitelist.

---

### 6️⃣ Test Structure — ✅ РЕШЕНО

**Файлы:**
1. `tests/test_bmi_engine_golden_parity.py` — golden parity tests
2. `tests/test_no_bmi_math_outside_core.py` — anti-duplication guard

**Тесты в golden parity:**
1. `test_golden_parity_matrix_strict_fields()` — параметризованный тест на 12–15 кейсов
2. `test_golden_parity_waist_risk_semantic()` — 2–3 кейса male/female waist risk
3. `test_golden_parity_language_normalization()` — lang normalization (en-US → en)

**Тесты в guard:**
1. `test_no_bmi_formula_outside_core()` — scan for BMI formula
2. `test_no_bmi_thresholds_outside_core()` — scan for threshold constants
3. `test_no_whtr_formula_outside_core()` — scan for WHtR formula

---

### 7️⃣ Non-goals Commit 4 — ✅ ЗАФИКСИРОВАНО

**Что НЕ делаем:**
- ❌ Менять engine / thresholds / risk
- ❌ Трогать router/API
- ❌ i18n migration (Commit 5)
- ❌ Удалять legacy BMI (PR-456)
- ❌ Сравнивать exact strings для notes/interpretation (только semantic)

---

## 📋 Итоговый чек-лист для реализации

### Код

- [ ] Создать `tests/test_bmi_engine_golden_parity.py`:
  - [ ] Helper `_legacy_calculate_bmi(inputs) -> dict`
  - [ ] Helper `assert_strict_fields_equal()`
  - [ ] Helper `assert_semantic_fields_ok()`
  - [ ] `test_golden_parity_matrix_strict_fields()` (12–15 кейсов)
  - [ ] `test_golden_parity_waist_risk_semantic()` (2–3 кейса)
  - [ ] `test_golden_parity_language_normalization()` (lang aliases)

- [ ] Создать `tests/test_no_bmi_math_outside_core.py`:
  - [ ] Whitelist paths
  - [ ] Regex patterns для BMI formula
  - [ ] Regex patterns для thresholds
  - [ ] Regex patterns для WHtR
  - [ ] `test_no_bmi_formula_outside_core()`
  - [ ] `test_no_bmi_thresholds_outside_core()`
  - [ ] `test_no_whtr_formula_outside_core()`

### Проверки

- [ ] Все тесты проходят
- [ ] Guard test не падает на whitelist файлах
- [ ] Guard test падает на forbidden patterns (если есть тестовый файл)

---

## 🎯 Commit Message

```
test(bmi): add golden parity tests and anti-duplication guard

- Add golden parity tests: legacy (bmi_core) vs engine (12-15 cases)
- Compare strict fields: bmi, group, category, wht_ratio, age_band
- Compare semantic fields: waist_risk, notes, interpretation
- Add anti-duplication guard: scan for BMI math outside core/bmi/*
- Whitelist: core/bmi/, tests/, legacy_app.py, docs/, bmi_core.py

PR-455 (GitHub #468) Commit 4
```

---

## ✅ Готово к реализации

Все вопросы решены, решения зафиксированы. Можно приступать к коду.

**Legacy oracle:** `bmi_core.py` (чистая доменная логика, легко использовать в тестах).

