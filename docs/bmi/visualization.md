# BMI Visualization — Contract (BMIScaleV1Spec)

## Purpose

The `/api/v1/bmi/calculate` endpoint may return an optional `visualization` field.
This object is a UI-friendly, group-aware BMI scale spec derived from the canonical BMI engine
thresholds (single source of truth: `core/bmi/engine.py`).

Clients (iOS/Web) must treat `visualization` as **optional**.

---

## Where it appears

Endpoint:
- `POST /api/v1/bmi/calculate`

Response DTO:
- `BMICalculateResponse.visualization: BMIScaleV1Spec | None`

Schema location:
- `app/schemas/bmi.py` → `BMIScaleV1Spec`, `BMIRangeSpec`, `BMIMarkerSpec`

---

## When `visualization` is `null`

`visualization` is **null** when any of the following applies:

1. The computed BMI group has no compatible adult-style category mapping
   (e.g., **too_young/child/teen/pregnant** outputs where category logic differs).
2. Visualization builder fails (should be fail-soft):
   - The endpoint must still return **200**
   - `visualization` is set to **null**

> Contract invariant: visualization is "best-effort UI sugar", not a critical field.

**Groups that return `visualization: null`:**
- `too_young` (age < 12)
- `child` (age == 12)
- `teen` (age 13-19)
- `pregnant` (any age, if `pregnant=True`)

**Groups that return `visualization` spec:**
- `general` (adult, age 20-59)
- `athlete` (adult with `athlete=True`)
- `elderly` (age >= 60)

---

## BMIScaleV1Spec — structure

`BMIScaleV1Spec` describes a continuous BMI scale with labeled ranges and a BMI marker.

### Fields

- `kind` (string, literal): `"bmi_scale_v1"` (constant)
- `bmi` (number): BMI value used for the marker (rounded to 1 decimal)
- `min` (number): scale minimum (default: `0.0`)
- `max` (number): scale maximum (default: `60.0`)
- `ranges` (array): ordered, contiguous segments of the scale (exactly 4 ranges)
- `marker` (object): current BMI marker (at least `{ "value": <bmi> }`)

### Range objects (BMIRangeSpec)

Each range is:
- `key` (string): i18n key for the label (e.g., `"bmi.normal"`)
- `from` (number): inclusive start (serialized as `"from"` via Pydantic alias)
- `to` (number): exclusive end (or inclusive end; clients should render as segment boundary)

**i18n keys used:**
- `"bmi.underweight"` — underweight range
- `"bmi.normal"` — normal range
- `"bmi.overweight"` — overweight range
- `"bmi.obesity"` — obesity range (aggregates obesity_1/2/3)

### Required invariants

1. `ranges` are sorted by `from` (ascending)
2. Ranges are contiguous (no gaps):
   - `ranges[i].to == ranges[i+1].from` for all `i < len(ranges) - 1`
3. Coverage:
   - `ranges[0].from == min`
   - `ranges[-1].to == max`
4. `marker.value == bmi` (exact match, validated by Pydantic)
5. `min < max`, `min <= bmi <= max` (validated by Pydantic)
6. Exactly 4 ranges (underweight, normal, overweight, obesity)

---

## Group-aware ranges

Visualization ranges reflect the BMI engine thresholds **for the resolved group**.

The ranges are derived from `core/bmi/engine.py` → `get_bmi_visual_ranges()` which uses
the centralized `_BMI_BREAKPOINTS` registry.

**Key differences by group:**

| Group | Underweight → Normal | Normal → Overweight | Notes |
|-------|---------------------|---------------------|-------|
| **Adult (general)** | 0 → 18.5 | 18.5 → 25.0 | WHO standard |
| **Athlete** | 0 → 18.5 | 18.5 → 27.0 | Normal extends to 27.0 |
| **Elderly** | 0 → 17.5 | 17.5 → 26.0 | Lower underweight threshold, higher normal upper |

> Clients must not hardcode WHO adult ranges. Always render what API returns.

---

## Examples

> Note: Numbers below illustrate shape + group differences. Always trust API output.

### Example A — Adult (general)

```json
{
  "bmi": 23.4,
  "category": "normal",
  "group": "general",
  "visualization": {
    "kind": "bmi_scale_v1",
    "bmi": 23.4,
    "min": 0.0,
    "max": 60.0,
    "ranges": [
      {"key": "bmi.underweight", "from": 0.0, "to": 18.5},
      {"key": "bmi.normal",      "from": 18.5, "to": 25.0},
      {"key": "bmi.overweight",  "from": 25.0, "to": 30.0},
      {"key": "bmi.obesity",     "from": 30.0, "to": 60.0}
    ],
    "marker": {"value": 23.4}
  }
}
```

### Example B — Athlete (normal upper bound differs)

```json
{
  "bmi": 26.2,
  "category": "normal",
  "group": "athlete",
  "visualization": {
    "kind": "bmi_scale_v1",
    "bmi": 26.2,
    "min": 0.0,
    "max": 60.0,
    "ranges": [
      {"key": "bmi.underweight", "from": 0.0, "to": 18.5},
      {"key": "bmi.normal",      "from": 18.5, "to": 27.0},
      {"key": "bmi.overweight",  "from": 27.0, "to": 30.0},
      {"key": "bmi.obesity",     "from": 30.0, "to": 60.0}
    ],
    "marker": {"value": 26.2}
  }
}
```

**Note:** Athlete normal range extends to 27.0 (vs 25.0 for adult general).

### Example C — Elderly (bounds differ)

```json
{
  "bmi": 18.2,
  "category": "normal",
  "group": "elderly",
  "visualization": {
    "kind": "bmi_scale_v1",
    "bmi": 18.2,
    "min": 0.0,
    "max": 60.0,
    "ranges": [
      {"key": "bmi.underweight", "from": 0.0, "to": 17.5},
      {"key": "bmi.normal",      "from": 17.5, "to": 26.0},
      {"key": "bmi.overweight",  "from": 26.0, "to": 30.0},
      {"key": "bmi.obesity",     "from": 30.0, "to": 60.0}
    ],
    "marker": {"value": 18.2}
  }
}
```

**Note:** Elderly has lower underweight threshold (17.5) and higher normal upper (26.0).

### Example D — Child/Teen/Too Young/Pregnant (no visualization)

```json
{
  "bmi": 18.5,
  "category": null,
  "group": "child",
  "visualization": null
}
```

**Note:** Groups with `category=None` return `visualization: null` to avoid misleading
adult-style ranges for users where BMI categories don't apply.

---

## Client guidance (iOS/Web)

### Handling `visualization`

* Treat `visualization` as optional (`nil` / `null` / `Optional`)
* Check `if visualization is not None` before rendering
* If `null`, show BMI value and category text only (no scale visualization)

### Rendering the scale

When `visualization` is present:

1. **Render segments** from `ranges[]`:
   - Each range is a segment from `from` to `to`
   - Use `key` to look up localized label (e.g., `"bmi.normal"` → "Normal" / "Норма")
   - Apply colors/styles on client (not from API)

2. **Render marker** at `marker.value`:
   - Position marker at BMI value on the scale
   - Ensure marker is within `[min, max]` bounds

3. **Scale bounds**:
   - Use `min` and `max` for scale axis
   - Default: `0.0` to `60.0`

### Do not

* ❌ Infer thresholds from BMI category strings
* ❌ Hardcode WHO adult ranges (use API ranges)
* ❌ Assume all groups have same ranges
* ❌ Render visualization when `visualization` is `null`

---

## Implementation references

### Backend

* **Canonical engine thresholds:**
  * `core/bmi/engine.py`:
    - `_BMI_BREAKPOINTS` — centralized threshold registry
    - `get_bmi_visual_ranges()` — derives visualization ranges from thresholds
    - `_age_band()` — age band mapping (too_young/child/teen/adult/elderly)

* **Visualization builder:**
  * `app/services/bmi_visualization.py`:
    - `build_bmi_scale_v1()` — builds spec from `BMICalculateResult`
    - Returns `None` for groups with `category=None`

* **Endpoint:**
  * `app/routers/bmi.py`:
    - `POST /api/v1/bmi/calculate`
    - Graceful fallback: returns `200` with `visualization: null` if builder fails

* **Schemas:**
  * `app/schemas/bmi.py`:
    - `BMIScaleV1Spec` — visualization spec model
    - `BMIRangeSpec` — range model (with `from` alias)
    - `BMIMarkerSpec` — marker model
    - `BMICalculateResponse` — response model with `visualization` field

### Age band mapping

From `core/bmi/engine.py` → `_age_band()`:

- `age < 12` → `too_young`
- `age == 12` → `child`
- `13 <= age <= 19` → `teen`
- `20 <= age < 60` → `adult`
- `age >= 60` → `elderly`

---

## Contract invariants (for testing)

1. **Structure:**
   - `visualization` field exists in response (may be `null`)
   - If not `null`, has `kind`, `bmi`, `min`, `max`, `ranges`, `marker`
   - `kind == "bmi_scale_v1"` (constant)

2. **Ranges:**
   - Exactly 4 ranges
   - Sorted by `from` (ascending)
   - Contiguous (no gaps)
   - Covers `[min, max]` completely

3. **Group awareness:**
   - Athlete normal upper != adult normal upper
   - Elderly underweight threshold != adult underweight threshold

4. **Null cases:**
   - `visualization: null` for too_young/child/teen/pregnant
   - `visualization: null` if builder fails (endpoint still returns 200)

---

## Related documentation

- `docs/pr/PR_490B_COVERAGE_NOTE.md` — PR-490B implementation notes
- `docs/pr/HANDOFF_PR_490_491.md` — Architecture handoff
- `docs/audit/PROJECT_AUDIT_2026_Q1.md` — Project audit
