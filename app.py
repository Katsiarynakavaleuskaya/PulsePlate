import logging
import os
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

try:
    from prometheus_client import Counter, Histogram, generate_latest
except ImportError:
    Counter = None
    Histogram = None
    generate_latest = None

import inspect

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader

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
    if os.getenv("PYTEST_CURRENT_TEST") is None and os.getenv("APP_ENV", "").lower() not in {
        "test",
        "ci",
    }:
        dotenv.load_dotenv()

try:
    from bodyfat import get_router as get_bodyfat_router
except ImportError:
    get_bodyfat_router = None

try:
    from bmi_visualization import MATPLOTLIB_AVAILABLE, generate_bmi_visualization
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

from bmi_core import bmi_category, bmi_value

# Add import for the new BMI Pro functions
from core.bmi_extras import (
    ffmi,
    interpret_whr_ratio,
    interpret_wht_ratio,
    stage_obesity,
    whr_ratio,
    wht_ratio,
)
from core.food_apis.scheduler import start_background_updates, stop_background_updates

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


# Add import for export functions
from core.exports import to_csv_day, to_csv_week, to_pdf_day, to_pdf_week

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await start_background_updates(update_interval_hours=24)
        logger.info("Started background database updates")
    except Exception as e:
        logger.error(f"Failed to start background updates: {e}")

    yield

    # Shutdown
    try:
        await stop_background_updates()
        logger.info("Stopped background database updates")
    except Exception as e:
        logger.error(f"Error stopping background updates: {e}")


app = FastAPI(title="BMI-App 2025", lifespan=lifespan)

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
    if expected and api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


# Rate limiting setup (only if slowapi is available)
if slowapi_available and Limiter is not None:
    limiter = Limiter(key_func=get_remote_address)  # type: ignore
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
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
    lang: Literal["ru", "en"] = "ru"
    premium: Optional[bool] = False
    include_chart: Optional[bool] = False  # New parameter for visualization

    @model_validator(mode="before")
    @classmethod
    def _normalize_values(cls, values: Dict):
        for k in ["gender", "pregnant", "athlete", "lang"]:
            if k in values and isinstance(values[k], str):
                values[k] = values[k].strip().lower()
        return values


# Add the new BMI Pro request model
class BMIProRequest(BaseModel):
    """Request model for BMI Pro analysis"""

    weight_kg: StrictFloat = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    age: int = Field(..., ge=0, le=120)
    gender: str
    pregnant: str
    athlete: str
    waist_cm: float = Field(..., gt=0)
    hip_cm: Optional[float] = Field(None, gt=0)
    bodyfat_pct: Optional[float] = Field(None, ge=0, le=100)
    lang: Literal["ru", "en"] = "en"


# Add the new BMI Pro response model
class BMIProResponse(BaseModel):
    """Response model for BMI Pro analysis"""

    bmi: float
    bmi_category: str
    wht_ratio: float
    wht_risk_category: str
    wht_risk_level: str
    wht_description: str
    whr_ratio: Optional[float] = None
    whr_risk_level: Optional[str] = None
    whr_description: Optional[str] = None
    ffmi: Optional[float] = None
    ffm_kg: Optional[float] = None
    obesity_stage: str
    risk_factors: int
    recommendation: str
    note: str


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


def waist_risk(waist_cm: Optional[float], gender_male: bool, lang: str) -> str:
    if waist_cm is None:
        return ""
    warn, high = (94, 102) if gender_male else (80, 88)
    if waist_cm >= high:
        return "Высокий риск по талии" if lang == "ru" else "High waist-related risk"
    if waist_cm >= warn:
        return "Повышенный риск по талии" if lang == "ru" else "Increased waist-related risk"
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
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            form { margin-bottom: 20px; }
            input, button { display: block; margin: 10px 0; padding: 10px; width: 100%; }
            .result { margin-top: 20px; padding: 10px; border: 1px solid #ccc; }
        </style>
    </head>
    <body>
        <h1>BMI Calculator</h1>
        <form id="bmiForm">
            <label for="weight">Weight (kg):</label>
            <input type="number" id="weight" step="0.1" required>

            <label for="height">Height (m):</label>
            <input type="number" id="height" step="0.01" required>

            <label for="age">Age:</label>
            <input type="number" id="age" required>

            <label for="gender">Gender:</label>
            <select id="gender" required>
                <option value="male">Male</option>
                <option value="female">Female</option>
            </select>

            <label for="pregnant">Pregnant:</label>
            <select id="pregnant">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>

            <label for="athlete">Athlete:</label>
            <select id="athlete">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>

            <label for="waist">Waist (cm, optional):</label>
            <input type="number" id="waist" step="0.1">

            <button type="submit">Calculate BMI</button>
        </form>

        <div id="result" class="result" style="display:none;"></div>

        <script>
            document.getElementById('bmiForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const data = {
                    weight_kg: parseFloat(document.getElementById('weight').value),
                    height_m: parseFloat(document.getElementById('height').value),
                    age: parseInt(document.getElementById('age').value),
                    gender: document.getElementById('gender').value,
                    pregnant: document.getElementById('pregnant').value,
                    athlete: document.getElementById('athlete').value,
                    waist_cm: document.getElementById('waist').value ? parseFloat(document.getElementById('waist').value) : null,
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


# ---------- v0 endpoints (bmi/plan) ----------


@app.post("/bmi")
async def bmi_endpoint(req: BMIRequest):
    flags = normalize_flags(req.gender, req.pregnant, req.athlete)
    bmi = calc_bmi(req.weight_kg, req.height_m)

    if flags["is_pregnant"]:
        note = (
            "BMI не применим при беременности"
            if req.lang == "ru"
            else "BMI is not valid during pregnancy"
        )
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

    category = bmi_category(bmi, req.lang, req.age, "athlete" if flags["is_athlete"] else "general")
    notes = []
    if flags["is_athlete"]:
        notes.append(
            "У спортсменов BMI может завышать жировую массу"
            if req.lang == "ru"
            else "For athletes, BMI may overestimate body fat"
        )
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


@app.post("/api/v1/bmi/visualize")
async def bmi_visualize_endpoint(req: BMIRequest, api_key: str = Depends(get_api_key)):
    """Generate BMI visualization chart."""
    import sys as _sys

    _module = _sys.modules[__name__]
    _viz_func = getattr(_module, "generate_bmi_visualization", None)
    _mpl_available = getattr(_module, "MATPLOTLIB_AVAILABLE", False)

    if not _viz_func:
        raise HTTPException(
            status_code=503, detail="Visualization not available - module not found"
        )

    if not _mpl_available:
        raise HTTPException(
            status_code=503,
            detail="Visualization not available - matplotlib not installed",
        )

    # Calculate BMI
    bmi = calc_bmi(req.weight_kg, req.height_m)

    # Generate visualization
    viz_result = _viz_func(
        bmi=bmi,
        age=req.age,
        gender=req.gender,
        pregnant=req.pregnant,
        athlete=req.athlete,
        lang=req.lang,
    )

    if not viz_result.get("available"):
        raise HTTPException(
            status_code=500,
            detail=viz_result.get("error", "Visualization generation failed"),
        )

    return {
        "bmi": bmi,
        "visualization": viz_result,
        "message": (
            "BMI visualization generated successfully"
            if req.lang == "en"
            else "Визуализация ИМТ создана успешно"
        ),
    }


@app.post("/plan")
async def plan_endpoint(req: BMIRequest):
    flags = normalize_flags(req.gender, req.pregnant, req.athlete)
    bmi = calc_bmi(req.weight_kg, req.height_m)
    category = None if flags["is_pregnant"] else bmi_category(bmi, req.lang)

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
            "next_steps": [
                "Steps: 7–10k/day",
                "Protein: 1.2–1.6 g/kg",
                "Sleep: 7–9 h",
            ],
            "healthy_bmi": healthy_bmi,
            "action": "Take a brisk 20-min walk today",
        }
        if req.premium:
            base["premium_reco"] = [
                "Calorie deficit 300–500 kcal",
                "2–3 strength sessions/week",
            ]

    return base


@app.post("/api/v1/insight", dependencies=[Depends(get_api_key)])
async def api_v1_insight(req: InsightRequest):
    try:
        import llm
    except Exception as e:
        raise HTTPException(status_code=503, detail="LLM module is not available") from e

    provider = llm.get_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="insight provider not configured")

    try:
        result = provider.generate(req.text)
        txt = await result if inspect.isawaitable(result) else result
    except Exception:
        raise HTTPException(status_code=503, detail="insight provider unavailable")
    return {"provider": getattr(provider, "name", "unknown"), "insight": txt}


@app.post("/insight")
async def insight(req: InsightRequest):
    # 0) If explicitly disabled via env, short-circuit
    flag_raw = os.getenv("FEATURE_INSIGHT")
    if flag_raw is not None:
        flag = str(flag_raw).strip().lower()
        if flag in {"0", "false", "no", "off"}:
            raise HTTPException(status_code=503, detail="insight feature disabled")

    # 1) Provider must be configured
    try:
        import llm
    except Exception as e:
        raise HTTPException(status_code=503, detail="LLM module is not available") from e

    provider = llm.get_provider()
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail=("No LLM provider configured. Set LLM_PROVIDER=stub|grok|ollama"),
        )

    # 2) Implicit default: disabled unless explicitly enabled
    flag = str(os.getenv("FEATURE_INSIGHT", "")).strip().lower()
    if flag and flag not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=503, detail="insight feature disabled")

    try:
        result = provider.generate(req.text)
        txt = await result if inspect.isawaitable(result) else result
    except Exception:
        raise HTTPException(status_code=503, detail="insight provider unavailable")

    return {"provider": getattr(provider, "name", "unknown"), "insight": txt}


@app.get("/metrics")
async def metrics():
    return {"uptime_seconds": time.time() - start_time}


@app.get("/privacy")
async def privacy():
    return {
        "policy": (
            "This app processes BMI data for health insights. "
            "Data is not stored or shared. Complies with GDPR."
        ),
        "contact": "For privacy concerns, contact the developer.",
    }


# ---------- Optional routers ----------

if get_bodyfat_router is not None:
    app.include_router(get_bodyfat_router(), prefix="/api/v1")


# ---------- v1 health/bmi ----------


@app.get("/api/v1/health")
async def api_v1_health():
    return {"status": "ok", "version": "v1"}


class BMIRequestV1(BaseModel):
    weight_kg: StrictFloat = Field(..., gt=0, description="Weight in kg")
    height_cm: StrictFloat = Field(..., gt=0, description="Height in cm")
    group: str = "general"


class BMRRequest(BaseModel):
    """Request model for Premium BMR/TDEE calculation"""

    weight_kg: StrictFloat = Field(..., gt=0, description="Weight in kilograms")
    height_cm: StrictFloat = Field(..., gt=0, description="Height in centimeters")
    age: int = Field(..., ge=0, le=120, description="Age in years")
    sex: Literal["male", "female"] = Field(..., description="Biological sex")
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = Field(
        ..., description="Physical activity level"
    )
    bodyfat: Optional[float] = Field(
        None,
        ge=0,
        le=50,
        description="Body fat percentage (optional, for Katch-McArdle formula)",
    )
    lang: Literal["ru", "en"] = Field("en", description="Response language")


class BMIResponse(BaseModel):
    bmi: float
    category: str
    interpretation: str


def _bmi_value(w: float, h_cm: float) -> float:
    h = h_cm / 100.0
    if h <= 0:
        raise ValueError("height must be > 0")
    # Align rounding policy to 1 decimal for v1
    return round(w / (h * h), 1)


def _bmi_category(b: float) -> str:
    if b < 18.5:
        return "Underweight"
    elif b < 25:
        return "Normal"
    elif b < 30:
        return "Overweight"
    else:
        return "Obese"


def _interpretation(b: float, g: str) -> str:
    base = _bmi_category(b)
    g = g.lower().strip()
    if g == "athlete":
        return f"{base} (мышечная масса может искажать BMI)"
    elif g == "pregnant":
        return "BMI не применим при беременности"
    elif g == "elderly":
        return f"{base} (возрастные изменения состава тела)"
    elif g == "teen":
        return "Используйте педиатрические перцентили BMI"
    else:
        return base


@app.post("/api/v1/bmi", response_model=BMIResponse, dependencies=[Depends(get_api_key)])
async def api_v1_bmi(payload: BMIRequestV1) -> BMIResponse:
    try:
        v = bmi_value(payload.weight_kg, payload.height_cm / 100.0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return BMIResponse(
        bmi=v,
        category=bmi_category(v, "en"),
        interpretation="",
    )


@app.post("/api/v1/premium/bmr", dependencies=[Depends(get_api_key)])
async def api_premium_bmr(data: BMRRequest):
    """Premium BMR/TDEE calculation endpoint with multiple formulas.

    Returns BMR calculated using multiple validated formulas:
    - Mifflin-St Jeor (most accurate for general population)
    - Harris-Benedict (traditional formula)
    - Katch-McArdle (optional, requires body fat percentage)

    Also calculates TDEE (Total Daily Energy Expenditure) based on activity level.
    """
    import sys as _sys

    _module = _sys.modules[__name__]
    _calc_all_bmr = getattr(_module, "calculate_all_bmr", None)
    _calc_all_tdee = getattr(_module, "calculate_all_tdee", None)
    if not _calc_all_bmr or not _calc_all_tdee:
        raise HTTPException(status_code=503, detail="Nutrition module not available")

    try:
        # Calculate BMR using all available formulas
        bmr_results = _calc_all_bmr(
            weight=data.weight_kg,
            height=data.height_cm,
            age=data.age,
            sex=data.sex,
            bodyfat_percent=data.bodyfat,
        )

        # Calculate TDEE for all BMR formulas
        tdee_results = _calc_all_tdee(bmr_results, data.activity)

        # Get activity descriptions
        _get_act_desc = getattr(_module, "get_activity_descriptions", None)
        activity_descriptions = _get_act_desc() if _get_act_desc else {}

        # Build response based on language
        if data.lang == "ru":
            response = {
                "bmr": bmr_results,
                "tdee": tdee_results,
                "activity_level": data.activity,
                "activity_description": activity_descriptions.get(data.activity, ""),
                "recommended_intake": {
                    "description": "Рекомендуемое потребление калорий на основе TDEE",
                    "maintenance": tdee_results.get("mifflin", 0),
                    "weight_loss": round(tdee_results.get("mifflin", 0) * 0.8),  # 20% deficit
                    "weight_gain": round(tdee_results.get("mifflin", 0) * 1.1),  # 10% surplus
                },
                "formulas_used": list(bmr_results.keys()),
                "notes": {
                    "mifflin": "Наиболее точная формула для общей популяции",
                    "harris": "Традиционная формула, менее точная",
                    "katch": (
                        "Для спортсменов с известным % жира" if "katch" in bmr_results else None
                    ),
                },
            }
        else:
            response = {
                "bmr": bmr_results,
                "tdee": tdee_results,
                "activity_level": data.activity,
                "activity_description": activity_descriptions.get(data.activity, ""),
                "recommended_intake": {
                    "description": "Recommended calorie intake based on TDEE",
                    "maintenance": tdee_results.get("mifflin", 0),
                    "weight_loss": round(tdee_results.get("mifflin", 0) * 0.8),  # 20% deficit
                    "weight_gain": round(tdee_results.get("mifflin", 0) * 1.1),  # 10% surplus
                },
                "formulas_used": list(bmr_results.keys()),
                "notes": {
                    "mifflin": "Most accurate formula for general population",
                    "harris": "Traditional formula, less accurate",
                    "katch": (
                        "For athletes with known body fat %" if "katch" in bmr_results else None
                    ),
                },
            }

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BMR calculation failed: {str(e)}") from e


try:
    from core.menu_engine import (
        analyze_nutrient_gaps,
        make_daily_menu,
        make_weekly_menu,
    )
    from core.plate import make_plate
    from core.recommendations import build_nutrition_targets
except ImportError:
    make_plate = None
    build_nutrition_targets = None
    make_daily_menu = None
    make_weekly_menu = None
    analyze_nutrient_gaps = None


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
    macros: Dict[str, int]  # {"protein_g": int, "fat_g": int, "carbs_g": int, "fiber_g": int}
    portions: Dict[
        str, Any
    ]  # {"protein_palm": float, "carb_cups": float, "veg_cups": float, "fat_thumbs": float}
    layout: List[VisualShape]  # спецификация визуалки
    meals: List[Dict[str, Any]]  # список блюд с калориями/макро


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
    life_stage: Literal["adult", "pregnant", "lactating"] = "adult"


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
    warnings: List[str] = []  # Safety warnings if any


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
            raise HTTPException(status_code=503, detail="Enhanced plate feature not available")

        _calc_all_bmr = getattr(_module, "calculate_all_bmr", None)
        _calc_all_tdee = getattr(_module, "calculate_all_tdee", None)
        if _calc_all_bmr is None or _calc_all_tdee is None:
            raise HTTPException(status_code=503, detail="BMR/TDEE calculation not available")

        # 1) Calculate BMR/TDEE (using Mifflin-St Jeor as default, can add formula choice later)
        bmr_results = _calc_all_bmr(req.weight_kg, req.height_cm, req.age, req.sex, req.bodyfat)
        tdee_results = _calc_all_tdee(bmr_results, req.activity)
        tdee_val = tdee_results["mifflin"]  # Use Mifflin-St Jeor as primary

        # 2) Generate plate with enhanced logic
        diet_flags_str = {str(flag) for flag in req.diet_flags} if req.diet_flags else None
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

        return PlateResponse(
            kcal=plate_data["kcal"],
            macros=plate_data["macros"],
            portions=plate_data["portions"],
            layout=layout,
            meals=plate_data["meals"],
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Enhanced plate generation failed: {str(e)}"
        ) from e


# WHO-Based Nutrition Endpoints


@app.post(
    "/api/v1/premium/targets",
    dependencies=[Depends(get_api_key)],
    response_model=WHOTargetsResponse,
)
async def api_who_targets(req: WHOTargetsRequest) -> WHOTargetsResponse:
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

        # Calculate WHO-based targets
        targets = _build_targets(profile)

        # Validate safety
        from core.recommendations import validate_targets_safety

        warnings = validate_targets_safety(targets)

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
            warnings=warnings,
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
    RU: Генерирует недельное меню на основе целей ВОЗ.
    EN: Generates weekly menu based on WHO nutrition targets.

    Advanced weekly planning with:
    - 7-day menu with nutritional variety
    - Micronutrient adequacy over the week (>80% average)
    - Shopping list with quantities
    - Cost estimation and adherence scoring
    - Diet flag adaptations (VEG, GF, DAIRY_FREE, LOW_COST)

    Uses WHO guidelines for nutrient priorities and food-first approach
    for meeting micronutrient needs without supplements.
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

        # Generate weekly menu
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
        # Re-raise HTTP exceptions as-is
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
        adequate_nutrients = sum(1 for cov in coverage.values() if cov.coverage_percent >= 80)
        adherence_score = (adequate_nutrients / total_nutrients * 100) if total_nutrients > 0 else 0

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
        raise HTTPException(status_code=500, detail=f"Force update failed: {str(e)}") from e


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
        raise HTTPException(status_code=500, detail=f"Update check failed: {str(e)}") from e


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
        success = await scheduler.update_manager.rollback_database(source, target_version)

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
        raise HTTPException(status_code=500, detail=f"Rollback operation failed: {str(e)}") from e


@app.post(
    "/api/v1/bmi/pro",
    response_model=BMIProResponse,
    dependencies=[Depends(get_api_key)],
)
async def api_v1_bmi_pro(payload: BMIProRequest):
    """
    BMI Pro: Advanced BMI analysis with waist measurements, body composition, and risk staging.

    Provides comprehensive health risk assessment including:
    - Traditional BMI and category
    - Waist-to-Height Ratio (WHtR) with risk interpretation
    - Waist-to-Hip Ratio (WHR) with sex-specific risk thresholds
    - Fat-Free Mass Index (FFMI) for body composition analysis
    - Multi-factor obesity staging and personalized recommendations
    """
    try:
        # Calculate traditional BMI
        height_m = payload.height_cm / 100.0
        bmi = round(payload.weight_kg / (height_m**2), 1)
        bmi_cat = bmi_category(bmi, payload.lang)

        # Calculate WHtR
        wht = wht_ratio(payload.waist_cm, payload.height_cm)
        wht_interpretation = interpret_wht_ratio(wht)

        # Normalize gender for functions that expect Literal["male", "female"]
        normalized_gender = "male" if payload.gender.lower() in {"male", "муж", "м"} else "female"

        # Calculate WHR if hip measurement provided
        whr = None
        whr_interpretation = None
        if payload.hip_cm:
            whr = whr_ratio(payload.waist_cm, payload.hip_cm, normalized_gender)
            whr_interpretation = interpret_whr_ratio(whr, normalized_gender)

        # Calculate FFMI if body fat percentage provided
        ffm_result = None
        if payload.bodyfat_pct is not None:
            ffm_result = ffmi(payload.weight_kg, payload.height_cm, payload.bodyfat_pct)

        # Stage obesity using multiple metrics
        obesity_staging = stage_obesity(bmi, wht, whr or 0, normalized_gender)

        # Build response
        response = BMIProResponse(
            bmi=bmi,
            bmi_category=bmi_cat,
            wht_ratio=wht,
            wht_risk_category=wht_interpretation["category"],
            wht_risk_level=wht_interpretation["risk"],
            wht_description=wht_interpretation["description"],
            obesity_stage=obesity_staging["stage"],
            risk_factors=int(obesity_staging["risk_factors"]),
            recommendation=obesity_staging["recommendation"],
            note="BMI Pro analysis complete",
        )

        # Add WHR data if available
        if whr is not None and whr_interpretation is not None:
            response.whr_ratio = whr
            response.whr_risk_level = whr_interpretation["risk"]
            response.whr_description = whr_interpretation["description"]

        # Add FFMI data if available
        if ffm_result is not None:
            response.ffmi = ffm_result["ffmi"]
            response.ffm_kg = ffm_result["ffm_kg"]

        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BMI Pro analysis failed: {str(e)}") from e


# Export Endpoints


@app.get("/api/v1/premium/exports/day/{plan_id}.csv", dependencies=[Depends(get_api_key)])
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

        csv_data = to_csv_day(mock_plan)

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=daily_plan_{plan_id}.csv"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}") from e


@app.get("/api/v1/premium/exports/week/{plan_id}.csv", dependencies=[Depends(get_api_key)])
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

        csv_data = to_csv_week(mock_weekly_plan)

        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=weekly_plan_{plan_id}.csv"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}") from e


@app.get("/api/v1/premium/exports/day/{plan_id}.pdf", dependencies=[Depends(get_api_key)])
async def export_daily_plan_pdf(plan_id: str):
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

        pdf_data = to_pdf_day(mock_plan)

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=daily_plan_{plan_id}.pdf"},
        )

    except ImportError:
        raise HTTPException(
            status_code=503, detail="PDF export not available - ReportLab not installed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}") from e


@app.get("/api/v1/premium/exports/week/{plan_id}.pdf", dependencies=[Depends(get_api_key)])
async def export_weekly_plan_pdf(plan_id: str):
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

        pdf_data = to_pdf_week(mock_weekly_plan)

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=weekly_plan_{plan_id}.pdf"},
        )

    except ImportError:
        raise HTTPException(
            status_code=503, detail="PDF export not available - ReportLab not installed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}") from e
