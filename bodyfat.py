from __future__ import annotations

import math
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator


# ---------- Formulas ----------
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
        return 86.010 * math.log10(waist_cm - neck_cm) - 70.041 * math.log10(height_cm) + 36.76

    # Female calculation
    if hip_cm is None:
        raise ValueError("hip_cm required for female")
    return (
        163.205 * math.log10(waist_cm + hip_cm - neck_cm) - 97.684 * math.log10(height_cm) - 78.387
    )


def bf_ymca(weight_kg: float, waist_cm: float, gender: str) -> float:
    weight_lb = weight_kg * 2.20462
    waist_in = waist_cm / 2.54
    if gender.lower().startswith("male"):
        body_fat = (weight_lb * 1.082 + 94.42) - (waist_in * 4.15)
    else:
        body_fat = (weight_lb * 0.732 + 8.987) + (waist_in / 3.14)
    return (body_fat / weight_lb) * 100.0


# ---------- Aggregator ----------
def estimate_all(data: dict[str, Any]) -> dict[str, object]:
    results: dict[str, float] = {}

    if {"bmi", "age", "gender"} <= data.keys():
        try:
            # Convert inputs directly; allow ValueError/TypeError to skip invalid data
            bmi = float(data["bmi"])
            age = int(data["age"])
            gender = str(data["gender"])
        except (ValueError, TypeError):
            pass  # skip calculation on bad input
        else:
            results["deurenberg"] = bf_deurenberg(bmi, age, gender)

    if {"height_cm", "neck_cm", "waist_cm", "gender"} <= data.keys():
        try:
            # Convert inputs directly; hip_cm is optional and only converted if present
            height_cm = float(data["height_cm"])
            neck_cm = float(data["neck_cm"])
            waist_cm = float(data["waist_cm"])
            gender = str(data["gender"])
            hip_cm = float(data["hip_cm"]) if data.get("hip_cm") is not None else None
        except (ValueError, TypeError):
            pass  # skip calculation on bad input
        else:
            try:
                results["us_navy"] = bf_us_navy(height_cm, neck_cm, waist_cm, gender, hip_cm)
            except (ValueError, TypeError):
                pass  # skip when required measurements are missing

    if {"weight_kg", "waist_cm", "gender"} <= data.keys():
        try:
            # Convert inputs directly without unsafe casts
            weight_kg = float(data["weight_kg"])
            waist_cm = float(data["waist_cm"])
            gender = str(data["gender"])
        except (ValueError, TypeError):
            pass  # skip calculation on bad input
        else:
            results["ymca"] = bf_ymca(weight_kg, waist_cm, gender)

    # round to 2 decimal places
    results = {k: round(v, 2) for k, v in results.items()}
    values = list(results.values())
    median = round(sorted(values)[len(values) // 2], 2) if values else None
    return {"methods": results, "median": median}


# ---------- FastAPI ----------
class BodyFatRequest(BaseModel):
    height_m: Optional[float] = Field(None, gt=0, description="Height in meters, must be positive")
    weight_kg: Optional[float] = Field(
        None, gt=0, description="Weight in kilograms, must be positive"
    )
    age: Optional[int] = Field(
        None, ge=1, le=120, description="Age in years, must be between 1 and 120"
    )
    gender: str
    bmi: Optional[float] = Field(
        None, ge=0, le=100, description="BMI value, must be between 0 and 100"
    )
    neck_cm: Optional[float] = Field(
        None, gt=0, description="Neck circumference in cm, must be positive"
    )
    waist_cm: Optional[float] = Field(
        None, gt=0, description="Waist circumference in cm, must be positive"
    )
    hip_cm: Optional[float] = Field(
        None, gt=0, description="Hip circumference in cm, must be positive"
    )
    language: Optional[str] = "en"  # "en" | "ru"

    @model_validator(mode="after")
    def _validate_gender(self) -> "BodyFatRequest":
        gender_normalized = (self.gender or "").strip().lower()
        if gender_normalized not in {"male", "female"}:
            raise ValueError("gender must be 'male' or 'female'")
        self.gender = gender_normalized
        return self


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
        labels_es = {"methods": "métodos", "median": "mediana", "units": "%"}

        # Select labels based on language
        if lang == "ru":
            labels = labels_ru
        elif lang == "es":
            labels = labels_es
        else:
            labels = labels_en

        resp = {
            "methods": result["methods"],
            "median": result["median"],
            "lang": lang,
            "labels": labels,
        }
        return resp

    return router


# ---- export aliases for tests ----
deurenberg = bf_deurenberg
us_navy = bf_us_navy
ymca = bf_ymca
