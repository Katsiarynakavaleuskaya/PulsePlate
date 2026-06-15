"""Service helpers for legacy BMI compatibility routes."""

from __future__ import annotations

from decimal import Decimal
import logging
import sys
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from starlette import status

from app.routers.bmi import bmi_calculate_handler
from app.schemas.bmi import BMICalculateRequest
from app.schemas.bmi_compat import BMIRequest, BMIRequestV1, _YES_VALUES_PREGNANT
from bmi_visualization import MATPLOTLIB_AVAILABLE, generate_bmi_visualization
from core.bmi.compat_plan import legacy_plan_category
from core.bmi.engine import HEALTHY_BMI_RANGE, _normalize_bool_flag
from core.i18n import Language, normalize_lang, t
from core.utils import resolve_attr

logger = logging.getLogger(__name__)
bmi_logger = logging.getLogger("app.bmi")


def add_visualization_if_requested(result: dict[str, Any], req: BMIRequest) -> None:
    """Add BMI visualization to result if requested and available."""
    if not req.include_chart:
        return

    pkg_flag = getattr(sys.modules.get("app"), "MATPLOTLIB_AVAILABLE", MATPLOTLIB_AVAILABLE)

    legacy_module = sys.modules.get("legacy_app")
    legacy_flag = getattr(legacy_module, "MATPLOTLIB_AVAILABLE", MATPLOTLIB_AVAILABLE)

    if not pkg_flag or not legacy_flag or not MATPLOTLIB_AVAILABLE:
        result["visualization"] = {
            "error": "Visualization not available - matplotlib not installed",
            "available": False,
        }
        return

    candidates = [
        sys.modules.get("_app_top_module"),
        sys.modules.get("app"),
        legacy_module,
        sys.modules.get(__name__),
    ]
    if viz_func := resolve_attr(
        "generate_bmi_visualization",
        generate_bmi_visualization,
        candidates,
    ):
        viz_result = viz_func(
            bmi=result["bmi"],
            age=req.age,
            gender=req.gender,
            pregnant=req.pregnant,
            athlete=req.athlete,
            lang=req.lang,
        )
        if viz_result.get("available"):
            result["visualization"] = viz_result
        else:
            result["visualization"] = {
                "error": "Visualization not available - generation failed",
                "available": False,
            }


def _localized_legacy_bmi_result(
    canonical_result: dict[str, Any],
    *,
    lang: Language,
) -> dict[str, Any]:
    lang_norm: Language = normalize_lang(str(lang))

    category_slug = canonical_result.get("category")
    category_display: str | None = None
    if category_slug:
        category_i18n_map = {
            "underweight": "bmi_underweight",
            "normal": "bmi_normal",
            "overweight": "bmi_overweight",
            "obesity_1": "bmi_obese_1",
            "obesity_2": "bmi_obese_2",
            "obesity_3": "bmi_obese_3",
        }
        i18n_key = category_i18n_map.get(category_slug)
        category_display = t(lang_norm, i18n_key) if i18n_key else category_slug

    group = canonical_result.get("group", "")
    notes_list = canonical_result.get("notes", [])
    interpretation = canonical_result.get("interpretation") or ""

    legacy_note = ""
    if group == "pregnant":
        legacy_note = t(lang_norm, "bmi_not_valid_during_pregnancy")
    elif group == "athlete":
        legacy_note = t(lang_norm, "advice_athlete_bmi")
        if notes_list:
            waist_notes = " | ".join(notes_list)
            legacy_note = f"{legacy_note} | {waist_notes}" if waist_notes else legacy_note
    elif notes_list:
        legacy_note = " | ".join(notes_list)
    else:
        legacy_note = interpretation or ""

    return {
        "bmi": canonical_result["bmi"],
        "category": category_display,
        "note": legacy_note,
        "athlete": canonical_result["group"] == "athlete",
        "group": canonical_result["group"],
    }


def _build_bmi_request_payload(req: BMIRequest) -> dict[str, Any]:
    return {
        "weight_kg": req.weight_kg,
        "height_cm": round(float(req.height_m) * 100.0, 1),
        "age": req.age,
        "gender": req.gender,
        "pregnant": req.pregnant,
        "athlete": req.athlete,
        "waist_cm": req.waist_cm,
        "lang": str(req.lang),
    }


def _build_bmi_v1_request_payload(req: BMIRequestV1) -> dict[str, Any]:
    return {
        "weight_kg": req.weight_kg,
        "height_cm": req.height_cm,
        "age": req.age,
        "gender": req.gender,
        "pregnant": req.pregnant,
        "athlete": req.athlete,
        "waist_cm": req.waist_cm,
        "lang": str(req.lang),
    }


def _validate_canonical_bmi_payload(payload: dict[str, Any]) -> BMICalculateRequest:
    try:
        return BMICalculateRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=jsonable_encoder(exc.errors()),
        ) from exc


async def bmi_endpoint(req: BMIRequest) -> dict[str, Any]:
    canonical_req = _validate_canonical_bmi_payload(_build_bmi_request_payload(req))
    canonical_result = await bmi_calculate_handler(canonical_req)
    legacy_result = _localized_legacy_bmi_result(canonical_result, lang=req.lang)

    add_visualization_if_requested(legacy_result, req)

    is_athlete = legacy_result["athlete"]
    group_category = legacy_result["group"]
    log_msg = f"BMI calculation complete [group={group_category} athlete={is_athlete}]"
    logger.info(log_msg)
    bmi_logger.info(log_msg)

    return legacy_result


async def plan_endpoint(req: BMIRequest) -> dict[str, Any]:
    height_cm = round(req.height_m * 100.0, 1)
    bmi_payload = {
        "weight_kg": req.weight_kg,
        "height_cm": height_cm,
        "age": req.age,
        "gender": req.gender,
        "pregnant": req.pregnant,
        "athlete": req.athlete,
        "lang": req.lang,
        "waist_cm": req.waist_cm,
    }

    canonical = await bmi_calculate_handler(bmi_payload)
    bmi_value = canonical.get("bmi")
    bmi_dec = Decimal(str(bmi_value)) if bmi_value is not None else Decimal("0")

    canonical_group = canonical.get("group") or "general"
    engine_category = canonical.get("category")

    pregnant_bool = _normalize_bool_flag(req.pregnant, yes_values=_YES_VALUES_PREGNANT) and (
        req.gender == "female"
    )
    if pregnant_bool:
        cat = None
    else:
        cat_result = legacy_plan_category(
            engine_category=engine_category,
            bmi=bmi_dec,
            age=req.age,
            lang=req.lang,
            group=canonical_group,
        )
        cat = cat_result.category

    healthy_bmi = {"min": HEALTHY_BMI_RANGE.min, "max": HEALTHY_BMI_RANGE.max}
    lang_for_response = req.lang if req.lang in ("ru", "en") else "en"

    if lang_for_response == "ru":
        base: dict[str, Any] = {
            "summary": "Персональный план (MVP)",
            "bmi": float(bmi_dec),
            "category": cat,
            "premium": bool(req.premium),
            "next_steps": [
                "Шаги: 7–10 тыс/день",
                "Белок: 1.2–1.6 г/кг",
                "Сон: 7–9 часов",
            ],
            "healthy_bmi": healthy_bmi,
            "action": "Сделай сегодня 20-мин быструю прогулку",
        }
        if req.premium:
            base["premium_reco"] = [
                "Дефицит 300–500 ккал",
                "2–3 силовые тренировки/нед",
            ]
    else:
        base = {
            "summary": "Personal plan (MVP)",
            "bmi": float(bmi_dec),
            "category": cat,
            "premium": bool(req.premium),
            "next_steps": ["Steps: 7–10k/day", "Protein: 1.2–1.6 g/kg", "Sleep: 7–9 h"],
            "healthy_bmi": healthy_bmi,
            "action": "Take a brisk 20-min walk today",
        }
        if req.premium:
            base["premium_reco"] = [
                "Calorie deficit 300–500 kcal",
                "2–3 strength sessions/week",
            ]

    return base


async def bmi_endpoint_v1(req: BMIRequestV1) -> dict[str, Any]:
    canonical_req = _validate_canonical_bmi_payload(_build_bmi_v1_request_payload(req))
    canonical_result = await bmi_calculate_handler(canonical_req)
    legacy_result = _localized_legacy_bmi_result(canonical_result, lang=req.lang)

    is_athlete = legacy_result["athlete"]
    group_category = legacy_result["group"]
    log_msg = f"BMI v1 calculation complete [group={group_category} athlete={is_athlete}]"
    logger.info(log_msg)
    bmi_logger.info(log_msg)

    return legacy_result
