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

## Example curl Command

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
    "goal": "maintain"
  }'
```

## Response Example

```json
{
  "kcal_daily": 2556,
  "macros": {
    "protein_g": 112,
    "fat_g": 63,
    "carbs_g": 385,
    "fiber_g": 35
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
    "moderate_aerobic_min": 150,
    "strength_sessions": 2,
    "steps_daily": 8000
  },
  "calculation_date": "2025-01-15",
  "warnings": []
}
```

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
  - Protein: 1.6-1.8 g/kg body weight
  - Fat: 0.8-1.0 g/kg body weight
  - Carbs: Calculated from residual calories
  - Fiber: 25-35 g daily
- Micronutrient targets are based on WHO/EFSA RDA values for 19-50 age group
- Hydration targets are appropriate for body weight and activity level (~30 ml/kg)
- Activity targets follow WHO recommendations (150/75 min/week)