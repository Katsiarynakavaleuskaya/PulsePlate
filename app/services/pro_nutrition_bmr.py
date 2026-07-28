"""Canonical premium BMR/TDEE response orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import math
from typing import TypeAlias, cast

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
from core.i18n import t

logger = logging.getLogger(__name__)

_BMRRequest: TypeAlias = BMRRequest | BMRRequestLegacy
_BMRCalculator = Callable[[float, float, int, str, float | None], object]
_TDEECalculator = Callable[[dict[str, float], str], object]


@dataclass(frozen=True, slots=True)
class BMRDependencies:
    """Explicit calculation dependencies for deterministic tests and callers."""

    calculate_all_bmr: _BMRCalculator | None
    calculate_all_tdee: _TDEECalculator | None


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
    expected_keys = {"mifflin", "harris"}
    if bodyfat_supplied:
        expected_keys.add("katch")
    if set(bmr_results) != expected_keys:
        raise _MalformedBMRCalculationError("BMR result keys do not match the core contract")
    if set(tdee_results) != expected_keys:
        raise _MalformedBMRCalculationError("TDEE result keys do not match the core contract")


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
        resolved = dependencies if dependencies is not None else _resolve_dependencies()
        if not callable(resolved.calculate_all_bmr) or not callable(resolved.calculate_all_tdee):
            raise _MissingBMRDependencyError("core BMR calculators are unavailable")

        raw_bmr_results = resolved.calculate_all_bmr(
            req.weight_kg,
            req.height_cm,
            req.age,
            req.sex,
            req.bodyfat,
        )
        bmr_results = _validated_calculation_map(raw_bmr_results, name="BMR results")

        raw_tdee_results = resolved.calculate_all_tdee(
            bmr_results,
            req.activity,
        )
        tdee_results = _validated_calculation_map(raw_tdee_results, name="TDEE results")
        _require_result_contract(
            bmr_results,
            tdee_results,
            bodyfat_supplied=req.bodyfat is not None,
        )

        primary_tdee = int(tdee_results["mifflin"])
        notes = (
            [t(req.lang, "bmr_katch_note")]
            if "katch" in bmr_results and req.bodyfat is not None
            else []
        )
        activity_level = t(
            req.lang,
            f"activity_{req.activity}",
        )
        recommended_intake = _validated_calculation_map(
            {
                "maintenance": primary_tdee,
                "weight_loss": primary_tdee * nutrition_bmr.WEIGHT_LOSS_MULTIPLIER,
                "weight_gain": primary_tdee * nutrition_bmr.WEIGHT_GAIN_MULTIPLIER,
            },
            name="Recommended intake",
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
        logger.error("Premium BMR calculation returned malformed data")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BMR_CALCULATION_FAILED_DETAIL,
        ) from None
    except Exception:
        logger.error("Premium BMR calculation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BMR_CALCULATION_FAILED_DETAIL,
        ) from None

    return BMRResponse(
        bmr=bmr_results,
        tdee=tdee_results,
        activity_level=activity_level,
        recommended_intake=recommended_intake,
        formulas_used=list(bmr_results),
        notes=notes,
    )
