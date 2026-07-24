"""Canonical premium BMR/TDEE response orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import math
from typing import cast

from fastapi import HTTPException, status

from app.http_error_details import (
    BMR_CALCULATION_FAILED_DETAIL,
    BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL,
    INVALID_BMR_INPUT_DETAIL,
    PREMIUM_BMR_FEATURE_UNAVAILABLE_DETAIL,
)
from app.schemas.bmr import BMRRequest, BMRRequestLegacy, BMRResponse
from app.utils.feature_flags import is_premium_nutrition_enabled
import core.bmr as nutrition_bmr
from core.i18n import Language, t

logger = logging.getLogger(__name__)

_BMRRequest = BMRRequest | BMRRequestLegacy
_BMRCalculator = Callable[[float, float, int, str, float | None], object]
_TDEECalculator = Callable[[dict[str, float], str], object]
_VALID_SEXES = frozenset({"male", "female"})
_VALID_ACTIVITIES = frozenset({"sedentary", "light", "moderate", "active", "very_active"})
_VALID_LANGUAGES = frozenset({"ru", "en", "es"})


@dataclass(frozen=True, slots=True)
class BMRDependencies:
    """Explicit calculation dependencies for deterministic tests and callers."""

    calculate_all_bmr: _BMRCalculator | None
    calculate_all_tdee: _TDEECalculator | None


@dataclass(frozen=True, slots=True)
class _ValidatedBMRInput:
    weight_kg: float
    height_cm: float
    age: int
    sex: str
    activity: str
    bodyfat: float | None
    lang: Language


class _MissingBMRDependencyError(RuntimeError):
    """A required core calculation callable is unavailable."""


class _MalformedBMRCalculationError(RuntimeError):
    """A calculation dependency returned an unsafe response shape."""


def _resolve_dependencies() -> BMRDependencies:
    """Resolve direct core calculators on every call."""

    bmr_calculator = getattr(nutrition_bmr, "calculate_all_bmr", None)
    tdee_calculator = getattr(nutrition_bmr, "calculate_all_tdee", None)
    return BMRDependencies(
        calculate_all_bmr=(
            cast(_BMRCalculator, bmr_calculator) if callable(bmr_calculator) else None
        ),
        calculate_all_tdee=(
            cast(_TDEECalculator, tdee_calculator) if callable(tdee_calculator) else None
        ),
    )


def _positive_finite_number(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a positive finite number")
    try:
        numeric_value = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive finite number") from exc
    if not math.isfinite(numeric_value) or numeric_value <= 0:
        raise ValueError(f"{field_name} must be a positive finite number")
    return numeric_value


def _validate_effective_request(req: _BMRRequest) -> _ValidatedBMRInput:
    weight_kg = _positive_finite_number(req.weight_kg, field_name="weight_kg")
    height_cm = _positive_finite_number(req.height_cm, field_name="height_cm")

    if isinstance(req.age, bool) or not isinstance(req.age, int) or not 1 <= req.age <= 120:
        raise ValueError("age must be an integer between 1 and 120")
    if req.sex not in _VALID_SEXES:
        raise ValueError("invalid sex")
    if req.activity not in _VALID_ACTIVITIES:
        raise ValueError("invalid activity")
    if req.lang not in _VALID_LANGUAGES:
        raise ValueError("invalid language")

    bodyfat = None
    if req.bodyfat is not None:
        bodyfat = _positive_finite_number(req.bodyfat, field_name="bodyfat")
        if bodyfat > 50:
            raise ValueError("bodyfat must be at most 50")

    return _ValidatedBMRInput(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=req.age,
        sex=req.sex,
        activity=req.activity,
        bodyfat=bodyfat,
        lang=req.lang,
    )


def _validated_calculation_map(value: object, *, name: str) -> dict[str, float]:
    if not isinstance(value, dict) or not value:
        raise _MalformedBMRCalculationError(f"{name} must be a non-empty mapping")

    validated: dict[str, float] = {}
    for key, raw_result in value.items():
        if not isinstance(key, str) or not key.strip():
            raise _MalformedBMRCalculationError(f"{name} contains an invalid key")
        if isinstance(raw_result, bool) or not isinstance(raw_result, (int, float)):
            raise _MalformedBMRCalculationError(f"{name}[{key!r}] must be numeric")
        try:
            result = float(raw_result)
        except (OverflowError, TypeError, ValueError) as exc:
            raise _MalformedBMRCalculationError(f"{name}[{key!r}] must be numeric") from exc
        if not math.isfinite(result) or result <= 0:
            raise _MalformedBMRCalculationError(f"{name}[{key!r}] must be positive and finite")
        validated[key] = result
    return validated


def _require_result_contract(
    bmr_results: dict[str, float],
    tdee_results: dict[str, float],
    *,
    bodyfat_supplied: bool,
) -> None:
    if "mifflin" not in bmr_results:
        raise _MalformedBMRCalculationError("BMR results must include mifflin")
    if bodyfat_supplied and "katch" not in bmr_results:
        raise _MalformedBMRCalculationError(
            "BMR results must include katch when bodyfat is supplied"
        )
    if bmr_results.keys() != tdee_results.keys():
        raise _MalformedBMRCalculationError("BMR and TDEE result keys must be identical")


async def calculate_bmr_response(
    req: _BMRRequest,
    *,
    dependencies: BMRDependencies | None = None,
) -> BMRResponse:
    """Calculate the stable premium BMR response for both compatibility routes."""

    if not is_premium_nutrition_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PREMIUM_BMR_FEATURE_UNAVAILABLE_DETAIL,
        )

    try:
        validated = _validate_effective_request(req)
        resolved = dependencies if dependencies is not None else _resolve_dependencies()
        if not callable(resolved.calculate_all_bmr) or not callable(resolved.calculate_all_tdee):
            raise _MissingBMRDependencyError("core BMR calculators are unavailable")

        raw_bmr_results = resolved.calculate_all_bmr(
            validated.weight_kg,
            validated.height_cm,
            validated.age,
            validated.sex,
            validated.bodyfat,
        )
        bmr_results = _validated_calculation_map(raw_bmr_results, name="BMR results")

        raw_tdee_results = resolved.calculate_all_tdee(
            bmr_results,
            validated.activity,
        )
        tdee_results = _validated_calculation_map(raw_tdee_results, name="TDEE results")
        _require_result_contract(
            bmr_results,
            tdee_results,
            bodyfat_supplied=validated.bodyfat is not None,
        )

        primary_tdee = int(tdee_results["mifflin"])
        notes = (
            [t(validated.lang, "bmr_katch_note")]
            if "katch" in bmr_results and validated.bodyfat is not None
            else []
        )
        return BMRResponse(
            bmr=bmr_results,
            tdee=tdee_results,
            activity_level=t(
                validated.lang,
                f"activity_{validated.activity}",
            ),
            recommended_intake={
                "maintenance": primary_tdee,
                "weight_loss": primary_tdee * nutrition_bmr.WEIGHT_LOSS_MULTIPLIER,
                "weight_gain": primary_tdee * nutrition_bmr.WEIGHT_GAIN_MULTIPLIER,
            },
            formulas_used=list(bmr_results),
            notes=notes,
        )
    except (ImportError, _MissingBMRDependencyError):
        logger.warning("Premium BMR dependency unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=BMR_CALCULATION_MODULE_UNAVAILABLE_DETAIL,
        ) from None
    except ValueError:
        logger.info("Premium BMR input rejected")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=INVALID_BMR_INPUT_DETAIL,
        ) from None
    except _MalformedBMRCalculationError:
        logger.exception("Premium BMR calculation returned malformed data")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BMR_CALCULATION_FAILED_DETAIL,
        ) from None
    except Exception:
        logger.exception("Premium BMR calculation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BMR_CALCULATION_FAILED_DETAIL,
        ) from None
