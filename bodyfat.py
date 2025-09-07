import math
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel


# ---------- Формулы ----------
def bf_deurenberg(bmi: float, age: int, gender: str) -> float:
    sex = 1 if gender.lower().startswith("male") else 0
    return 1.20 * bmi + 0.23 * age - 10.8 * sex - 5.4


def bf_us_navy(
    height_cm: float,
    neck_cm: float,
    waist_cm: float,
    gender: str,
    hip_cm: Optional[float] = None,
) -> float:
    g = gender.lower()
    if g.startswith("male"):
        return (
            86.010 * math.log10(waist_cm - neck_cm)
            - 70.041 * math.log10(height_cm)
            + 36.76
        )
    else:
        if hip_cm is None:
            raise ValueError("hip_cm required for female")
        return (
            163.205 * math.log10(waist_cm + hip_cm - neck_cm)
            - 97.684 * math.log10(height_cm)
            - 78.387
        )


def bf_ymca(weight_kg: float, waist_cm: float, gender: str) -> float:
    weight_lb = weight_kg * 2.20462
    waist_in = waist_cm / 2.54
    if gender.lower().startswith("male"):
        body_fat = (weight_lb * 1.082 + 94.42) - (waist_in * 4.15)
    else:
        body_fat = (weight_lb * 0.732 + 8.987) + (waist_in / 3.14)
    return (body_fat / weight_lb) * 100.0


# ---------- Агрегатор ----------
def estimate_all(data: Dict[str, Any]) -> Dict[str, Any]:
    results: Dict[str, float] = {}

    if {"bmi", "age", "gender"} <= data.keys():
        results["deurenberg"] = bf_deurenberg(data["bmi"], data["age"], data["gender"])

    if {"height_cm", "neck_cm", "waist_cm", "gender"} <= data.keys():
        try:
            results["us_navy"] = bf_us_navy(
                data["height_cm"],
                data["neck_cm"],
                data["waist_cm"],
                data["gender"],
                data.get("hip_cm"),
            )
        except ValueError:
            pass

    if {"weight_kg", "waist_cm", "gender"} <= data.keys():
        results["ymca"] = bf_ymca(data["weight_kg"], data["waist_cm"], data["gender"])

    # округляем до 2 знаков
    results = {k: round(v, 2) for k, v in results.items()}
    values = list(results.values())
    median = round(sorted(values)[len(values) // 2], 2) if values else None
    return {"methods": results, "median": median}


# ---------- FastAPI ----------
class BodyFatRequest(BaseModel):
    height_m: Optional[float] = None
    weight_kg: Optional[float] = None
    age: Optional[int] = None
    gender: str
    bmi: Optional[float] = None
    neck_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    language: Optional[str] = "en"  # "en" | "ru"


def get_router() -> APIRouter:
    router = APIRouter()

    @router.post("/bodyfat")
    def calc_bodyfat(req: BodyFatRequest):
        lang = (req.language or "en").lower()
        # Use Pydantic v2 API to avoid deprecation warning
        data = req.model_dump(exclude_none=True)
        if "bmi" not in data and ("weight_kg" in data and "height_m" in data):
            data["bmi"] = data["weight_kg"] / (data["height_m"] ** 2)

        result = estimate_all(data)

        labels_en = {"methods": "methods", "median": "median", "units": "%"}
        labels_ru = {"methods": "методы", "median": "медиана", "units": "%"}
        resp = {
            "methods": result["methods"],
            "median": result["median"],
            "lang": lang,
            "labels": labels_ru if lang == "ru" else labels_en,
        }
        return resp

    return router


# ---- export aliases for tests ----
deurenberg = bf_deurenberg
us_navy = bf_us_navy
ymca = bf_ymca
