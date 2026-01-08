# PR-494 — Commit 1 Skeleton (Models + Validation)

## 🎯 Commit 1: `feat(bmi): add interpretation models and request validation`

### Файлы для создания/изменения

1. `core/bmi/interpretation_models.py` (новый)
2. `app/schemas/bmi.py` (добавить валидатор)
3. `tests/test_bmi_interpretation_validation.py` (новый)

---

## 📄 `core/bmi/interpretation_models.py`

```python
"""
BMI Interpretation Models

RU: Модели данных для интерпретации BMI результатов.
EN: Data models for BMI result interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, TypedDict, Union

# Semantic i18n key type alias (exported)
I18nKey = str

# Goal direction types
GoalDirection = Literal["maintain", "reduce", "increase", "medical_review"]

# Numeric target range
class NumericRange(TypedDict):
    """Numeric BMI target range."""

    min: float
    max: float


# Qualitative target types
QualitativeTarget = Literal[
    "age_appropriate_growth",
    "prenatal_guidelines",
]

# Target range union
TargetRange = Union[NumericRange, QualitativeTarget]


@dataclass(frozen=True)
class BMIInterpretation:
    """
    RU: Интерпретация BMI результата с рекомендациями и целями.
    EN: BMI result interpretation with recommendations and targets.

    All text fields are i18n keys (not translated strings).
    """

    goal_direction: GoalDirection
    target_range: Optional[TargetRange]
    risk_flags: tuple[I18nKey, ...]
    priority_notes: tuple[I18nKey, ...]
    disclaimers: tuple[I18nKey, ...]
```

---

## 📄 `app/schemas/bmi.py` (добавить валидатор)

**Место вставки:** После `lang: Language = Field(...)` в `BMICalculateRequest`, перед закрывающей скобкой класса.

```python
    @model_validator(mode="after")
    def validate_gender_pregnant(self) -> "BMICalculateRequest":
        """
        RU: Валидация: мужчина не может быть беременным.
        EN: Validation: males cannot be pregnant.

        Raises:
            ValueError: If gender is male and pregnant is True
        """
        # Local gender normalization (no import from core.bmi.engine)
        gender_str = (self.gender or "").strip().lower()
        is_female = (
            gender_str == "female"
            or gender_str.startswith("жен")
            or gender_str.startswith("mujer")
        )

        # Local pregnant normalization (simple bool check)
        pregnant_bool = False
        if isinstance(self.pregnant, bool):
            pregnant_bool = self.pregnant
        elif isinstance(self.pregnant, str):
            s = self.pregnant.strip().lower()
            pregnant_bool = s in {"yes", "y", "true", "1", "да", "д", "истина", "si", "sí"}

        # Validation: male + pregnant → error
        if not is_female and pregnant_bool:
            raise ValueError("Pregnancy is only applicable to females")

        return self
```

---

## 📄 `tests/test_bmi_interpretation_validation.py`

```python
"""
Tests for BMI interpretation validation.

RU: Тесты валидации запросов BMI (gender+pregnant).
EN: Tests for BMI request validation (gender+pregnant).
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app import app
from app.schemas.bmi import BMICalculateRequest


@pytest.fixture()
def client() -> TestClient:
    """TestClient fixture for BMI API tests."""
    return TestClient(app)


class TestGenderPregnantValidation:
    """Tests for gender+pregnant validation."""

    def test_male_pregnant_raises_validation_error(self) -> None:
        """
        RU: Мужчина с pregnant=True должен вызывать ValueError.
        EN: Male with pregnant=True must raise ValueError.
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="male",
                pregnant=True,
            )

    def test_male_pregnant_string_yes_raises_validation_error(self) -> None:
        """
        RU: Мужчина с pregnant="yes" должен вызывать ValueError.
        EN: Male with pregnant="yes" must raise ValueError.
        """
        with pytest.raises(ValueError, match="only applicable to females"):
            BMICalculateRequest(
                weight_kg=70.0,
                height_cm=175.0,
                age=30,
                gender="male",
                pregnant="yes",
            )

    def test_female_pregnant_validation_ok(self) -> None:
        """
        RU: Женщина с pregnant=True должна проходить валидацию.
        EN: Female with pregnant=True must pass validation.
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="female",
            pregnant=True,
        )
        assert req.gender == "female"
        assert req.pregnant is True

    def test_female_pregnant_string_yes_validation_ok(self) -> None:
        """
        RU: Женщина с pregnant="yes" должна проходить валидацию.
        EN: Female with pregnant="yes" must pass validation.
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="female",
            pregnant="yes",
        )
        assert req.gender == "female"

    def test_male_pregnant_false_validation_ok(self) -> None:
        """
        RU: Мужчина с pregnant=False должен проходить валидацию.
        EN: Male with pregnant=False must pass validation.
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            pregnant=False,
        )
        assert req.gender == "male"
        assert req.pregnant is False

    def test_male_pregnant_string_no_validation_ok(self) -> None:
        """
        RU: Мужчина с pregnant="no" должен проходить валидацию.
        EN: Male with pregnant="no" must pass validation.
        """
        req = BMICalculateRequest(
            weight_kg=70.0,
            height_cm=175.0,
            age=30,
            gender="male",
            pregnant="no",
        )
        assert req.gender == "male"

    def test_male_pregnant_api_returns_422(self, client: TestClient) -> None:
        """
        RU: API должен возвращать 422 для male+pregnant.
        EN: API must return 422 for male+pregnant.
        """
        payload = {
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",
            "pregnant": True,
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "only applicable to females" in resp.json()["detail"][0]["msg"].lower()

    def test_female_pregnant_api_returns_200(self, client: TestClient) -> None:
        """
        RU: API должен возвращать 200 для female+pregnant.
        EN: API must return 200 for female+pregnant.
        """
        payload = {
            "weight_kg": 65.0,
            "height_cm": 165.0,
            "age": 28,
            "gender": "female",
            "pregnant": True,
        }
        resp = client.post("/api/v1/bmi/calculate", json=payload)
        assert resp.status_code == status.HTTP_200_OK

    def test_gender_normalization_ru_female_validation_ok(self) -> None:
        """
        RU: Нормализация gender "жен" должна работать.
        EN: Gender normalization "жен" must work.
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="жен",
            pregnant=True,
        )
        # Validation should pass (not raise)

    def test_gender_normalization_es_female_validation_ok(self) -> None:
        """
        RU: Нормализация gender "mujer" должна работать.
        EN: Gender normalization "mujer" must work.
        """
        req = BMICalculateRequest(
            weight_kg=65.0,
            height_cm=165.0,
            age=28,
            gender="mujer",
            pregnant=True,
        )
        # Validation should pass (not raise)
```

---

## 🧪 Команды для проверки Commit 1

```bash
# 1. Локальная проверка типов и линт
make lint

# 2. Запуск тестов валидации
pytest -q tests/test_bmi_interpretation_validation.py -v

# 3. Быстрая проверка всех тестов
make test-fast

# 4. Проверка coverage для новых файлов
pytest --cov=core/bmi/interpretation_models --cov=app/schemas/bmi --cov-report=term-missing tests/test_bmi_interpretation_validation.py

# 5. Финальная проверка перед коммитом
make cov-check
```

---

## ✅ Checklist перед коммитом

- [ ] `core/bmi/interpretation_models.py` создан с правильными типами
- [ ] `app/schemas/bmi.py` содержит `validate_gender_pregnant()` без импорта из `core.bmi.engine`
- [ ] Все тесты проходят (`pytest -q tests/test_bmi_interpretation_validation.py`)
- [ ] API возвращает 422 для male+pregnant (проверено через TestClient)
- [ ] Линт чистый (`make lint`)
- [ ] Coverage для новых строк ≥100% (diff-cover)

---

## 📝 Commit message (готовый)

```
feat(bmi): add interpretation models and request validation

- Add BMIInterpretation dataclass with goal_direction, target_range, risk_flags, priority_notes, disclaimers
- Add gender+pregnant validation in BMICalculateRequest (local normalization, no engine import)
- Validation raises ValueError for male+pregnant → FastAPI returns 422
- Add comprehensive tests for validation (constructor + API level)

Part of PR-494: BMI targets / interpretation layer.
```
