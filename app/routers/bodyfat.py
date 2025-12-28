from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from core.bodyfat import estimate_all

LABELS_BY_LANG: dict[str, dict[str, str]] = {
    "en": {"methods": "methods", "median": "median", "units": "%"},
    "ru": {"methods": "методы", "median": "медиана", "units": "%"},
    "es": {"methods": "métodos", "median": "mediana", "units": "%"},
}


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

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: str) -> str:
        v = value.strip().lower()
        if v in {"male", "m", "man", "hombre", "masculino", "varon", "varón"}:
            return "male"
        if v in {"female", "f", "woman", "mujer", "femenino"}:
            return "female"
        raise ValueError(
            "gender must be 'male' or 'female' (also accepts m/f, hombre/mujer, masculino/femenino)"
        )


def get_router() -> APIRouter:
    router = APIRouter()

    @router.post("/bodyfat")
    async def calc_bodyfat(req: BodyFatRequest) -> dict[str, object]:
        lang = (req.language or "en").lower()
        data: dict[str, object] = dict(req.model_dump(exclude_none=True))

        if req.bmi is None and req.weight_kg is not None and req.height_m is not None:
            data["bmi"] = req.weight_kg / (req.height_m**2)

        result = estimate_all(data)

        labels = LABELS_BY_LANG.get(lang, LABELS_BY_LANG["en"])

        return {
            "methods": result["methods"],
            "median": result["median"],
            "lang": lang,
            "labels": labels,
        }

    return router
