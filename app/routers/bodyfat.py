from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.bodyfat import estimate_all


class BodyFatRequest(BaseModel):
    height_m: Optional[float] = Field(None, gt=0, description="Height in meters, must be positive")
    weight_kg: Optional[float] = Field(None, gt=0, description="Weight in kg, must be positive")
    age: Optional[int] = Field(None, ge=1, le=120, description="Age in years, 1..120")
    gender: str
    bmi: Optional[float] = Field(None, ge=0, le=100, description="BMI value, 0..100")
    neck_cm: Optional[float] = Field(
        None, gt=0, description="Neck circumference in cm, must be > 0"
    )
    waist_cm: Optional[float] = Field(
        None, gt=0, description="Waist circumference in cm, must be > 0"
    )
    hip_cm: Optional[float] = Field(None, gt=0, description="Hip circumference in cm, must be > 0")
    language: Optional[str] = "en"  # "en" | "ru" | "es"


def get_router() -> APIRouter:
    router = APIRouter()

    @router.post("/bodyfat")
    def calc_bodyfat(req: BodyFatRequest) -> dict[str, object]:
        lang = (req.language or "en").lower()
        data: dict[str, object] = dict(req.model_dump(exclude_none=True))

        if "bmi" not in data and ("weight_kg" in data and "height_m" in data):
            weight_kg_val = data["weight_kg"]
            height_m_val = data["height_m"]
            # Type narrowing: we know these are floats from Pydantic model
            if isinstance(weight_kg_val, (int, float)) and isinstance(height_m_val, (int, float)):
                weight_kg = float(weight_kg_val)
                height_m = float(height_m_val)
                data["bmi"] = weight_kg / (height_m**2)

        result = estimate_all(data)

        labels_en = {"methods": "methods", "median": "median", "units": "%"}
        labels_ru = {"methods": "методы", "median": "медиана", "units": "%"}
        labels_es = {"methods": "métodos", "median": "mediana", "units": "%"}

        if lang == "ru":
            labels = labels_ru
        elif lang == "es":
            labels = labels_es
        else:
            labels = labels_en

        return {
            "methods": result["methods"],
            "median": result["median"],
            "lang": lang,
            "labels": labels,
        }

    return router
