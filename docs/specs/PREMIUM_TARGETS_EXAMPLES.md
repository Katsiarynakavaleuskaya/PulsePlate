# Premium Targets API (WHO/EFSA Nutrition Standards)

This endpoint calculates personalized nutrition targets based on WHO/EFSA/DRI recommendations for macronutrients, micronutrients, hydration, and physical activity.

## Endpoint

```
POST /api/v1/premium/targets
```

## Request Headers

```
X-API-Key: YOUR_API_KEY
Content-Type: application/json
```

## Request Body

```json
{
  "sex": "male",
  "age": 30,
  "height_cm": 175,
  "weight_kg": 70,
  "activity": "moderate",
  "goal": "maintain",
  "life_stage": "adult"
}
```

## Example curl Commands

### English (default)

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "male",
    "age": 30,
    "height_cm": 175,
    "weight_kg": 70,
    "activity": "moderate",
    "goal": "maintain",
    "life_stage": "adult",
    "lang": "en"
  }'
```

### Spanish (Español)

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "female",
    "age": 25,
    "height_cm": 165,
    "weight_kg": 60,
    "activity": "active",
    "goal": "maintain",
    "life_stage": "adult",
    "lang": "es"
  }'
```

### Russian (Русский)

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "female",
    "age": 35,
    "height_cm": 170,
    "weight_kg": 65,
    "activity": "moderate",
    "goal": "loss",
    "deficit_pct": 15,
    "life_stage": "adult",
    "lang": "ru"
  }'
```

## Response Example

```json
{
  "kcal_daily": 2450,
  "macros": {
    "protein_g": 112,
    "fat_g": 63,
    "carbs_g": 306,
    "fiber_g": 34
  },
  "water_ml": 2100,
  "priority_micros": {
    "iron_mg": 8.0,
    "calcium_mg": 1000.0,
    "folate_ug": 400.0,
    "vitamin_d_iu": 600.0,
    "b12_ug": 2.4,
    "iodine_ug": 150.0,
    "magnesium_mg": 400.0,
    "potassium_mg": 3500.0
  },
  "activity_weekly": {
    "moderate_min": 150,
    "strength_sessions": 2,
    "steps_daily": 8000
  },
  "calculation_date": "2025-01-15",
  "warnings": [
    {
      "code": "pregnant",
      "message": "Pregnancy: requirements differ; consult specialized references."
    }
  ]
}
```

## Life Stage Warnings

The API provides localized warnings for special life stages:

### Warning Codes

- **teen**: Teenage years (12-18) - use age-appropriate references
- **pregnant**: Pregnancy - requirements differ from standard adult
- **lactating**: Breastfeeding - increased nutrient requirements
- **elderly**: Age 51+ - micronutrient needs may differ
- **child**: Under 12 years - use pediatric references

### Localized Messages

- **English (en)**: "Teen life stage: use age-appropriate references."
- **Spanish (es)**: "Etapa adolescente: use referencias apropiadas para la edad."
- **Russian (ru)**: "Подростковая группа: используйте специализированные нормы."

## Required Micronutrients Provided

The API returns targets for these key micronutrients as required:

- **Fe** (Iron) - `iron_mg`
- **Ca** (Calcium) - `calcium_mg`
- **VitD** (Vitamin D) - `vitamin_d_iu`
- **B12** (Vitamin B12) - `b12_ug`
- **I** (Iodine) - `iodine_ug`
- **Folate** (Folic Acid) - `folate_ug`
- **K** (Potassium) - `potassium_mg`
- **Mg** (Magnesium) - `magnesium_mg`

## Validation

All targets are validated to ensure:

- Calorie targets are within safe ranges (1200-4000 kcal)
- Macronutrient distribution follows WHO guidelines
- Micronutrient targets are based on WHO/EFSA RDA values for 19-50 age group
- Hydration targets are appropriate for body weight and activity level
