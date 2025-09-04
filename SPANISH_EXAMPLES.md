# Spanish Language Support Examples

This document provides examples of how to use the BMI App with Spanish language support.

## Web Interface

The web interface now supports Spanish language selection. When you visit the root endpoint (`/`), you can select "Español" from the language dropdown in the top right corner. The form labels and buttons will automatically translate to Spanish.

## API Examples

### 1. BMI Calculation in Spanish

```bash
curl -X POST "http://localhost:8000/bmi" \
  -H "Content-Type: application/json" \
  -d '{
    "weight_kg": 70,
    "height_m": 1.75,
    "age": 30,
    "gender": "hombre",
    "pregnant": "no",
    "athlete": "no",
    "waist_cm": 80,
    "lang": "es"
  }'
```

**Response:**
```json
{
  "bmi": 22.9,
  "category": "Peso normal",
  "note": "",
  "athlete": false,
  "group": "general"
}
```

### 2. Body Fat Estimation in Spanish

```bash
curl -X POST "http://localhost:8000/api/v1/bodyfat" \
  -H "Content-Type: application/json" \
  -d '{
    "weight_kg": 70,
    "height_m": 1.75,
    "age": 30,
    "gender": "hombre",
    "waist_cm": 80,
    "neck_cm": 35,
    "language": "es"
  }'
```

**Response:**
```json
{
  "methods": {
    "deurenberg": 19.45,
    "us_navy": 18.72,
    "ymca": 18.21
  },
  "median": 18.72,
  "lang": "es",
  "labels": {
    "methods": "métodos",
    "median": "mediana",
    "units": "%"
  }
}
```

### 3. BMI Pro Analysis in Spanish

```bash
curl -X POST "http://localhost:8000/api/v1/bmi/pro" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "weight_kg": 70,
    "height_cm": 175,
    "age": 30,
    "gender": "hombre",
    "pregnant": "no",
    "athlete": "no",
    "waist_cm": 80,
    "hip_cm": 90,
    "lang": "es"
  }'
```

**Response:**
```json
{
  "bmi": 22.9,
  "bmi_category": "Peso normal",
  "wht_ratio": 0.46,
  "wht_risk_category": "Riesgo bajo para la salud",
  "wht_risk_level": "Bajo",
  "wht_description": "Rango de peso saludable",
  "whr_ratio": 0.89,
  "whr_risk_level": "Moderado",
  "whr_description": "CCR ≥ 0.8 para hombres → riesgo adicional.",
  "ffmi": null,
  "ffm_kg": null,
  "obesity_stage": "0",
  "risk_factors": 1,
  "recommendation": "Mantén el equilibrio actual.",
  "note": ""
}
```

## Supported Spanish Terms

The application recognizes Spanish terms for various fields:

- **Gender**: "hombre" (male), "mujer" (female)
- **Pregnant**: "si" or "sí" (yes), "no" (no)
- **Athlete**: "atleta" (athlete), "si" (yes), "no" (no)

## Language Parameter

All API endpoints accept a language parameter:
- `/bmi` endpoint: `lang` parameter
- `/api/v1/bodyfat` endpoint: `language` parameter
- `/api/v1/bmi/pro` endpoint: `lang` parameter

The supported language codes are:
- "ru" for Russian
- "en" for English  
- "es" for Spanish

When no language parameter is provided, the application defaults to Russian ("ru").