"""Contracts for the legacy premium weekly-plan compatibility alias."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.schemas.nutrition_targets import TargetsIn
from app.schemas.premium_contracts import Activity, DietFlag, Goal, LifeStage, Sex


class LegacyWeekPlanRequest(BaseModel):
    """Extended request for week plan with optional pre-calculated targets."""

    model_config = ConfigDict(title="LegacyWeekPlanRequest", extra="forbid")

    targets: Optional[Dict[str, Any]] = None
    sex: Optional[Sex] = None
    age: Optional[int] = Field(None, ge=1, le=120)
    height_cm: Optional[float] = Field(None, gt=0)
    weight_kg: Optional[float] = Field(None, gt=0)
    activity: Optional[Activity] = None
    goal: Optional[Goal] = None
    deficit_pct: Optional[float] = Field(None, ge=5, le=25)
    surplus_pct: Optional[float] = Field(None, ge=5, le=20)
    bodyfat: Optional[float] = Field(None, ge=3, le=60)
    diet_flags: Optional[set[DietFlag]] = None
    life_stage: LifeStage = "adult"
    lang: str = "en"

    @model_validator(mode="before")
    @classmethod
    def _normalize_values(
        cls, values: dict[str, Any] | "LegacyWeekPlanRequest"
    ) -> dict[str, Any] | "LegacyWeekPlanRequest":
        if not isinstance(values, Mapping):
            return values
        if any(isinstance(values.get(field), bool) for field in ("age", "height_cm", "weight_kg")):
            raise ValueError("Boolean values are invalid for numeric profile fields")

        normalized_values = dict(values)
        goal = normalized_values.get("goal")
        if isinstance(goal, str):
            normalized_goal = goal.strip().lower()
            if normalized_goal in {"lose", "loss", "weight_loss"}:
                normalized_values["goal"] = "loss"
            elif normalized_goal in {"maintain", "maintenance"}:
                normalized_values["goal"] = "maintain"
            elif normalized_goal in {"gain", "weight_gain"}:
                normalized_values["goal"] = "gain"
        return normalized_values

    @model_validator(mode="after")
    def _validate_request_mode(self) -> "LegacyWeekPlanRequest":
        """Ensure either targets or full profile data is provided."""

        if isinstance(self.targets, dict) and ("macros" in self.targets or "micro" in self.targets):
            try:
                TargetsIn.model_validate(self.targets)
            except ValidationError as exc:
                raise ValueError(f"Invalid targets payload: {exc}") from exc

        profile_values = (
            self.sex,
            self.age,
            self.height_cm,
            self.weight_kg,
            self.activity,
            self.goal,
        )
        has_any_profile_value = any(value is not None for value in profile_values)
        has_complete_profile = all(value is not None for value in profile_values)
        if (self.targets is None or has_any_profile_value) and not has_complete_profile:
            raise ValueError(
                "Either 'targets' must be provided without profile fields, or all profile fields "
                "(sex, age, height_cm, weight_kg, activity, goal) must be present"
            )
        return self


class WeeklyMenuResponse(BaseModel):
    """RU: Ответ с недельным меню. EN: Response with weekly menu."""

    week_summary: Dict[str, Any]
    daily_menus: List[Dict[str, Any]]
    weekly_coverage: Dict[str, float]
    shopping_list: Dict[str, float]
    total_cost: float
    adherence_score: float
