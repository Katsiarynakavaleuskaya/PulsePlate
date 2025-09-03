# BMI-App 2025 (FastAPI)
[![python-tests](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/python-tests.yml/badge.svg)](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/python-tests.yml)
[![CI](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/ci.yml/badge.svg)](https://github.com/Katsiarynakavaleuskaya/BMI-App_2025_clean/actions/workflows/ci.yml)

Приложение для расчёта BMI на FastAPI с автотестами, покрытием и Docker.

---

## 🚀 Quick Start

### 1) Локальный запуск (venv)

```bash
make venv
source .venv/bin/activate
make dev
# откроется на http://127.0.0.1:8001/docs
```

### 2) Docker

```bash
make docker-build
make docker-run
```

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
  "sex": "female",
  "age": 30,
  "height_cm": 170,
  "weight_kg": 65,
  "activity": "moderate",
  "goal": "loss",
  "deficit_pct": 15,
  "diet_flags": ["VEG", "LOW_COST"]
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

---

## 🔧 Development

See also: `CONTRIBUTING.md` for branch policy and PR rules.

<!-- verify auto-delete workflow: temporary PR note -->

### Testing

```bash
make test
make coverage
```

### Testing & Coverage (pytest)

- Run all tests with coverage summary:

```bash
pytest -q --maxfail=1 --disable-warnings --cov --cov-report=term-missing
```

- Generate HTML coverage report (open `htmlcov/index.html`):

```bash
pytest --cov --cov-report=html
```

- Run only fast, focused tests for the integrations layer:

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
  - BMI visualization charts (when matplotlib available)
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
