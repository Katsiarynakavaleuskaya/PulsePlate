"""Data sanitization and validation utilities.

RU: Утилиты для санитации и валидации данных из внешних источников (БД, API).
EN: Utilities for sanitizing and validating data from external sources (DB, API).

Provides:
- Pydantic validators for normalizing types, clamping ranges, handling None/NaN
- Sanity filters for aggregated nutrition data
- Safe defaults for missing or invalid values
"""

from __future__ import annotations

import logging
import math
from typing import Any, Mapping

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from core.nutrition_constants import (
    CARBS_G_MAX,
    FAT_G_MAX,
    FIBER_MAX_G,
    FIBER_MIN_G,
    KCAL_MAX_SAFE,
    KCAL_MIN_SUPERVISED,
    PROTEIN_G_MAX,
)

NumericLike = int | float | str | None

logger = logging.getLogger(__name__)

# Reuse central thresholds to stay aligned with WHO/USDA data
KCAL_MIN = int(KCAL_MIN_SUPERVISED)
KCAL_MAX = int(KCAL_MAX_SAFE)
FIBER_G_MIN = int(FIBER_MIN_G)
FIBER_G_MAX = int(FIBER_MAX_G)

# Safe fallback defaults reused across sanitizers
NUTRITION_FALLBACK_DEFAULTS: dict[str, int] = {
    "kcal": 2000,
    "protein_g": 100,
    "fat_g": 70,
    "carbs_g": 250,
    "fiber_g": FIBER_G_MIN,
}

# Log message constants for numeric conversion warnings
INVALID_NUMERIC_MSG = "Invalid numeric value (NaN/inf): %s, defaulting to 0"
CONVERSION_FAILED_MSG = "Could not convert value '%s' to numeric: %s, defaulting to 0"


class NutritionSanitizationError(Exception):
    """Exception raised when nutrition data sanitization fails.

    RU: Исключение, возникающее при сбое санитизации данных о питании.
    EN: Exception raised when nutrition data sanitization fails.

    Attributes:
        original_exception: The original exception that caused the failure
        request_context: Optional context about the request/data being sanitized
        fallback_defaults: Dictionary with safe default values that can be used
    """

    def __init__(
        self,
        message: str,
        original_exception: Exception | None = None,
        request_context: dict[str, Any] | None = None,
        fallback_defaults: dict[str, int] | None = None,
    ) -> None:
        """Initialize NutritionSanitizationError.

        Args:
            message: Error message describing what went wrong
            original_exception: The original exception that caused the failure
            request_context: Optional context about the request/data being sanitized
            fallback_defaults: Dictionary with safe default values
        """
        super().__init__(message)
        self.original_exception = original_exception
        self.request_context = request_context or {}
        self.fallback_defaults = (
            fallback_defaults.copy() if fallback_defaults else NUTRITION_FALLBACK_DEFAULTS.copy()
        )


class NutritionData(BaseModel):
    """Sanitized nutrition data with validated ranges.

    RU: Санитизированные данные о питании с валидированными диапазонами.
    EN: Sanitized nutrition data with validated ranges.

    Default values are all zeros to clearly indicate "no data" state.
    """

    kcal: int = Field(default=0)
    protein_g: int = Field(default=0)
    fat_g: int = Field(default=0)
    carbs_g: int = Field(default=0)
    fiber_g: int = Field(default=0)

    @field_validator("kcal", "protein_g", "fat_g", "carbs_g", "fiber_g", mode="before")
    @classmethod
    def sanitize_numeric(cls, value: Any) -> int:  # type: ignore[override]  # type: ignore[ANN401]
        """Sanitize numeric values: handle None, NaN, inf, and coerce to int.

        RU: Санитизация числовых значений: обработка None, NaN, inf, приведение к int.
        EN: Sanitize numeric values: handle None, NaN, inf, and coerce to int.
        """
        if value is None:
            return 0

        try:
            float_val = float(value)
            if math.isnan(float_val) or math.isinf(float_val):
                logger.warning(INVALID_NUMERIC_MSG, value)
                return 0
            return int(round(float_val))
        except (ValueError, TypeError) as e:
            logger.warning(CONVERSION_FAILED_MSG, value, e)
            return 0

    @field_validator("kcal", "protein_g", "fat_g", "carbs_g", "fiber_g")
    @classmethod
    def clamp_to_safe_ranges(cls, value: int, info: ValidationInfo) -> int:
        """Clamp nutrition values to safe maximum ranges.

        RU: Ограничить значения нутриентов безопасными максимумами (минимум = 0).
        EN: Clamp nutrition values to safe maximum ranges (minimum = 0).

        Note: Minimum is always 0 to preserve "no data" state.
        """
        field_name = info.field_name
        if field_name is None:
            return value

        # Define max ranges for each field (min is always 0)
        max_ranges = {
            "kcal": KCAL_MAX,
            "protein_g": PROTEIN_G_MAX,
            "fat_g": FAT_G_MAX,
            "carbs_g": CARBS_G_MAX,
            "fiber_g": FIBER_G_MAX,
        }

        max_val = max_ranges.get(field_name, float("inf"))

        if value < 0:
            logger.warning("%s %s below zero, clamping to 0", field_name, value)
            return 0
        if value > max_val:
            logger.warning("%s %s above maximum %s, clamping", field_name, value, max_val)
            return int(max_val)
        return value

    def validate_macro_sum(self) -> bool:
        """Check if macro sum matches kcal (with tolerance).

        RU: Проверить, соответствует ли сумма макросов ккал (с допуском).
        EN: Check if macro sum matches kcal (with tolerance).

        Returns:
            True if macros sum is within 20% of kcal, False otherwise
        """
        computed_kcal = self.protein_g * 4 + self.fat_g * 9 + self.carbs_g * 4
        if computed_kcal == 0:
            return self.kcal == 0

        deviation = abs(computed_kcal - self.kcal) / max(1, self.kcal)
        if deviation > 0.2:
            logger.warning(
                "Macro sum (%s kcal) deviates >20%% from declared kcal (%s)",
                computed_kcal,
                self.kcal,
            )
            return False
        return True


def sanitize_nutrition_dict(data: dict[str, Any]) -> dict[str, int]:
    """Sanitize a nutrition dictionary using NutritionData validator.

    RU: Санитизировать словарь с данными о питании через NutritionData валидатор.
    EN: Sanitize a nutrition dictionary using NutritionData validator.

    Args:
        data: Raw nutrition data dictionary (may contain None, NaN, invalid types)

    Returns:
        Sanitized dictionary with validated integer values

    Raises:
        NutritionSanitizationError: If validation fails, with fallback defaults
            available in exception.fallback_defaults attribute
    """
    try:
        validated = NutritionData.model_validate(data)
        result = {
            "kcal": validated.kcal,
            "protein_g": validated.protein_g,
            "fat_g": validated.fat_g,
            "carbs_g": validated.carbs_g,
            "fiber_g": validated.fiber_g,
        }
        if not validated.validate_macro_sum():
            logger.info("Macro sum validation failed, returning sanitized data anyway")
        return result
    except Exception as e:
        fallback_defaults = NUTRITION_FALLBACK_DEFAULTS
        error_msg = f"Failed to sanitize nutrition data: {e}"
        logger.error(
            "Failed to sanitize nutrition data: %s, context: %s",
            e,
            {"data_keys": list(data.keys()) if isinstance(data, dict) else "not_a_dict"},
            exc_info=True,
        )
        raise NutritionSanitizationError(
            message=error_msg,
            original_exception=e,
            request_context={
                "data_keys": list(data.keys()) if isinstance(data, dict) else "not_a_dict"
            },
            fallback_defaults=fallback_defaults,
        ) from e


def sanitize_macros_dict(macros: dict[str, Any]) -> dict[str, int]:
    """Sanitize a macros-only dictionary (protein, fat, carbs, fiber).

    RU: Санитизировать словарь только с макросами (белок, жир, углеводы, клетчатка).
    EN: Sanitize a macros-only dictionary (protein, fat, carbs, fiber).

    Args:
        macros: Raw macros dictionary

    Returns:
        Sanitized dictionary with validated integer values

    Raises:
        NutritionSanitizationError: If validation fails, with fallback defaults
            available in exception.fallback_defaults attribute
    """
    full_data = {
        "kcal": macros.get("kcal", 0),  # Will be recalculated or validated
        "protein_g": macros.get("protein_g", 0),
        "fat_g": macros.get("fat_g", 0),
        "carbs_g": macros.get("carbs_g", 0),
        "fiber_g": macros.get("fiber_g", 0),
    }
    try:
        sanitized = sanitize_nutrition_dict(full_data)
    except NutritionSanitizationError as e:
        # Re-raise with updated context
        raise NutritionSanitizationError(
            message=f"Failed to sanitize macros dict: {e}",
            original_exception=e.original_exception,
            request_context={
                **e.request_context,
                "macros_keys": list(macros.keys()) if isinstance(macros, dict) else "not_a_dict",
            },
            fallback_defaults=e.fallback_defaults,
        ) from e
    # Return all essential macro keys
    result = {
        "protein_g": sanitized["protein_g"],
        "fat_g": sanitized["fat_g"],
        "carbs_g": sanitized["carbs_g"],
        "fiber_g": sanitized["fiber_g"],
    }
    # Include kcal if it was in original
    if "kcal" in macros:
        result["kcal"] = sanitized["kcal"]
    return result


class MealData(BaseModel):
    """Sanitized meal data with validated nutrition.

    RU: Санитизированные данные о приёме пищи с валидированным составом.
    EN: Sanitized meal data with validated nutrition.
    """

    title: str = Field(default="Unnamed Meal")
    kcal: int = Field(ge=0, le=4000, default=500)
    macros: dict[str, int] = Field(default_factory=dict)

    @field_validator("title", mode="before")
    @classmethod
    def sanitize_title(cls, value: object) -> str:
        """Ensure title is a non-empty string.

        RU: Убедиться, что заголовок — непустая строка.
        EN: Ensure title is a non-empty string.
        """
        if not value or not isinstance(value, str):
            return "Unnamed Meal"
        return str(value).strip() or "Unnamed Meal"

    @field_validator("macros", mode="before")
    @classmethod
    def sanitize_macros(cls, value: Mapping[str, Any] | object) -> dict[str, int]:
        """Sanitize macros dictionary.

        RU: Санитизировать словарь макросов.
        EN: Sanitize macros dictionary.
        """
        if not isinstance(value, dict):
            logger.warning("Invalid macros type: %s, using empty dict", type(value))
            return {}
        try:
            return sanitize_macros_dict(value)
        except NutritionSanitizationError as exc:
            logger.warning("Failed to sanitize macros: %s; using fallback defaults", exc)
            return exc.fallback_defaults.copy()


def sanitize_meal_list(meals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sanitize a list of meal dictionaries.

    RU: Санитизировать список словарей с приёмами пищи.
    EN: Sanitize a list of meal dictionaries.

    Args:
        meals: Raw meal data list

    Returns:
        List of sanitized meal dictionaries
    """
    if not isinstance(meals, list):
        logger.warning("Invalid meals type: %s, returning empty list", type(meals))
        return []

    sanitized = []
    for idx, meal in enumerate(meals):
        if not isinstance(meal, dict):
            logger.warning("Meal %s is not a dict: %s, skipping", idx, type(meal))
            continue

        try:
            # Sanitize individual meal fields while preserving original structure
            sanitized_meal = dict(meal)  # Copy original

            # Sanitize title
            if "title" in sanitized_meal and not isinstance(sanitized_meal["title"], str):
                sanitized_meal["title"] = str(sanitized_meal["title"])

            # Sanitize kcal
            if "kcal" in sanitized_meal:
                try:
                    sanitized_meal["kcal"] = int(round(float(sanitized_meal["kcal"])))
                except (ValueError, TypeError):
                    logger.debug("Invalid kcal in meal %s, keeping original", idx)

            # Sanitize macros dict if present
            if "macros" in sanitized_meal and isinstance(sanitized_meal["macros"], dict):
                try:
                    sanitized_meal["macros"] = sanitize_macros_dict(sanitized_meal["macros"])
                except NutritionSanitizationError as e:
                    logger.warning(
                        "Failed to sanitize macros in meal %s: %s, using fallback defaults",
                        idx,
                        e,
                    )
                    sanitized_meal["macros"] = e.fallback_defaults.copy()

            sanitized.append(sanitized_meal)
        except Exception as e:
            logger.warning("Failed to sanitize meal %s: %s, keeping original", idx, e)
            sanitized.append(meal)  # Keep original on error

    return sanitized


def sanity_filter_plate_data(plate_data: dict[str, Any]) -> dict[str, Any]:
    """Apply sanity filter to plate data before using in API response.

    RU: Применить фильтр здравого смысла к данным тарелки перед использованием в API.
    EN: Apply sanity filter to plate data before using in API response.

    Args:
        plate_data: Raw plate data dictionary

    Returns:
        Sanitized plate data dictionary with validated values
    """
    try:
        # Sanitize kcal
        kcal = plate_data.get("kcal", NUTRITION_FALLBACK_DEFAULTS["kcal"])
        try:
            kcal = int(round(float(kcal)))
            kcal = max(KCAL_MIN, min(KCAL_MAX, kcal))
        except (ValueError, TypeError):
            logger.warning(
                "Invalid kcal value: %s, defaulting to %s",
                kcal,
                NUTRITION_FALLBACK_DEFAULTS["kcal"],
            )
            kcal = NUTRITION_FALLBACK_DEFAULTS["kcal"]

        # Sanitize macros
        macros = plate_data.get("macros", {})
        if isinstance(macros, dict):
            try:
                macros = sanitize_macros_dict(macros)
            except NutritionSanitizationError as e:
                logger.error(
                    "Failed to sanitize macros in plate data: %s, using fallback defaults",
                    e,
                    exc_info=True,
                )
                macros = e.fallback_defaults.copy()
        else:
            logger.warning("Invalid macros type: %s, using defaults", type(macros))
            macros = {k: v for k, v in NUTRITION_FALLBACK_DEFAULTS.items() if k != "kcal"}

        # Sanitize meals
        meals = plate_data.get("meals", [])
        meals = sanitize_meal_list(meals)

        # Keep other fields as-is (portions, layout, micros, etc.)
        # Preserve all original fields except those we sanitized
        result = dict(plate_data)
        result.update(
            {
                "kcal": kcal,
                "macros": macros,
                "meals": meals,
            }
        )
        # Ensure required fields have defaults
        result.setdefault("portions", {})
        result.setdefault("layout", [])
        result.setdefault("meals_per_day", 3)
        return result
    except Exception as e:
        logger.error("Failed to apply sanity filter to plate data: %s", e, exc_info=True)
        # Return minimal safe defaults
        return {
            "kcal": NUTRITION_FALLBACK_DEFAULTS["kcal"],
            "macros": {k: v for k, v in NUTRITION_FALLBACK_DEFAULTS.items() if k != "kcal"},
            "meals": [],
            "portions": {},
            "layout": [],
            "meals_per_day": 3,
        }
