# -*- coding: utf-8 -*-
"""
VIP Schemas

RU: Схемы для VIP функций - микронутриентные цели, авто-ремонт, региональные настройки.
EN: Schemas for VIP features - micronutrient goals, auto-repair, regional settings.
"""

from enum import Enum
from typing import List, Literal, Optional, Set

from pydantic import BaseModel, Field, model_validator


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

    # Core required fields for full functionality
    sex: Optional[Literal["female", "male"]] = Field(None, description="Gender (male/female)")
    age: Optional[int] = Field(None, ge=1, le=120, description="Age in years")
    height_cm: Optional[float] = Field(None, gt=0, le=300, description="Height in centimeters")
    weight_kg: Optional[float] = Field(None, gt=0, le=500, description="Weight in kilograms")
    activity: Optional[Literal["sedentary", "light", "moderate", "active", "very_active"]] = Field(
        None, description="Activity level"
    )
    goal: Optional[Literal["loss", "maintain", "gain"]] = Field(None, description="Nutrition goal")

    # Legacy/alternative fields for backward compatibility
    calories: Optional[int] = Field(None, ge=100, le=10000, description="Daily calories target")
    protein: Optional[float] = Field(None, ge=0, le=500, description="Daily protein target (g)")
    user_id: Optional[str] = Field(None, description="User identifier")
    preferences: dict = Field(default_factory=dict, description="User preferences")
    goals: dict = Field(default_factory=dict, description="Nutrition goals")
    constraints: dict = Field(default_factory=dict, description="Dietary constraints")

    @model_validator(mode="after")
    def validate_required_fields(self):
        """Validate that either all core fields are present OR at least one
        alternative field is provided."""
        # Core required fields
        core_fields = ["sex", "age", "height_cm", "weight_kg", "activity", "goal"]
        # Alternative fields
        alt_fields = ["calories", "protein"]

        # Check if all core fields are present (not None)
        core_present = all(getattr(self, field) is not None for field in core_fields)

        # Check if at least one alternative field is present
        alt_present = any(getattr(self, field) is not None for field in alt_fields)

        if not core_present and not alt_present:
            raise ValueError(
                "Either all core fields (sex, age, height_cm, weight_kg, activity, goal) "
                "must be provided, or at least one alternative field (calories or protein) "
                "must be provided."
            )

        return self

    model_config = {"extra": "allow"}  # Allow additional fields for flexibility


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
