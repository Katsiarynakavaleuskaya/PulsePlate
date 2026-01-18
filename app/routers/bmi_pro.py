from __future__ import annotations

import logging
import os
from typing import Literal, Optional, Protocol

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.middleware.api_tiers import require_pro_tier
from app.schemas.bmi import (
    BMICalculateProRequest,
    BMICalculateProResponse,
    SoftPaywallAvailability,
    SoftPaywallHook,
    SoftPaywallMessage,
    WaistRiskResultSchema,
)
from app.services.bmi_visualization import build_bmi_scale_v1

# Use canonical BMI extras module - Pro tier functions only
# Pro endpoint must use Pro tier functions exclusively (no mixing with Free/Simple tier)
from core.bmi_extras import (
    BMIProCard,
    ffmi,
    stage_obesity_optional_whr,
    whr_ratio,
    wht_ratio,
)

# Import canonical BMI engine
# Alias calc_bmi for test patching compatibility (no BMI math in router, just symbol)
from core.bmi.engine import _compute_bmi as calc_bmi

# Import i18n functionality
from core.i18n import Language, normalize_lang, t

logger = logging.getLogger(__name__)


# Import engine (same pattern as bmi.py)
class CalculateBmiResult(Protocol):
    def __call__(
        self,
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str,
        pregnant: bool,
        athlete: bool,
        waist_cm: float | None,
        hip_cm: float | None,
        lang: str | None,
    ) -> "BMICalculateResult": ...  # noqa: F821


def _get_engine_calculator() -> CalculateBmiResult | None:
    """
    RU: Изолируем импорт engine для тестируемости fallback без reload/sys.modules.
    EN: Isolate engine import to test ImportError fallback without reload/sys.modules.

    Returns:
        calculate_bmi_result function if engine is available, None otherwise.
    """
    try:
        from core.bmi.engine import calculate_bmi_result  # noqa: WPS433 (local import by design)

        return calculate_bmi_result
    except ImportError:
        return None


# Helper functions (same as bmi.py)
def _env_bool(name: str, default: bool) -> bool:
    """Parse boolean env var."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _normalize_bool_flag(value: str | bool, yes_values: set[str] | None = None) -> bool:
    """Normalize boolean flag from string or bool."""
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return False
    s = value.strip().lower()
    if not s:
        return False
    allowed = yes_values or {"yes", "y", "true", "1", "да", "д", "si", "sí"}
    return s in allowed


def _build_soft_paywall_hook(lang: str) -> SoftPaywallHook | None:
    """Build text-only soft paywall hook (no BMI logic)."""
    enabled = _env_bool("SOFT_PAYWALL_ENABLED", default=False)
    if not enabled:
        return None

    safe_lang = normalize_lang(lang)

    message = SoftPaywallMessage(
        lang=safe_lang,
        title_key="soft_paywall.title",
        body_key="soft_paywall.body",
        cta_key="soft_paywall.cta",
        default_title=t(safe_lang, "soft_paywall.title"),
        default_body=t(safe_lang, "soft_paywall.body"),
        default_cta=t(safe_lang, "soft_paywall.cta"),
    )

    availability = SoftPaywallAvailability(pro_available=True, reason_key=None)

    return SoftPaywallHook(
        id="bmi.pro_interpretation_v1",
        message=message,
        availability=availability,
        target="pro_paywall",
    )


router = APIRouter(prefix="/api/v1/pro", tags=["pro"])


def _adapt_pro_stage_to_response(
    stage_dict: dict[str, str], lang: Language
) -> tuple[Literal["low", "moderate", "high"], list[str]]:
    """Adapt Pro tier stage_obesity Dict response to BMIProResponse format.

    Pro tier stage_obesity returns Dict with keys: stage, recommendation, risk_factors, etc.
    BMIProResponse expects: risk_level (Literal) and notes (list[str]).

    This is contract adaptation, not tier mixing - all calculations use Pro tier.

    Args:
        stage_dict: Pro tier stage_obesity result (Dict[str, str])
        lang: Language code for i18n notes

    Returns:
        Tuple of (risk_level, notes_list) compatible with BMIProResponse
    """
    stage = stage_dict.get("stage", "low_risk")

    # Map Pro tier stage to risk_level
    if stage == "high_risk":
        risk_level: Literal["low", "moderate", "high"] = "high"
    elif stage == "moderate_risk":
        risk_level = "moderate"
    else:
        risk_level = "low"

    # Build notes list from Pro tier recommendations
    notes: list[str] = []
    recommendation = stage_dict.get("recommendation")
    if recommendation:
        notes.append(recommendation)

    # Add risk factor information if available
    risk_factors = stage_dict.get("risk_factors")
    if risk_factors and risk_factors != "0":
        notes.append(t(lang, "bmi_pro_risk_factors", count=risk_factors))

    # Add individual risk assessments (wht_risk, whr_risk) if available
    # These provide additional context from Pro tier analysis
    wht_risk = stage_dict.get("wht_risk")
    whr_risk = stage_dict.get("whr_risk")
    if wht_risk and wht_risk != "low":
        notes.append(t(lang, "bmi_pro_wht_risk", risk=wht_risk))

    # WHR: if unknown (missing hip), show only the translated explanation (no duplicate "WHR risk: unknown")
    if whr_risk == "unknown":
        notes.append(t(lang, "bmi_pro_whr_missing_hip"))
    elif whr_risk and whr_risk != "low":
        notes.append(t(lang, "bmi_pro_whr_risk", risk=whr_risk))

    return risk_level, notes


Sex = Literal["female", "male"]


class BMIProRequest(BaseModel):
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    sex: Sex
    age: int = Field(..., ge=10, le=100)
    waist_cm: float = Field(..., gt=0)
    hip_cm: Optional[float] = Field(None, gt=0)
    bodyfat_percent: Optional[float] = Field(None, ge=0, le=60)
    lang: Language = "en"  # Add language parameter


class BMIProResponse(BaseModel):
    bmi: float
    whtr: float
    whr: Optional[float]
    ffmi: Optional[float]
    risk_level: Literal["low", "moderate", "high"]
    notes: list[str]


@router.post(
    "/bmi",
    response_model=BMIProResponse,
    dependencies=[Depends(require_pro_tier)],
    deprecated=True,  # DEPRECATED: Use /api/v1/pro/bmi/calculate (canonical engine-based endpoint)
    summary="[DEPRECATED] Legacy PRO BMI endpoint",
    description="""
    DEPRECATED: This endpoint uses legacy BMI calculation logic outside canonical engine.
    Use `/api/v1/pro/bmi/calculate` instead (canonical engine-based endpoint with WHR support).

    RU: Устаревший endpoint. Используйте /api/v1/pro/bmi/calculate.
    EN: Deprecated endpoint. Use /api/v1/pro/bmi/calculate instead.
    """,
)
def bmi_pro(req: BMIProRequest) -> BMIProResponse:
    try:
        # Convert height to meters for calc_bmi(weight, height_m)
        bmi_val = calc_bmi(req.weight_kg, req.height_cm / 100.0)
        # Use Pro tier functions exclusively (no mixing with Free/Simple tier)
        v_whtr = wht_ratio(req.waist_cm, req.height_cm)  # Pro: 3 decimal places
        # Pro tier whr_ratio requires hip_cm; if missing, WHR is None (not 0.0)
        # Do NOT substitute 0.0 - missing data must be treated as "unknown", not "low risk"
        v_whr = (
            whr_ratio(req.waist_cm, float(req.hip_cm), req.sex) if req.hip_cm is not None else None
        )
        # Use Pro tier ffmi (returns dict), extract ffmi value for response compatibility
        # Contract: ffmi=None when bodyfat_percent is missing (no estimate mode in remediation)
        # Estimate mode can be added in separate product PR with contract update
        v_ffmi: Optional[float] = None
        if req.bodyfat_percent is not None:
            ffmi_dict = ffmi(req.weight_kg, req.height_cm, req.bodyfat_percent)
            v_ffmi = ffmi_dict["ffmi"]
        # Pro tier stage_obesity_optional_whr handles missing WHR correctly
        # Returns whr_risk="unknown" if whr is None (not "low")
        stage_dict = stage_obesity_optional_whr(
            bmi=bmi_val, wht=v_whtr, whr=v_whr, sex=req.sex, lang=req.lang
        )
        # Adapt Pro tier Dict response to BMIProResponse format (risk_level, notes)
        risk_level, notes = _adapt_pro_stage_to_response(stage_dict, req.lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    card = BMIProCard(
        bmi=bmi_val,
        whtr=v_whtr,
        whr=v_whr,
        ffmi=v_ffmi,
        risk_level=risk_level,
        notes=notes,
    )
    return BMIProResponse(**card.__dict__)


# PRO tier endpoint for BMI calculation with WHR support (canonical namespace)
@router.post(
    "/bmi/calculate",
    response_model=BMICalculateProResponse,
    response_model_by_alias=True,
    dependencies=[Depends(require_pro_tier)],
    summary="Calculate BMI with WHR (PRO tier)",
    description="""
    PRO tier BMI calculation endpoint with WHR (Waist-to-Hip Ratio) support.

    RU: Расчет BMI с поддержкой WHR для PRO уровня.
    EN: PRO tier BMI calculation with WHR support.

    Requires: PRO tier API key in X-API-Key header

    Features:
    - All FREE tier features (BMI, category, WHtR, waist risk)
    - WHR calculation (requires hip_cm)
    - PRO tier soft paywall hooks
    """,
)
async def calculate_bmi_pro(req: BMICalculateProRequest) -> BMICalculateProResponse:
    """
    RU: Рассчитывает BMI через единый engine с поддержкой WHR (PRO уровень).
    EN: Calculate BMI via unified engine with WHR support (PRO tier).

    PRO tier endpoint (requires PRO API key).

    Args:
        req: BMICalculateProRequest with user parameters (includes hip_cm)

    Returns:
        BMICalculateProResponse with BMI calculation results including WHR

    Raises:
        HTTPException: 400 if domain validation fails
                      401/403 if PRO tier key is missing/invalid
                      422 if Pydantic validation fails
                      500 if engine is not available
    """
    # Normalize language once at the beginning (same pattern as FREE endpoint)
    lang = normalize_lang(str(req.lang))

    # Normalize boolean flags (same as FREE endpoint)
    pregnant_bool = (
        req.pregnant if isinstance(req.pregnant, bool) else _normalize_bool_flag(req.pregnant)
    )
    athlete_bool = (
        req.athlete if isinstance(req.athlete, bool) else _normalize_bool_flag(req.athlete)
    )

    # Call engine with hip_cm (PRO tier feature)
    calc = _get_engine_calculator()
    if calc is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=t(lang, "bmi_engine_unavailable"),
        )

    try:
        result = calc(
            weight_kg=req.weight_kg,
            height_cm=req.height_cm,
            age=req.age,
            gender=req.gender
            or "male",  # TODO(P1): Move gender normalization to schema/engine, not router
            pregnant=pregnant_bool,
            athlete=athlete_bool,
            waist_cm=req.waist_cm,
            hip_cm=req.hip_cm,  # PRO tier: enable WHR calculation
            lang=str(req.lang),
        )
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=t(lang, "bmi_engine_unavailable"),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=t(lang, "bmi_invalid_parameters"),
        ) from e
    except Exception as e:
        logger.exception("BMI calculation failed (PRO tier)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t(lang, "bmi_calculation_failed"),
        ) from e

    # Serialize waist_risk (dataclass → Pydantic schema)
    waist_risk_schema: WaistRiskResultSchema | None = None
    if result.waist_risk:
        waist_risk_schema = WaistRiskResultSchema(
            wht_ratio=result.waist_risk.wht_ratio,
            risk_level=result.waist_risk.risk_level,
            notes=result.waist_risk.notes,
        )

    # Build soft paywall hook (same logic as FREE endpoint)
    # Note: _build_soft_paywall_hook checks SOFT_PAYWALL_ENABLED internally
    soft_paywall_hook = _build_soft_paywall_hook(lang)

    # Map to PRO API response (includes whr)
    resp = BMICalculateProResponse(
        bmi=result.bmi,
        category=result.category,
        group=result.group,
        group_display=result.group_display,
        interpretation=result.interpretation,
        wht_ratio=result.wht_ratio,
        whr=result.whr,  # PRO tier: include WHR
        waist_risk=waist_risk_schema,
        notes=list(result.notes),
        age_band=result.age_band,
        visualization=None,
        interpretation_v1=None,
        soft_paywall=soft_paywall_hook,
    )

    # Add visualization spec (graceful fallback)
    try:
        resp.visualization = build_bmi_scale_v1(result)
    except Exception as e:
        logger.warning("Failed to build BMI scale visualization: %s", e)
        # visualization remains None (graceful degradation)

    return resp
