# Spanish (Español) API Examples

This document provides Spanish language examples for the Premium Targets API.

## Endpoint

```
POST /api/v1/premium/targets
```

## Request Headers

```
X-API-Key: YOUR_API_KEY
Content-Type: application/json
```

## Spanish Examples

### 1. Adult Female (Mujer Adulta)

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "female",
    "age": 30,
    "height_cm": 165,
    "weight_kg": 60,
    "activity": "moderate",
    "goal": "maintain",
    "life_stage": "adult",
    "lang": "es"
  }'
```

**Response:**

```json
{
  "kcal_daily": 2075,
  "macros": {
    "protein_g": 102,
    "fat_g": 54,
    "carbs_g": 295,
    "fiber_g": 25
  },
  "water_ml": 1800,
  "priority_micros": {
    "iron_mg": 18.0,
    "calcium_mg": 1000.0,
    "folate_ug": 400.0,
    "vitamin_d_iu": 600.0,
    "b12_ug": 2.4,
    "iodine_ug": 150.0,
    "magnesium_mg": 320.0,
    "potassium_mg": 2600.0
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

### 2. Pregnant Woman (Mujer Embarazada)

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "female",
    "age": 28,
    "height_cm": 170,
    "weight_kg": 70,
    "activity": "moderate",
    "goal": "maintain",
    "life_stage": "pregnant",
    "lang": "es"
  }'
```

**Response:**

```json
{
  "kcal_daily": 2200,
  "macros": {
    "protein_g": 110,
    "fat_g": 58,
    "carbs_g": 312,
    "fiber_g": 28
  },
  "water_ml": 2100,
  "priority_micros": {
    "iron_mg": 27.0,
    "calcium_mg": 1000.0,
    "folate_ug": 600.0,
    "vitamin_d_iu": 600.0,
    "b12_ug": 2.6,
    "iodine_ug": 220.0,
    "magnesium_mg": 350.0,
    "potassium_mg": 2900.0
  },
  "activity_weekly": {
    "moderate_aerobic_min": 150,
    "strength_sessions": 2,
    "steps_daily": 8000
  },
  "calculation_date": "2025-01-15",
  "warnings": [
    {
      "code": "pregnant",
      "message": "Embarazo: los requisitos difieren; consulte referencias especializadas."
    }
  ]
}
```

### 3. Teenage Boy (Adolescente)

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "male",
    "age": 16,
    "height_cm": 175,
    "weight_kg": 65,
    "activity": "active",
    "goal": "maintain",
    "life_stage": "teen",
    "lang": "es"
  }'
```

**Response:**

```json
{
  "kcal_daily": 2800,
  "macros": {
    "protein_g": 120,
    "fat_g": 70,
    "carbs_g": 400,
    "fiber_g": 30
  },
  "water_ml": 1950,
  "priority_micros": {
    "iron_mg": 11.0,
    "calcium_mg": 1300.0,
    "folate_ug": 400.0,
    "vitamin_d_iu": 600.0,
    "b12_ug": 2.4,
    "iodine_ug": 150.0,
    "magnesium_mg": 410.0,
    "potassium_mg": 3000.0
  },
  "activity_weekly": {
    "moderate_aerobic_min": 150,
    "strength_sessions": 2,
    "steps_daily": 8000
  },
  "calculation_date": "2025-01-15",
  "warnings": [
    {
      "code": "teen",
      "message": "Etapa adolescente: use referencias apropiadas para la edad."
    }
  ]
}
```

### 4. Elderly Person (Persona Mayor)

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "X-API-Key: test_key" \
  -H "Content-Type: application/json" \
  -d '{
    "sex": "male",
    "age": 70,
    "height_cm": 175,
    "weight_kg": 75,
    "activity": "light",
    "goal": "maintain",
    "life_stage": "elderly",
    "lang": "es"
  }'
```

**Response:**

```json
{
  "kcal_daily": 2100,
  "macros": {
    "protein_g": 105,
    "fat_g": 58,
    "carbs_g": 300,
    "fiber_g": 25
  },
  "water_ml": 2250,
  "priority_micros": {
    "iron_mg": 8.0,
    "calcium_mg": 1200.0,
    "folate_ug": 400.0,
    "vitamin_d_iu": 800.0,
    "b12_ug": 2.4,
    "iodine_ug": 150.0,
    "magnesium_mg": 420.0,
    "potassium_mg": 3500.0
  },
  "activity_weekly": {
    "moderate_aerobic_min": 150,
    "strength_sessions": 2,
    "steps_daily": 8000
  },
  "calculation_date": "2025-01-15",
  "warnings": [
    {
      "code": "elderly",
      "message": "51+: las necesidades de micronutrientes pueden diferir."
    }
  ]
}
```

## Warning Messages in Spanish

The API provides localized warning messages in Spanish:

- **teen**: "Etapa adolescente: use referencias apropiadas para la edad."
- **pregnant**: "Embarazo: los requisitos difieren; consulte referencias especializadas."
- **lactating**: "Lactancia: requisitos de nutrientes aumentados."
- **elderly**: "51+: las necesidades de micronutrientes pueden diferir."
- **child**: "Edad infantil: use referencias pediátricas."

## Units and Sources

### Micronutrient Units

- **Iron**: mg (milligrams)
- **Calcium**: mg (milligrams)
- **Folate**: μg (micrograms)
- **Vitamin D**: IU (International Units)
- **Vitamin B12**: μg (micrograms)
- **Iodine**: μg (micrograms)
- **Magnesium**: mg (milligrams)
- **Potassium**: mg (milligrams)

### Data Sources

- **WHO**: World Health Organization guidelines
- **EFSA**: European Food Safety Authority
- **DRI**: Dietary Reference Intakes (US)
- **IOM**: Institute of Medicine recommendations

## Validation Rules

All targets are validated to ensure:

- Calorie targets are within safe ranges (1200-4000 kcal)
- Macronutrient distribution follows WHO guidelines
- Micronutrient targets are based on WHO/EFSA RDA values
- Hydration targets are appropriate for body weight and activity level
- Activity targets follow WHO recommendations
