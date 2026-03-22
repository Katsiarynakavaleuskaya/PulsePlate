# PulsePlate (FastAPI)

[![CI](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/ci.yml/badge.svg)](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/ci.yml)
[![Tests + Coverage](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/coverage.yml/badge.svg)](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/workflows/coverage.yml)
[![codecov](https://codecov.io/gh/Katsiarynakavaleuskaya/PulsePlate/branch/main/graph/badge.svg)](https://codecov.io/gh/Katsiarynakavaleuskaya/PulsePlate)

[![Data sources: USDA, OFF](https://img.shields.io/badge/Data%20sources-USDA%2C%20OFF-brightgreen)](DATA_SOURCES.md)

## 🤖 AI Agent Instructions

Before any changes, read `AGENTS.md` in the repo root and in the relevant module
(for example `app/AGENTS.md`, `core/AGENTS.md`) and follow those rules.

## 📚 Documentation navigation

Quick links to the most important documentation sections:

- 🧭 **Policy & invariants**
  Architectural rules, hard constraints, and engineering lessons
  → [`docs/policy/`](docs/policy/)

- 🛠 **Runbooks (CI / Debug / Ops)**
  How to run checks, debug failures, and operate the system safely
  → [`docs/runbooks/`](docs/runbooks/)

- 🚀 **Deployment**
  Production, staging, infrastructure, Docker, secrets, and platform setup
  → [`docs/deploy/`](docs/deploy/)

- 📐 **Specs & API contracts**
  Backend API, mobile integration, premium targets, formats, sources & units
  → [`docs/specs/`](docs/specs/)

- 🗺 **Roadmaps & plans**
  Product and engineering roadmaps, rollout strategies
  → [`docs/roadmap/`](docs/roadmap/)

- 📊 **Reports & status**
  Progress summaries, fix logs, coverage reports, historical snapshots
  → [`docs/reports/`](docs/reports/)

- 📋 **API Documentation**
  - **VIP Shoplist API**: [`docs/VIP_Shoplist_API.md`](docs/VIP_Shoplist_API.md) — Contract freeze for generate/daily/weekly endpoints

## 🚀 Quick Start

### 🐳 Docker Best Practices

**Docker Image Management:**

```bash
# Build with versioning (recommended)
make docker-build  # Creates both :latest and :<commit-hash> tags

# Clean old images regularly
make docker-clean-images  # Keeps latest 3 versions

# Test locally before CI
make docker-build && docker run -p 8000:8000 pulseplate:latest
curl http://localhost:8000/health  # Verify it works
```

**Docker Quality Checklist:**

- ✅ Always test Docker builds locally before pushing
- ✅ Use versioned tags for production deployments
- ✅ Clean up old images regularly to save disk space
- ✅ Verify health checks work: `curl http://localhost:8000/health`

### ⚠️ Important: Pre-commit Setup

**Always run pre-commit checks before pushing:**

```bash
# Option 1: Use the existing pre-commit hook (recommended)
git commit  # Automatically runs pre-commit hooks

# Option 2: Manual pre-commit
pre-commit run --all-files

# Option 3: Clean cache manually if needed
./scripts/clean-cache.sh
```

**Pre-commit hooks include:**

- ✅ **Black** formatting (line length 100)
- ✅ **Ruff** linting and import sorting
- ✅ **MyPy** type checking
- ✅ **Bandit** security scanning
- ✅ **Automatic cache cleanup** (removes `__pycache__` and `.pyc` files)

### Python Version

- Закреплена версия Python: 3.13.6 (`.python-version`, `.tool-versions`).
- Рекомендуемая установка через `pyenv` или `asdf`.

Setup (pyenv):

```bash
pyenv install 3.13.6 -s
pyenv local 3.13.6
python -V  # Python 3.13.6
```

Setup (asdf):

```bash
asdf plugin add python || true
asdf install python 3.13.6
asdf local python 3.13.6
python -V  # Python 3.13.6
```

Create venv and install deps:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
pip install -r requirements-dev.txt
pip install -r requirements.txt
```

**Important**: The `.venv` directory is not tracked in git and should never be committed. Each developer must create their own virtualenv locally using the command above. This ensures that activation scripts contain dynamic paths specific to each developer's environment, avoiding hardcoded absolute paths.

## Инструменты автоматизации (cspell, husky, и т.д.)

```bash
npm ci

# Быстрый запуск окружения (shell + PYTHONPATH + алиасы)
source scripts/dev_shell.sh

# Проверка типов (автоустановка missing types)
./scripts/mypy_check.sh

# (Опционально) Настроить git post-commit напоминание
./scripts/install_post_commit_reminder.sh
```

**📋 Archived planning docs moved to `docs/archive/`**
**⚡ [QUICK_START.md](docs/archive/2025-09-16/QUICK_START.md)** - Исторический быстрый старт

## Database

- Приложение использует SQLAlchemy 2.x + Alembic. Базовая конфигурация находится в `core/db.py`.
- По умолчанию создаётся SQLite-файл `cache/app.db`. Переопределите `DATABASE_URL`, чтобы подключиться к PostgreSQL (через `psycopg[binary]`) или другой БД.
- Миграции управляются Alembic (`alembic.ini`, каталог `alembic/`). Первичная ревизия создаёт таблицу `users`.
- Быстрый старт data layer:
  1. `alembic upgrade head` — применить миграции к текущему `DATABASE_URL`.
  2. `uvicorn app.main:app --reload` — запустить API локально.
  3. `curl -s http://127.0.0.1:8000/health/db` — убедиться, что подключение к БД работает.
- Примеры запросов к пользовательскому API:

  ```bash
  curl -s -X POST http://127.0.0.1:8000/api/v1/users \
       -H 'Content-Type: application/json' \
       -d '{"email": "demo@example.com", "name": "Demo"}'
  curl -s http://127.0.0.1:8000/api/v1/users
  ```

### Database fallback behavior (ops)

When primary DB initialization fails, the app can fall back to SQLite based on
explicit opt-in flags. Use these controls to keep production safe and observable:

- `DB_FALLBACK_URL` (default: `sqlite:///:memory:`) — fallback SQLite URL used only
  when fallback is triggered. Example: `sqlite:///./fallback.db`.
- `ALLOW_DB_PERSISTENT_FALLBACK` (default: unset/false) — required in production to
  allow any fallback. Production never accepts in-memory fallbacks.
- `ALLOW_DB_INMEMORY_FALLBACK` (default: unset/false) — allows in-memory fallbacks in
  non-production; otherwise non-prod only falls back on IO errors.

**Production constraints**

- In-memory fallback is never allowed in production.
- Set `ALLOW_DB_PERSISTENT_FALLBACK=1` and a persistent `DB_FALLBACK_URL` to enable
  fallback (for example `sqlite:///./fallback.db`).

**Non-production behavior**

- Fallback is allowed when `ALLOW_DB_INMEMORY_FALLBACK=1` or when the initial DB
  error is an IO error (e.g., filesystem/network issue). Default fallback target is
  in-memory unless `DB_FALLBACK_URL` is set.

**Signals and monitoring**

- `DB_HEALTH_DEGRADED=1` environment flag is set when fallback is active.
- Module flag `_db_fallback_active` is toggled to `True`.
- Metrics: `db_fallback_active` counter (tags `env:<env>` and `backend:<memory|sqlite>`).

**Recommended actions when fallback is active**

- Verify `DATABASE_URL` connectivity, credentials, and upstream DB health.
- Confirm `DB_FALLBACK_URL` points to persistent storage before enabling production fallback.
- Restore primary DB connectivity, then redeploy with fallback disabled to return to normal.

## Overview

PulsePlate is a comprehensive health and nutrition application that provides BMI calculations, body fat percentage analysis, and personalized nutrition recommendations.

### Feature Flags and Auth

- `FEATURE_PREMIUM_NUTRITION` — enable premium endpoints (plate/targets). Off by default.
- `VIP_MODULE_ENABLED` — include VIP router if available (safe fallback if missing).
- `FEATURE_RAG` — enable lightweight RAG context in `/insight` endpoints. Off by default.
- `API_KEY` — API key for `/api/v1/*` routes. When set, strict equality is enforced.
- `API_KEY_REQUIRED` — when `true` and `API_KEY` is not set, requests are rejected (prod safety).

Fine-tuning options and integrating tuned models: see `docs/finetune/README.md`.

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

- `GET /` - Direct-API JSON probe when hitting FastAPI without Caddy (operators / scanners); apex browsers get the SPA from static hosting
- `GET /legacy/bmi-calculator` - Legacy standalone HTML form for BMI (same UI historically served at `/`)

### Body Fat Estimation

- `POST /api/v1/bodyfat` - Body fat percentage estimation

### Insight (AI-powered)

- `POST /api/v1/insight` - AI insight on text (requires X-API-Key header)
  - Input: `{"text": "I feel tired"}`
  - Output: `{"provider": "stub", "insight": "insight::deriat"}`
- `POST /api/v1/insight/fitchef` - VIP-only FitChef mascot coaching insight (feature-flagged)
  - Input: `{"query": "I keep snacking late at night"}`
  - Output: mascot coaching envelope with `message`, `action_items`, `sources`, and `warnings`
- `POST /api/v1/insight/fitchef/weekly-reflection` - VIP-only FitChef weekly reflection coaching (feature-flagged)
  - Input: `{"summary": "Late dinners made the week feel uneven", "goal": "more steady meals"}`
  - Output: weekly reflection coaching envelope with `message`, `action_items`, `sources`, and `warnings`
- `POST /api/v1/insight/fitchef/slip-support` - VIP-only FitChef slip-support coaching (feature-flagged)
  - Input: `{"event_text": "I kept snacking after dinner", "goal": "more steady meals"}`
  - Output: slip-support coaching envelope with `message`, `action_items`, `sources`, and `warnings`

### Tiered Nutrition APIs

For the current canonical tier map and compatibility surface, see `docs/contracts/API_CANONICAL_MAP.md`.

#### Legacy-Compatible BMR/TDEE Endpoints

- `POST /api/v1/premium/bmr` - Advanced BMR calculation using multiple formulas (requires X-API-Key header; legacy-compatible premium namespace)
  - Input: `{"weight_kg": 70, "height_cm": 175, "age": 30, "sex": "male", "bodyfat": 15}`
  - Output: BMR values using Harris-Benedict, Mifflin-St Jeor, and Katch-McArdle formulas

- `POST /api/v1/premium/tdee` - TDEE calculation with activity factors (requires X-API-Key header; legacy-compatible premium namespace)
  - Input: BMR data + `{"activity": "moderate"}`
  - Output: TDEE values for different activity levels

#### Plate / Targets / Weekly Planning

- `POST /api/v1/premium/plate` remains available as a legacy compatibility surface.
- Canonical PRO and VIP planning routes are documented in `docs/contracts/API_CANONICAL_MAP.md`.
- Use the canonical map when choosing between `/api/v1/pro/*`, `/api/v1/vip/*`, and deprecated `/api/v1/premium/*` paths.

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
    "veg_cups": 1.0
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
  ],
  "meals_per_day": 3,
  "day_micros": {}
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

**Response Fields:**

- `meals_per_day` (int): Number of meals recommended per day
- `day_micros` (Dict[str, float]): Daily micronutrient totals. Keys follow pattern `{nutrient}_{unit}` (e.g., `iron_mg`, `vitamin_d_iu`, `b12_ug`) with units `mg`, `ug`, or `iu`. Currently returns `{}`; will be populated in v2.0+. Frontend: map string keys to float values.

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
   git clone https://github.com/Katsiarynakavaleuskaya/PulsePlate.git
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
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Note: the ASGI entrypoint is now `app.main:app` (the legacy `legacy_app.py` entrypoint
is deprecated), so update any local scripts or CI that still invoke `legacy_app.py`.

Access the API at `http://localhost:8000`

## API Endpoints

- `POST /api/v1/bmi` - Calculate BMI
- `POST /api/v1/bodyfat` - Calculate body fat percentage
- `POST /api/v1/insight` - Generate AI insight text output (requires `API_KEY`)
- `POST /api/v1/insight/fitchef` - Generate VIP-only FitChef mascot coaching output (requires VIP-tier `API_KEY` access and `FEATURE_FITCHEF_MASCOT`)
- `POST /api/v1/insight/fitchef/weekly-reflection` - Generate VIP-only FitChef weekly reflection output (requires VIP-tier `API_KEY` access and `FEATURE_FITCHEF_MASCOT`)
- `POST /api/v1/insight/fitchef/slip-support` - Generate VIP-only FitChef slip-support output (requires VIP-tier `API_KEY` access and `FEATURE_FITCHEF_MASCOT`)
- Tiered nutrition, planning, payments, and compatibility routes are summarized in `docs/contracts/API_CANONICAL_MAP.md`

### Weekly planning note

- Canonical weekly planning surfaces live in the `/api/v1/pro/*` and `/api/v1/vip/*` namespaces.
- The legacy compatibility route `/api/v1/premium/plan/week` is retained for migration, but it should not be treated as the canonical namespace.
- Dev (default): open access to simplify local testing and CI for the compatibility weekly-plan route.
- Prod (optional): set `FEATURE_ENFORCE_AUTH_WEEK=1` and `API_KEY=...` to enforce header `X-API-Key` for `/api/v1/premium/plan/week`.
  - With the flag enabled, invalid or missing key returns `403`.
  - Other premium endpoints remain protected by `API_KEY` as usual.

## Testing

Run tests:

```bash
pytest
```

## CRON Setup

To automatically update the food database weekly, see [CRON.md](docs/runbooks/CRON.md)

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

- GitHub Actions runs on Python 3.13.6 with full coverage enforcement at 97%.
- Coverage is enforced at 97% via `--cov-fail-under=97`.
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
  - **Pre-commit hooks** for code quality (Black, Ruff, MyPy, Bandit)
  - **Automatic cache cleanup** in CI and pre-commit hooks
  - API key authentication and optional rate limiting

## 🚀 Staging Deployment

### Prerequisites

- VPS with Docker and Docker Compose installed
- Domain name pointing to your server
- GitHub repository with staging environment configured

### Server Setup

1. **Install Docker and Docker Compose**:

   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER
   ```

2. **Create staging directory**:

   ```bash
   sudo mkdir -p /srv/pulseplate-staging
   ```

3. **Copy deployment files**:

   ```bash
   sudo cp deploy/docker-compose.staging.yaml /srv/pulseplate-staging/
   sudo cp deploy/Caddyfile /srv/pulseplate-staging/
   sudo cp scripts/deploy.sh /srv/pulseplate-staging/
   sudo chmod +x /srv/pulseplate-staging/deploy.sh
   ```

4. **Create environment file**:

   ```bash
   sudo touch /srv/pulseplate-staging/.env
   # Add your application secrets and STAGING_DOMAIN=your-domain.com
   ```

### GitHub Environment Setup

Configure the following secrets in GitHub → Settings → Environments → `staging`:

- `SSH_HOST_STAGING` - Your server IP or domain
- `SSH_USER` - SSH username
- `SSH_KEY` - Private SSH key
- `GHCR_READ_TOKEN` - GitHub PAT with read:packages permission
- `STAGING_DOMAIN` - Your staging domain (e.g., staging.example.com)

### Deployment

Staging automatically deploys when you push to the `main` branch. The deployment process:

1. Builds Docker image and pushes to GHCR
2. Connects to staging server via SSH
3. Pulls latest image
4. Runs database migrations
5. Restarts application stack
6. Verifies health endpoint

### Manual Deployment

To deploy manually:

```bash
cd /srv/pulseplate-staging
./deploy.sh latest
```

## 🚀 Production Deployment

Production deployments are automated via GitHub Actions with manual approval gates.

### Production Prerequisites

- Production server configured (see [PRODUCTION.md](docs/deploy/PRODUCTION.md))
- GitHub environment `production` configured with required secrets
- Protection rules enabled for manual approval

### Deployment Process

1. **Create a release tag**:

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **GitHub Actions will**:
   - Build and push Docker image (triggered by tag push)
   - Wait for manual approval (production environment)
   - Wait for Docker image to be available (up to 5 minutes)
   - Deploy to production server
   - Run health checks

3. **Monitor deployment**:
   - Check GitHub Actions logs
   - Verify health endpoint: `https://yourdomain.com/health`

## PulsePlate Copilot Agent

Интеграция кастомного Copilot‑агента для проекта PulsePlate. Файл спецификации агента находится по пути [.github/agents/my-agent.md](.github/agents/my-agent.md). В нём описаны роли, миссия, режимы отчётов, технические и маркетинговые требования. Добавьте этот файл в репозиторий, чтобы активировать агента Copilot для разработки и аналитики.

### Production Features

- ✅ **Manual approval gates** for safety
- ✅ **Automatic database backups** before deployment (keeps last 30 backups for recovery flexibility)
- ✅ **Health checks** with retry logic
- ✅ **Rollback capability** via previous tags
- ✅ **SSL/TLS** automatic via Caddy + Cloudflare Full Strict
- ✅ **Security headers** (HSTS, CSP, X-Frame-Options, etc.)
- ✅ **Server hardening** (UFW, fail2ban, SSH key-only access)
- ✅ **Resource limits** and monitoring
- ✅ **Monitoring & alerting** (Prometheus, Grafana, PagerDuty) - see [PRODUCTION.md](docs/deploy/PRODUCTION.md#monitoring)

For detailed setup instructions, see:

- **[START_HERE_RU.md](docs/START_HERE_RU.md)** - Главная точка входа для новичков
- [OVERVIEW.md](docs/deploy/OVERVIEW.md) - Полная пошаговая инструкция
- [PRODUCTION.md](docs/deploy/PRODUCTION.md) - Детальная настройка production

## License

This project is proprietary software. All rights reserved. Unauthorized copying, distribution, modification, or use of this code is strictly prohibited without prior written permission from the author.

For commercial or licensing inquiries, please contact: <lexakm532@gmail.com>

See the [LICENSE](LICENSE) file for full details.
