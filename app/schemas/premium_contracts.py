# -*- coding: utf-8 -*-
"""
Premium/PRO Nutrition Contracts (Plate + WHO Targets)

RU: Контракты для "plate" и WHO targets, которые должны оставаться стабильными между
PRO (канон) и deprecated premium алиасами.
EN: Stable contracts for "plate" and WHO targets shared between canonical PRO endpoints
and deprecated premium aliases.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, Field, model_validator

Sex = Literal["female", "male"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["loss", "maintain", "gain"]
DietFlag = Literal[
    "VEG",
    "GF",
    "DAIRY_FREE",
    "LOW_COST",
    "HIGH_PROTEIN",
    "LOW_CARB",
    "MEDITERRANEAN",
    "VEGAN",
    "KETO",
    "PALEO",
]
LifeStage = Literal["child", "teen", "adult", "pregnant", "lactating", "elderly"]


class PlateRequest(BaseModel):
    """RU: Запрос на генерацию «Моей Тарелки». EN: Request to generate 'My Plate'."""

    sex: Sex
    age: int = Field(..., ge=10, le=100)
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    activity: Activity
    goal: Goal
    deficit_pct: Optional[float] = Field(None, ge=5, le=25)  # loss
    surplus_pct: Optional[float] = Field(None, ge=5, le=20)  # gain
    bodyfat: Optional[float] = Field(None, ge=3, le=60)
    diet_flags: Optional[Set[DietFlag]] = None
    life_stage: LifeStage = "adult"
    lang: str = "en"


class VisualShape(BaseModel):
    """RU: Примитив для фронтенда. EN: Primitive for frontend visualization."""

    kind: Literal["plate_sector", "bowl", "marker"]
    fraction: float
    label: str
    tooltip: str


class PlateResponse(BaseModel):
    kcal: int
    macros: Dict[str, int]
    portions: Dict[str, float]
    layout: List[VisualShape]
    meals: List[Dict[str, Any]]
    day_micros: Dict[str, float] = Field(default_factory=dict)
    meals_per_day: int = 3


class WHOTargetsRequest(BaseModel):
    """RU: Запрос на расчёт целей по нормам ВОЗ. EN: WHO-based targets request."""

    sex: Sex
    age: int = Field(..., ge=1, le=120)
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    activity: Activity
    goal: Goal = "maintain"
    deficit_pct: Optional[float] = Field(None, ge=5, le=25)
    surplus_pct: Optional[float] = Field(None, ge=5, le=20)
    bodyfat: Optional[float] = Field(None, ge=3, le=60)
    diet_flags: Optional[Set[DietFlag]] = None
    life_stage: LifeStage = "adult"
    lang: str = "en"
    targets: Optional[Dict[str, Any]] = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def _normalize_values(
        cls, values: dict[str, Any] | "WHOTargetsRequest"
    ) -> dict[str, Any] | "WHOTargetsRequest":
        if not isinstance(values, dict):
            return values
        goal = values.get("goal")
        if isinstance(goal, str):
            g = goal.strip().lower()
            if g in {"lose", "loss", "weight_loss"}:
                values["goal"] = "loss"
            elif g in {"maintain", "maintenance"}:
                values["goal"] = "maintain"
            elif g in {"gain", "weight_gain"}:
                values["goal"] = "gain"
        return values


class WHOTargetsResponse(BaseModel):
    """RU: Ответ с целевыми значениями по ВОЗ. EN: WHO targets response."""

    kcal_daily: int
    macros: Dict[str, int]
    water_ml: int
    priority_micros: Dict[str, float]
    activity_weekly: Dict[str, int]
    calculation_date: str
    warnings: List[Dict[str, str]] = Field(default_factory=list)
