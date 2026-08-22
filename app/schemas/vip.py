# -*- coding: utf-8 -*-
"""
VIP Schemas

RU: Схемы для VIP функций - микронутриентные цели, авто-ремонт, региональные настройки.
EN: Schemas for VIP features - micronutrient goals, auto-repair, regional settings.
"""

from collections.abc import Mapping
from enum import Enum
import math
from numbers import Real
from typing import Any, List, Literal, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, field_validator, model_validator


class MicronutrientType(str, Enum):
    """RU: Типы микронутриентов; EN: Micronutrient types."""

    # Vitamins
    VITAMIN_A = "vitamin_a"  # Retinol equivalents (mcg)
    VITAMIN_B1 = "vitamin_b1"  # Thiamine (mg)
    VITAMIN_B2 = "vitamin_b2"  # Riboflavin (mg)
    VITAMIN_B3 = "vitamin_b3"  # Niacin (mg)
    VITAMIN_B6 = "vitamin_b6"  # Pyridoxine (mg)
    VITAMIN_B9 = "vitamin_b9"  # Folate (mcg)
    VITAMIN_B12 = "vitamin_b12"  # Cobalamin (mcg)
    VITAMIN_C = "vitamin_c"  # Ascorbic acid (mg)
    VITAMIN_D = "vitamin_d"  # Cholecalciferol (mcg)
    VITAMIN_E = "vitamin_e"  # Tocopherol (mg)
    VITAMIN_K = "vitamin_k"  # Phylloquinone (mcg)

    # Minerals
    CALCIUM = "calcium"  # Ca (mg)
    IRON = "iron"  # Fe (mg)
    MAGNESIUM = "magnesium"  # Mg (mg)
    PHOSPHORUS = "phosphorus"  # P (mg)
    POTASSIUM = "potassium"  # K (mg)
    SODIUM = "sodium"  # Na (mg)
    ZINC = "zinc"  # Zn (mg)
    COPPER = "copper"  # Cu (mg)
    MANGANESE = "manganese"  # Mn (mg)
    SELENIUM = "selenium"  # Se (mcg)
    IODINE = "iodine"  # I (mcg)


class AgeGroup(str, Enum):
    """RU: Возрастные группы; EN: Age groups."""

    INFANT_0_6M = "infant_0_6m"
    INFANT_7_12M = "infant_7_12m"
    CHILD_1_3Y = "child_1_3y"
    CHILD_4_8Y = "child_4_8y"
    CHILD_9_13Y = "child_9_13y"
    ADOLESCENT_14_18Y = "adolescent_14_18y"
    ADULT_19_50Y = "adult_19_50y"
    ADULT_51_70Y = "adult_51_70y"
    ELDERLY_70Y_PLUS = "elderly_70y_plus"
    PREGNANT = "pregnant"
    LACTATING = "lactating"


class Gender(str, Enum):
    """RU: Пол; EN: Gender."""

    MALE = "male"
    FEMALE = "female"


class Region(str, Enum):
    """RU: Поддерживаемые регионы; EN: Supported regions."""

    ES = "es"  # Spain
    US = "us"  # United States


class Currency(str, Enum):
    """RU: Поддерживаемые валюты; EN: Supported currencies."""

    EUR = "EUR"
    USD = "USD"


class MicronutrientGoal(BaseModel):
    """
    RU: Цель по микронутриенту с приоритетом.
    EN: Micronutrient goal with priority.
    """

    nutrient: str = Field(..., description="Nutrient name (e.g., 'Fe_mg', 'VitD_IU')")
    target_daily: float = Field(..., gt=0, description="Daily target in appropriate units")
    priority: int = Field(default=1, ge=1, le=5, description="Priority 1-5 (5 = highest)")
    deficiency_threshold: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Deficiency threshold (0.8 = 80% of target)",
    )


class AutoRepairConfig(BaseModel):
    """
    RU: Конфигурация авто-ремонта меню.
    EN: Auto-repair menu configuration.
    """

    enabled: bool = Field(default=True, description="Enable auto-repair")
    max_replacements: int = Field(
        default=3, ge=1, le=10, description="Max ingredient replacements per meal"
    )
    preserve_flags: Set[str] = Field(
        default_factory=set, description="Dietary flags to preserve (VEG, GF, etc.)"
    )
    prefer_local_products: bool = Field(default=True, description="Prefer local/regional products")


_AUTO_REPAIR_TARGET_FIELDS = (
    "iron_mg",
    "calcium_mg",
    "magnesium_mg",
    "zinc_mg",
    "potassium_mg",
    "iodine_ug",
    "selenium_ug",
    "folate_ug",
    "b12_ug",
    "vitamin_d_iu",
    "vitamin_a_ug",
    "vitamin_c_mg",
)


class AutoRepairIngredient(BaseModel):
    """One ingredient admitted by the weekly auto-repair wire contract."""

    name: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def validate_nonempty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Ingredient name must be non-empty")
        return value

    model_config = ConfigDict(extra="allow")


_AUTO_REPAIR_BASELINE_FIELDS = (
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    *_AUTO_REPAIR_TARGET_FIELDS,
)


class AutoRepairMealNutrients(BaseModel):
    """Complete explicit per-meal evidence required by bounded repair."""

    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fiber_g: float
    iron_mg: float
    calcium_mg: float
    magnesium_mg: float
    zinc_mg: float
    potassium_mg: float
    iodine_ug: float
    selenium_ug: float
    folate_ug: float
    b12_ug: float
    vitamin_d_iu: float
    vitamin_a_ug: float
    vitamin_c_mg: float

    @model_validator(mode="before")
    @classmethod
    def validate_complete_baseline(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        for field_name in _AUTO_REPAIR_BASELINE_FIELDS:
            raw_value = values.get(field_name)
            if isinstance(raw_value, bool) or not isinstance(raw_value, Real):
                raise ValueError(f"{field_name} must be a real number")
            value = float(raw_value)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{field_name} must be finite and nonnegative")
        return values

    model_config = ConfigDict(extra="allow")


class AutoRepairMeal(BaseModel):
    """One meal with explicit nutrient evidence for safe bounded repair."""

    ingredients: List[AutoRepairIngredient] = Field(..., min_length=1)
    nutrients: AutoRepairMealNutrients

    @model_validator(mode="before")
    @classmethod
    def validate_nutrient_evidence(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        nutrients = values.get("nutrients")
        if not isinstance(nutrients, Mapping):
            raise ValueError("Meal nutrients must be a mapping")
        for nutrient, raw_value in nutrients.items():
            if not isinstance(nutrient, str) or not nutrient:
                raise ValueError("Meal nutrient names must be non-empty strings")
            if isinstance(raw_value, bool) or not isinstance(raw_value, Real):
                raise ValueError("Meal nutrient values must be real numbers")
            value = float(raw_value)
            if not math.isfinite(value) or value < 0:
                raise ValueError("Meal nutrient values must be finite and nonnegative")
        return values

    model_config = ConfigDict(extra="allow")


class AutoRepairDay(BaseModel):
    """One non-empty day in the weekly auto-repair request."""

    meals: List[AutoRepairMeal] = Field(..., min_length=1)

    model_config = ConfigDict(extra="allow")


class AutoRepairWeekPlan(BaseModel):
    """Non-empty weekly plan admitted by the public auto-repair route."""

    days: List[AutoRepairDay] = Field(..., min_length=1)

    model_config = ConfigDict(extra="allow")


class AutoRepairTargetRanges(BaseModel):
    """Exact twelve positive monotonic micronutrient triplets."""

    iron_mg: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    calcium_mg: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    magnesium_mg: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    zinc_mg: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    potassium_mg: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    iodine_ug: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    selenium_ug: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    folate_ug: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    b12_ug: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    vitamin_d_iu: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    vitamin_a_ug: tuple[PositiveFloat, PositiveFloat, PositiveFloat]
    vitamin_c_mg: tuple[PositiveFloat, PositiveFloat, PositiveFloat]

    @model_validator(mode="before")
    @classmethod
    def validate_target_triplets(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        for field_name in _AUTO_REPAIR_TARGET_FIELDS:
            raw_range = values.get(field_name)
            if not isinstance(raw_range, (list, tuple)) or len(raw_range) != 3:
                raise ValueError(f"{field_name} must contain exactly three values")
            normalized: list[float] = []
            for raw_value in raw_range:
                if isinstance(raw_value, bool) or not isinstance(raw_value, Real):
                    raise ValueError(f"{field_name} values must be real numbers")
                value = float(raw_value)
                if not math.isfinite(value) or value <= 0:
                    raise ValueError(f"{field_name} values must be finite and positive")
                normalized.append(value)
            minimum, target, maximum = normalized
            if not minimum <= target <= maximum:
                raise ValueError(f"{field_name} must satisfy minimum <= target <= maximum")
        return values

    model_config = ConfigDict(extra="forbid")


class AutoRepairProfile(BaseModel):
    """Explicit profile used as NutritionTargets.calculated_for authority."""

    sex: Literal["female", "male"]
    age: int = Field(..., ge=1, le=120, strict=True)
    height_cm: float = Field(..., gt=0, le=300)
    weight_kg: float = Field(..., gt=0, le=500)
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"]
    goal: Literal["loss", "maintain", "gain"]
    deficit_pct: Optional[float] = Field(..., ge=5, le=25)
    surplus_pct: Optional[float] = Field(..., ge=5, le=20)
    bodyfat: Optional[float] = Field(..., gt=0, le=100)
    region: str = Field(..., min_length=1)
    timezone: str = Field(..., min_length=1)
    diet_flags: Set[str]
    life_stage: Literal["child", "teen", "adult", "pregnant", "lactating", "elderly"]
    medical_conditions: Set[str]

    @model_validator(mode="before")
    @classmethod
    def reject_ambiguous_profile_numbers(cls, values: Any) -> Any:
        if not isinstance(values, Mapping):
            return values
        for field_name in (
            "age",
            "height_cm",
            "weight_kg",
            "deficit_pct",
            "surplus_pct",
            "bodyfat",
        ):
            raw_value = values.get(field_name)
            if raw_value is None and field_name in {"deficit_pct", "surplus_pct", "bodyfat"}:
                continue
            if isinstance(raw_value, bool) or not isinstance(raw_value, Real):
                raise ValueError(f"{field_name} must be a real number")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite")
        return values

    model_config = ConfigDict(extra="forbid")


class AutoRepairMacroTargets(BaseModel):
    """Explicit daily macro targets using canonical 4/4/9 arithmetic."""

    protein_g: int = Field(..., gt=0, le=1000, strict=True)
    fat_g: int = Field(..., gt=0, le=1000, strict=True)
    carbs_g: int = Field(..., gt=0, le=2000, strict=True)
    fiber_g: int = Field(..., gt=0, le=500, strict=True)

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_macros(cls, values: Any) -> Any:
        if isinstance(values, Mapping) and any(
            isinstance(values.get(field_name), bool)
            for field_name in ("protein_g", "fat_g", "carbs_g", "fiber_g")
        ):
            raise ValueError("Macro targets must be non-boolean integers")
        return values

    model_config = ConfigDict(extra="forbid")


class AutoRepairActivityTargets(BaseModel):
    """Explicit bounded weekly activity targets."""

    moderate_aerobic_min: int = Field(..., ge=0, le=10080, strict=True)
    vigorous_aerobic_min: int = Field(..., ge=0, le=10080, strict=True)
    strength_sessions: int = Field(..., gt=0, le=21, strict=True)
    steps_daily: int = Field(..., gt=0, le=100000, strict=True)

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_activity(cls, values: Any) -> Any:
        if isinstance(values, Mapping) and any(
            isinstance(values.get(field_name), bool)
            for field_name in (
                "moderate_aerobic_min",
                "vigorous_aerobic_min",
                "strength_sessions",
                "steps_daily",
            )
        ):
            raise ValueError("Activity targets must be non-boolean integers")
        return values

    model_config = ConfigDict(extra="forbid")


class AutoRepairDailyTargets(BaseModel):
    """Explicit shared daily targets used by every admitted day."""

    kcal_daily: int = Field(..., gt=0, le=10000, strict=True)
    macros: AutoRepairMacroTargets
    water_ml_daily: int = Field(..., gt=0, le=10000, strict=True)
    activity: AutoRepairActivityTargets
    calculation_date: str = Field(..., min_length=1)

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_daily_targets(cls, values: Any) -> Any:
        if isinstance(values, Mapping) and any(
            isinstance(values.get(field_name), bool)
            for field_name in ("kcal_daily", "water_ml_daily")
        ):
            raise ValueError("Daily targets must be non-boolean integers")
        return values

    model_config = ConfigDict(extra="forbid")


class AutoRepairWeeklyRequest(BaseModel):
    """Typed public request validated explicitly after VIP authorization."""

    week_plan: AutoRepairWeekPlan
    targets: AutoRepairTargetRanges
    profile: AutoRepairProfile
    daily_targets: AutoRepairDailyTargets
    strategy: Literal["conservative", "balanced", "aggressive"] = "balanced"
    user_preferences: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class WeeklyRecipeMeal(BaseModel):
    """One non-empty meal admitted by weekly recipe synthesis."""

    ingredients: List[AutoRepairIngredient] = Field(..., min_length=1)

    model_config = ConfigDict(extra="allow")


class WeeklyRecipeDay(BaseModel):
    """One non-empty recipe-synthesis day."""

    day: str = Field(..., min_length=1)
    meals: List[WeeklyRecipeMeal] = Field(..., min_length=1)

    @field_validator("day")
    @classmethod
    def normalize_day_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Recipe day identifier must be non-empty")
        return normalized

    model_config = ConfigDict(extra="allow")


class WeeklyRecipePlan(BaseModel):
    """Non-empty weekly recipe plan."""

    days: List[WeeklyRecipeDay] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_day_identifiers(self) -> "WeeklyRecipePlan":
        day_identifiers = [day.day for day in self.days]
        if len(day_identifiers) != len(set(day_identifiers)):
            raise ValueError("Recipe day identifiers must be unique")
        return self

    model_config = ConfigDict(extra="allow")


class WeeklyRecipesRequest(BaseModel):
    """Typed weekly recipe request validated after VIP authorization."""

    week_plan: WeeklyRecipePlan
    recipes_per_day: int = Field(default=1, gt=0, le=20, strict=True)

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_recipe_count(cls, values: Any) -> Any:
        if isinstance(values, Mapping) and isinstance(values.get("recipes_per_day", 1), bool):
            raise ValueError("recipes_per_day must be a non-boolean positive integer")
        return values

    model_config = ConfigDict(extra="allow")


class RegionalConfig(BaseModel):
    """
    RU: Региональная конфигурация.
    EN: Regional configuration.
    """

    region: Region = Field(..., description="Target region")
    currency: Currency = Field(..., description="Local currency")
    language: str = Field(default="en", description="Language code")
    units_system: str = Field(default="metric", description="Units system (metric/imperial)")
    local_brands: List[str] = Field(default_factory=list, description="Preferred local brands")


class ShoplistConfig(BaseModel):
    """
    RU: Конфигурация списка покупок.
    EN: Shopping list configuration.
    """

    round_to_packages: bool = Field(default=True, description="Round quantities to package sizes")
    include_alternatives: bool = Field(default=True, description="Include product alternatives")
    group_by_category: bool = Field(default=True, description="Group items by food category")
    show_prices: bool = Field(default=True, description="Show estimated prices")


class RecipeGenerationConfig(BaseModel):
    """
    RU: Конфигурация генерации рецептов.
    EN: Recipe generation configuration.
    """

    max_ingredients: int = Field(default=8, ge=3, le=15, description="Max ingredients per recipe")
    cooking_time_max: int = Field(
        default=60, ge=15, le=180, description="Max cooking time in minutes"
    )
    difficulty_levels: List[str] = Field(
        default=["easy", "medium"], description="Allowed difficulty levels"
    )
    cuisine_styles: List[str] = Field(default_factory=list, description="Preferred cuisine styles")


class VIPConfig(BaseModel):
    """
    RU: Основная конфигурация VIP функций.
    EN: Main VIP features configuration.
    """

    micronutrient_goals: List[MicronutrientGoal] = Field(default_factory=list)
    auto_repair: AutoRepairConfig = Field(default_factory=AutoRepairConfig)
    regional: RegionalConfig = Field(
        default_factory=lambda: RegionalConfig(region=Region.US, currency=Currency.USD)
    )
    shoplist: ShoplistConfig = Field(default_factory=ShoplistConfig)
    recipe_generation: RecipeGenerationConfig = Field(default_factory=RecipeGenerationConfig)
    enabled_features: Set[str] = Field(default_factory=set, description="Enabled VIP features")


class VIPFeatureFlags(BaseModel):
    """
    RU: Флаги функций VIP.
    EN: VIP feature flags.
    """

    micronutrient_goals_enabled: bool = Field(default=False)
    auto_repair_enabled: bool = Field(default=False)
    regional_pricing_enabled: bool = Field(default=False)
    smart_shoplist_enabled: bool = Field(default=False)
    recipe_generation_enabled: bool = Field(default=False)
    i18n_enabled: bool = Field(default=False)


class WeeklyPlanRequest(BaseModel):
    """
    RU: Запрос на создание недельного плана питания.
    EN: Request for creating a weekly meal plan.
    """

    # Core profile fields required for admission.
    sex: Literal["female", "male"] = Field(..., description="Gender (male/female)")
    age: int = Field(..., ge=1, le=120, description="Age in years")
    height_cm: float = Field(..., gt=0, le=300, description="Height in centimeters")
    weight_kg: float = Field(..., gt=0, le=500, description="Weight in kilograms")
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = Field(
        ..., description="Activity level"
    )
    goal: Literal["loss", "maintain", "gain"] = Field(..., description="Nutrition goal")

    # Legacy/alternative fields for backward compatibility
    calories: Optional[int] = Field(None, ge=100, le=10000, description="Daily calories target")
    protein: Optional[float] = Field(None, ge=0, le=500, description="Daily protein target (g)")
    user_id: Optional[str] = Field(None, description="User identifier")
    preferences: dict = Field(default_factory=dict, description="User preferences")
    goals: dict = Field(default_factory=dict, description="Nutrition goals")
    constraints: dict = Field(default_factory=dict, description="Dietary constraints")

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_numeric_profile_fields(cls, values: Any) -> Any:
        """Reject booleans before Pydantic can coerce them to profile numbers."""

        if isinstance(values, Mapping) and any(
            isinstance(values.get(field), bool) for field in ("age", "height_cm", "weight_kg")
        ):
            raise ValueError("Boolean values are invalid for numeric profile fields")
        return values

    model_config = ConfigDict(extra="allow")  # Allow additional fields for flexibility


class WeeklyPlanResponse(BaseModel):
    """
    RU: Ответ с недельным планом питания.
    EN: Response with weekly meal plan.
    """

    status: str = Field(..., description="Response status")
    data: dict = Field(default_factory=dict, description="Weekly plan data")
    message: str = Field(default="", description="Additional message")


class ErrorResponse(BaseModel):
    """
    RU: Ответ об ошибке.
    EN: Error response.
    """

    status: str = Field(default="error", description="Response status")
    message: str = Field(..., description="Error message")
    data: dict = Field(default_factory=dict, description="Additional error data")
