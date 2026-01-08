# PR-494 — Updated Scope (BMI Targets / Interpretation)

## ✅ Уточнения приняты (критически важные)

### 1️⃣ Беременные могут быть атлетами

**Текущая логика:**
- В `_auto_group()`: `pregnant=True` + `gender="female"` → `group="pregnant"` (приоритет над athlete)
- Но для interpretation нужно учесть **оба фактора**

**Решение для PR-494:**
- Interpretation для `group="pregnant"` должен проверять `athlete` flag из исходного запроса
- Если `pregnant=True` + `athlete=True` → interpretation включает:
  - `risk_flags`: может включать `"athlete_body_composition"` (если применимо)
  - `priority_notes`: учитывает оба фактора (беременность + состав тела)
  - `disclaimers`: объединяет pregnancy + athlete disclaimers

**Структура данных:**
```python
# BMICalculateResult уже содержит group, но для interpretation нужен доступ к исходным флагам
# Решение: передавать athlete flag в build_interpretation() отдельно
def build_interpretation(
    result: BMICalculateResult,
    athlete: bool,  # исходный флаг из запроса
) -> BMIInterpretation | None:
    ...
    if result.group == "pregnant" and athlete:
        # Специальная логика для pregnant+athlete
```

---

### 2️⃣ Мужчина не может быть беременным (валидация)

**Проблема:**
- В `BMICalculateRequest` нет валидации `gender="male"` + `pregnant=True`
- Это создавало баг на сайте (мужчина получал group="pregnant")

**Решение для PR-494:**
- Добавить `@model_validator` в `BMICalculateRequest`:
  ```python
  @model_validator(mode="after")
  def validate_gender_pregnant(self) -> "BMICalculateRequest":
      gender_norm = _normalize_gender(self.gender)
      pregnant_bool = _normalize_bool_flag(self.pregnant)

      if gender_norm == "male" and pregnant_bool:
          raise ValueError("Pregnancy is only applicable to females")
      return self
  ```
- Это **fail-loud validation** на уровне схемы (до вызова engine)
- Тесты: добавить `test_male_pregnant_validation_raises_error`

---

## 🧱 Обновлённый Scope PR-494

### Что добавляем

1. **BMIInterpretation models** (как было)
2. **Interpretation rules** с учётом:
   - `pregnant + athlete` комбинации
   - Всех групп (child, teen, general, athlete, elderly, pregnant)
3. **Gender+pregnant validation** в `BMICalculateRequest`
4. **Builder** который принимает `athlete` flag отдельно для pregnant+athlete логики

### Что НЕ меняем

- ❌ Не меняем `_auto_group()` логику (group остаётся "pregnant" для беременных)
- ❌ Не меняем BMI математику
- ❌ Не меняем категории

---

## 🧪 Обновлённый Test Plan

### Новые тесты (обязательные)

1. **Gender+pregnant validation:**
   ```python
   def test_male_pregnant_raises_validation_error():
       with pytest.raises(ValueError, match="only applicable to females"):
           BMICalculateRequest(
               weight_kg=70, height_cm=175, age=25,
               gender="male", pregnant=True
           )
   ```

2. **Pregnant+athlete interpretation:**
   ```python
   def test_interpretation_pregnant_athlete():
       result = BMICalculateResult(..., group="pregnant", ...)
       interpretation = build_interpretation(result, athlete=True)
       assert "athlete_body_composition" in interpretation.risk_flags or ...
   ```

3. **Female+pregnant validation passes:**
   ```python
   def test_female_pregnant_validation_passes():
       req = BMICalculateRequest(..., gender="female", pregnant=True)
       assert req.gender == "female"
       assert _normalize_bool_flag(req.pregnant) is True
   ```

---

## 🔐 Security & Ethics (обновлено)

- ✅ **Gender validation** предотвращает некорректные медицинские интерпретации
- ✅ **Pregnant+athlete** учитывает оба фактора без смешения рекомендаций
- ✅ Все disclaimers усилены для комбинированных случаев

---

## 📌 Commit Plan (обновлён)

**Commit 1 — models + validation:**
- `interpretation_models.py`
- `BMICalculateRequest` validation (gender+pregnant)

**Commit 2 — rules:**
- `interpretation_rules.py`
- Специальная логика для `pregnant + athlete`

**Commit 3 — builder:**
- `interpretation.py`
- Принимает `athlete` flag отдельно

**Commit 4 — API:**
- Схемы (keys only)

---

## ✅ Scope заморожен (финальный)

- Hybrid targets (как было)
- Athlete: maintain при норме, medical_review при экстремумах
- Child/Teen: maintain при норме, medical_review вне нормы
- Elderly: стабильность > снижение
- API: всегда возвращаем interpretation (может быть null)
- **NEW:** Pregnant+athlete комбинация учитывается в interpretation
- **NEW:** Gender+pregnant validation в схеме (fail-loud)
