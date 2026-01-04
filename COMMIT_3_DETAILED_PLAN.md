# Commit 3: Add BMI Schemas (API Contract) - Подробный план

## 📋 Что уже есть в проекте

### ✅ Существующие компоненты

1. **`core/i18n.py`**:
   - `Language = Literal["ru", "en", "es"]` — уже определен
   - Используется в других схемах (`app/schemas/bmr.py`)

2. **`app/schemas/bmr.py`** — пример структуры:
   ```python
   from core.i18n import Language
   from pydantic import BaseModel, Field
   ```

3. **`legacy_app.py`** — существующие BMI схемы (НЕ в `app/schemas/`):
   - `BMIRequest` — использует `height_m`, имеет `premium`, `include_chart`
   - `BMIRequestV1` — использует `height_cm`, более простой

4. **`app/routers/bmi_pro.py`** — PRO tier схемы:
   - `BMIProRequest` — использует `sex` вместо `gender`, требует `waist_cm`
   - `BMIProResponse` — возвращает `bmi`, `whtr`, `whr`, `ffmi`, `risk_level`, `notes`

5. **`core/bmi/risk.py`** (PR-452):
   - `WaistRiskResult` — dataclass (не Pydantic)
   - `calculate_waist_risk()` — возвращает `WaistRiskResult | None`

---

## 🎯 Что создаем в Commit 3

### Файл: `app/schemas/bmi.py` (NEW)

**Цель**: Единый API контракт для нового endpoint `/api/v1/bmi/calculate` (FREE tier).

---

## 📝 Детальная структура `BMICalculateRequest`

### Поля (по порядку)

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from core.i18n import Language


class BMICalculateRequest(BaseModel):
    """
    RU: Запрос для расчета BMI через единый engine.
    EN: Request for BMI calculation via unified engine.

    FREE tier endpoint (no API key required).
    """

    # Обязательные поля
    weight_kg: float = Field(
        ...,
        gt=0,
        description="Weight in kilograms. Must be positive.",
        examples=[65.5, 70.0, 80.3]
    )

    height_cm: float = Field(
        ...,
        gt=0,
        description="Height in centimeters. Must be positive.",
        examples=[170.0, 175.5, 180.0]
    )

    age: int = Field(
        ...,
        ge=1,
        le=120,
        description="Age in years. Range: 1-120.",
        examples=[25, 30, 45, 65]
    )

    # Опциональные поля с дефолтами
    gender: str = Field(
        default="male",
        description="Gender: 'male' or 'female'. Will be normalized by engine.",
        examples=["male", "female", "муж", "жен"]
    )

    pregnant: str | bool = Field(
        default="no",
        description="Pregnancy status. Accepts: 'yes'/'no' (string) or True/False (bool). Will be normalized to bool by engine.",
        examples=["no", "yes", False, True]
    )

    athlete: str | bool = Field(
        default="no",
        description="Athlete status. Accepts: 'yes'/'no' (string) or True/False (bool). Will be normalized to bool by engine.",
        examples=["no", "yes", False, True]
    )

    waist_cm: float | None = Field(
        None,
        gt=0,
        description="Waist circumference in centimeters (optional). If provided, enables WHtR and waist risk assessment.",
        examples=[80.0, 90.5, None]
    )

    lang: Language = Field(
        default="en",
        description="Language for localized responses: 'ru', 'en', or 'es'.",
        examples=["en", "ru", "es"]
    )
```

### Валидация (что НЕ делаем в схеме)

⚠️ **Важно**: Валидация BMI bounds (10-100) НЕ в схеме, а в engine:
- Схема проверяет только базовые типы и диапазоны (`gt=0`, `ge=1`, `le=120`)
- BMI bounds проверяются в `core/bmi/engine.py` после вычисления BMI
- Это позволяет engine возвращать `ValueError` для domain validation

### Отличия от существующих схем

| Поле | `BMIRequest` (legacy) | `BMIRequestV1` (legacy) | `BMIProRequest` (PRO) | `BMICalculateRequest` (NEW) |
|------|----------------------|------------------------|----------------------|----------------------------|
| `height` | `height_m` (метры) | `height_cm` (см) | `height_cm` (см) | `height_cm` (см) ✅ |
| `gender` | `gender` (str) | `gender` (str) | `sex` (Literal) | `gender` (str) ✅ |
| `pregnant` | `str \| bool` | `str \| bool` | ❌ нет | `str \| bool` ✅ |
| `athlete` | `str \| bool` | `str \| bool` | ❌ нет | `str \| bool` ✅ |
| `waist_cm` | Optional | Optional | **Required** | Optional ✅ |
| `premium` | ✅ есть | ❌ нет | ❌ нет | ❌ нет (FREE tier) |
| `include_chart` | ✅ есть | ❌ нет | ❌ нет | ❌ нет (в будущем PR) |

---

## 📤 Детальная структура `BMICalculateResponse`

### Поля

```python
class BMICalculateResponse(BaseModel):
    """
    RU: Ответ с результатами расчета BMI через единый engine.
    EN: Response with BMI calculation results via unified engine.

    Note: `category` может быть `None` для беременных и детей <12 лет
    (это не ошибка, а медицинский дисклеймер).
    """

    # Основные результаты
    bmi: float = Field(
        ...,
        description="Calculated BMI value (weight_kg / (height_m ** 2)).",
        examples=[22.5, 25.3, 18.7]
    )

    category: str | None = Field(
        None,
        description=(
            "BMI category (localized). "
            "None for pregnant/too_young - not an error, medical disclaimer. "
            "BMI is not valid during pregnancy or for children <12 years."
        ),
        examples=["normal", "overweight", None]
    )

    group: str = Field(
        ...,
        description="User group determined by auto_group(): 'general', 'athlete', 'elderly', 'child', 'too_young', 'pregnant'.",
        examples=["general", "athlete", "elderly"]
    )

    group_display: str = Field(
        ...,
        description="Localized display name for the group.",
        examples=["General", "Athlete", "Elderly"]
    )

    interpretation: str = Field(
        ...,
        description="Localized interpretation text for the BMI value in the context of the group.",
        examples=["Your BMI is within the normal range for your age group."]
    )

    # Опциональные метрики
    wht_ratio: float | None = Field(
        None,
        description="Waist-to-Height Ratio (WHtR). Calculated only if waist_cm was provided.",
        examples=[0.47, 0.52, None]
    )

    waist_risk: dict[str, Any] | None = Field(
        None,
        description=(
            "Waist risk assessment result (serialized WaistRiskResult). "
            "Present only if waist_cm was provided and risk was calculated. "
            "Structure: {'wht_ratio': float | None, 'risk_level': 'low'|'moderate'|'high', 'notes': tuple[str, ...]}"
        ),
        examples=[
            {
                "wht_ratio": 0.52,
                "risk_level": "moderate",
                "notes": ["Increased waist-related risk"]
            },
            None
        ]
    )

    notes: list[str] = Field(
        default_factory=list,
        description="Aggregated notes (currently only from waist_risk.notes). Empty list if no notes.",
        examples=[[], ["Increased waist-related risk"]]
    )

    age_band: Literal["too_young", "child", "teen", "adult", "elderly"] = Field(
        ...,
        description="Age band for UI differentiation: 'too_young' (<12), 'child' (12-14), 'teen' (15-18), 'adult' (19-59), 'elderly' (>=60).",
        examples=["adult", "teen", "elderly"]
    )
```

### Маппинг `BMICalculateResult` (engine) → `BMICalculateResponse` (API)

```python
# В endpoint (Commit 4):
result = calculate_bmi_result(...)  # Returns BMICalculateResult (dataclass)

return BMICalculateResponse(
    bmi=result.bmi,
    category=result.category if result.category else None,  # Handle None at API level
    group=result.group,
    group_display=result.group_display,
    interpretation=result.interpretation,
    wht_ratio=result.wht_ratio,
    waist_risk=result.waist_risk.model_dump() if result.waist_risk else None,  # Serialize dataclass
    notes=list(result.notes),  # Convert tuple to list for JSON
    age_band=result.age_band,
)
```

### Отличия от существующих response схем

| Поле | `BMIProResponse` (PRO) | Legacy endpoints | `BMICalculateResponse` (NEW) |
|------|----------------------|-----------------|------------------------------|
| `bmi` | ✅ | ✅ | ✅ |
| `category` | ❌ | ✅ | ✅ (может быть None) |
| `group` | ❌ | ✅ | ✅ |
| `group_display` | ❌ | ❌ | ✅ (NEW) |
| `interpretation` | ❌ | ❌ | ✅ (NEW) |
| `whtr` | ✅ | ❌ | ✅ (как `wht_ratio`) |
| `whr` | ✅ | ❌ | ❌ (PRO only) |
| `ffmi` | ✅ | ❌ | ❌ (PRO only) |
| `risk_level` | ✅ | ❌ | ✅ (внутри `waist_risk`) |
| `notes` | ✅ | ✅ (как `note` str) | ✅ (как list) |
| `waist_risk` | ❌ | ❌ | ✅ (NEW, структурированный) |
| `age_band` | ❌ | ❌ | ✅ (NEW) |

---

## 🧪 Тесты: `tests/test_bmi_schemas.py` (NEW)

### 1. Schema validation (422 cases)

```python
def test_bmi_calculate_request_validation():
    """Test Pydantic validation for BMICalculateRequest."""

    # ✅ Valid request
    valid = BMICalculateRequest(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        gender="male",
        lang="en"
    )
    assert valid.weight_kg == 70.0

    # ❌ Negative weight
    with pytest.raises(ValidationError):
        BMICalculateRequest(weight_kg=-10, height_cm=175, age=30)

    # ❌ Zero height
    with pytest.raises(ValidationError):
        BMICalculateRequest(weight_kg=70, height_cm=0, age=30)

    # ❌ Age out of range
    with pytest.raises(ValidationError):
        BMICalculateRequest(weight_kg=70, height_cm=175, age=0)  # < 1

    with pytest.raises(ValidationError):
        BMICalculateRequest(weight_kg=70, height_cm=175, age=121)  # > 120

    # ❌ Negative waist_cm (if provided)
    with pytest.raises(ValidationError):
        BMICalculateRequest(weight_kg=70, height_cm=175, age=30, waist_cm=-10)

    # ✅ Optional waist_cm = None (OK)
    valid_no_waist = BMICalculateRequest(
        weight_kg=70.0,
        height_cm=175.0,
        age=30,
        waist_cm=None
    )
    assert valid_no_waist.waist_cm is None
```

### 2. Default values

```python
def test_bmi_calculate_request_defaults():
    """Test default values for optional fields."""
    req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30)

    assert req.gender == "male"
    assert req.pregnant == "no"
    assert req.athlete == "no"
    assert req.waist_cm is None
    assert req.lang == "en"
```

### 3. Language validation

```python
def test_bmi_calculate_request_language():
    """Test Language field accepts only ru/en/es."""
    # ✅ Valid languages
    for lang in ["ru", "en", "es"]:
        req = BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang=lang)
        assert req.lang == lang

    # ❌ Invalid language (Pydantic will raise ValidationError)
    with pytest.raises(ValidationError):
        BMICalculateRequest(weight_kg=70, height_cm=175, age=30, lang="fr")
```

### 4. Response structure (golden tests)

```python
def test_bmi_calculate_response_structure():
    """Test BMICalculateResponse structure matches engine output."""
    # Minimal response (no waist)
    response = BMICalculateResponse(
        bmi=22.5,
        category="normal",
        group="general",
        group_display="General",
        interpretation="Your BMI is within the normal range.",
        wht_ratio=None,
        waist_risk=None,
        notes=[],
        age_band="adult"
    )

    assert response.bmi == 22.5
    assert response.category == "normal"
    assert response.notes == []

    # Full response (with waist risk)
    response_full = BMICalculateResponse(
        bmi=25.3,
        category="overweight",
        group="general",
        group_display="General",
        interpretation="Your BMI indicates overweight.",
        wht_ratio=0.52,
        waist_risk={
            "wht_ratio": 0.52,
            "risk_level": "moderate",
            "notes": ["Increased waist-related risk"]
        },
        notes=["Increased waist-related risk"],
        age_band="adult"
    )

    assert response_full.waist_risk is not None
    assert response_full.waist_risk["risk_level"] == "moderate"
```

### 5. Category None (pregnant/too_young)

```python
def test_bmi_calculate_response_category_none():
    """Test that category=None is valid (pregnant/too_young cases)."""
    # Pregnant case
    response_pregnant = BMICalculateResponse(
        bmi=24.5,
        category=None,  # Valid for pregnant
        group="pregnant",
        group_display="Pregnant",
        interpretation="BMI is not valid during pregnancy.",
        wht_ratio=None,
        waist_risk=None,
        notes=[],
        age_band="adult"
    )

    assert response_pregnant.category is None

    # Too young case
    response_child = BMICalculateResponse(
        bmi=18.5,
        category=None,  # Valid for <12 years
        group="too_young",
        group_display="Too Young",
        interpretation="BMI interpretation is not available for children under 12.",
        wht_ratio=None,
        waist_risk=None,
        notes=[],
        age_band="too_young"
    )

    assert response_child.category is None
```

---

## 📦 Импорты и зависимости

### `app/schemas/bmi.py`

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from core.i18n import Language
```

**Важно**: НЕ импортируем `core.bmi.*` в схемы (это нарушит разделение слоев).

---

## ✅ Commit message

```
feat(api): add BMI request/response schemas

- Create app/schemas/bmi.py with BMICalculateRequest/Response
- Request: weight_kg, height_cm, age, gender, pregnant, athlete, waist_cm, lang
- Response: bmi, category, group, group_display, interpretation, wht_ratio, waist_risk, notes, age_band
- Validation: basic type/range checks (BMI bounds validated in engine)
- Support category=None for pregnant/too_young (medical disclaimer)
- Add comprehensive schema validation tests
```

---

## 🔗 Связь с другими коммитами

### Commit 2 (engine) → Commit 3 (schemas)
- Engine возвращает `BMICalculateResult` (dataclass)
- Schemas определяют API контракт (Pydantic)
- Маппинг происходит в Commit 4 (endpoint)

### Commit 3 (schemas) → Commit 4 (endpoint)
- Endpoint использует `BMICalculateRequest` для валидации входящих данных
- Endpoint возвращает `BMICalculateResponse` для сериализации JSON

### Commit 3 (schemas) → Commit 5 (legacy shims)
- Legacy endpoints могут использовать `BMICalculateRequest` для валидации (опционально)
- Legacy endpoints сохраняют свой формат ответа (не используют `BMICalculateResponse`)

---

## ⚠️ Важные замечания

1. **BMI bounds (10-100) НЕ в схеме**:
   - Схема проверяет только базовые типы
   - BMI bounds проверяются в engine после вычисления
   - Это позволяет engine возвращать `ValueError` для domain validation

2. **Gender normalization НЕ в схеме**:
   - Схема принимает любой `str`
   - Нормализация происходит в engine через `auto_group()`

3. **Pregnant/athlete string→bool НЕ в схеме**:
   - Схема принимает `str | bool`
   - Конвертация в `bool` происходит в engine

4. **Category=None — это НЕ ошибка**:
   - Для беременных и детей <12 лет `category=None` — это медицинский дисклеймер
   - Схема явно документирует это в `description`

5. **WaistRiskResult сериализация**:
   - Engine возвращает `WaistRiskResult` (dataclass)
   - Endpoint сериализует через `.model_dump()` или `dict(...)`
   - Response содержит `dict[str, Any]` (не Pydantic модель)

---

## 📊 Checklist перед коммитом

- [ ] Создан `app/schemas/bmi.py`
- [ ] `BMICalculateRequest` со всеми полями и валидацией
- [ ] `BMICalculateResponse` со всеми полями и описаниями
- [ ] Создан `tests/test_bmi_schemas.py`
- [ ] Тесты покрывают: validation (422), defaults, language, response structure, category=None
- [ ] `ruff check` и `ruff format` проходят
- [ ] `pytest tests/test_bmi_schemas.py` проходит
- [ ] Импорты корректны (нет циклических зависимостей)
- [ ] Документация в docstrings на RU/EN

---

## 🎯 Итог

Commit 3 создает **чистый API контракт** для нового endpoint `/api/v1/bmi/calculate`:
- Request схема валидирует входящие данные (базовые типы и диапазоны)
- Response схема определяет структуру ответа (с поддержкой `category=None`)
- Тесты фиксируют контракт и предотвращают регрессии

Этот коммит **не зависит от Commit 2** (engine), но **используется в Commit 4** (endpoint).
