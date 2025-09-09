# Sources & Units Documentation

## Overview

This document provides comprehensive information about the sources and units
used in the BMI App 2025 nutrition calculation system.

## Data Sources

### WHO (World Health Organization)

- **Primary source** for international nutrition recommendations
- **Reference**: WHO Technical Report Series 916 - Diet, Nutrition and the
  Prevention of Chronic Diseases
- **Coverage**: Global recommendations for macronutrients, micronutrients, and
  physical activity
- **Languages**: Available in multiple languages including English, Spanish,
  and Russian

### EFSA (European Food Safety Authority)

- **Secondary source** for European-specific nutrition guidelines
- **Reference**: EFSA Panel on Dietetic Products, Nutrition and Allergies (NDA)
- **Coverage**: European Union nutrition recommendations and safety assessments
- **Focus**: Micronutrient reference values and tolerable upper intake levels

### DRI (Dietary Reference Intakes)

- **US/Canadian source** for comprehensive nutrition standards
- **Reference**: Institute of Medicine (IOM) Dietary Reference Intakes
- **Coverage**: Complete set of nutrient recommendations for North America
- **Categories**: EAR, RDA, AI, UL for all essential nutrients

## Units and Conversions

### Vitamin D Conversion

- **Standard conversion**: 1 µg (microgram) = 40 IU (International Units)
- **Formula**: `IU = µg × 40`
- **Example**: 15 µg = 600 IU
- **Reference**: WHO/FAO Vitamin and Mineral Requirements in Human Nutrition

### Micronutrient Units

#### Minerals

- **Iron (Fe)**: mg (milligrams)
- **Calcium (Ca)**: mg (milligrams)
- **Magnesium (Mg)**: mg (milligrams)
- **Potassium (K)**: mg (milligrams)
- **Iodine (I)**: µg (micrograms)

#### Vitamins

- **Vitamin D**: IU (International Units)
- **Vitamin B12**: µg (micrograms)
- **Folate**: µg (micrograms)

#### Macronutrients

- **Protein**: g (grams)
- **Fat**: g (grams)
- **Carbohydrates**: g (grams)
- **Fiber**: g (grams)
- **Water**: ml (milliliters)

### Physical Activity Units

- **Aerobic exercise**: minutes per week
- **Strength training**: sessions per week
- **Daily steps**: steps per day

## API Examples

### Spanish (ES) Localization Example

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "sex": "female",
    "age": 30,
    "height_cm": 168,
    "weight_kg": 60,
    "activity": "moderate",
    "goal": "maintain",
    "life_stage": "adult",
    "lang": "es"
  }'
```

**Expected Response (Spanish)**:

```json
{
  "kcal_daily": 2075,
  "macros": {
    "protein_g": 96,
    "fat_g": 54,
    "carbs_g": 301,
    "fiber_g": 29
  },
  "water_ml": 1800,
  "priority_micros": {
    "iron_mg": 18.0,
    "calcium_mg": 1000.0,
    "folate_ug": 400.0,
    "vitamin_d_iu": 600.0,
    "b12_ug": 2.4,
    "iodine_ug": 150.0,
    "magnesium_mg": 310.0,
    "potassium_mg": 3500.0
  },
  "activity_weekly": {
    "moderate_aerobic_min": 150,
    "strength_sessions": 2,
    "steps_daily": 8000
  },
  "calculation_date": "2025-09-08",
  "warnings": []
}
```

### English (EN) Localization Example

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "sex": "male",
    "age": 35,
    "height_cm": 180,
    "weight_kg": 75,
    "activity": "active",
    "goal": "maintain",
    "life_stage": "adult",
    "lang": "en"
  }'
```

### Russian (RU) Localization Example

```bash
curl -X POST "http://localhost:8000/api/v1/premium/targets" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "sex": "female",
    "age": 28,
    "height_cm": 170,
    "weight_kg": 65,
    "activity": "light",
    "goal": "maintain",
    "life_stage": "pregnant",
    "lang": "ru"
  }'
```

## Life Stage Warnings

### Warning Codes and Messages

#### Teen (12-18 years)

- **EN**: "Teen life stage: use age-appropriate references."
- **ES**: "Etapa adolescente: use referencias apropiadas para la edad."
- **RU**: "Подростковая группа: используйте специализированные нормы."

#### Pregnant

- **EN**: "Pregnancy: requirements differ; consult specialized guidelines."
- **ES**: "Embarazo: los requisitos difieren; consulte guías especializadas."
- **RU**: "Беременность: нормы отличаются; обратитесь к специализированным рекомендациям."

#### Lactating

- **EN**: "Lactation: increased nutrient requirements."
- **ES**: "Lactancia: requisitos de nutrientes aumentados."
- **RU**: "Лактация: повышенные потребности в нутриентах."

#### Elderly (51+ years)

- **EN**: "Age 51+: micronutrient needs may differ."
- **ES**: "51+: las necesidades de micronutrientes pueden diferir."
- **RU**: "51+: возможна иная потребность в микронутриентах."

#### Child (<12 years)

- **EN**: "Child age: use pediatric references."
- **ES**: "Edad infantil: use referencias pediátricas."
- **RU**: "Детский возраст: используйте педиатрические нормы."

## Validation Rules

### Age Validation

- **Minimum**: 1 year
- **Maximum**: 100 years
- **Special cases**: 0 years returns 422 error

### Height Validation

- **Minimum**: 0.1 cm
- **Maximum**: No upper limit (practical limit ~300 cm)
- **Special cases**: 0 cm returns 422 error

### Weight Validation

- **Minimum**: 0.1 kg
- **Maximum**: No upper limit (practical limit ~500 kg)
- **Special cases**: 0 kg returns 422 error

### Body Fat Validation

- **Minimum**: 0%
- **Maximum**: 50%
- **Special cases**: Negative values or >50% return 422 error

### Deficit/Surplus Validation

- **Deficit**: 0-25% (for weight loss goal)
- **Surplus**: 0-20% (for weight gain goal)
- **Special cases**: Values outside ranges return 422 error

## Error Handling

### 422 Unprocessable Entity

Returned for:

- Missing required fields
- Invalid enum values
- Out-of-range numeric values
- Type mismatches
- Malformed JSON

### 200 OK

Returned for:

- Valid requests
- Invalid language codes (API is tolerant)
- Extra fields (API is tolerant)
- Empty string values (API is tolerant)

## ES Example

**Spanish API Example with curl:**

```bash
curl -s http://localhost:8000/api/v1/premium/targets \
  -H "Content-Type: application/json" \
  -d '{
    "sex":"female","age":30,"height_cm":170,"weight_kg":65,
    "activity":"moderate","goal":"maintain","lang":"es"
  }' | jq
```

## References

1. WHO Technical Report Series 916 - Diet, Nutrition and the Prevention of
   Chronic Diseases
2. EFSA Panel on Dietetic Products, Nutrition and Allergies (NDA) - Scientific
   Opinion on Dietary Reference Values
3. Institute of Medicine (IOM) - Dietary Reference Intakes
4. WHO/FAO Vitamin and Mineral Requirements in Human Nutrition
5. FastAPI Documentation - Request Validation and Error Handling

## Version History

- **v1.0** (2025-09-08): Initial documentation
- **v1.1** (2025-09-08): Added Spanish localization examples
- **v1.2** (2025-09-08): Added validation rules and error handling
