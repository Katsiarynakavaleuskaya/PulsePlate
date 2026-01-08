# PR-494: Interpretation V1 Contract

## 📋 API Contract

**Key invariant:** `interpretation_v1` is always present for all groups except `too_young`. Pregnancy always returns structured interpretation.

### Response Fields

The `/api/v1/bmi/calculate` endpoint now includes:

1. **`interpretation: str`** (legacy, preserved)
   - Localized interpretation text (string)
   - Always present (required field)
   - Backward compatibility maintained

2. **`interpretation_v1: BMIInterpretationV1Schema | None`** (new, optional)
   - Structured interpretation with i18n keys only
   - `None` for: `too_young` only
   - Present for: `general`, `athlete`, `elderly`, `child`, `teen`, `pregnant` (with or without athlete)

---

## 🧩 Interpretation V1 Schema

```typescript
interface BMIInterpretationV1 {
  goal_direction: "maintain" | "reduce" | "increase" | "medical_review";
  target_range: NumericRange | QualitativeTarget | null;
  risk_flags: string[];  // i18n keys only
  priority_notes: string[];  // i18n keys only
  disclaimers: string[];  // i18n keys only
}

interface NumericRange {
  min: number;  // inclusive
  max: number;  // inclusive
}

type QualitativeTarget = "age_appropriate_growth" | "prenatal_guidelines";
```

---

## 📐 Boundary Semantics

### Numeric Ranges

- **Backend returns mathematically correct boundaries** (e.g., `{"min": 18.5, "max": 25.0}`)
- **UI is responsible for rendering labels** (e.g., "≤ 24.9" for `max=25.0`)
- **Backend never adjusts numbers for UI display** (no `-0.1` tricks)

### Examples

- `{"min": 18.5, "max": 25.0}` → UI may display as "18.5 - 24.9" or "18.5 - 25.0"
- `{"min": 18.5, "max": 30.0}` → UI may display as "18.5 - 29.9" or "18.5 - 30.0"

---

## 🤰 Pregnancy Rules

### Default Behavior

- **`pregnant=True` + `athlete=False`** → `interpretation_v1` present
  - `goal_direction: "medical_review"`
  - `target_range: "prenatal_guidelines"`
  - Disclaimers: pregnancy + medical_review

### Special Case

- **`pregnant=True` + `athlete=True`** → `interpretation_v1` present
  - Includes combined disclaimers (pregnancy + athlete body composition + medical_review)
  - `goal_direction: "medical_review"`
  - `target_range: "prenatal_guidelines"`
  - Additional risk flag: `athlete_body_composition`

---

## 🚫 Hard Invariants

### Gender + Pregnancy

- **`gender="male"` + `pregnant=True`** → **`422 Unprocessable Entity`**
- Error message: `"Pregnancy is only applicable to females"` (English)
- Validation at schema level (before engine call)

---

## 🔑 i18n Keys Format

All text fields in `interpretation_v1` are i18n keys (not translated strings):

- **Risk flags**: `"bmi.interpretation.risk.*"`
- **Priority notes**: `"bmi.interpretation.priority.*"`
- **Disclaimers**: `"bmi.interpretation.disclaimer.*"`

### Examples

```json
{
  "risk_flags": ["bmi.interpretation.risk.extreme_value"],
  "priority_notes": ["bmi.interpretation.priority.stability_first"],
  "disclaimers": ["bmi.interpretation.disclaimer.general"]
}
```

---

## 🛡️ Fail-Soft Behavior

If `build_interpretation_v1()` fails (exception):

- Endpoint still returns `200 OK`
- `interpretation_v1: null`
- Error is logged (not exposed to client)
- Legacy `interpretation: str` field is still present

This ensures that interpretation failures do not break the BMI calculation endpoint.

---

## 📊 Group-Specific Behavior

| Group | interpretation_v1 | Notes |
|-------|-------------------|-------|
| `too_young` | `null` | Always |
| `pregnant` (no athlete) | Present | Medical review with prenatal guidelines |
| `pregnant` (with athlete) | Present | Special case with combined disclaimers |
| `child` | Present | Qualitative targets |
| `teen` | Present | Qualitative targets |
| `general` | Present | Numeric targets |
| `athlete` | Present | Numeric targets (18.5-30 range) |
| `elderly` | Present | Stability-first, numeric targets |

---

## 🔄 Backward Compatibility

- **Legacy `interpretation: str` field is preserved** (always present)
- **New `interpretation_v1` field is optional** (may be `null`)
- **No breaking changes** to existing API contract
- **Frontend can migrate gradually** (use `interpretation_v1` when available, fallback to `interpretation`)

---

## 📝 Notes for Frontend

1. **Check `interpretation_v1` first** (if present, use structured data)
2. **Fallback to `interpretation`** (legacy string field)
3. **Handle `null` gracefully** (only for `too_young`)
4. **Render numeric ranges** as appropriate for your UI (backend provides clean boundaries)
5. **Translate i18n keys** using your localization system

