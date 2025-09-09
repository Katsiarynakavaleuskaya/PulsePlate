import logging
import os
import time
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

# VIP Module Feature Flag
VIP_MODULE_ENABLED = os.getenv("VIP_MODULE_ENABLED", "false").lower() == "true"

try:
    from prometheus_client import Counter, Histogram, generate_latest
except ImportError:
    Counter = None
    Histogram = None
    generate_latest = None

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader

# Import routers
from app.routers.foods import router as foods_router
from app.routers.recipes import router as recipes_router

# VIP router (conditional import)
if VIP_MODULE_ENABLED:
    from app.routers.vip import router as vip_router

if TYPE_CHECKING:
    # Type hints for slowapi when not available at runtime
    Limiter = None  # type: ignore
    _rate_limit_exceeded_handler = None  # type: ignore
    RateLimitExceeded = None  # type: ignore
    SlowAPIMiddleware = None  # type: ignore
    get_remote_address = None  # type: ignore
    slowapi_available = False
else:
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware
        from slowapi.util import get_remote_address

        slowapi_available = True
    except ImportError:
        Limiter = None
        _rate_limit_exceeded_handler = None
        get_remote_address = None
        RateLimitExceeded = None
        SlowAPIMiddleware = None
        slowapi_available = False

from pydantic import BaseModel, Field, StrictFloat, model_validator

with suppress(ImportError):
    import dotenv

    # Avoid auto-loading .env during tests/CI to keep predictable defaults
    if os.getenv("PYTEST_CURRENT_TEST") is None and os.getenv(
        "APP_ENV", ""
    ).lower() not in {
        "test",
        "ci",
    }:
        dotenv.load_dotenv()

try:
    from bodyfat import get_router as get_bodyfat_router
except ImportError:
    get_bodyfat_router = None

try:
    from bmi_visualization import (
        MATPLOTLIB_AVAILABLE,
        generate_bmi_visualization,
    )
except ImportError:
    generate_bmi_visualization = None
    MATPLOTLIB_AVAILABLE = False

try:
    from nutrition_core import (
        calculate_all_bmr,
        calculate_all_tdee,
        get_activity_descriptions,
    )
except ImportError:
    calculate_all_bmr = None
    calculate_all_tdee = None
    get_activity_descriptions = None

from bmi_core import bmi_category

# Add import for the new BMI Pro functions
# Note: These imports are kept for potential future use
# from core.bmi_extras import (
#     ffmi,
#     interpret_whr_ratio,
#     interpret_wht_ratio,
#     stage_obesity,
#     whr_ratio,
#     wht_ratio,
# )
# Add import for export functions
from core.exports import to_csv_day, to_csv_week, to_pdf_day, to_pdf_week
from core.food_apis.scheduler import (
    start_background_updates,
    stop_background_updates,
)

# Import routers
try:
    from app.routers.bmi_pro import router as bmi_pro_router
except ImportError:
    bmi_pro_router = None

try:
    from app.routers.premium_week import router as premium_week_router
except ImportError:
    premium_week_router = None

# Import i18n functionality
from core.i18n import Language, t

# Ensure a patchable getter is always available on this module
try:
    from core.food_apis.scheduler import (
        get_update_scheduler as _scheduler_getter,
    )  # type: ignore
except Exception:  # pragma: no cover
    _scheduler_getter = None  # type: ignore


async def get_update_scheduler():  # type: ignore[no-redef]
    """Return the global update scheduler (wrapper to aid patching in tests)."""
    if _scheduler_getter is None:
        from core.food_apis.scheduler import (
            get_update_scheduler as _late_getter,
        )  # type: ignore

        return await _late_getter()
    return await _scheduler_getter()  # type: ignore[misc]


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        import sys as _sys

        _pkg = _sys.modules.get("app")
        _start = (
            getattr(_pkg, "start_background_updates", None)
            if _pkg and hasattr(_pkg, "start_background_updates")
            else start_background_updates
        )
        if callable(_start):
            await _start(update_interval_hours=24)
        logger.info("Started background database updates")
    except Exception as e:
        logger.error(f"Failed to start background updates: {e}")

    yield

    # Shutdown
    try:
        import sys as _sys

        _pkg = _sys.modules.get("app")
        _stop = (
            getattr(_pkg, "stop_background_updates", None)
            if _pkg and hasattr(_pkg, "stop_background_updates")
            else stop_background_updates
        )
        if callable(_stop):
            await _stop()
        logger.info("Stopped background database updates")
    except Exception as e:
        logger.error(f"Error stopping background updates: {e}")


app = FastAPI(title="PulsePlate", lifespan=lifespan)

# Include API routers
app.include_router(foods_router)
app.include_router(recipes_router)

# Include VIP router (conditional)
if VIP_MODULE_ENABLED:
    app.include_router(vip_router)

start_time = time.time()

# Legacy event handlers - replaced with lifespan
# @app.on_event("startup")
# @app.on_event("shutdown")


# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time_req = time.time()
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Request: {request.method} {request.url} from {client_host}")
    response = await call_next(request)
    process_time = time.time() - start_time_req
    logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
    return response


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: str = Depends(api_key_header)):
    expected = os.getenv("API_KEY")
    # For testing, use a default key if none is set
    if expected is None:
        expected = "test_key"

    # Validate the provided key
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


# ---------- Helpers ----------


def legacy_category_label(cat: str, lang: str) -> str:
    """Map core category labels to legacy wording for the v0 endpoints only.

    - EN: "Normal weight" → "Healthy weight"
    - RU: "Избыточная масса" → "Избыточный вес"
    """
    try:
        lang_code = (lang or "ru").lower()
    except Exception:
        lang_code = "ru"
    if lang_code.startswith("en") and cat == "Normal weight":
        return "Healthy weight"
    if lang_code.startswith("ru") and cat == "Избыточная масса":
        return "Избыточный вес"
    return cat


# Rate limiting setup (only if slowapi is available)
def _is_rate_limiting_available():
    return (
        slowapi_available
        and Limiter is not None
        and RateLimitExceeded is not None
        and _rate_limit_exceeded_handler is not None
    )


if _is_rate_limiting_available():
    limiter = Limiter(key_func=get_remote_address)  # type: ignore
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded, _rate_limit_exceeded_handler
    )  # type: ignore
    app.add_middleware(SlowAPIMiddleware)  # type: ignore
else:
    limiter = None


# ---------- Models ----------


class InsightRequest(BaseModel):
    text: str = Field(..., min_length=1)


class BMIRequest(BaseModel):
    weight_kg: StrictFloat = Field(..., gt=0)
    height_m: float = Field(..., gt=0)
    age: int = Field(..., ge=0, le=120)
    gender: str
    pregnant: str
    athlete: str
    waist_cm: Optional[float] = Field(None, gt=0)
    lang: Language = "ru"
    premium: Optional[bool] = False
    include_chart: Optional[bool] = False  # New parameter for visualization


class BMIRequestV1(BaseModel):
    weight_kg: StrictFloat = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    group: str = "general"
    age: int = Field(default=30, ge=0, le=120)
    gender: str = "male"
    pregnant: str = "no"
    athlete: str = "no"
    waist_cm: Optional[float] = Field(None, gt=0)
    lang: Language = "en"

    @model_validator(mode="after")
    def validate_realistic_values(self):
        """Validate that weight and height are realistic."""
        # Check for unrealistic weight (too low for height)
        height_m = self.height_cm / 100.0
        bmi = self.weight_kg / (height_m**2)

        if bmi < 10:  # Unrealistically low BMI
            raise ValueError("Weight is unrealistically low for the given height")
        if bmi > 100:  # Unrealistically high BMI
            raise ValueError("Weight is unrealistically high for the given height")

        return self

    @model_validator(mode="before")
    @classmethod
    def _normalize_values(cls, values: Dict):
        for k in ["gender", "pregnant", "athlete", "lang"]:
            if k in values and isinstance(values[k], str):
                values[k] = values[k].strip().lower()
        return values


# BMR Request and Response models
class BMRRequest(BaseModel):
    """Request model for BMR calculation"""

    weight_kg: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    age: int = Field(..., ge=0, le=120)
    sex: str = Field(..., pattern="^(male|female)$")
    activity: str = Field(
        ..., pattern="^(sedentary|light|moderate|active|very_active)$"
    )
    bodyfat: Optional[float] = Field(None, ge=0, le=60)
    lang: Language = "en"


class BMRResponse(BaseModel):
    """Response model for BMR calculation"""

    bmr: Dict[str, float]
    tdee: Dict[str, float]
    activity_level: str
    recommended_intake: Dict[str, float]
    formulas_used: List[str]
    notes: List[str]


# ---------- Core logic ----------


def calc_bmi(weight_kg: StrictFloat, height_m: float) -> float:
    return round(weight_kg / (height_m**2), 1)


def normalize_flags(gender: str, pregnant: str, athlete: str) -> Dict[str, bool]:
    gender_norm = {
        "male": "male",
        "муж": "male",
        "м": "male",
        "female": "female",
        "жен": "female",
        "ж": "female",
    }.get(gender, gender)

    preg_true = pregnant in {"да", "беременна", "pregnant", "yes", "y"}
    preg_false = pregnant in {"нет", "no", "not", "n"}
    is_pregnant = preg_true and gender_norm == "female" and not preg_false

    is_athlete = athlete in {"спортсмен", "да", "yes", "y", "athlete"}

    return {
        "gender_male": gender_norm == "male",
        "is_pregnant": is_pregnant,
        "is_athlete": is_athlete,
    }


def waist_risk(waist_cm: Optional[float], gender_male: bool, lang: Language) -> str:
    if waist_cm is None:
        return ""
    warn, high = (94, 102) if gender_male else (80, 88)
    if waist_cm >= high:
        return "Высокий риск по талии" if lang == "ru" else "High waist-related risk"
    if waist_cm >= warn:
        return (
            "Повышенный риск по талии"
            if lang == "ru"
            else "Increased waist-related risk"
        )
    return ""


# ---------- Misc routes ----------


@app.get("/")
async def root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BMI Calculator 2025</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                   padding: 20px; }
            form { margin-bottom: 20px; }
            input, button, select { display: block; margin: 10px 0; padding: 10px; width: 100%; }
            .result { margin-top: 20px; padding: 10px; border: 1px solid #ccc; }
            .language-selector { position: absolute; top: 20px; right: 20px; }
        </style>
    </head>
    <body>
        <div class="language-selector">
            <label for="language">Language:</label>
            <select id="language" onchange="changeLanguage()">
                <option value="en">English</option>
                <option value="ru">Русский</option>
                <option value="es">Español</option>
            </select>
        </div>

        <h1 id="title">BMI Calculator</h1>
        <form id="bmiForm">
            <label for="weight" id="label_weight">Weight (kg):</label>
            <input type="number" id="weight" step="0.1" required>

            <label for="height" id="label_height">Height (m):</label>
            <input type="number" id="height" step="0.01" required>

            <label for="age" id="label_age">Age:</label>
            <input type="number" id="age" required>

            <label for="gender" id="label_gender">Gender:</label>
            <select id="gender" required>
                <option value="male" id="option_male">Male</option>
                <option value="female" id="option_female">Female</option>
            </select>

            <label for="pregnant" id="label_pregnant">Pregnant:</label>
            <select id="pregnant">
                <option value="no" id="option_pregnant_no">No</option>
                <option value="yes" id="option_pregnant_yes">Yes</option>
            </select>

            <label for="athlete" id="label_athlete">Athlete:</label>
            <select id="athlete">
                <option value="no" id="option_athlete_no">No</option>
                <option value="yes" id="option_athlete_yes">Yes</option>
            </select>

            <label for="waist" id="label_waist">Waist (cm, optional):</label>
            <input type="number" id="waist" step="0.1">

            <button type="submit" id="button_calculate">Calculate BMI</button>
        </form>

        <div id="result" class="result" style="display:none;"></div>

        <script>
            // Language translations
            const translations = {
                en: {
                    title: "BMI Calculator",
                    label_weight: "Weight (kg):",
                    label_height: "Height (m):",
                    label_age: "Age:",
                    label_gender: "Gender:",
                    option_male: "Male",
                    option_female: "Female",
                    label_pregnant: "Pregnant:",
                    option_pregnant_no: "No",
                    option_pregnant_yes: "Yes",
                    label_athlete: "Athlete:",
                    option_athlete_no: "No",
                    option_athlete_yes: "Yes",
                    label_waist: "Waist (cm, optional):",
                    button_calculate: "Calculate BMI"
                },
                ru: {
                    title: "Калькулятор ИМТ",
                    label_weight: "Вес (кг):",
                    label_height: "Рост (м):",
                    label_age: "Возраст:",
                    label_gender: "Пол:",
                    option_male: "Мужской",
                    option_female: "Женский",
                    label_pregnant: "Беременность:",
                    option_pregnant_no: "Нет",
                    option_pregnant_yes: "Да",
                    label_athlete: "Спортсмен:",
                    option_athlete_no: "Нет",
                    option_athlete_yes: "Да",
                    label_waist: "Талия (см, опционально):",
                    button_calculate: "Рассчитать ИМТ"
                },
                es: {
                    title: "Calculadora de IMC",
                    label_weight: "Peso (kg):",
                    label_height: "Altura (m):",
                    label_age: "Edad:",
                    label_gender: "Género:",
                    option_male: "Masculino",
                    option_female: "Femenino",
                    label_pregnant: "Embarazada:",
                    option_pregnant_no: "No",
                    option_pregnant_yes: "Sí",
                    label_athlete: "Atleta:",
                    option_athlete_no: "No",
                    option_athlete_yes: "Sí",
                    label_waist: "Cintura (cm, opcional):",
                    button_calculate: "Calcular IMC"
                }
            };

            // Set language from cookie or URL parameter
            function getLanguage() {
                // Check URL parameter first
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.has('lang')) {
                    return urlParams.get('lang');
                }
                // Check cookie
                const cookies = document.cookie.split(';');
                for (let cookie of cookies) {
                    const [name, value] = cookie.trim().split('=');
                    if (name === 'lang') {
                        return value;
                    }
                }
                // Default to English
                return 'en';
            }

            // Update UI based on selected language
            function updateUILanguage(lang) {
                const langCode = translations[lang] ? lang : 'en';
                const t = translations[langCode];

                // Update text elements
                document.getElementById('title').textContent = t.title;
                document.getElementById('label_weight').textContent = t.label_weight;
                document.getElementById('label_height').textContent = t.label_height;
                document.getElementById('label_age').textContent = t.label_age;
                document.getElementById('label_gender').textContent = t.label_gender;
                document.getElementById('option_male').textContent = t.option_male;
                document.getElementById('option_female').textContent = t.option_female;
                document.getElementById('label_pregnant').textContent = t.label_pregnant;
                document.getElementById('option_pregnant_no').textContent = t.option_pregnant_no;
                document.getElementById('option_pregnant_yes').textContent = t.option_pregnant_yes;
                document.getElementById('label_athlete').textContent = t.label_athlete;
                document.getElementById('option_athlete_no').textContent = t.option_athlete_no;
                document.getElementById('option_athlete_yes').textContent = t.option_athlete_yes;
                document.getElementById('label_waist').textContent = t.label_waist;
                document.getElementById('button_calculate').textContent = t.button_calculate;

                // Set language selector
                document.getElementById('language').value = langCode;
            }

            // Set language selector based on current language
            const currentLang = getLanguage();
            updateUILanguage(currentLang);

            // Change language function
            function changeLanguage() {
                const lang = document.getElementById('language').value;
                // Set cookie
                document.cookie = `lang=${lang}; path=/`;
                // Update UI
                updateUILanguage(lang);
            }

            document.getElementById('bmiForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const lang = getLanguage();
                const data = {
                    weight_kg: parseFloat(document.getElementById('weight').value),
                    height_m: parseFloat(document.getElementById('height').value),
                    age: parseInt(document.getElementById('age').value),
                    gender: document.getElementById('gender').value,
                    pregnant: document.getElementById('pregnant').value,
                    athlete: document.getElementById('athlete').value,
                    waist_cm: document.getElementById('waist').value ?
                              parseFloat(document.getElementById('waist').value) : null,
                    lang: 'en'
                };

                try {
                    const response = await fetch('/bmi', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    const result = await response.json();
                    document.getElementById('result').innerHTML = `
                        <h2>BMI: ${result.bmi}</h2>
                        <p>Category: ${result.category}</p>
                        <p>Note: ${result.note}</p>
                    `;
                    document.getElementById('result').style.display = 'block';
                } catch (error) {
                    document.getElementById('result').innerHTML = '<p>Error calculating BMI</p>';
                    document.getElementById('result').style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/health")
async def health_v1():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if generate_latest:
        return Response(generate_latest(), media_type="text/plain")
    return {"error": "Prometheus client not available"}


@app.get("/privacy")
async def privacy():
    """Privacy policy endpoint."""
    return {
        "privacy_policy": (
            "This application processes BMI calculations locally. "
            "No personal data is stored or transmitted to external servers."
        ),
        "data_retention": "No data is retained beyond the current session.",
        "contact": "For privacy concerns, please contact the application administrator.",
    }


# ---------- v0 endpoints (bmi/plan) ----------


@app.post("/bmi")
async def bmi_endpoint(req: BMIRequest):
    flags = normalize_flags(req.gender, req.pregnant, req.athlete)
    bmi = calc_bmi(req.weight_kg, req.height_m)

    if flags["is_pregnant"]:
        note = t(req.lang, "bmi_not_valid_during_pregnancy")
        result = {
            "bmi": bmi,
            "category": None,
            "note": note,
            "athlete": flags["is_athlete"],
            "group": "athlete" if flags["is_athlete"] else "general",
        }

        # Add visualization if requested and available
        if req.include_chart and generate_bmi_visualization:
            viz_result = generate_bmi_visualization(
                bmi=bmi,
                age=req.age,
                gender=req.gender,
                pregnant=req.pregnant,
                athlete=req.athlete,
                lang=req.lang,
            )
            if viz_result.get("available"):
                result["visualization"] = viz_result

        return result

    category = bmi_category(
        bmi, req.lang, req.age, "athlete" if flags["is_athlete"] else "general"
    )
    notes = []
    if flags["is_athlete"]:
        notes.append(t(req.lang, "advice_athlete_bmi"))
    if wr := waist_risk(req.waist_cm, flags["gender_male"], req.lang):
        notes.append(wr)

    result = {
        "bmi": bmi,
        "category": category,
        "note": " | ".join(notes) if notes else "",
        "athlete": flags["is_athlete"],
        "group": "athlete" if flags["is_athlete"] else "general",
    }

    # Add visualization if requested and available
    if req.include_chart and generate_bmi_visualization:
        viz_result = generate_bmi_visualization(
            bmi=bmi,
            age=req.age,
            gender=req.gender,
            pregnant=req.pregnant,
            athlete=req.athlete,
            lang=req.lang,
        )
        if viz_result.get("available"):
            result["visualization"] = viz_result
        elif not MATPLOTLIB_AVAILABLE:
            result["visualization"] = {
                "error": "Visualization not available - matplotlib not installed",
                "available": False,
            }

    return result


@app.post("/plan")
async def plan_endpoint(req: BMIRequest):
    """Generate a personal plan based on BMI and user profile."""
    flags = normalize_flags(req.gender, req.pregnant, req.athlete)
    bmi = calc_bmi(req.weight_kg, req.height_m)
    category = (
        None
        if flags["is_pregnant"]
        else bmi_category(
            bmi, req.lang, req.age, "athlete" if flags["is_athlete"] else "general"
        )
    )

    healthy_bmi = {"min": 18.5, "max": 24.9}

    if req.lang == "ru":
        base = {
            "summary": "Персональный план (MVP)",
            "bmi": bmi,
            "category": category,
            "premium": bool(req.premium),
            "next_steps": [
                "Шаги: 7–10 тыс/день",
                "Белок: 1.2–1.6 г/кг",
                "Сон: 7–9 часов",
            ],
            "healthy_bmi": healthy_bmi,
            "action": "Сделай сегодня 20-мин быструю прогулку",
        }
        if req.premium:
            base["premium_reco"] = [
                "Дефицит 300–500 ккал",
                "2–3 силовые тренировки/нед",
            ]
    else:
        base = {
            "summary": "Personal plan (MVP)",
            "bmi": bmi,
            "category": category,
            "premium": bool(req.premium),
            "next_steps": ["Steps: 7–10k/day", "Protein: 1.2–1.6 g/kg", "Sleep: 7–9 h"],
            "healthy_bmi": healthy_bmi,
            "action": "Take a brisk 20-min walk today",
        }
        if req.premium:
            base["premium_reco"] = [
                "Calorie deficit 300–500 kcal",
                "2–3 strength sessions/week",
            ]

    return base


@app.post("/api/v1/bmi", dependencies=[Depends(get_api_key)])
async def bmi_endpoint_v1(req: BMIRequestV1):
    """V1 BMI endpoint with API key authentication."""
    # Convert height_cm to height_m
    height_m = req.height_cm / 100.0

    flags = normalize_flags(req.gender, req.pregnant, req.athlete)
    bmi = calc_bmi(req.weight_kg, height_m)

    if flags["is_pregnant"]:
        note = t(req.lang, "bmi_not_valid_during_pregnancy")
        return {
            "bmi": bmi,
            "category": None,
            "note": note,
            "athlete": flags["is_athlete"],
            "group": "athlete" if flags["is_athlete"] else "general",
        }

    category = bmi_category(
        bmi, req.lang, req.age, "athlete" if flags["is_athlete"] else "general"
    )
    notes = []
    if flags["is_athlete"]:
        notes.append(t(req.lang, "advice_athlete_bmi"))
    if wr := waist_risk(req.waist_cm, flags["gender_male"], req.lang):
        notes.append(wr)

    return {
        "bmi": bmi,
        "category": category,
        "note": " | ".join(notes) if notes else "",
        "athlete": flags["is_athlete"],
        "group": "athlete" if flags["is_athlete"] else "general",
    }


# ---------- Insight endpoints ----------
class InsightReq(BaseModel):
    text: str = Field(..., min_length=1)


@app.post("/insight")
async def insight(req: InsightReq):
    """Generate insight using LLM provider."""
    if str(os.getenv("FEATURE_INSIGHT", "")).strip().lower() not in {
        "1",
        "true",
        "on",
        "yes",
    }:
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")

    # отложенный импорт, чтобы не падать, если файла нет
    try:
        from llm import get_provider
    except Exception:
        raise HTTPException(status_code=503, detail="LLM module is not available")

    provider = get_provider()
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="No LLM provider configured. Set LLM_PROVIDER=stub|grok",
        )

    try:
        insight_text = await provider.generate(req.text)
        return {"provider": provider.name, "insight": insight_text}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {str(e)}",
        )


@app.post("/api/v1/insight", dependencies=[Depends(get_api_key)])
async def insight_v1(req: InsightReq):
    """Generate insight using LLM provider (v1 with API key)."""
    if str(os.getenv("FEATURE_INSIGHT", "")).strip().lower() not in {
        "1",
        "true",
        "on",
        "yes",
    }:
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")

    # отложенный импорт, чтобы не падать, если файла нет
    try:
        from llm import get_provider
    except Exception:
        raise HTTPException(status_code=503, detail="LLM module is not available")

    provider = get_provider()
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="No LLM provider configured. Set LLM_PROVIDER=stub|grok",
        )

    try:
        insight_text = await provider.generate(req.text)
        return {"provider": provider.name, "insight": insight_text}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM provider error: {str(e)}",
        )


try:
    from core.menu_engine import (
        analyze_nutrient_gaps,
        make_daily_menu,
        make_weekly_menu,
        repair_week_plan,
    )
    from core.plate import make_plate
    from core.recommendations import build_nutrition_targets
except ImportError:
    make_plate = None
    build_nutrition_targets = None
    try:
        # Ensure attribute exists for patching in tests
        from core.menu_engine import analyze_nutrient_gaps as _analyze_ng  # type: ignore

        analyze_nutrient_gaps = _analyze_ng  # type: ignore
    except Exception:
        analyze_nutrient_gaps = None  # type: ignore
    make_daily_menu = None
    make_weekly_menu = None
    repair_week_plan = None

# Ensure analyze_nutrient_gaps is available at module level for tests
if "analyze_nutrient_gaps" not in globals():
    try:
        from core.menu_engine import analyze_nutrient_gaps

        globals()["analyze_nutrient_gaps"] = analyze_nutrient_gaps
    except Exception:
        pass

# Ensure make_weekly_menu is available at module level for tests
if "make_weekly_menu" not in globals():
    try:
        from core.menu_engine import make_weekly_menu

        globals()["make_weekly_menu"] = make_weekly_menu
    except Exception:
        pass

# Ensure repair_week_plan is available at module level for tests
if "repair_week_plan" not in globals():
    try:
        from core.menu_engine import repair_week_plan

        globals()["repair_week_plan"] = repair_week_plan
    except Exception:
        pass

# Enhanced Plate API Models
Sex = Literal["female", "male"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["loss", "maintain", "gain"]
DietFlag = Literal["VEG", "GF", "DAIRY_FREE", "LOW_COST"]


class PlateRequest(BaseModel):
    """RU: Запрос на генерацию «Моей Тарелки».
    EN: Request to generate 'My Plate'.
    """

    sex: Sex
    age: int = Field(..., ge=10, le=100)
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    activity: Activity
    goal: Goal
    # RU: Для цели loss/gain задаём процент; для maintain можно опустить или 0.
    # EN: For loss/gain provide percent; for maintain can omit or use 0.
    deficit_pct: Optional[float] = Field(None, ge=5, le=25)  # for loss
    surplus_pct: Optional[float] = Field(None, ge=5, le=20)  # for gain
    bodyfat: Optional[float] = Field(None, ge=3, le=60)
    diet_flags: Optional[set[DietFlag]] = None


class VisualShape(BaseModel):
    """RU: Примитив для фронтенда (сектор тарелки/чашка/метка).
    EN: Primitive for frontend (plate sector/bowl/dot).
    """

    kind: Literal["plate_sector", "bowl", "marker"]
    # fraction: доля сектора 0..1 для plate_sector, или вместимость чашки в 'cups'
    fraction: float
    label: str
    tooltip: str


class PlateResponse(BaseModel):
    kcal: int
    macros: Dict[
        str, int
    ]  # {"protein_g": int, "fat_g": int, "carbs_g": int, "fiber_g": int}
    portions: Dict[
        str, Any
    ]  # {"protein_palm": float, "carb_cups": float, "veg_cups": float, "fat_thumbs": float}
    layout: List[VisualShape]  # спецификация визуалки
    meals: List[Dict[str, Any]]  # список блюд с калориями/макро
    day_micros: Dict[str, float] = {}  # агрегированные микронутриенты за день


# WHO-Based Nutrition Models
class WHOTargetsRequest(BaseModel):
    """RU: Запрос на расчёт целей по нормам ВОЗ.
    EN: Request for WHO-based nutrition targets.
    """

    sex: Sex
    age: int = Field(..., ge=1, le=120)
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    activity: Activity
    goal: Goal = "maintain"
    deficit_pct: Optional[float] = Field(None, ge=5, le=25)
    surplus_pct: Optional[float] = Field(None, ge=5, le=20)
    bodyfat: Optional[float] = Field(None, ge=3, le=60)
    diet_flags: Optional[set[DietFlag]] = None
    life_stage: Literal[
        "child", "teen", "adult", "pregnant", "lactating", "elderly"
    ] = "adult"
    lang: str = "en"  # Language for localized warnings


class WHOTargetsResponse(BaseModel):
    """RU: Ответ с целевыми значениями по ВОЗ.
    EN: Response with WHO-based targets.
    """

    kcal_daily: int
    macros: Dict[str, int]
    water_ml: int
    priority_micros: Dict[str, float]  # Key micronutrients
    activity_weekly: Dict[str, int]  # Weekly activity targets
    calculation_date: str
    warnings: List[Dict[str, str]] = []  # Life stage warnings with codes and messages


class NutrientGapsRequest(BaseModel):
    """RU: Запрос на анализ дефицитов нутриентов.
    EN: Request for nutrient gap analysis.
    """

    consumed_nutrients: Dict[str, float]  # Actual daily intake
    user_profile: WHOTargetsRequest  # User profile for targets


class NutrientGapsResponse(BaseModel):
    """RU: Ответ с анализом дефицитов и рекомендациями.
    EN: Response with gap analysis and recommendations.
    """

    gaps: Dict[str, Dict[str, Any]]  # Detailed gap analysis
    food_recommendations: List[str]  # Food-based solutions
    adherence_score: float  # Overall adequacy score


class WeeklyMenuResponse(BaseModel):
    """RU: Ответ с недельным меню.
    EN: Response with weekly menu.
    """

    week_summary: Dict[str, Any]
    daily_menus: List[Dict[str, Any]]
    weekly_coverage: Dict[str, float]  # Average nutrient coverage
    shopping_list: Dict[str, float]  # Weekly shopping needs
    total_cost: float
    adherence_score: float


class WeeklyPlanFlexibleRequest(BaseModel):
    # Either 'targets' or a lightweight user profile
    targets: Optional[Dict[str, Any]] = None
    sex: Optional[Sex] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity: Optional[Activity] = "moderate"
    goal: Optional[Goal] = "maintain"
    deficit_pct: Optional[float] = None
    surplus_pct: Optional[float] = None
    bodyfat: Optional[float] = None
    diet_flags: Optional[set[DietFlag]] = None
    life_stage: Optional[
        Literal["child", "teen", "adult", "pregnant", "lactating", "elderly"]
    ] = "adult"
    lang: Optional[str] = "en"


@app.post(
    "/api/v1/premium/plate",
    dependencies=[Depends(get_api_key)],
    response_model=PlateResponse,
)
async def api_premium_plate(req: PlateRequest) -> PlateResponse:
    """
    RU: Генерирует «Мою Тарелку» под цель/дефицит/активность.
    EN: Generates 'My Plate' for goal/deficit/activity.

    Enhanced Plate API with visual sectors and hand/cup portions:
    - Visual plate layout with 4 sectors + 2 bowls
    - Precise deficit/surplus percentage control
    - Hand/cup portion method for real-world application
    - Diet flags support (VEG, GF, DAIRY_FREE, LOW_COST)
    - Macro-balanced meal suggestions
    """
    try:
        import sys as _sys

        _module = _sys.modules[__name__]
        _make_plate = getattr(_module, "make_plate", None)
        if _make_plate is None:
            raise HTTPException(
                status_code=503, detail="Enhanced plate feature not available"
            )

        _calc_all_bmr = getattr(_module, "calculate_all_bmr", None)
        _calc_all_tdee = getattr(_module, "calculate_all_tdee", None)
        if _calc_all_bmr is None or _calc_all_tdee is None:
            raise HTTPException(
                status_code=503, detail="BMR/TDEE calculation not available"
            )

        # 1) Calculate BMR/TDEE (using Mifflin-St Jeor as default, can add formula choice later)
        bmr_results = _calc_all_bmr(
            req.weight_kg, req.height_cm, req.age, req.sex, req.bodyfat
        )
        tdee_results = _calc_all_tdee(bmr_results, req.activity)
        tdee_val = tdee_results["mifflin"]  # Use Mifflin-St Jeor as primary

        # 2) Generate plate with enhanced logic
        diet_flags_str = (
            {str(flag) for flag in req.diet_flags} if req.diet_flags else None
        )
        plate_data = _make_plate(
            weight_kg=req.weight_kg,
            tdee_val=tdee_val,
            goal=req.goal,
            deficit_pct=req.deficit_pct,
            surplus_pct=req.surplus_pct,
            diet_flags=diet_flags_str,
        )

        # 3) Convert layout to VisualShape objects
        layout = [VisualShape(**item) for item in plate_data["layout"]]

        # 4) Aggregate daily micronutrients from meals
        day_micros = {}

        # Mock micronutrient data for demonstration (in real implementation,
        # this would come from the meal generation logic)
        mock_micros_per_meal = {
            "iron_mg": 2.5,
            "calcium_mg": 150.0,
            "magnesium_mg": 45.0,
            "potassium_mg": 300.0,
            "vitamin_c_mg": 25.0,
            "folate_ug": 50.0,
            "vitamin_d_iu": 100.0,
            "b12_ug": 1.2,
        }

        # Add micronutrients to each meal and aggregate
        for meal in plate_data["meals"]:
            # Add mock micronutrients to meal data
            meal["micros"] = mock_micros_per_meal.copy()

            # Aggregate daily totals
            for nutrient, amount in mock_micros_per_meal.items():
                day_micros[nutrient] = day_micros.get(nutrient, 0) + amount

        return PlateResponse(
            kcal=plate_data["kcal"],
            macros=plate_data["macros"],
            portions=plate_data["portions"],
            layout=layout,
            meals=plate_data["meals"],
            day_micros=day_micros if day_micros else {},
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        logger.error(f"premium_plate error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Enhanced plate generation failed: {str(e)}"
        ) from e


# Premium BMR Endpoint
@app.post(
    "/api/v1/premium/bmr",
    dependencies=[Depends(get_api_key)],
    response_model=BMRResponse,
)
async def api_premium_bmr(req: BMRRequest) -> BMRResponse:
    """
    RU: Рассчитывает BMR и TDEE с использованием нескольких формул.
    EN: Calculates BMR and TDEE using multiple formulas.

    Supports:
    - Mifflin-St Jeor equation (primary)
    - Harris-Benedict equation (secondary)
    - Katch-McArdle equation (if body fat provided)
    - Multiple activity levels
    - Localized responses
    """
    try:
        # Check if nutrition module is available
        _calc_all_bmr = getattr(
            globals().get("__module__", None), "calculate_all_bmr", None
        )
        _calc_all_tdee = getattr(
            globals().get("__module__", None), "calculate_all_tdee", None
        )

        if _calc_all_bmr is None or _calc_all_tdee is None:
            # Try to import from nutrition_core
            try:
                from nutrition_core import calculate_all_bmr, calculate_all_tdee

                _calc_all_bmr = calculate_all_bmr
                _calc_all_tdee = calculate_all_tdee
            except ImportError:
                raise HTTPException(
                    status_code=503, detail="BMR calculation module not available"
                )

        # Calculate BMR using multiple formulas
        bmr_results = _calc_all_bmr(
            req.weight_kg, req.height_cm, req.age, req.sex, req.bodyfat
        )

        # Calculate TDEE
        tdee_results = _calc_all_tdee(bmr_results, req.activity)

        # Prepare response
        formulas_used = list(bmr_results.keys())
        notes = []

        # Add activity level description
        activity_descriptions = {
            "sedentary": t(req.lang, "activity_sedentary"),
            "light": t(req.lang, "activity_light"),
            "moderate": t(req.lang, "activity_moderate"),
            "active": t(req.lang, "activity_active"),
            "very_active": t(req.lang, "activity_very_active"),
        }
        activity_level = activity_descriptions.get(req.activity, req.activity)

        # Add notes based on formulas used
        if "katch" in bmr_results and req.bodyfat:
            notes.append(t(req.lang, "bmr_katch_note"))

        # Calculate recommended intake (using Mifflin as primary)
        # primary_bmr = bmr_results.get("mifflin", list(bmr_results.values())[0])
        # Not used currently
        primary_tdee = tdee_results.get("mifflin", list(tdee_results.values())[0])

        recommended_intake = {
            "maintenance": primary_tdee,
            "weight_loss": primary_tdee * 0.8,  # 20% deficit
            "weight_gain": primary_tdee * 1.2,  # 20% surplus
        }

        return BMRResponse(
            bmr=bmr_results,
            tdee=tdee_results,
            activity_level=activity_level,
            recommended_intake=recommended_intake,
            formulas_used=formulas_used,
            notes=notes,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        logger.error(f"premium_bmr error: {e}")
        raise HTTPException(
            status_code=500, detail=f"BMR calculation failed: {str(e)}"
        ) from e


# WHO-Based Nutrition Endpoints


@app.post(
    "/api/v1/premium/targets",
    dependencies=[Depends(get_api_key)],
    response_model=WHOTargetsResponse,
)
async def api_who_targets(req: WHOTargetsRequest) -> WHOTargetsResponse:
    # sourcery skip: use-contextlib-suppress
    """
    RU: Рассчитывает индивидуальные цели по нормам ВОЗ.
    EN: Calculates individual nutrition targets based on WHO guidelines.

    Evidence-based targets for:
    - Daily calorie needs (BMR/TDEE + goal adjustments)
    - Macronutrient distribution (WHO/IOM acceptable ranges)
    - Priority micronutrients (WHO/EFSA RDA values)
    - Hydration requirements (body weight + activity)
    - Physical activity goals (WHO recommendations)

    All targets are personalized based on age, sex, activity level,
    and special conditions (pregnancy, lactation).
    """
    try:
        import sys as _sys

        _module = _sys.modules[__name__]
        _build_targets = getattr(_module, "build_nutrition_targets", None)
        if _build_targets is None:
            raise HTTPException(
                status_code=503, detail="WHO nutrition targets feature not available"
            )

        # Convert request to UserProfile
        from core.targets import UserProfile, _life_stage_warnings

        profile = UserProfile(
            sex=req.sex,
            age=req.age,
            height_cm=req.height_cm,
            weight_kg=req.weight_kg,
            activity=req.activity,
            goal=req.goal,
            deficit_pct=req.deficit_pct,
            surplus_pct=req.surplus_pct,
            bodyfat=req.bodyfat,
            diet_flags=set(req.diet_flags or []),
            life_stage=req.life_stage,
        )

        # Calculate WHO-based targets
        targets = _build_targets(profile)

        # Generate life stage warnings
        life_stage_warnings = _life_stage_warnings(
            age=req.age, life_stage=req.life_stage, lang=req.lang
        )

        # Validate safety (if function exists)
        try:
            from core.recommendations import validate_targets_safety

            safety_warnings = validate_targets_safety(targets)
            # Convert safety warnings to the new format if needed
            if isinstance(safety_warnings, list) and safety_warnings:
                for warning in safety_warnings:
                    if isinstance(warning, str):
                        life_stage_warnings.append(
                            {"code": "safety", "message": warning}
                        )
        except ImportError:
            # If validate_targets_safety doesn't exist, just use life stage warnings
            pass

        return WHOTargetsResponse(
            kcal_daily=targets.kcal_daily,
            macros={
                "protein_g": targets.macros.protein_g,
                "fat_g": targets.macros.fat_g,
                "carbs_g": targets.macros.carbs_g,
                "fiber_g": targets.macros.fiber_g,
            },
            water_ml=targets.water_ml_daily,
            priority_micros=targets.micros.get_priority_nutrients(),
            activity_weekly={
                "moderate_aerobic_min": targets.activity.moderate_aerobic_min,
                "strength_sessions": targets.activity.strength_sessions,
                "steps_daily": targets.activity.steps_daily,
            },
            calculation_date=targets.calculation_date,
            warnings=life_stage_warnings,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"WHO targets calculation failed: {str(e)}"
        ) from e


@app.post(
    "/api/v1/premium/plan/week",
    dependencies=[Depends(get_api_key)],
    response_model=WeeklyMenuResponse,
)
async def api_weekly_menu(req: WHOTargetsRequest) -> WeeklyMenuResponse:
    """
    RU: Генерирует недельный план питания (через core.menu_engine.make_weekly_menu).
    EN: Generate a weekly meal plan using core.menu_engine.make_weekly_menu.

    Returns keys: week_summary, daily_menus, weekly_coverage, shopping_list.
    """
    try:
        import sys as _sys

        _module = _sys.modules[__name__]
        _make_weekly_menu = getattr(_module, "make_weekly_menu", None)
        if _make_weekly_menu is None:
            raise HTTPException(
                status_code=503, detail="Weekly menu generation feature not available"
            )

        # Convert to UserProfile
        from core.targets import UserProfile

        profile = UserProfile(
            sex=req.sex,
            age=req.age,
            height_cm=req.height_cm,
            weight_kg=req.weight_kg,
            activity=req.activity,
            goal=req.goal,
            deficit_pct=req.deficit_pct,
            surplus_pct=req.surplus_pct,
            bodyfat=req.bodyfat,
            diet_flags=set(req.diet_flags or []),
            life_stage=req.life_stage,
        )

        # Generate weekly menu via core.menu_engine
        week_menu = _make_weekly_menu(profile)

        return WeeklyMenuResponse(
            week_summary={
                "week_start": week_menu.week_start,
                "total_days": len(week_menu.daily_menus),
                "avg_daily_cost": round(week_menu.total_cost / 7, 2),
            },
            daily_menus=[
                {
                    "date": menu.date,
                    "meals": menu.meals,
                    "total_kcal": sum(meal.get("kcal", 0) for meal in menu.meals),
                    "daily_cost": menu.estimated_cost,
                }
                for menu in week_menu.daily_menus
            ],
            weekly_coverage=week_menu.weekly_coverage,
            shopping_list=week_menu.shopping_list,
            total_cost=week_menu.total_cost,
            adherence_score=week_menu.adherence_score,
        )

    except HTTPException:
        # Pass through expected HTTP errors
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Weekly menu generation failed: {str(e)}"
        ) from e


@app.post(
    "/api/v1/premium/gaps",
    dependencies=[Depends(get_api_key)],
    response_model=NutrientGapsResponse,
)
async def api_nutrient_gaps(req: NutrientGapsRequest) -> NutrientGapsResponse:
    """
    RU: Анализирует дефициты нутриентов и даёт рекомендации.
    EN: Analyzes nutrient deficiencies and provides food recommendations.

    Smart gap analysis:
    - Compares actual intake vs WHO targets
    - Identifies priority deficiencies (iron, calcium, folate, etc.)
    - Suggests specific foods to close gaps
    - Adapts recommendations for dietary restrictions
    - No supplement recommendations (food-first approach)

    Perfect for food diary analysis and meal optimization.
    """
    try:
        import sys as _sys

        _module = _sys.modules[__name__]
        _analyze_gaps = getattr(_module, "analyze_nutrient_gaps", None)
        if _analyze_gaps is None:
            raise HTTPException(
                status_code=503, detail="Nutrient gap analysis feature not available"
            )

        # Build targets from profile
        from core.targets import UserProfile

        profile = UserProfile(
            sex=req.user_profile.sex,
            age=req.user_profile.age,
            height_cm=req.user_profile.height_cm,
            weight_kg=req.user_profile.weight_kg,
            activity=req.user_profile.activity,
            goal=req.user_profile.goal,
            deficit_pct=req.user_profile.deficit_pct,
            surplus_pct=req.user_profile.surplus_pct,
            bodyfat=req.user_profile.bodyfat,
            diet_flags=set(req.user_profile.diet_flags or []),
            life_stage=req.user_profile.life_stage,
        )

        _build_targets = getattr(_module, "build_nutrition_targets", None)
        if _build_targets is None:
            raise HTTPException(
                status_code=503,
                detail="Nutrition targets calculation feature not available",
            )

        targets = _build_targets(profile)

        # Analyze gaps
        gaps = _analyze_gaps(targets, req.consumed_nutrients)

        # Generate food recommendations
        from core.recommendations import (
            generate_deficiency_recommendations,
            score_nutrient_coverage,
        )

        coverage = score_nutrient_coverage(req.consumed_nutrients, targets)
        food_recommendations = generate_deficiency_recommendations(coverage, profile)

        # Calculate adherence score
        total_nutrients = len(coverage)
        # sourcery skip: simplify-constant-sum
        adequate_nutrients = sum(
            1 for cov in coverage.values() if cov.coverage_percent >= 80
        )
        adherence_score = (
            (adequate_nutrients / total_nutrients * 100) if total_nutrients > 0 else 0
        )

        return NutrientGapsResponse(
            gaps=gaps,
            food_recommendations=food_recommendations,
            adherence_score=round(adherence_score, 1),
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Nutrient gap analysis failed: {str(e)}"
        ) from e


@app.get("/debug_env")
async def debug_env():
    data = {
        "FEATURE_INSIGHT": os.getenv("FEATURE_INSIGHT", ""),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER", ""),
        "GROK_MODEL": os.getenv("GROK_MODEL", ""),
        "GROK_ENDPOINT": os.getenv("GROK_ENDPOINT", ""),
    }
    flag = str(os.getenv("FEATURE_INSIGHT", "")).strip().lower()
    data["insight_enabled"] = str(flag in {"1", "true", "yes", "on"})
    return JSONResponse(content=data)


# ========================================
# Database Auto-Update Management Endpoints
# ========================================


@app.get("/api/v1/admin/db-status", dependencies=[Depends(get_api_key)])
async def get_database_status():
    """
    RU: Получить статус всех баз данных и планировщика обновлений.
    EN: Get status of all databases and update scheduler.

    Returns information about:
    - Database versions and last update times
    - Update scheduler status
    - Retry counts and error states
    - Data integrity checksums
    """
    try:
        # Resolve getter dynamically to respect runtime patches in tests
        import sys as _sys

        _getter = getattr(_sys.modules[__name__], "get_update_scheduler")
        logger.debug(f"get_database_status using getter: {_getter!r}")
        scheduler = await _getter()
        status = scheduler.get_status()
        return JSONResponse(content=status)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get database status: {str(e)}"
        ) from e


@app.post("/api/v1/admin/force-update", dependencies=[Depends(get_api_key)])
async def force_database_update(source: Optional[str] = None):
    """
    RU: Принудительно запустить обновление баз данных.
    EN: Force immediate database update.

    Args:
        source: Optional specific source to update ("usda", "openfoodfacts")
                If None, updates all sources

    Returns:
        Update results with statistics on records changed
    """
    try:
        import sys as _sys

        _getter = getattr(_sys.modules[__name__], "get_update_scheduler")
        logger.debug(f"force_database_update using getter: {_getter!r}")
        scheduler = await _getter()
        results = await scheduler.force_update(source)

        # Format response
        response = {
            "message": f"Force update completed for {source or 'all sources'}",
            "results": {},
        }

        for src, result in results.items():
            response["results"][src] = {
                "success": result.success,
                "old_version": result.old_version,
                "new_version": result.new_version,
                "records_added": result.records_added,
                "records_updated": result.records_updated,
                "records_removed": result.records_removed,
                "duration_seconds": result.duration_seconds,
                "errors": result.errors,
            }

        return JSONResponse(content=response)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Force update failed: {str(e)}"
        ) from e


@app.post("/api/v1/admin/check-updates", dependencies=[Depends(get_api_key)])
async def check_for_updates():
    """
    RU: Проверить наличие доступных обновлений без их установки.
    EN: Check for available updates without installing them.

    Returns:
        Dictionary showing which sources have updates available
    """
    try:
        import sys as _sys

        _getter = getattr(_sys.modules[__name__], "get_update_scheduler")
        logger.debug(f"check_for_updates using getter: {_getter!r}")
        scheduler = await _getter()
        available_updates = await scheduler.update_manager.check_for_updates()

        response = {
            "message": "Update check completed",
            "updates_available": available_updates,
            "total_sources_with_updates": sum(available_updates.values()),
        }

        return JSONResponse(content=response)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Update check failed: {str(e)}"
        ) from e


@app.post("/api/v1/admin/rollback", dependencies=[Depends(get_api_key)])
async def rollback_database(source: str, target_version: str):
    """
    RU: Откатить базу данных к предыдущей версии.
    EN: Rollback database to a previous version.

    Args:
        source: Data source name ("usda", "openfoodfacts")
        target_version: Version to rollback to

    Returns:
        Success status and rollback details
    """
    try:
        import sys as _sys

        _getter = getattr(_sys.modules[__name__], "get_update_scheduler")
        logger.debug(f"rollback_database using getter: {_getter!r}")
        scheduler = await _getter()
        success = await scheduler.update_manager.rollback_database(
            source, target_version
        )

        if success:
            return JSONResponse(
                content={
                    "message": f"Successfully rolled back {source} to version {target_version}",
                    "success": True,
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Rollback failed for {source} to version {target_version}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Rollback operation failed: {str(e)}"
        ) from e


# Export Endpoints


@app.get(
    "/api/v1/premium/exports/day/{plan_id}.csv", dependencies=[Depends(get_api_key)]
)
async def export_daily_plan_csv(plan_id: str):
    """
    RU: Экспортировать дневной план в CSV.
    EN: Export daily meal plan to CSV.

    Args:
        plan_id: ID of the daily plan to export

    Returns:
        CSV file download
    """
    try:
        # In a real implementation, this would fetch the plan from a database
        # For now, we'll return a placeholder response
        from fastapi.responses import Response

        # Mock data - in real implementation, fetch from database
        mock_plan = {
            "meals": [
                {
                    "name": "Breakfast",
                    "food_item": "Oatmeal",
                    "kcal": 300,
                    "protein_g": 10,
                    "carbs_g": 50,
                    "fat_g": 5,
                },
                {
                    "name": "Lunch",
                    "food_item": "Chicken Salad",
                    "kcal": 450,
                    "protein_g": 35,
                    "carbs_g": 20,
                    "fat_g": 25,
                },
                {
                    "name": "Dinner",
                    "food_item": "Grilled Fish",
                    "kcal": 400,
                    "protein_g": 40,
                    "carbs_g": 15,
                    "fat_g": 20,
                },
            ],
            "total_kcal": 1150,
            "total_protein": 85,
            "total_carbs": 85,
            "total_fat": 50,
        }

        import sys as _sys

        _pkg = _sys.modules.get("app")
        _to_csv_day = (
            getattr(_pkg, "to_csv_day", None)
            if _pkg and hasattr(_pkg, "to_csv_day")
            else to_csv_day
        )
        csv_data = _to_csv_day(mock_plan)

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=daily_plan_{plan_id}.csv"
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"CSV export failed: {str(e)}"
        ) from e


@app.get(
    "/api/v1/premium/exports/week/{plan_id}.csv", dependencies=[Depends(get_api_key)]
)
async def export_weekly_plan_csv(plan_id: str):
    """
    RU: Экспортировать недельный план в CSV.
    EN: Export weekly meal plan to CSV.

    Args:
        plan_id: ID of the weekly plan to export

    Returns:
        CSV file download
    """
    try:
        from fastapi.responses import Response

        # Mock data - in real implementation, fetch from database
        mock_weekly_plan = {
            "daily_menus": [
                {
                    "date": "2023-01-01",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "food_item": "Oatmeal",
                            "kcal": 300,
                            "protein_g": 10,
                            "carbs_g": 50,
                            "fat_g": 5,
                            "cost": 1.5,
                        },
                        {
                            "name": "Lunch",
                            "food_item": "Chicken Salad",
                            "kcal": 450,
                            "protein_g": 35,
                            "carbs_g": 20,
                            "fat_g": 25,
                            "cost": 3.2,
                        },
                    ],
                },
                {
                    "date": "2023-01-02",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "food_item": "Scrambled Eggs",
                            "kcal": 250,
                            "protein_g": 18,
                            "carbs_g": 1,
                            "fat_g": 20,
                            "cost": 1.2,
                        },
                        {
                            "name": "Lunch",
                            "food_item": "Beef Stir Fry",
                            "kcal": 500,
                            "protein_g": 30,
                            "carbs_g": 40,
                            "fat_g": 20,
                            "cost": 4.5,
                        },
                    ],
                },
            ],
            "shopping_list": {
                "oats": 500,
                "chicken_breast": 300,
                "eggs": 12,
                "beef": 400,
            },
            "total_cost": 150.0,
            "adherence_score": 92.5,
        }

        import sys as _sys

        _pkg = _sys.modules.get("app")
        _to_csv_week = (
            getattr(_pkg, "to_csv_week", None)
            if _pkg and hasattr(_pkg, "to_csv_week")
            else to_csv_week
        )
        csv_data = _to_csv_week(mock_weekly_plan)

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=weekly_plan_{plan_id}.csv"
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"CSV export failed: {str(e)}"
        ) from e


@app.get(
    "/api/v1/premium/exports/day/{plan_id}.pdf", dependencies=[Depends(get_api_key)]
)
async def export_daily_plan_pdf(plan_id: str):
    # sourcery skip: raise-from-previous-error
    """
    RU: Экспортировать дневной план в PDF.
    EN: Export daily meal plan to PDF.

    Args:
        plan_id: ID of the daily plan to export

    Returns:
        PDF file download
    """
    try:
        from fastapi.responses import Response

        # Mock data - in real implementation, fetch from database
        mock_plan = {
            "meals": [
                {
                    "name": "Breakfast",
                    "food_item": "Oatmeal",
                    "kcal": 300,
                    "protein_g": 10,
                    "carbs_g": 50,
                    "fat_g": 5,
                },
                {
                    "name": "Lunch",
                    "food_item": "Chicken Salad",
                    "kcal": 450,
                    "protein_g": 35,
                    "carbs_g": 20,
                    "fat_g": 25,
                },
                {
                    "name": "Dinner",
                    "food_item": "Grilled Fish",
                    "kcal": 400,
                    "protein_g": 40,
                    "carbs_g": 15,
                    "fat_g": 20,
                },
            ],
            "total_kcal": 1150,
            "total_protein": 85,
            "total_carbs": 85,
            "total_fat": 50,
        }

        import sys as _sys

        _pkg = _sys.modules.get("app")
        _to_pdf_day = (
            getattr(_pkg, "to_pdf_day", None)
            if _pkg and hasattr(_pkg, "to_pdf_day")
            else to_pdf_day
        )
        pdf_data = _to_pdf_day(mock_plan)

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=daily_plan_{plan_id}.pdf"
            },
        )

    except ImportError:
        raise HTTPException(
            status_code=503, detail="PDF export not available - ReportLab not installed"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"PDF export failed: {str(e)}"
        ) from e


@app.get(
    "/api/v1/premium/exports/week/{plan_id}.pdf", dependencies=[Depends(get_api_key)]
)
async def export_weekly_plan_pdf(plan_id: str):
    # sourcery skip: raise-from-previous-error
    """
    RU: Экспортировать недельный план в PDF.
    EN: Export weekly meal plan to PDF.

    Args:
        plan_id: ID of the weekly plan to export

    Returns:
        PDF file download
    """
    try:
        from fastapi.responses import Response

        # Mock data - in real implementation, fetch from database
        mock_weekly_plan = {
            "daily_menus": [
                {
                    "date": "2023-01-01",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "food_item": "Oatmeal",
                            "kcal": 300,
                            "protein_g": 10,
                            "carbs_g": 50,
                            "fat_g": 5,
                            "cost": 1.5,
                        },
                        {
                            "name": "Lunch",
                            "food_item": "Chicken Salad",
                            "kcal": 450,
                            "protein_g": 35,
                            "carbs_g": 20,
                            "fat_g": 25,
                            "cost": 3.2,
                        },
                    ],
                },
                {
                    "date": "2023-01-02",
                    "meals": [
                        {
                            "name": "Breakfast",
                            "food_item": "Scrambled Eggs",
                            "kcal": 250,
                            "protein_g": 18,
                            "carbs_g": 1,
                            "fat_g": 20,
                            "cost": 1.2,
                        },
                        {
                            "name": "Lunch",
                            "food_item": "Beef Stir Fry",
                            "kcal": 500,
                            "protein_g": 30,
                            "carbs_g": 40,
                            "fat_g": 20,
                            "cost": 4.5,
                        },
                    ],
                },
            ],
            "shopping_list": {
                "oats": 500,
                "chicken_breast": 300,
                "eggs": 12,
                "beef": 400,
            },
            "total_cost": 150.0,
            "adherence_score": 92.5,
        }

        import sys as _sys

        _pkg = _sys.modules.get("app")
        _to_pdf_week = (
            getattr(_pkg, "to_pdf_week", None)
            if _pkg and hasattr(_pkg, "to_pdf_week")
            else to_pdf_week
        )
        pdf_data = _to_pdf_week(mock_weekly_plan)

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=weekly_plan_{plan_id}.pdf"
            },
        )

    except ImportError:
        raise HTTPException(
            status_code=503, detail="PDF export not available - ReportLab not installed"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"PDF export failed: {str(e)}"
        ) from e


# Include bodyfat router if available
if get_bodyfat_router:
    app.include_router(get_bodyfat_router(), prefix="/api/v1")

# Include BMI Pro router
if bmi_pro_router:
    app.include_router(bmi_pro_router)

# Include Premium Week router
if premium_week_router:
    app.include_router(premium_week_router)
