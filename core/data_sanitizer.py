"""Data sanitizer for plate inputs used by premium endpoints.

Provides strict validation and normalization to prevent injection attacks,
invalid data, and ensure type safety.
"""

import html
import re
from typing import Any, Dict, List, Literal, Optional, TypedDict, cast

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator

# Constants for validation
MAX_STRING_LENGTH = 500
MAX_MEALS = 10
MAX_LAYOUT_ITEMS = 20
MAX_MICRO_NUTRIENTS = 100

# Regex to strip HTML/JS tags (defense in depth)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
JS_EVENT_PATTERN = re.compile(r"on\w+\s*=\s*['\"].*?['\"]|javascript:", re.IGNORECASE)


class MacrosDict(TypedDict):
    """Typed dictionary for macronutrient data with strict schema."""

    protein_g: int
    fat_g: int
    carbs_g: int
    fiber_g: int


def _sanitize_micros(
    v: Optional[Dict[str, float]], max_items: int = MAX_MICRO_NUTRIENTS
) -> Optional[Dict[str, float]]:
    """Sanitize and validate micronutrient dictionary.

    Args:
        v: Micronutrient dictionary (key=nutrient name, value=amount)
        max_items: Maximum number of micronutrients allowed

    Returns:
        Sanitized micronutrient dictionary with escaped keys and validated numeric values,
        or None if input is None

    Raises:
        ValueError: If validation fails (non-dict type, too many items, invalid keys/values)
    """
    if v is None:
        return None
    if not isinstance(v, dict):
        raise ValueError("Micros must be a dictionary")
    if len(v) > max_items:
        raise ValueError(f"Too many micronutrients (max {max_items})")

    sanitized = {}
    for key, value in v.items():
        if not isinstance(key, str):
            raise ValueError("Micronutrient keys must be strings")
        # Sanitize key name: strip HTML tags first
        clean_key = HTML_TAG_PATTERN.sub("", key)
        # Check length before escaping to avoid inflated length from html.escape
        if len(clean_key) > 100:
            raise ValueError("Micronutrient key too long")
        # Only after length check, apply HTML escaping
        clean_key = html.escape(clean_key, quote=True).strip()
        if not isinstance(value, (int, float)):
            raise ValueError(f"Micronutrient value for {key} must be numeric")
        if not (0 <= value <= 100000):  # Reasonable upper bound
            raise ValueError(f"Micronutrient value for {key} out of range")
        sanitized[clean_key] = float(value)
    return sanitized


class ValidationError(ValueError):
    """Custom validation error for plate data sanitization."""


class VisualShapeSchema(BaseModel):
    """Schema for visual layout items (plate sectors, bowls, markers)."""

    kind: Literal["plate_sector", "bowl", "marker"] = Field(
        ..., description="Type of visual element"
    )
    fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of plate (0.0-1.0)")
    label: str = Field(..., max_length=MAX_STRING_LENGTH, description="Display label")
    tooltip: str = Field(..., max_length=MAX_STRING_LENGTH, description="Tooltip text")

    @field_validator("label", "tooltip")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        """Strip HTML/JS tags and escape dangerous characters."""
        # Strip HTML tags
        v = HTML_TAG_PATTERN.sub("", v)
        # Strip JS event handlers
        v = JS_EVENT_PATTERN.sub("", v)
        # Enforce max length before escaping
        if len(v) > MAX_STRING_LENGTH:
            raise ValueError(f"String exceeds max length {MAX_STRING_LENGTH}")
        # HTML escape for safety
        v = html.escape(v, quote=True)
        return v.strip()


class MealSchema(BaseModel):
    """Schema for individual meal data."""

    title: str = Field(..., max_length=MAX_STRING_LENGTH, description="Meal title")
    kcal: int = Field(..., ge=0, le=5000, description="Calories (0-5000)")
    protein_g: int = Field(..., ge=0, le=500, description="Protein in grams (0-500)")
    fat_g: int = Field(..., ge=0, le=300, description="Fat in grams (0-300)")
    carbs_g: int = Field(..., ge=0, le=1000, description="Carbs in grams (0-1000)")
    fiber_g: Optional[int] = Field(None, ge=0, le=100, description="Fiber in grams (0-100)")
    micros: Optional[Dict[str, float]] = Field(None, description="Micronutrients (optional)")

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        """Strip HTML/JS tags and escape dangerous characters."""
        # Strip HTML tags
        v = HTML_TAG_PATTERN.sub("", v)
        # Strip JS event handlers
        v = JS_EVENT_PATTERN.sub("", v)
        # Enforce max length before escaping
        if len(v) > MAX_STRING_LENGTH:
            raise ValueError(f"Title exceeds max length {MAX_STRING_LENGTH}")
        # HTML escape
        v = html.escape(v, quote=True)
        return v.strip()

    @field_validator("micros")
    @classmethod
    def validate_micros(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """Validate micronutrient data."""
        return _sanitize_micros(v, MAX_MICRO_NUTRIENTS)


class PlateDataSchema(BaseModel):
    """Strict schema for plate data validation.

    Enforces required fields, types, ranges, and sanitization.
    """

    kcal: int = Field(..., ge=0, le=10000, description="Total calories (0-10000)")
    macros: MacrosDict = Field(
        ..., description="Macronutrients (protein_g, fat_g, carbs_g, fiber_g)"
    )
    portions: Dict[str, float] = Field(..., description="Portion sizes")
    layout: List[Dict[str, Any]] = Field(
        ..., max_length=MAX_LAYOUT_ITEMS, description="Visual layout items"
    )
    meals: List[Dict[str, Any]] = Field(..., max_length=MAX_MEALS, description="Meal breakdown")
    day_micros: Dict[str, float] = Field(default_factory=dict, description="Daily micronutrients")
    meals_per_day: int = Field(default=3, ge=1, le=10, description="Number of meals per day")

    @field_validator("macros")
    @classmethod
    def validate_macros(cls, v: Dict[str, int]) -> MacrosDict:
        """Validate macronutrient data against MacrosDict schema."""
        if not isinstance(v, dict):
            raise ValueError("Macros must be a dictionary")

        required_keys = {"protein_g", "fat_g", "carbs_g", "fiber_g"}
        if not required_keys.issubset(v.keys()):
            missing = required_keys - v.keys()
            raise ValueError(f"Missing required macro keys: {missing}")

        # Validate ranges
        ranges = {
            "protein_g": (0, 500),
            "fat_g": (0, 300),
            "carbs_g": (0, 1000),
            "fiber_g": (0, 100),
        }

        sanitized = {}
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Macro keys must be strings")
            # Only allow expected macro keys
            if key not in ranges:
                raise ValueError(
                    f"Unexpected macro key '{key}' - only {list(ranges.keys())} are allowed"
                )
            if not isinstance(value, int):
                raise ValueError(f"Macro value for {key} must be an integer")
            min_val, max_val = ranges[key]
            if not (min_val <= value <= max_val):
                raise ValueError(f"Macro {key}={value} out of range [{min_val}, {max_val}]")
            sanitized[key] = value

        return cast(MacrosDict, sanitized)

    @field_validator("portions")
    @classmethod
    def validate_portions(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate portion data."""
        if not isinstance(v, dict):
            raise ValueError("Portions must be a dictionary")

        expected_keys = {"protein_palm", "fat_thumbs", "carb_cups", "veg_cups"}
        if not expected_keys.issubset(v.keys()):
            missing = expected_keys - v.keys()
            raise ValueError(f"Missing required portion keys: {missing}")

        sanitized = {}
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Portion keys must be strings")
            # Only allow expected portion keys
            if key not in expected_keys:
                raise ValueError(
                    f"Unexpected portion key '{key}' - only {list(expected_keys)} are allowed"
                )
            if not isinstance(value, (int, float)):
                raise ValueError(f"Portion value for {key} must be numeric")
            if not (0 <= value <= 50):  # Reasonable upper bound
                raise ValueError(f"Portion {key}={value} out of range [0, 50]")
            sanitized[key] = float(value)

        return sanitized

    @field_validator("layout")
    @classmethod
    def validate_layout(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate layout items."""
        if not isinstance(v, list):
            raise ValueError("Layout must be a list")
        if len(v) > MAX_LAYOUT_ITEMS:
            raise ValueError(f"Too many layout items (max {MAX_LAYOUT_ITEMS})")

        validated = []
        for item in v:
            if not isinstance(item, dict):
                raise ValueError("Layout items must be dictionaries")
            # Validate using VisualShapeSchema
            validated_item = VisualShapeSchema.model_validate(item)
            validated.append(validated_item.model_dump())

        return validated

    @field_validator("meals")
    @classmethod
    def validate_meals(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate meal data."""
        if not isinstance(v, list):
            raise ValueError("Meals must be a list")
        if len(v) > MAX_MEALS:
            raise ValueError(f"Too many meals (max {MAX_MEALS})")

        validated = []
        for meal in v:
            if not isinstance(meal, dict):
                raise ValueError("Meal items must be dictionaries")
            # Validate using MealSchema
            validated_meal = MealSchema.model_validate(meal)
            validated.append(validated_meal.model_dump(exclude_none=True))

        return validated

    @field_validator("day_micros")
    @classmethod
    def validate_day_micros(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate daily micronutrient data."""
        result = _sanitize_micros(v, MAX_MICRO_NUTRIENTS)
        # day_micros is required (default_factory=dict), so result should not be None
        return result if result is not None else {}

    model_config = {
        "extra": "forbid",  # Reject unexpected keys
        "str_strip_whitespace": True,
    }


def sanity_filter_plate_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize plate data.

    Enforces strict schema validation, type checking, range validation,
    and HTML/JS injection prevention. Output is safe to use with
    parameterized queries (SQL safety depends on proper query construction).

    Args:
        data: Raw plate data dictionary from database or external source

    Returns:
        Sanitized and validated dictionary conforming to PlateDataSchema

    Raises:
        ValidationError: If data fails validation (invalid types, ranges,
                        injection attempts, or missing required fields)
    """
    if not isinstance(data, dict):
        raise ValidationError(f"Input must be a dictionary, got {type(data).__name__}")

    try:
        # Validate using Pydantic schema
        validated = PlateDataSchema.model_validate(data)
        # Return validated dict; SQL safety enforced by parameterized queries in data-access layer
        result = validated.model_dump(exclude_none=True)
        return result
    except PydanticValidationError as e:
        # Convert Pydantic validation errors to our custom ValidationError
        errors = e.errors()
        if any(err.get("loc", [None])[0] == "macros" for err in errors):
            message = "Missing required macro keys"
        elif any(err.get("loc", [None])[0] == "portions" for err in errors):
            message = "Missing required portion keys"
        else:
            message = f"Plate data validation failed: {str(e)}"
        raise ValidationError(message) from e
