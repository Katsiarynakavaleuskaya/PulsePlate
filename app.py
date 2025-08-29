import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, model_validator, StrictFloat
# optio, StrictFloatnal dotenv
##DOTENV_OPTIONAL##


from typing import Literal, Optional, Dict
try:
    from dotenv import load_dotenv  # type: ignore

except Exception:
    # dotenv is optional; skip if missing in test env
    pass
from llm import get_provider


# Загружаем .env


app = FastAPI(title="BMI-App 2025")

# ---------- Models ----------
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

    # Нормализуем строковые флаги до нижнего регистра
    @model_validator(mode="before")
    @classmethod
    def _normalize_values(cls, values: Dict):
        for k in ["gender", "pregnant", "athlete", "lang"]:
            if k in values and isinstance(values[k], str):
                values[k] = values[k].strip().lower()
        return values


# ---------- Core logic ----------
def calc_bmi(weight_kg: StrictFloat, height_m: float) -> float:
    return round(weight_kg / (height_m ** 2), 1)


def category_by_bmi(bmi: float, lang: str = "ru") -> str:
    # В тестах ожидается "Healthy weight" (а не "Normal")
    if bmi < 18.5:
        return "Недостаточная масса" if lang == "ru" else "Underweight"
    if bmi < 25:
        return "Норма" if lang == "ru" else "Healthy weight"
    if bmi < 30:
        return "Избыточный вес" if lang == "ru" else "Overweight"
    return "Ожирение" if lang == "ru" else "Obesity"


def normalize_flags(gender: str, pregnant: str, athlete: str) -> Dict[str, bool]:
    gender_norm = {
        "male": "male", "муж": "male", "м": "male",
        "female": "female", "жен": "female", "ж": "female",
    }.get(gender, gender)

    preg_true = pregnant in {"да", "беременна", "pregnant", "yes", "y"}
    preg_false = pregnant in {"нет", "no", "not", "n"}
    is_pregnant = preg_true and gender_norm == "female" and not preg_false

    is_athlete = athlete in {"спортсмен", "да", "yes", "y", "athlete"}

    return {"gender_male": gender_norm == "male", "is_pregnant": is_pregnant, "is_athlete": is_athlete}


def waist_risk(waist_cm: Optional[float], gender_male: bool, lang: str = "ru") -> str:
    if waist_cm is None:
        return ""
    warn, high = (94, 102) if gender_male else (80, 88)
    if waist_cm >= high:
        return "Высокий риск по талии" if lang == "ru" else "High waist-related risk"
    if waist_cm >= warn:
        return "Повышенный риск по талии" if lang == "ru" else "Increased waist-related risk"
    return ""


# ---------- Endpoints ----------
@app.get("/favicon.ico")
def favicon():
    # Пустой ответ, чтобы не было 404 в логах
    return Response(status_code=204)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/bmi")
def bmi_endpoint(req: BMIRequest):
    flags = normalize_flags(req.gender, req.pregnant, req.athlete)
    bmi = calc_bmi(req.weight_kg, req.height_m)

    if flags["is_pregnant"]:
        note = "BMI не применим при беременности" if req.lang == "ru" else "BMI is not valid during pregnancy"
        return {
            "bmi": bmi,
            "category": None,
            "note": note,
            "athlete": flags["is_athlete"],
            "group": "athlete" if flags["is_athlete"] else "general",
        }

    category = category_by_bmi(bmi, req.lang)
    notes = []
    if flags["is_athlete"]:
        notes.append("У спортсменов BMI может завышать жировую массу" if req.lang == "ru"
                     else "For athletes, BMI may overestimate body fat")
    wr = waist_risk(req.waist_cm, flags["gender_male"], req.lang)
    if wr:
        notes.append(wr)

    return {
        "bmi": bmi,
        "category": category,
        "note": " | ".join(notes) if notes else "",
        "athlete": flags["is_athlete"],
        "group": "athlete" if flags["is_athlete"] else "general",
    }


@app.post("/plan")
def plan_endpoint(req: BMIRequest):
    flags = normalize_flags(req.gender, req.pregnant, req.athlete)
    bmi = calc_bmi(req.weight_kg, req.height_m)
    category = None if flags["is_pregnant"] else category_by_bmi(bmi, req.lang)

    healthy_bmi = {"min": 18.5, "max": 24.9}

    if req.lang == "ru":
        base = {
            "summary": "Персональный план (MVP)",
            "bmi": bmi,
            "category": category,
            "premium": bool(req.premium),
            "next_steps": ["Шаги: 7–10 тыс/день", "Белок: 1.2–1.6 г/кг", "Сон: 7–9 часов"],
            "healthy_bmi": healthy_bmi,
            "action": "Сделай сегодня 20-мин быструю прогулку",
        }
        if req.premium:
            base["premium_reco"] = ["Дефицит 300–500 ккал", "2–3 силовые тренировки/нед"]
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
            base["premium_reco"] = ["Calorie deficit 300–500 kcal", "2–3 strength sessions/week"]

    return base


# ---------- Insight (LLM) ----------
class InsightReq(BaseModel):
    text: str = Field(..., min_length=1)


@app.post("/insight")
def insight(req: InsightReq):
    if str(os.getenv("FEATURE_INSIGHT", "")).strip().lower() not in {"1", "true", "on", "yes"}:
        raise HTTPException(status_code=503, detail="FEATURE_INSIGHT is disabled")

    # отложенный импорт, чтобы не падать, если файла нет
    try:
        from llm import get_provider
    except Exception:
        raise HTTPException(status_code=503, detail="LLM module is not available")

    provider = get_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="No LLM provider configured. Set LLM_PROVIDER=stub|grok")

    insight_text = provider.generate(req.text)
    return {"provider": provider.name, "insight": insight_text}


# ---------- Debug env ----------
@app.get("/debug_env")
def debug_env():
    """
    Diagnostic endpoint to inspect env flags (.env).
    """
    data = {
        "FEATURE_INSIGHT": os.getenv("FEATURE_INSIGHT", ""),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER", ""),
        "GROK_MODEL": os.getenv("GROK_MODEL", ""),
        "GROK_ENDPOINT": os.getenv("GROK_ENDPOINT", ""),
    }
    data["insight_enabled"] = str(str(os.getenv("FEATURE_INSIGHT", "")).strip().lower() in {"1", "true", "yes", "on"})
    return JSONResponse(content=data)


from bodyfat import get_router as get_bodyfat_router
app.include_router(get_bodyfat_router())


# --- API v1: health ---
@app.get("/api/v1/health")
def api_v1_health():
    return {"status": "ok", "version": "v1"}


# --- API v1: bmi ---
from pydantic import BaseModel, Field
from fastapi import HTTPException

class BMIRequest(BaseModel):
    weight_kg: StrictFloat = Field(..., gt=0, description="Weight in kilograms")
    height_cm: StrictFloat = Field(..., gt=0, description="Height in centimeters")
    group: str = Field("general", description="general|athlete|pregnant|elderly|teen")

class BMIResponse(BaseModel):
    bmi: float
    category: str
    interpretation: str

def _bmi_value(w: float, h_cm: float) -> float:
    h = h_cm / 100.0
    if h <= 0:
        raise ValueError("height must be > 0")
    return round(w / (h * h), 2)

def _bmi_category(b: float) -> str:
    if b < 18.5: return "Underweight"
    if b < 25:   return "Normal"
    if b < 30:   return "Overweight"
    return "Obese"

def _interpretation(b: float, g: str) -> str:
    base = _bmi_category(b)
    g = g.lower().strip()
    if g == "athlete":  return f"{base} (мышечная масса может искажать BMI)"
    if g == "pregnant": return "BMI не применим при беременности"
    if g == "elderly":  return f"{base} (возрастные изменения состава тела)"
    if g == "teen":     return "Используйте педиатрические перцентили BMI"
    return base

@app.post("/api/v1/bmi", response_model=BMIResponse)
def api_v1_bmi(payload: BMIRequest) -> BMIResponse:
    try:
        v = _bmi_value(payload.weight_kg, payload.height_cm)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return BMIResponse(
        bmi=v,
        category=_bmi_category(v),
        interpretation=_interpretation(v, payload.group)
    )
