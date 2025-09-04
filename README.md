# PulsePlate

[![Data sources: USDA, OFF](https://img.shields.io/badge/Data%20sources-USDA%2C%20OFF-brightgreen)](DATA_SOURCES.md)

## Overview

PulsePlate is a comprehensive health and nutrition application that provides BMI calculations, body fat percentage analysis, and personalized nutrition recommendations.

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

```
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

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/PulsePlate.git
   cd PulsePlate
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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
