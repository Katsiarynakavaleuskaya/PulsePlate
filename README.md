# BMI-App 2025 (FastAPI)

[![python-tests](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/python-tests.yml)
[![CI](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/ci.yml/badge.svg)](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/ci.yml)

[![Data sources: USDA, OFF](https://img.shields.io/badge/Data%20sources-USDA%2C%20OFF-brightgreen)](DATA_SOURCES.md)

## 🚀 Quick Start

**📋 [TODO.md](TODO.md)** - Основной план задач (спринт "Улучшение покрытия и документации" завершен ✅)  
**⚡ [QUICK_START.md](QUICK_START.md)** - Быстрый старт работы с проектом

## Overview

BMI-App 2025 is a comprehensive health and nutrition application that provides BMI calculations, body fat percentage analysis, and personalized nutrition recommendations.

## Features

- BMI calculation with category classification
- Body fat percentage analysis using multiple formulas
- Personalized nutrition targets based on WHO recommendations
- **Weekly meal planning with nutrient coverage analysis**
- **Professional food database pipeline with data from USDA and Open Food Facts**

## Professional Food Database Pipeline

The application now includes a professional food database pipeline that merges data from multiple sources:

- **USDA FoodData Central** - Primary source for nutrient data
- **Open Food Facts** - Secondary source for additional foods and brand information
- **Canonical mapping** - Eliminates duplicates and standardizes food names
- **Automated merging** - Combines data with priority rules and conflict resolution
- **CRON scheduling** - Automatic weekly updates

### Data Pipeline Components

```text
core/
  food_sources/
    base.py          # Base adapter interface
    usda.py          # USDA adapter
    off.py           # Open Food Facts adapter
  food_merge.py      # Data merging logic
  units.py           # Unit conversion helpers
  aliases.py         # Canonical name mapping
data/
  food_aliases.csv   # Alias to canonical name mapping
  food_db.csv        # Merged food database (generated)
  food_merge_report.json # Merge statistics and reports
scripts/
  build_food_db.py   # Build script
  schedule_food_db_update.py # CRON scheduler
external/
  usda_fdc_sample.csv # USDA data sample
  off_products_sample.csv # OFF data sample
```

### Food Database Schema

The merged food database follows a standardized schema:

---

## 📋 API Endpoints

### Health & Monitoring

- `GET /health` - Health check
- `GET /api/v1/health` - V1 health check
- `GET /metrics` - Uptime metrics
- `GET /privacy` - Privacy policy

### BMI Calculation

- `POST /bmi` - Legacy BMI endpoint
- `POST /api/v1/bmi` - V1 BMI calculation (requires X-API-Key header)
  - Input: `{"weight_kg": 70, "height_cm": 170, "group": "general"}`
  - Output: `{"bmi": 24.2, "category": "Healthy weight", "interpretation": ""}`

### Web UI

- `GET /` - Simple web interface for BMI calculation

### Body Fat Estimation

- `POST /api/v1/bodyfat` - Body fat percentage estimation

### Insight (AI-powered)

- `POST /api/v1/insight` - AI insight on text (requires X-API-Key header)
  - Input: `{"text": "I feel tired"}`
  - Output: `{"provider": "stub", "insight": "insight::deriat"}`

### Premium APIs

#### BMR/TDEE Calculations

- `POST /api/v1/premium/bmr` - Advanced BMR calculation using multiple formulas (requires X-API-Key header)
  - Input: `{"weight_kg": 70, "height_cm": 175, "age": 30, "sex": "male", "bodyfat": 15}`
  - Output: BMR values using Harris-Benedict, Mifflin-St Jeor, and Katch-McArdle formulas

- `POST /api/v1/premium/tdee` - TDEE calculation with activity factors (requires X-API-Key header)
  - Input: BMR data + `{"activity": "moderate"}`
  - Output: TDEE values for different activity levels

#### Enhanced My Plate - Visual Nutrition Planning

- `POST /api/v1/premium/plate` - Generate personalized visual plate with hand/cup portions (requires X-API-Key header)

**Request Example:**

```json
{
  "name": "spinach_raw",
  "group": "veg",
  "per_g": 100.0,
  "kcal": 23.0,
  "protein_g": 2.9,
  "fat_g": 0.4,
  "carbs_g": 3.6,
  "fiber_g": 2.2,
  "Fe_mg": 2.7,
  "Ca_mg": 99.0,
  "VitD_IU": 0.0,
  "B12_ug": 0.0,
  "Folate_ug": 194.0,
  "Iodine_ug": 20.0,
  "K_mg": 558.0,
  "Mg_mg": 79.0,
  "flags": ["GF", "VEG"],
  "price": 0.0,
  "source": "MERGED(USDA,OFF)",
  "version_date": "2025-09-04"
}
```

**Response Example:**

```json
{
  "kcal": 1846,
  "macros": {
    "protein_g": 117,
    "fat_g": 52,
    "carbs_g": 228,
    "fiber_g": 25
  },
  "portions": {
    "protein_palm": 1.3,
    "fat_thumbs": 1.4,
    "carb_cups": 1.9,
    "veg_cups": 1.0,
    "meals_per_day": 3
  },
  "layout": [
    {
      "kind": "plate_sector",
      "fraction": 0.3,
      "label": "Овощи/Зелень",
      "tooltip": "Низкая калорийность, клетчатка 25–35 г/сут"
    },
    {
      "kind": "plate_sector",
      "fraction": 0.23,
      "label": "Белок",
      "tooltip": "117 г/сут"
    },
    {
      "kind": "plate_sector",
      "fraction": 0.35,
      "label": "Крахмалы/Зерно",
      "tooltip": "228 г/сут"
    },
    {
      "kind": "plate_sector",
      "fraction": 0.12,
      "label": "Полезные жиры",
      "tooltip": "52 г/сут"
    },
    {
      "kind": "bowl",
      "fraction": 1.0,
      "label": "Чашка крупы",
      "tooltip": "≈1 cup/приём"
    },
    {
      "kind": "bowl",
      "fraction": 1.0,
      "label": "Чашка овощей",
      "tooltip": "≈1–2 cup/приём"
    }
  ],
  "meals": [
    {
      "title": "Овсянка + орехи + ягоды (бюджет)",
      "kcal": 461,
      "protein_g": 29,
      "fat_g": 13,
      "carbs_g": 57
    },
    {
      "title": "Гречка + тофу + салат (бюджет)",
      "kcal": 646,
      "protein_g": 40,
      "fat_g": 18,
      "carbs_g": 79
    },
    {
      "title": "Рис + нут + овощи (бюджет)",
      "kcal": 738,
      "protein_g": 46,
      "fat_g": 20,
      "carbs_g": 91
    }
  ]
}
```

**Enhanced Parameters:**

- `sex` (required): Biological sex ("male" or "female")
- `age` (required): Age in years (10-100)
- `height_cm` (required): Height in centimeters (> 0)
- `weight_kg` (required): Weight in kilograms (> 0)
- `activity` (required): Activity level ("sedentary", "light", "moderate", "active", "very_active")
- `goal` (required): Nutrition goal ("loss", "maintain", "gain")
- `deficit_pct` (optional): Calorie deficit percentage for loss goal (5-25%)
- `surplus_pct` (optional): Calorie surplus percentage for gain goal (5-20%)
- `bodyfat` (optional): Body fat percentage (3-60%)
- `diet_flags` (optional): Diet preferences (["VEG", "GF", "DAIRY_FREE", "LOW_COST"])

**Visual Plate Features:**

- **4 Plate Sectors**: Vegetables (30%), Protein, Carbs, Healthy Fats (proportional to macros)
- **2 Serving Bowls**: Grain cup and vegetable cup visualization
- **Hand/Cup Portions**: Real-world measurements (palms, thumbs, cups)
- **Precise Control**: Custom deficit/surplus percentages vs. fixed goals
- **Diet Adaptations**: Meal modifications for dietary preferences
- **Frontend Ready**: JSON layout specification for SVG/Canvas rendering

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean.git
   cd BMI-App_2025_clean
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Usage

Start the application:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Access the API at `http://localhost:8000`

## API Endpoints

- `POST /api/v1/bmi` - Calculate BMI
- `POST /api/v1/bodyfat` - Calculate body fat percentage
- `POST /api/v1/premium/bmr` - Calculate BMR and TDEE (requires `API_KEY`)
- `POST /api/v1/premium/plan/week` - Generate weekly meal plan (open by default)

### Auth behavior for weekly plan

- Dev (default): open access to simplify local testing and CI.
- Prod (optional): set `FEATURE_ENFORCE_AUTH_WEEK=1` and `API_KEY=...` to enforce header `X-API-Key` for `/api/v1/premium/plan/week`.
  - With the flag enabled, invalid or missing key returns `403`.
  - Other premium endpoints remain protected by `API_KEY` as usual.

## Testing

Run tests:

```bash
pytest
```

## CRON Setup

To automatically update the food database weekly, see [CRON_SETUP.md](CRON_SETUP.md)

### Advanced Testing

```bash
pytest -q tests/test_food_apis_*.py
```

- Example env for endpoints requiring API key:

```bash
export API_KEY=test_key
```

Locally (without Makefile):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q --maxfail=1 --cov=. --cov-report=term-missing
```

### Linting

```bash
make lint
```

---

## 🧪 CI & Coverage Policy

- GitHub Actions runs on Python 3.12 and 3.13 (matrix).
- Coverage is enforced at 100% via `--cov-fail-under=100`.
- Environment sets `APP_ENV=ci` to avoid auto-loading `.env` during tests.
- Bandit & Safety run as non-blocking checks (artifacts available in CI logs).
- Coverage report (`coverage.xml`) is uploaded as an artifact per job.

## 🔒 Security & Compliance

- API Key authentication for sensitive endpoints
- Optional rate limiting with SlowAPI
- GDPR compliance for health data (no storage, privacy policy)
- Property-based testing with Hypothesis for robustness

---

## 📊 Features

- **Asynchronous Endpoints**: All endpoints are now async for better concurrency and scalability
- **Free Tier**:
  - BMI calculation with categories and special population support
  - Body fat estimation using multiple formulas
  - BMI visualization charts (when **matplotlib** available)
  - AI insights via configurable LLM providers (Stub, Grok, Ollama)
- **Premium Tier**:
  - Advanced BMR calculations (Harris-Benedict, Mifflin-St Jeor, Katch-McArdle)
  - TDEE calculations with activity level factors
  - **Enhanced My Plate**: Visual nutrition planning with plate sectors and hand/cup portions
  - Precise deficit/surplus percentage control (5-25% loss, 5-20% gain)
  - Diet flag adaptations (VEG, GF, DAIRY_FREE, LOW_COST)
  - Visual layout specification for frontend rendering (SVG/Canvas ready)
  - Goal-specific macro optimization and meal suggestions
  - Real-world portion measurements (palms, thumbs, cups)
- **Development & Operations**:
  - Comprehensive test suite with 97%+ coverage (enforced in CI)
  - Docker support with optimized production builds
  - CI/CD with GitHub Actions and automated security scans
  - Simple web UI at root path for easy BMI calculation
  - Structured logging and request monitoring
  - API key authentication and optional rate limiting

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
