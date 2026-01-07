# PR-490A: Backend-only BMI Visualization Spec (≤7 files)

## 🎯 Цель

Добавить JSON spec визуализации BMI в `/api/v1/bmi/calculate` **без frontend изменений**.

**Критерий готовности:** curl endpoint → видим `visualization` в ответе.

---

## 📋 Точный список файлов (строго ≤7)

### Изменяемые файлы (4)

1. **`app/schemas/bmi.py`**
   - Добавить `BMIRangeSpec`, `BMIMarkerSpec`, `BMIScaleV1Spec`
   - Добавить `visualization: BMIScaleV1Spec | None` в `BMICalculateResponse`

2. **`app/services/bmi_visualization.py`** (новый файл)
   - Функция `build_bmi_scale_v1(bmi: float) -> BMIScaleV1Spec`

3. **`app/routers/bmi.py`**
   - В `bmi_calculate_handler()` добавить 2-3 строки: импорт + присвоение `resp.visualization`

4. **`tests/test_bmi_visualization_spec.py`** (новый файл)
   - 4 теста: структура, ranges monotonic, marker, endpoint response

### Опциональные файлы (2-3, не обязательны для функциональности)

5. **`docs/pr/PR_490_DESCRIPTION.md`** (если создаём)
6. **`docs/pr/PR_490_CURSOR_CHECKLIST.md`** (если создаём)
7. **`docs/pr/PR_BMI_VISUALIZATION_SPEC.md`** (если обновляем)

**Итого:** 4 обязательных + 0-3 опциональных = **4-7 файлов**

---

## ✅ Жёсткие ограничения (чтобы PR не расползся)

### ❌ НЕ трогаем

- `legacy_app.py` — не изменяем
- `bmi_visualization.py` (корневой) — не трогаем
- Frontend файлы — **строго вне scope**
- `core/` — не добавляем туда spec builder (это API adapter, не domain logic)
- Refactoring существующего кода — только добавление

### ✅ Только добавляем

- Новые Pydantic модели
- Новый builder в `app/services/`
- Минимальная интеграция в router (2-3 строки)
- Тесты

---

## 🔧 Commit Strategy (4 коммита, строго по порядку)

### Commit 1: Schema models

**Файл:** `app/schemas/bmi.py`

**Что добавить:**

```python
class BMIRangeSpec(BaseModel):
    """BMI range with i18n key."""
    key: str = Field(..., description="i18n key for range label")
    from_: float = Field(..., alias="from", description="Range start (inclusive)")
    to: float = Field(..., description="Range end (exclusive)")

class BMIMarkerSpec(BaseModel):
    """BMI marker position."""
    value: float = Field(..., description="Current BMI value")

class BMIScaleV1Spec(BaseModel):
    """BMI scale visualization spec v1."""
    kind: Literal["bmi_scale_v1"] = "bmi_scale_v1"
    bmi: float = Field(..., description="BMI value")
    min: float = Field(0.0, description="Scale minimum")
    max: float = Field(60.0, description="Scale maximum")
    ranges: list[BMIRangeSpec] = Field(..., description="BMI ranges with i18n keys")
    marker: BMIMarkerSpec = Field(..., description="Current BMI marker")
```

**Обновить `BMICalculateResponse`:**
```python
visualization: BMIScaleV1Spec | None = Field(
    None,
    description="Optional BMI scale visualization spec (v1). Frontend should render this if available."
)
```

**Message:**
```
feat(bmi): add BMIScaleV1Spec schema for visualization

- Add BMIRangeSpec, BMIMarkerSpec, BMIScaleV1Spec models
- Add visualization field to BMICalculateResponse
- Use alias "from" for Python reserved word
```

---

### Commit 2: Spec builder

**Файл:** `app/services/bmi_visualization.py` (новый)

**Что создать:**

```python
# -*- coding: utf-8 -*-
"""
BMI Visualization Service

RU: Сервис для генерации spec визуализации BMI.
EN: Service for generating BMI visualization spec.

This is an API adapter, not domain logic.
"""

from app.schemas.bmi import BMIScaleV1Spec, BMIRangeSpec, BMIMarkerSpec


def build_bmi_scale_v1(bmi: float) -> BMIScaleV1Spec:
    """
    Build BMI scale v1 spec for frontend rendering.
    
    Uses fixed thresholds (0-60) regardless of group.
    Group-specific interpretation is handled separately in category/interpretation fields.
    
    Args:
        bmi: BMI value (will be rounded to 1 decimal)
    
    Returns:
        BMIScaleV1Spec with fixed scale 0-60 and WHO standard thresholds
    """
    # Fixed thresholds (WHO standard)
    ranges = [
        BMIRangeSpec(key="bmi.underweight", from_=0.0, to=18.5),
        BMIRangeSpec(key="bmi.normal", from_=18.5, to=25.0),
        BMIRangeSpec(key="bmi.overweight", from_=25.0, to=30.0),
        BMIRangeSpec(key="bmi.obesity", from_=30.0, to=60.0),
    ]
    
    rounded_bmi = round(bmi, 1)
    
    return BMIScaleV1Spec(
        kind="bmi_scale_v1",
        bmi=rounded_bmi,
        min=0.0,
        max=60.0,
        ranges=ranges,
        marker=BMIMarkerSpec(value=rounded_bmi),
    )
```

**Message:**
```
feat(bmi): add build_bmi_scale_v1 spec builder

- Create app/services/bmi_visualization.py
- Fixed scale 0-60 with WHO standard thresholds
- i18n keys: bmi.underweight|normal|overweight|obesity
- API adapter (not domain logic)
```

---

### Commit 3: Integration

**Файл:** `app/routers/bmi.py`

**Где:** В `bmi_calculate_handler()` после создания `resp`

**Что добавить:**

```python
from app.services.bmi_visualization import build_bmi_scale_v1

# После:
resp = BMICalculateResponse(...)

# Добавить:
resp.visualization = build_bmi_scale_v1(result.bmi)

# Return as dict for legacy compatibility
# IMPORTANT: use by_alias=True to ensure "from" (not "from_") in JSON
response_dict: dict[str, Any] = resp.model_dump(by_alias=True)
return response_dict
```

**⚠️ Критично:** `by_alias=True` обязателен, иначе в JSON будет `from_` вместо `from`.

**Message:**
```
feat(bmi): integrate visualization spec in calculate endpoint

- Add visualization to bmi_calculate_handler response
- Always return spec (no include_chart flag)
- Legacy base64 remains in legacy_app.py (not touched)
```

---

### Commit 4: Tests

**Файл:** `tests/test_bmi_visualization_spec.py` (новый)

**Что создать:**

```python
# -*- coding: utf-8 -*-
"""
Tests for BMI visualization spec builder and endpoint integration.
"""

import pytest
import math

from app.services.bmi_visualization import build_bmi_scale_v1
from app.schemas.bmi import BMIScaleV1Spec


def test_build_bmi_scale_v1_structure():
    """Test that spec has correct structure."""
    spec = build_bmi_scale_v1(23.4)
    
    assert spec.kind == "bmi_scale_v1"
    assert spec.bmi == 23.4
    assert spec.min == 0.0
    assert spec.max == 60.0
    assert len(spec.ranges) == 4
    assert spec.marker.value == 23.4


def test_ranges_monotonic_no_gaps():
    """Test that ranges are monotonic with no gaps."""
    spec = build_bmi_scale_v1(25.0)
    
    # Check each range: from_ < to
    for range_spec in spec.ranges:
        assert range_spec.from_ < range_spec.to, f"Range {range_spec.key}: from_ >= to"
    
    # Check sequence: end of previous == start of next
    for i in range(len(spec.ranges) - 1):
        assert spec.ranges[i].to == spec.ranges[i + 1].from_, \
            f"Gap between range {i} and {i + 1}"
    
    # Check boundaries
    assert spec.ranges[0].from_ == spec.min, "First range should start at min"
    assert spec.ranges[-1].to == spec.max, "Last range should end at max"


def test_marker_equals_bmi():
    """Test that marker value equals rounded BMI."""
    test_cases = [18.5, 22.3, 25.0, 30.0, 35.7]
    
    for bmi in test_cases:
        spec = build_bmi_scale_v1(bmi)
        assert spec.marker.value == round(bmi, 1), \
            f"Marker value {spec.marker.value} != rounded BMI {round(bmi, 1)}"
        assert spec.bmi == round(bmi, 1), \
            f"Spec BMI {spec.bmi} != rounded BMI {round(bmi, 1)}"


def test_build_bmi_scale_v1_edge_cases():
    """Test builder handles edge cases safely."""
    # Normal cases
    spec1 = build_bmi_scale_v1(0.0)
    assert spec1.bmi == 0.0
    assert spec1.marker.value == 0.0
    
    spec2 = build_bmi_scale_v1(60.0)
    assert spec2.bmi == 60.0
    assert spec2.marker.value == 60.0
    
    # Very small BMI
    spec3 = build_bmi_scale_v1(10.12345)
    assert spec3.bmi == 10.1  # rounded to 1 decimal
    assert spec3.marker.value == 10.1


def test_bmi_calculate_returns_visualization():
    """Test that /api/v1/bmi/calculate returns visualization field."""
    # Use canonical import pattern from project
    from app import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    response = client.post(
        "/api/v1/bmi/calculate",
        json={
            "weight_kg": 70.0,
            "height_cm": 175.0,
            "age": 30,
            "gender": "male",  # BMICalculateRequest uses "gender", not "sex"
            "lang": "en",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "visualization" in data, "Response should contain visualization field"
    assert data["visualization"] is not None, "Visualization should not be None"
    assert data["visualization"]["kind"] == "bmi_scale_v1", \
        "Visualization kind should be bmi_scale_v1"
    assert "ranges" in data["visualization"], "Visualization should contain ranges"
    assert "marker" in data["visualization"], "Visualization should contain marker"
    assert len(data["visualization"]["ranges"]) == 4, "Should have 4 ranges"
    
    # Verify alias "from" is used (not "from_")
    first_range = data["visualization"]["ranges"][0]
    assert "from" in first_range, "Range should use 'from' alias (not 'from_')"
    assert "from_" not in first_range, "Range should not contain 'from_' field"
```

**Message:**
```
test(bmi): add visualization spec tests

- Test spec structure and ranges monotonicity
- Test marker value equals BMI
- Test endpoint returns visualization field
```

---

## ✅ Verification Checklist

После всех коммитов проверить:

- [ ] `pytest -q tests/test_bmi_visualization_spec.py` — все тесты проходят
- [ ] `pytest -q` — полный test suite проходит (coverage не упало)
- [ ] `ruff check app/schemas/bmi.py app/services/bmi_visualization.py app/routers/bmi.py` — нет lint ошибок
- [ ] `mypy app/schemas/bmi.py app/services/bmi_visualization.py app/routers/bmi.py` — type check проходит (если включён)
- [ ] Ручная проверка: `curl -X POST http://localhost:8000/api/v1/bmi/calculate -H "Content-Type: application/json" -d '{"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male", "lang": "en"}' | jq .visualization`
  - Должен вернуть JSON с `kind: "bmi_scale_v1"`, `ranges`, `marker`

---

## 🚫 Что НЕ делаем (жёстко)

1. **НЕ трогаем `legacy_app.py`** — он остаётся как есть
2. **НЕ трогаем `bmi_visualization.py` (корневой)** — legacy base64 модуль
3. **НЕ добавляем frontend файлы** — это PR-490B
4. **НЕ делаем refactoring** — только добавление
5. **НЕ добавляем цвета в API** — только i18n keys
6. **НЕ используем `group` в spec builder** — фиксированная шкала
7. **НЕ добавляем matplotlib/base64** — только JSON spec

---

## 📊 Ожидаемый результат

После merge PR-490A:

- Endpoint `/api/v1/bmi/calculate` возвращает `visualization` в ответе
- Spec содержит правильную структуру (kind, ranges, marker)
- Тесты покрывают основные случаи
- Coverage не упало (97%+)
- Legacy не тронут

**Frontend может начать использовать spec сразу после merge PR-490A.**

---

## 🔗 Следующий шаг

После merge PR-490A → **PR-490B (frontend-only)**:
- Компонент `BmiScaleV1.tsx`
- i18n ключи
- Интеграция в UI
- Frontend тесты

