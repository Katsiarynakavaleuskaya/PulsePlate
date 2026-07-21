"""Canonical application service for PRO nutrition Plate generation."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from numbers import Number
from typing import Any, NoReturn, cast

from fastapi import HTTPException, status

import core.bmr as nutrition_bmr
import core.plate as nutrition_plate
import core.recommendations as nutrition_recommendations
import core.targets as nutrition_targets
from app.http_error_details import (
    ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
    INVALID_PREMIUM_PLATE_INPUT_DETAIL,
)
from app.schemas.premium_contracts import (
    PlateRequest,
    PlateResponse,
    VisualShape,
    WHOTargetsRequest,
    WHOTargetsResponse,
)
from app.services import recipe_store
from app.services.food_store import get_food
from app.services.pro_nutrition_targets import (
    TargetsBuilder,
    generate_who_targets_response,
    validate_targets_safety_warnings,
)
from app.utils.feature_flags import _is_truthy
from core.data_sanitizer import MissingOptionalDependencyError, sanity_filter_plate_data
from core.nutrition_utils import (
    alias_micros,
    clamp_daily_kcal,
)
from core.targets import FIBER_MIN_G
from core.utils import get_activity_factor

logger = logging.getLogger(__name__)

PLATE_FEATURE_UNAVAILABLE_DETAIL = "Enhanced plate feature not available"
_FALLBACK_KCAL_MAX = 2400
_SAFE_DEFAULT_KCAL = 1200
_MAX_MICRONUTRIENT_VALUE = 100000.0


class _InvalidPlateMicronutrientOutputError(RuntimeError):
    """A Plate dependency returned malformed micronutrient output."""


class _NonFinitePlateDependencyOutputError(_InvalidPlateMicronutrientOutputError):
    """A Plate dependency returned a numeric value unsafe for JSON output."""


class _InvalidPlateCalculationOutputError(RuntimeError):
    """A BMR/TDEE dependency returned malformed calculation output."""


def _validate_calculation_mapping(value: Any, *, required_key: str | None = None) -> None:
    """Require a non-empty finite numeric calculation mapping."""

    if not isinstance(value, dict) or not value:
        raise _InvalidPlateCalculationOutputError(
            "Plate calculation dependency returned malformed output"
        )
    if required_key is not None and required_key not in value:
        raise _InvalidPlateCalculationOutputError(
            "Plate calculation dependency omitted required output"
        )
    for key, raw_value in value.items():
        if (
            not isinstance(key, str)
            or isinstance(raw_value, (bool, str))
            or not isinstance(raw_value, Number)
        ):
            raise _InvalidPlateCalculationOutputError(
                "Plate calculation dependency returned malformed output"
            )
        try:
            numeric_value = float(cast(Any, raw_value))
        except (TypeError, ValueError, OverflowError):
            raise _InvalidPlateCalculationOutputError(
                "Plate calculation dependency returned malformed output"
            ) from None
        if not math.isfinite(numeric_value):
            raise _InvalidPlateCalculationOutputError(
                "Plate calculation dependency returned non-finite output"
            )


def _ensure_finite_dependency_output(value: Any) -> None:
    """Reject non-finite numeric objects without interpreting arbitrary text."""

    if isinstance(value, bool):
        return
    if isinstance(value, str):
        return
    if isinstance(value, Number):
        try:
            is_finite = math.isfinite(float(cast(Any, value)))
        except (TypeError, ValueError, OverflowError):
            is_finite = False
        if not is_finite:
            raise _NonFinitePlateDependencyOutputError(
                "Plate dependency returned non-finite numeric output"
            )
        return
    if isinstance(value, dict):
        for nested_value in value.values():
            _ensure_finite_dependency_output(nested_value)
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for nested_value in value:
            _ensure_finite_dependency_output(nested_value)


def _ensure_finite_numeric_value(value: Any) -> None:
    """Reject non-finite values where the response contract expects a number."""

    if isinstance(value, str):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError, OverflowError):
            return
        if not math.isfinite(numeric_value):
            raise _NonFinitePlateDependencyOutputError(
                "Plate dependency returned non-finite numeric output"
            )
        return
    _ensure_finite_dependency_output(value)


def _ensure_finite_numeric_mapping(value: Any) -> None:
    """Validate values in a schema-defined numeric mapping."""

    if not isinstance(value, dict):
        return
    for nested_value in value.values():
        _ensure_finite_numeric_value(nested_value)


def _validated_micronutrient_mapping(value: Any) -> dict[str, float]:
    """Return finite canonical-range micronutrients or fail closed."""

    if not isinstance(value, dict):
        raise _InvalidPlateMicronutrientOutputError(
            "Plate dependency returned malformed micronutrient output"
        )

    validated: dict[str, float] = {}
    for nutrient_key, raw_amount in value.items():
        if not isinstance(nutrient_key, str) or isinstance(raw_amount, (bool, str)):
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned malformed micronutrient output"
            )
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError, OverflowError):
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned malformed micronutrient output"
            ) from None
        if not math.isfinite(amount):
            raise _NonFinitePlateDependencyOutputError(
                "Plate dependency returned non-finite numeric output"
            )
        if not 0.0 <= amount <= _MAX_MICRONUTRIENT_VALUE:
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned out-of-range micronutrient output"
            )
        validated[nutrient_key] = amount
    return validated


def _ensure_finite_plate_response_output(value: Any) -> None:
    """Validate raw Plate output using its response-bound numeric paths."""

    _ensure_finite_dependency_output(value)
    if not isinstance(value, dict):
        return

    for key in ("kcal", "meals_per_day"):
        if key in value:
            _ensure_finite_numeric_value(value[key])
    for key in ("macros", "portions", "day_micros"):
        _ensure_finite_numeric_mapping(value.get(key))

    layout = value.get("layout")
    if isinstance(layout, list):
        for item in layout:
            if isinstance(item, dict) and "fraction" in item:
                _ensure_finite_numeric_value(item["fraction"])

    meals = value.get("meals")
    if isinstance(meals, list):
        for meal in meals:
            if not isinstance(meal, dict):
                continue
            for key in ("kcal", "protein_g", "fat_g", "carbs_g", "fiber_g"):
                if key in meal:
                    _ensure_finite_numeric_value(meal[key])
            _ensure_finite_numeric_mapping(meal.get("micros"))


PlateGenerator = Callable[..., dict[str, Any]]
BMRCalculator = Callable[..., dict[str, float]]
TDEECalculator = Callable[..., dict[str, float]]
DayMicrosAggregator = Callable[
    [list[dict[str, Any]]],
    Awaitable[dict[str, float] | None] | dict[str, float] | None,
]
TargetsResponseFactory = Callable[..., WHOTargetsResponse]


@dataclass(frozen=True)
class PlateServiceDependencies:
    """Explicit per-call dependency set for deterministic Plate execution.

    Production callers omit this argument and receive direct canonical ``core``
    dependencies resolved at call time. Tests may pass an immutable instance;
    there is no process-global override registry or import-time callable cache.
    """

    make_plate: PlateGenerator | None
    calculate_all_bmr: BMRCalculator | None
    calculate_all_tdee: TDEECalculator | None
    build_nutrition_targets: TargetsBuilder | None
    aggregate_day_micronutrients: DayMicrosAggregator


def _default_dependencies() -> PlateServiceDependencies:
    """Resolve direct canonical dependencies without caching mutable callables."""

    return PlateServiceDependencies(
        make_plate=cast(PlateGenerator, nutrition_plate.make_plate),
        calculate_all_bmr=cast(BMRCalculator, nutrition_bmr.calculate_all_bmr),
        calculate_all_tdee=cast(TDEECalculator, nutrition_bmr.calculate_all_tdee),
        build_nutrition_targets=cast(
            TargetsBuilder,
            nutrition_recommendations.build_nutrition_targets,
        ),
        aggregate_day_micronutrients=_aggregate_day_micronutrients,
    )


DB_TO_ALIAS_NUTRIENT_MAP: dict[str, str] = {
    "Fe_mg": "iron_mg",
    "Ca_mg": "calcium_mg",
    "Mg_mg": "magnesium_mg",
    "K_mg": "potassium_mg",
    "VitD_IU": "vitamin_d_iu",
    "B12_ug": "b12_ug",
    "Folate_ug": "folate_ug",
    "Iodine_ug": "iodine_ug",
}


def _convert_db_nutrients_to_alias_format(
    db_nutrients: dict[str, float],
) -> dict[str, float]:
    """Convert persisted nutrient names to the stable response aliases."""

    alias_nutrients: dict[str, float] = {}
    for db_key, value in db_nutrients.items():
        alias_key = DB_TO_ALIAS_NUTRIENT_MAP.get(db_key)
        if value is None or isinstance(value, bool):
            logger.warning(
                "Invalid nutrient value for key %s: type=%s",
                alias_key or db_key,
                type(value).__name__,
            )
            raise ValueError(f"Nutrient value for key '{db_key}' must be numeric")
        try:
            converted_value = float(value)
        except OverflowError:
            raise _NonFinitePlateDependencyOutputError(
                "Plate dependency returned non-finite numeric output"
            ) from None
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Invalid nutrient value for key %s: type=%s",
                alias_key or db_key,
                type(value).__name__,
            )
            raise ValueError(f"Nutrient value for key '{db_key}' must be numeric") from exc
        _ensure_finite_dependency_output(converted_value)
        alias_nutrients[alias_key or db_key] = converted_value
    return alias_nutrients


async def _aggregate_meal_micronutrients(
    ingredients: list[dict[str, Any]],
    meal_title: str = "",
) -> dict[str, float]:
    """Aggregate available persisted micronutrients for one meal."""

    meal_micros: dict[str, float] = {}
    default_per_g = 100.0
    db_micro_keys = tuple(DB_TO_ALIAS_NUTRIENT_MAP)

    for ingredient in ingredients:
        food_id = ingredient.get("food_id")
        grams_raw = ingredient.get("grams")
        if not food_id or not isinstance(food_id, str):
            logger.debug(
                "Skipping ingredient with missing food_id in meal %r",
                meal_title,
            )
            continue

        if isinstance(grams_raw, bool):
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned malformed ingredient grams"
            )
        try:
            grams = float(grams_raw) if grams_raw is not None else 0.0
        except OverflowError:
            raise _NonFinitePlateDependencyOutputError(
                "Plate dependency returned non-finite numeric output"
            ) from None
        except (TypeError, ValueError):
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned malformed ingredient grams"
            ) from None
        _ensure_finite_dependency_output(grams)
        if grams == 0:
            continue
        if grams < 0:
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned negative ingredient grams"
            )

        food = await asyncio.to_thread(get_food, food_id)
        if not food:
            logger.warning(
                "Food %r not found while aggregating meal %r",
                food_id,
                meal_title,
            )
            continue

        per_g_raw = food.get("per_g")
        if isinstance(per_g_raw, bool):
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned malformed serving basis"
            )
        try:
            per_g = float(per_g_raw) if per_g_raw is not None else default_per_g
        except OverflowError:
            raise _NonFinitePlateDependencyOutputError(
                "Plate dependency returned non-finite numeric output"
            ) from None
        except (TypeError, ValueError):
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned malformed serving basis"
            ) from None
        _ensure_finite_dependency_output(per_g)
        if per_g <= 0:
            raise _InvalidPlateMicronutrientOutputError(
                "Plate dependency returned non-positive serving basis"
            )
        ratio = grams / per_g

        for db_key in db_micro_keys:
            if db_key not in food or food[db_key] is None:
                continue
            nutrient_value = food[db_key]
            if isinstance(nutrient_value, bool):
                raise _InvalidPlateMicronutrientOutputError(
                    "Plate dependency returned malformed micronutrient output"
                )
            try:
                numeric_value = float(nutrient_value)
            except OverflowError:
                raise _NonFinitePlateDependencyOutputError(
                    "Plate dependency returned non-finite numeric output"
                ) from None
            except (TypeError, ValueError):
                raise _InvalidPlateMicronutrientOutputError(
                    "Plate dependency returned malformed micronutrient output"
                ) from None
            _ensure_finite_dependency_output(numeric_value)
            alias_key = DB_TO_ALIAS_NUTRIENT_MAP[db_key]
            aggregate_value = meal_micros.get(alias_key, 0.0) + numeric_value * ratio
            _ensure_finite_dependency_output(aggregate_value)
            meal_micros[alias_key] = aggregate_value

    return _validated_micronutrient_mapping(meal_micros)


def _get_recipe_ingredients_for_meal(meal_title: str) -> list[dict[str, Any]]:
    """Return normalized recipe ingredients when the generated meal has none."""

    recipes = recipe_store.search_recipes(meal_title, limit=1)
    if not recipes:
        return []
    recipe_id = recipes[0].get("recipe_id")
    if not recipe_id:
        return []
    recipe = recipe_store.get_recipe(recipe_id)
    if not recipe:
        return []
    ingredients_json = recipe.get("ingredients_json")
    if not ingredients_json:
        return []
    try:
        ingredients = json.loads(ingredients_json)
    except (json.JSONDecodeError, TypeError):
        raise _InvalidPlateMicronutrientOutputError(
            "Recipe provider returned malformed ingredients"
        ) from None
    if not isinstance(ingredients, list):
        raise _InvalidPlateMicronutrientOutputError(
            "Recipe provider returned malformed ingredients"
        )

    normalized: list[dict[str, Any]] = []
    for ingredient in ingredients:
        if isinstance(ingredient, dict):
            food_id = ingredient.get("food_id") or ingredient.get("id")
            grams = ingredient.get("grams")
            if not food_id or grams is None:
                raise _InvalidPlateMicronutrientOutputError(
                    "Recipe provider returned malformed ingredient"
                )
            normalized.append({"food_id": str(food_id), "grams": grams})
        elif isinstance(ingredient, (list, tuple)) and len(ingredient) >= 2:
            normalized.append({"food_id": str(ingredient[0]), "grams": ingredient[1]})
        else:
            raise _InvalidPlateMicronutrientOutputError(
                "Recipe provider returned malformed ingredient"
            )
    return normalized


async def _aggregate_day_micronutrients(
    meals: list[dict[str, Any]],
) -> dict[str, float]:
    """Aggregate micronutrients for all generated meals."""

    day_micros: dict[str, float] = {}
    for meal in meals:
        meal_title = str(meal.get("title", ""))
        existing = meal.get("micros")
        if isinstance(existing, dict) and existing:
            meal_micros: dict[str, Any] = dict(existing)
        else:
            ingredients = meal.get("ingredients") or []
            if not isinstance(ingredients, list):
                ingredients = []
            if not ingredients:
                ingredients = await asyncio.to_thread(
                    _get_recipe_ingredients_for_meal,
                    meal_title,
                )
            raw_micros = await _aggregate_meal_micronutrients(
                cast(list[dict[str, Any]], ingredients),
                meal_title=meal_title,
            )
            meal_micros = alias_micros(dict(raw_micros))
            meal["micros"] = dict(meal_micros)

        meal_micros = _validated_micronutrient_mapping(meal_micros)
        for nutrient_key, amount in meal_micros.items():
            if isinstance(amount, (int, float)):
                aggregate_value = day_micros.get(nutrient_key, 0.0) + float(amount)
                _ensure_finite_dependency_output(aggregate_value)
                day_micros[nutrient_key] = aggregate_value

    aliased = alias_micros(dict(day_micros))
    return _validated_micronutrient_mapping(aliased)


def _macros_to_kcal(macros: dict[str, Any]) -> int | None:
    """Convert macro grams into total kcal."""

    try:
        protein = float(macros.get("protein_g", 0))
        fat = float(macros.get("fat_g", 0))
        carbs = float(macros.get("carbs_g", 0))
        return int(round(protein * 4 + fat * 9 + carbs * 4))
    except (TypeError, ValueError, OverflowError):
        return None


def calculate_heuristic_macros(
    final_kcal: int,
    weight_kg: float,
) -> tuple[int, int, int]:
    """Calculate the established bounded macro fallback."""

    final_kcal = max(final_kcal, _SAFE_DEFAULT_KCAL)
    protein_raw = 1.6 * weight_kg
    fat_raw = 0.9 * weight_kg
    protein_kcal = protein_raw * 4
    fat_kcal = fat_raw * 9

    if protein_kcal + fat_kcal + 4 > final_kcal:
        available_kcal = final_kcal - 4
        if available_kcal > 0 and protein_kcal + fat_kcal > 0:
            scale = max(available_kcal / (protein_kcal + fat_kcal), 0.0)
            protein_raw *= scale
            fat_raw *= scale
        else:
            protein_raw = 0.0
            fat_raw = 0.0

    protein_g = max(0, int(round(protein_raw)))
    fat_g = max(0, int(round(fat_raw)))
    carbs_g = max(
        1,
        int(round((final_kcal - protein_g * 4 - fat_g * 9) / 4)),
    )
    return protein_g, fat_g, carbs_g


def _build_user_profile(req: PlateRequest) -> nutrition_targets.UserProfile:
    return nutrition_targets.UserProfile(
        sex=req.sex,
        age=req.age,
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        activity=req.activity,
        goal=req.goal,
        deficit_pct=req.deficit_pct,
        surplus_pct=req.surplus_pct,
        bodyfat=req.bodyfat,
        diet_flags=set(req.diet_flags or []),
        life_stage=req.life_stage,
    )


def build_fallback_plate(
    req: PlateRequest,
    _legacy_candidates: list[Any] | None = None,
    *,
    targets_builder: TargetsBuilder | None = None,
) -> PlateResponse:
    """Build the established bounded response when Plate backends are unavailable."""

    base_bmr = nutrition_bmr.FALLBACK_BMR_KCAL_PER_KG_PER_DAY * req.weight_kg
    tdee_value = int(base_bmr * get_activity_factor(req.activity))
    if req.goal == "loss":
        pct = req.deficit_pct if req.deficit_pct is not None else 15.0
        target_kcal = max(
            _SAFE_DEFAULT_KCAL,
            int(tdee_value * (1.0 - pct / 100.0)),
        )
    elif req.goal == "gain":
        pct = req.surplus_pct if req.surplus_pct is not None else 10.0
        target_kcal = max(
            _SAFE_DEFAULT_KCAL,
            int(tdee_value * (1.0 + pct / 100.0)),
        )
    else:
        target_kcal = max(_SAFE_DEFAULT_KCAL, tdee_value)

    protein_g = int(round(1.6 * req.weight_kg))
    fat_g = int(round(0.9 * req.weight_kg))
    used_kcal = protein_g * 4 + fat_g * 9
    carbs_g = max(0, int(round((target_kcal - used_kcal) / 4)))
    fiber_g = 25
    targets_used = False

    if callable(targets_builder):
        try:
            targets = targets_builder(_build_user_profile(req))
            validate_targets_safety_warnings(targets)
            target_macros = targets.macros
            resolved_target_kcal = int(targets.kcal_daily)
            resolved_protein_g = int(target_macros.protein_g)
            resolved_fat_g = int(target_macros.fat_g)
            resolved_carbs_g = int(target_macros.carbs_g)
            try:
                resolved_fiber_g = int(target_macros.fiber_g)
            except (TypeError, ValueError, OverflowError):
                logger.warning("Invalid fallback target fiber; using canonical minimum")
                resolved_fiber_g = int(round(FIBER_MIN_G))

            if _SAFE_DEFAULT_KCAL <= resolved_target_kcal <= _FALLBACK_KCAL_MAX:
                target_kcal = resolved_target_kcal
                protein_g = resolved_protein_g
                fat_g = resolved_fat_g
                carbs_g = resolved_carbs_g
                fiber_g = resolved_fiber_g
                targets_used = True
            else:
                logger.warning(
                    "Canonical target kcal %s is outside Plate fallback bounds; "
                    "using the bounded heuristic",
                    resolved_target_kcal,
                )
        except (ValueError, ImportError):
            logger.warning(
                "Plate target alignment unavailable during fallback",
                exc_info=True,
            )

    target_kcal = max(
        _SAFE_DEFAULT_KCAL,
        min(target_kcal, _FALLBACK_KCAL_MAX),
    )
    if not targets_used:
        used_kcal = protein_g * 4 + fat_g * 9
        carbs_g = max(0, int(round((target_kcal - used_kcal) / 4)))

    portions = {
        "protein_palm": round(protein_g / 25.0, 1),
        "carb_cups": round(carbs_g / 40.0, 1),
        "veg_cups": 3.0,
        "fat_thumbs": round(fat_g / 14.0, 1),
    }
    layout = [
        VisualShape(
            kind="plate_sector",
            fraction=0.35,
            label="Protein",
            tooltip="Lean protein",
        ),
        VisualShape(
            kind="plate_sector",
            fraction=0.40,
            label="Carbs",
            tooltip="Whole grains",
        ),
        VisualShape(
            kind="plate_sector",
            fraction=0.20,
            label="Vegetables",
            tooltip="Non-starchy veg",
        ),
        VisualShape(
            kind="plate_sector",
            fraction=0.05,
            label="Fats",
            tooltip="Healthy fats",
        ),
        VisualShape(
            kind="bowl",
            fraction=1.0,
            label="Grain cup",
            tooltip="1 cup",
        ),
        VisualShape(
            kind="bowl",
            fraction=1.0,
            label="Veg cup",
            tooltip="1 cup",
        ),
    ]
    meals = [
        {
            "title": "Breakfast",
            "kcal": int(target_kcal * 0.3),
            "macros": {
                "protein_g": int(protein_g * 0.3),
                "carbs_g": int(carbs_g * 0.3),
                "fat_g": int(fat_g * 0.3),
            },
        },
        {
            "title": "Lunch",
            "kcal": int(target_kcal * 0.4),
            "macros": {
                "protein_g": int(protein_g * 0.4),
                "carbs_g": int(carbs_g * 0.4),
                "fat_g": int(fat_g * 0.4),
            },
        },
        {
            "title": "Dinner",
            "kcal": int(target_kcal * 0.3),
            "macros": {
                "protein_g": protein_g - int(protein_g * 0.7),
                "carbs_g": carbs_g - int(carbs_g * 0.7),
                "fat_g": fat_g - int(fat_g * 0.7),
            },
        },
    ]
    return PlateResponse(
        kcal=target_kcal,
        macros={
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carbs_g": carbs_g,
            "fiber_g": fiber_g,
        },
        portions=portions,
        layout=layout,
        meals=meals,
        day_micros={},
        meals_per_day=3,
    )


def align_macros_with_targets(
    req: PlateRequest,
    plate_data: dict[str, Any],
    _legacy_candidates: list[Any] | None = None,
    *,
    targets_builder: TargetsBuilder | None = None,
    targets_response_factory: TargetsResponseFactory | None = None,
) -> tuple[dict[str, Any], int | None, bool]:
    """Align generated macros with canonical WHO targets when available."""

    macros_aligned = dict(plate_data["macros"])
    if not callable(targets_builder):
        return macros_aligned, None, False

    targets_req = WHOTargetsRequest(
        sex=req.sex,
        age=req.age,
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        activity=req.activity,
        goal=req.goal,
        deficit_pct=req.deficit_pct,
        surplus_pct=req.surplus_pct,
        bodyfat=req.bodyfat,
        diet_flags=req.diet_flags,
        life_stage=req.life_stage,
        lang=req.lang,
    )
    try:
        response_factory = targets_response_factory or generate_who_targets_response
        targets_response = response_factory(
            targets_req,
            targets_builder=targets_builder,
        )
    except HTTPException:
        logger.warning(
            "Canonical WHO target alignment rejected the Plate profile",
            exc_info=True,
        )
        raise
    except Exception:
        logger.exception("Unexpected WHO target alignment failure")
        raise

    alignment_succeeded = False
    for macro_name in ("protein_g", "fat_g", "carbs_g", "fiber_g"):
        if macro_name not in macros_aligned:
            continue
        target_value = targets_response.macros.get(macro_name)
        if target_value is None:
            continue
        if macro_name == "fiber_g" and macros_aligned.get("fiber_g") == int(round(FIBER_MIN_G)):
            continue
        macros_aligned[macro_name] = int(target_value)
        alignment_succeeded = True

    try:
        target_kcal = int(targets_response.kcal_daily)
    except (TypeError, ValueError, OverflowError):
        logger.warning("Canonical WHO target kcal was invalid; ignoring override")
        target_kcal = None
    return macros_aligned, target_kcal, alignment_succeeded


def sanitize_plate_data(plate_data_raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize fiber before required fail-closed HTML/data sanitization."""

    plate_data = dict(plate_data_raw)
    macros = plate_data.get("macros")
    if isinstance(macros, dict):
        normalized_macros = dict(macros)
        if "fiber_g" in normalized_macros:
            try:
                normalized_macros["fiber_g"] = int(round(float(normalized_macros["fiber_g"])))
            except (TypeError, ValueError, OverflowError):
                logger.warning("Invalid Plate fiber; using canonical minimum")
                normalized_macros["fiber_g"] = int(round(FIBER_MIN_G))
        plate_data["macros"] = normalized_macros
    sanitized_plate_data: dict[str, Any] = sanity_filter_plate_data(plate_data)
    return sanitized_plate_data


def _iter_exception_chain(err: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    current: BaseException | None = err
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _is_missing_nh3_error(err: BaseException) -> bool:
    for exc in _iter_exception_chain(err):
        if exc.__class__.__name__ == "MissingOptionalDependencyError" or isinstance(
            exc,
            MissingOptionalDependencyError,
        ):
            dependency = getattr(exc, "dependency", None)
            message = str(exc).lower()
            if dependency == "nh3" or ("optional dependency" in message and "nh3" in message):
                return True
        if isinstance(exc, ModuleNotFoundError):
            message = str(exc).lower()
            return getattr(exc, "name", None) == "nh3" or ("no module named 'nh3'" in message)
        if isinstance(exc, ImportError):
            message = str(exc).lower()
            if "no module named 'nh3'" in message or "no module named nh3" in message:
                return True
    return False


def _raise_missing_nh3_http_error(exc: Exception) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail={
            "error": "missing_dependency",
            "dependency": "nh3",
            "message": (
                "HTML sanitization library (nh3) is required for premium " "plate sanitization."
            ),
            "action": "Install server dependency: python -m pip install nh3",
        },
    ) from exc


async def aggregate_day_micros(
    meals: list[dict[str, Any]],
    _legacy_candidates: list[Any] | None = None,
    *,
    aggregator: DayMicrosAggregator | None = None,
) -> dict[str, float]:
    """Execute the explicit micronutrient dependency in sync or async form."""

    aggregate = aggregator or _aggregate_day_micronutrients
    result = aggregate(meals)
    if isinstance(result, Awaitable):
        result = await result
    resolved_result = {} if result is None else result
    return _validated_micronutrient_mapping(resolved_result)


async def generate_plate_response(
    req: PlateRequest,
    *,
    dependencies: PlateServiceDependencies | None = None,
) -> PlateResponse:
    """Generate the canonical Plate response with bounded, stable failures."""

    if not _is_truthy(os.getenv("FEATURE_PREMIUM_NUTRITION")):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PLATE_FEATURE_UNAVAILABLE_DETAIL,
        )

    deps = dependencies or _default_dependencies()
    try:
        if (
            not callable(deps.make_plate)
            or not callable(deps.calculate_all_bmr)
            or not callable(deps.calculate_all_tdee)
        ):
            return build_fallback_plate(
                req,
                targets_builder=deps.build_nutrition_targets,
            )

        bmr_results = deps.calculate_all_bmr(
            req.weight_kg,
            req.height_cm,
            req.age,
            req.sex,
            req.bodyfat,
        )
        _validate_calculation_mapping(bmr_results)
        tdee_results = deps.calculate_all_tdee(bmr_results, req.activity)
        _validate_calculation_mapping(tdee_results, required_key="mifflin")
        tdee_value = float(tdee_results["mifflin"])
        diet_flags = {str(flag) for flag in req.diet_flags} if req.diet_flags else None
        try:
            plate_data_raw = deps.make_plate(
                weight_kg=req.weight_kg,
                tdee_val=tdee_value,
                goal=req.goal,
                deficit_pct=req.deficit_pct,
                surplus_pct=req.surplus_pct,
                diet_flags=diet_flags,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_PREMIUM_PLATE_INPUT_DETAIL,
            ) from exc

        _ensure_finite_plate_response_output(plate_data_raw)
        plate_data = sanitize_plate_data(plate_data_raw)
        layout = [VisualShape(**item) for item in plate_data["layout"]]
        day_micros = await aggregate_day_micros(
            plate_data["meals"],
            aggregator=deps.aggregate_day_micronutrients,
        )
        (
            macros_aligned,
            target_kcal_override,
            alignment_succeeded,
        ) = align_macros_with_targets(
            req,
            plate_data,
            targets_builder=deps.build_nutrition_targets,
        )

        final_kcal_raw = (
            target_kcal_override if target_kcal_override is not None else plate_data["kcal"]
        )
        try:
            final_kcal = int(round(float(final_kcal_raw)))
        except (TypeError, ValueError, OverflowError):
            logger.warning("Invalid Plate kcal; using safe minimum")
            final_kcal = _SAFE_DEFAULT_KCAL

        if not alignment_succeeded:
            protein_g, fat_g, carbs_g = calculate_heuristic_macros(
                final_kcal,
                req.weight_kg,
            )
            macros_aligned.update(
                {
                    "protein_g": protein_g,
                    "fat_g": fat_g,
                    "carbs_g": carbs_g,
                }
            )

        if "fiber_g" in macros_aligned:
            try:
                macros_aligned["fiber_g"] = int(
                    round(max(FIBER_MIN_G, float(macros_aligned["fiber_g"])))
                )
            except (TypeError, ValueError, OverflowError):
                logger.warning("Invalid aligned Plate fiber; using canonical minimum")
                macros_aligned["fiber_g"] = int(round(FIBER_MIN_G))

        for macro_key, macro_value in list(macros_aligned.items()):
            try:
                macros_aligned[macro_key] = int(round(float(macro_value)))
            except (TypeError, ValueError, OverflowError):
                logger.warning("Invalid aligned Plate macro %s", macro_key)

        computed_kcal = _macros_to_kcal(macros_aligned)
        if alignment_succeeded and computed_kcal is not None:
            final_kcal = computed_kcal
        final_kcal = clamp_daily_kcal(final_kcal)

        _ensure_finite_dependency_output(plate_data["meals"])
        _ensure_finite_dependency_output(day_micros)
        return PlateResponse(
            kcal=final_kcal,
            macros=macros_aligned,
            portions=plate_data["portions"],
            layout=layout,
            meals=plate_data["meals"],
            day_micros=day_micros,
            meals_per_day=plate_data.get("meals_per_day", 3),
        )
    except _InvalidPlateCalculationOutputError:
        logger.exception("Rejected invalid Plate calculation dependency output")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
        ) from None
    except _InvalidPlateMicronutrientOutputError:
        logger.exception("Rejected invalid Plate micronutrient output")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
        ) from None
    except HTTPException:
        raise
    except ValueError as exc:
        if _is_missing_nh3_error(exc):
            _raise_missing_nh3_http_error(exc)
        logger.exception("Plate response validation failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
        ) from None
    except Exception as exc:
        if _is_missing_nh3_error(exc):
            _raise_missing_nh3_http_error(exc)
        logger.exception("Unexpected Plate generation failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ENHANCED_PLATE_GENERATION_FAILED_DETAIL,
        ) from None
