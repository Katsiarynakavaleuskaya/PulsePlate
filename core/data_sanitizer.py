"""Data sanitizer for plate inputs used by premium endpoints.

Provides strict validation and normalization to prevent injection attacks,
invalid data, and ensure type safety.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Protocol, Set, cast

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator
from typing_extensions import TypedDict


class _NH3Protocol(Protocol):
    """Protocol for nh3 module interface (type-safe soft import)."""

    def clean(
        self,
        html: str,
        tags: Optional[Set[str]] = None,
        attributes: Optional[Dict[str, Set[str]]] = None,
    ) -> str:  # pragma: no cover
        ...


# nh3 is a runtime requirement for production (sanitization/security).
# We use lazy import (import at call time) instead of module-level import
# to avoid caching None in pytest-xdist workers or hot-reload scenarios.


class MissingOptionalDependencyError(RuntimeError):
    """Raised when an optional runtime dependency is missing."""

    def __init__(self, dependency: str, message: str) -> None:
        super().__init__(message)
        self.dependency = dependency


# Constants for validation
MAX_STRING_LENGTH = 500
MAX_MEALS = 10
MAX_LAYOUT_ITEMS = 20
MAX_MICRO_NUTRIENTS = 100

# nh3 configuration: Allows basic formatting tags for rich text display
# nh3 strips all dangerous HTML/JS/XSS (event handlers, javascript: URIs, data: URIs, etc.)
# Output is safe for HTML context; additional escaping should be done at render time if needed
NH3_ALLOWED_TAGS = {"b", "i", "em", "strong", "u", "br", "p", "span"}
NH3_ALLOWED_ATTRS: Dict[str, Set[str]] = (
    {}
)  # No attributes allowed at all (no href, src, onclick, etc.)


def _require_nh3() -> _NH3Protocol:
    """Ensure nh3 dependency is available for sanitization.

    Uses lazy import (import at runtime) to avoid issues with pytest-xdist workers,
    hot-reload, and cached module-level imports.

    Returns:
        The nh3 module with type-safe interface (guaranteed after runtime check)

    Raises:
        MissingOptionalDependencyError: If nh3 is not installed
    """
    try:
        import nh3  # Runtime import - always fresh, no caching issues

        return cast(_NH3Protocol, nh3)
    except ModuleNotFoundError as e:
        raise MissingOptionalDependencyError(
            "nh3",
            (
                "Optional dependency 'nh3' is required for plate data sanitization. "
                "Install it with: python -m pip install nh3"
            ),
        ) from e


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
        Sanitized micronutrient dictionary with nh3-cleaned keys and validated numeric values,
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

    nh3 = _require_nh3()  # Ensure nh3 is available before sanitization
    sanitized = {}
    for key, value in v.items():
        if not isinstance(key, str):
            raise ValueError("Micronutrient keys must be strings")
        # Sanitize key name using nh3 (strips all HTML/JS, decodes entities, prevents XSS)
        # For micronutrient keys, we don't want any HTML tags, so use empty tag set
        clean_key = nh3.clean(key, tags=set(), attributes={}).strip()
        # Validate length on the final sanitized key
        if len(clean_key) > 100:
            raise ValueError("Micronutrient key too long")

        if not isinstance(value, (int, float)):
            # Use nh3.clean for error messages too to prevent XSS in error output
            safe_key = nh3.clean(str(key), tags=set(), attributes={})
            raise ValueError(f"Micronutrient value for '{safe_key}' must be numeric")
        if not (0 <= value <= 100000):  # Reasonable upper bound
            safe_key = nh3.clean(str(key), tags=set(), attributes={})
            raise ValueError(f"Micronutrient value for '{safe_key}' out of range")
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
        """Sanitize using nh3 (strips dangerous HTML/JS/XSS, allows safe formatting tags).

        nh3 handles all sanitization - removes XSS vectors while preserving allowed formatting.
        Output is safe for HTML rendering. Additional context-specific escaping (e.g., for
        attributes or plain-text contexts) should be done at render time if needed.
        """
        nh3 = _require_nh3()  # Ensure nh3 is available before sanitization
        # Use nh3 with strict allowlist - only basic formatting tags, no attributes
        v = nh3.clean(v, tags=NH3_ALLOWED_TAGS, attributes=NH3_ALLOWED_ATTRS)
        # Enforce max length on the sanitized output
        if len(v) > MAX_STRING_LENGTH:
            raise ValueError(f"String exceeds max length {MAX_STRING_LENGTH}")
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
        """Sanitize using nh3 (strips dangerous HTML/JS/XSS, allows safe formatting tags).

        nh3 handles all sanitization - removes XSS vectors while preserving allowed formatting.
        Output is safe for HTML rendering. Additional context-specific escaping (e.g., for
        attributes or plain-text contexts) should be done at render time if needed.
        """
        nh3 = _require_nh3()  # Ensure nh3 is available before sanitization
        # Use nh3 with strict allowlist - only basic formatting tags, no attributes
        v = nh3.clean(v, tags=NH3_ALLOWED_TAGS, attributes=NH3_ALLOWED_ATTRS)
        # Enforce max length on the sanitized output
        if len(v) > MAX_STRING_LENGTH:
            raise ValueError(f"Title exceeds max length {MAX_STRING_LENGTH}")
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
            # Allow integer-equivalent floats (e.g., 50.0) from JSON deserialization
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            elif not isinstance(value, int):
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
    def validate_day_micros(cls, v: Optional[Dict[str, float]]) -> Dict[str, float]:
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
        # TODO: Localize error messages using t(lang, "translation_key") for i18n support
        #       (English, Russian, Spanish). Currently hard-coded English strings.
        #       Consider adding lang parameter or translating at HTTP layer.
        errors = e.errors()
        if any(err.get("loc", [None])[0] == "macros" for err in errors):
            message = "Missing required macro keys"
        elif any(err.get("loc", [None])[0] == "portions" for err in errors):
            message = "Missing required portion keys"
        else:
            message = f"Plate data validation failed: {str(e)}"
        raise ValidationError(message) from e
