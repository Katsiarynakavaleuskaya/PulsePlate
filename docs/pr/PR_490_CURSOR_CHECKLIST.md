# PR #490: Cursor Checklist (step-by-step)

## A) Audit (5–10 мин, без кода)

### 1. Найти handler для `/api/v1/bmi/calculate`

**Файл:** `app/routers/bmi.py`

**Что искать:**
- Функция `calculate_bmi()` или `bmi_calculate_handler()`
- Endpoint `@router.post("/calculate")`

**Цель:** понять точку внедрения.

---

### 2. Найти `BMICalculateResponse`

**Файл:** `app/schemas/bmi.py`

**Что искать:**
- Класс `BMICalculateResponse(BaseModel)`
- Текущие поля ответа

**Цель:** понять, куда добавлять `visualization`.

---

### 3. Подтвердить legacy

**Файл:** `legacy_app.py`

**Что искать:**
- Функция `add_visualization_if_requested()`
- Параметр `include_chart` в `BMIRequest`
- Base64 generation через `generate_bmi_visualization()`

**Цель:** убедиться, что новый endpoint это **не вызывает** (оставляем как есть).

---

## B) Backend Changes

### 1) Добавить Pydantic модели (строго типизировано)

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

**Важно:** `"from"` в JSON — зарезервированное слово в Python, делаем `from_` + alias.

---

### 2) Добавить builder (pure function)

**Файл:** `app/services/bmi_visualization.py` (новый)

**Что создать:**

```python
from app.schemas.bmi import BMIScaleV1Spec, BMIRangeSpec, BMIMarkerSpec

def build_bmi_scale_v1(bmi: float) -> BMIScaleV1Spec:
    """
    Build BMI scale v1 spec for frontend rendering.

    Uses fixed thresholds (0-60) regardless of group.
    Group-specific interpretation is handled separately in category/interpretation fields.
    """
    # Fixed thresholds (WHO standard)
    ranges = [
        BMIRangeSpec(key="bmi.underweight", from_=0.0, to=18.5),
        BMIRangeSpec(key="bmi.normal", from_=18.5, to=25.0),
        BMIRangeSpec(key="bmi.overweight", from_=25.0, to=30.0),
        BMIRangeSpec(key="bmi.obesity", from_=30.0, to=60.0),
    ]

    return BMIScaleV1Spec(
        kind="bmi_scale_v1",
        bmi=round(bmi, 1),
        min=0.0,
        max=60.0,
        ranges=ranges,
        marker=BMIMarkerSpec(value=round(bmi, 1)),
    )
```

**Важно:**
- Шкала фикс: min=0, max=60
- Диапазоны WHO
- Округление: `round(bmi, 1)` (и в marker тоже)

---

### 3) Подключить в endpoint

**Файл:** `app/routers/bmi.py`

**Где:** В `bmi_calculate_handler()` после того как сформирован `resp`

**Что добавить:**

```python
from app.services.bmi_visualization import build_bmi_scale_v1

# После создания resp
resp = BMICalculateResponse(...)

# Добавить visualization
resp.visualization = build_bmi_scale_v1(result.bmi)

# Return as dict for legacy compatibility
response_dict: dict[str, Any] = resp.model_dump()
return response_dict
```

⚠️ **Не трогаем** `legacy_app.py` и `include_chart`.

---

## C) Backend Tests

**Файл:** `tests/test_bmi_visualization_spec.py` (новый)

**Тесты:**

1. `test_build_bmi_scale_v1_structure()`
   - Проверка структуры spec
   - Проверка `kind == "bmi_scale_v1"`
   - Проверка количества ranges (4)

2. `test_ranges_monotonic_no_gaps()`
   - `from_ < to` для каждого range
   - Последовательность ranges (конец предыдущего == начало следующего)
   - Первый range начинается с `min` (0)
   - Последний range заканчивается на `max` (60)

3. `test_marker_equals_bmi()`
   - `marker.value == bmi` (с округлением)

4. `test_bmi_calculate_returns_visualization()`
   - Через `TestClient`: POST `/api/v1/bmi/calculate`
   - Проверка наличия поля `visualization` в ответе
   - Проверка структуры `visualization`

---

## D) Frontend (выбери стратегию)

**Вариант 1 (лучше):** всё в одном PR (backend + frontend)
**Вариант 2:** backend PR сейчас, frontend — follow-up PR сразу после

### Если делаем в этом PR:

#### 1) i18n

**Файлы:** `frontend/src/locales/{ru,en,es}.json`

**Что добавить:**

```json
{
  "bmi": {
    "underweight": "Underweight",
    "normal": "Normal",
    "overweight": "Overweight",
    "obesity": "Obesity"
  }
}
```

**Для ru.json:**
```json
{
  "bmi": {
    "underweight": "Недостаточный вес",
    "normal": "Норма",
    "overweight": "Избыточный вес",
    "obesity": "Ожирение"
  }
}
```

**Для es.json:**
```json
{
  "bmi": {
    "underweight": "Bajo peso",
    "normal": "Normal",
    "overweight": "Sobrepeso",
    "obesity": "Obesidad"
  }
}
```

---

#### 2) Компонент

**Файл:** `frontend/src/components/BmiScaleV1.tsx` (новый)

**Что создать:**

```typescript
interface BMIScaleV1Spec {
  kind: "bmi_scale_v1";
  bmi: number;
  min: number;
  max: number;
  ranges: Array<{ key: string; from: number; to: number }>;
  marker: { value: number };
}

interface BmiScaleV1Props {
  spec: BMIScaleV1Spec;
}

export default function BmiScaleV1({ spec }: BmiScaleV1Props) {
  // SVG rendering with zones and marker
  // Use i18n keys from spec.ranges[].key
  // Colors and styles on frontend (not from API)
}
```

**Важно:**
- SVG-рендеринг шкалы с зонами и маркером
- Использование i18n ключей из spec
- Цвета и стили на фронте (не из API)

---

#### 3) Интеграция в UI

**Найти экран результата BMI** и отрендерить:

```typescript
if (response.visualization?.kind === "bmi_scale_v1") {
  return <BmiScaleV1 spec={response.visualization} />;
}
// Fallback: только текст
```

---

#### 4) Тесты

**Файл:** `frontend/src/components/__tests__/BmiScaleV1.test.tsx` (новый)

**Что тестировать:**
- Snapshot тест для SVG
- Базовая проверка маркера/лейблов
- Проверка i18n ключей

---

## E) Commands (локально)

### Backend

```bash
# Tests
pytest -q tests/test_bmi_visualization_spec.py

# Lint
ruff check app/schemas/bmi.py app/services/bmi_visualization.py app/routers/bmi.py

# Type check (если включён)
mypy app/schemas/bmi.py app/services/bmi_visualization.py app/routers/bmi.py

# Full test suite
pytest -q
```

### Frontend

```bash
# Tests
pnpm test  # или npm test

# Lint
pnpm lint  # или npm run lint
```

---

## F) Commit Strategy (рекомендуемый порядок)

### Commit 1: Backend schema
```
feat(bmi): add BMIScaleV1Spec schema for visualization

- Add BMIRangeSpec, BMIMarkerSpec, BMIScaleV1Spec models
- Add visualization field to BMICalculateResponse
- Use alias "from" for Python reserved word
```

### Commit 2: Backend builder
```
feat(bmi): add build_bmi_scale_v1 spec builder

- Create app/services/bmi_visualization.py
- Fixed scale 0-60 with WHO standard thresholds
- i18n keys: bmi.underweight|normal|overweight|obesity
```

### Commit 3: Backend integration
```
feat(bmi): integrate visualization spec in calculate endpoint

- Add visualization to bmi_calculate_handler response
- Always return spec (no include_chart flag)
- Legacy base64 remains in legacy_app.py
```

### Commit 4: Backend tests
```
test(bmi): add visualization spec tests

- Test spec structure and ranges monotonicity
- Test marker value equals BMI
- Test endpoint returns visualization field
```

### Commit 5: Frontend i18n (если в этом PR)
```
feat(web): add BMI i18n keys for visualization

- Add bmi.underweight|normal|overweight|obesity to locales
- Support ru/en/es
```

### Commit 6: Frontend component (если в этом PR)
```
feat(web): add BmiScaleV1 SVG component

- SVG rendering with zones and marker
- Use i18n keys from spec
- Colors and styles on frontend
```

### Commit 7: Frontend integration (если в этом PR)
```
feat(web): integrate BMI visualization in result view

- Render BmiScaleV1 if visualization.kind === "bmi_scale_v1"
- Fallback to text-only if visualization missing
```

### Commit 8: Frontend tests (если в этом PR)
```
test(web): add BmiScaleV1 snapshot tests

- Snapshot test for SVG rendering
- Test marker and label rendering
```

---

## G) Verification Checklist

- [ ] Backend: `pytest -q` passes
- [ ] Backend: `ruff check` passes
- [ ] Backend: `mypy` passes (если включён)
- [ ] Backend: curl `/api/v1/bmi/calculate` → проверка `visualization` в ответе
- [ ] Frontend: `pnpm test` passes (если делали)
- [ ] Frontend: `pnpm lint` passes (если делали)
- [ ] Frontend: ручная проверка рендера шкалы (если делали)
- [ ] Coverage: не упало ниже 97%

---

## H) PR Review Checklist

- [ ] Нет breaking changes в API (только опциональное поле)
- [ ] Legacy не тронут (`legacy_app.py` не изменён)
- [ ] Нет цветов в API (только i18n keys)
- [ ] Spec builder в `app/services/` (не в `core/`, не в router)
- [ ] Тесты покрывают основные случаи
- [ ] Документация обновлена (если нужно)
