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


class WHOTargetsUiLabels(BaseModel):
    """RU: Локализованные UI-лейблы для thin clients. EN: Localized UI labels."""

    kcal_daily: str
    macros_protein_g: str
    macros_fat_g: str
    macros_carbs_g: str
    macros_fiber_g: str
    water_ml: str
    priority_micros: str
    activity_weekly: str
    warnings: str


# RU: Единый источник переводов UI-лейблов; добавляйте новые языки только здесь и держите client i18n в sync.
# EN: Single source of truth for UI label translations; add new languages here and keep client i18n in sync.
_WHO_TARGETS_UI_LABELS_BY_LANG: dict[str, dict[str, str]] = {
    "en": {
        "kcal_daily": "Daily calories",
        "macros_protein_g": "Protein (g)",
        "macros_fat_g": "Fat (g)",
        "macros_carbs_g": "Carbs (g)",
        "macros_fiber_g": "Fiber (g)",
        "water_ml": "Water (ml)",
        "priority_micros": "Priority micros",
        "activity_weekly": "Weekly activity",
        "warnings": "Warnings",
    },
    "es": {
        "kcal_daily": "Calorías diarias",
        "macros_protein_g": "Proteínas (g)",
        "macros_fat_g": "Grasas (g)",
        "macros_carbs_g": "Carbohidratos (g)",
        "macros_fiber_g": "Fibra (g)",
        "water_ml": "Agua (ml)",
        "priority_micros": "Micronutrientes prioritarios",
        "activity_weekly": "Actividad semanal",
        "warnings": "Advertencias",
    },
    "ru": {
        "kcal_daily": "Ккал в день",
        "macros_protein_g": "Белки (г)",
        "macros_fat_g": "Жиры (г)",
        "macros_carbs_g": "Углеводы (г)",
        "macros_fiber_g": "Клетчатка (г)",
        "water_ml": "Вода (мл)",
        "priority_micros": "Приоритетные микроэлементы",
        "activity_weekly": "Активность за неделю",
        "warnings": "Предупреждения",
    },
}


def build_who_targets_ui_labels(lang: str | None) -> WHOTargetsUiLabels:
    """Build canonical localized UI labels for WHO targets contract."""

    language = str(lang or "en").lower()
    base_lang = language.split("-", 1)[0].split("_", 1)[0]
    labels = (
        _WHO_TARGETS_UI_LABELS_BY_LANG.get(language)
        or _WHO_TARGETS_UI_LABELS_BY_LANG.get(base_lang)
        or _WHO_TARGETS_UI_LABELS_BY_LANG["en"]
    )
    return WHOTargetsUiLabels(**labels)


class WHOTargetsResponse(BaseModel):
    """RU: Ответ с целевыми значениями по ВОЗ. EN: WHO targets response."""

    kcal_daily: int
    macros: Dict[str, int]
    water_ml: int
    priority_micros: Dict[str, float]
    activity_weekly: Dict[str, int]
    calculation_date: str
    warnings: List[Dict[str, str]] = Field(default_factory=list)
    ui_labels: WHOTargetsUiLabels
