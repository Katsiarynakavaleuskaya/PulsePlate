"""Contracts for the legacy premium weekly-plan compatibility alias."""

from __future__ import annotations

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
    goal: Goal = "maintain"
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
        if not isinstance(values, dict):
            return values
        goal = values.get("goal")
        if isinstance(goal, str):
            normalized_goal = goal.strip().lower()
            if normalized_goal in {"lose", "loss", "weight_loss"}:
                values["goal"] = "loss"
            elif normalized_goal in {"maintain", "maintenance"}:
                values["goal"] = "maintain"
            elif normalized_goal in {"gain", "weight_gain"}:
                values["goal"] = "gain"
        return values

    @model_validator(mode="after")
    def _validate_request_mode(self) -> "LegacyWeekPlanRequest":
        """Ensure either targets or full profile data is provided."""

        if isinstance(self.targets, dict) and ("macros" in self.targets or "micro" in self.targets):
            try:
                TargetsIn.model_validate(self.targets)
            except ValidationError as exc:
                raise ValueError(f"Invalid targets payload: {exc}") from exc

        if self.targets is None:
            if not all(
                x is not None
                for x in [self.sex, self.age, self.height_cm, self.weight_kg, self.activity]
            ):
                raise ValueError(
                    "Either 'targets' must be provided, or all profile fields "
                    "(sex, age, height_cm, weight_kg, activity) must be present"
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
