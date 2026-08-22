"""FitChef structured coaching router.

RU: Тонкий router для bounded structured FitChef coaching surfaces.
EN: Thin router for bounded structured FitChef coaching surfaces.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import logging
import os
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.contracts.vip_contract import vip_error
from app.middleware.api_tiers import require_pro_tier, require_vip_tier
from app.schemas.fitchef import (
    FitChefDistortionSimulatorInput,
    FitChefDistortionSimulatorTaskEnvelope,
    FitChefIdentityLoopMapperInput,
    FitChefIdentityLoopMapperTaskEnvelope,
)
from app.schemas.fitchef_coaching import (
    FitChefCoachingErrorResponse,
    FitChefCoachingSourceItem,
    FitChefDistortionSimulatorRequest,
    FitChefDistortionSimulatorResponse,
    FitChefIdentityLoopMapperRequest,
    FitChefIdentityLoopMapperResponse,
    FitChefIdentityLoopView,
    FitChefSupportHandoffRequest,
    FitChefSupportHandoffResponse,
    FitChefVipCoachingErrorResponse,
)
from app.security.agent_control_plane import normalize_execution_mode, require_execution_mode
from app.security.agent_input_guard import require_safe_ai_agent_input
from app.security.rate_limit import (
    RATE_LIMIT_429_RESPONSES,
    RATE_LIMIT_INSIGHT,
    limit_if_available,
)
from app.services import fitchef_runtime
from app.services.fitchef_support_handoff import build_fitchef_support_handoff
from core.insight.fitchef_companion import has_high_distress_boundary

logger = logging.getLogger(__name__)

FITCHEF_STRUCTURED_FLAG_ENV = "FEATURE_FITCHEF_STRUCTURED_COACH"
FITCHEF_STRUCTURED_EXECUTION_MODE_ENV = "FITCHEF_STRUCTURED_COACH_EXECUTION_MODE"
FitChefStructuredMode = Literal["auto-safe", "review-required", "blocked"]
FITCHEF_HIGH_DISTRESS_BOUNDARY_DETAIL = "fitchef_high_distress_boundary"
FITCHEF_STRUCTURED_DISABLED_DETAIL = "FEATURE_FITCHEF_STRUCTURED_COACH is disabled"
FITCHEF_IDENTITY_LOOP_VALIDATION_DETAIL = "fitchef_identity_loop_mapper_validation_error"
FITCHEF_SUPPORT_HANDOFF_VALIDATION_DETAIL = "fitchef_support_handoff_validation_error"

_VIP_ERROR_CODE_BY_DETAIL: dict[str, str] = {
    FITCHEF_STRUCTURED_DISABLED_DETAIL: "fitchef_structured_disabled",
    "LLM provider not available": "llm_provider_unavailable",
    "LLM provider returned empty response": "llm_provider_empty_response",
    "LLM provider call timed out": "llm_provider_timeout",
    "VIP access required": "vip_access_required",
    "API key does not have VIP tier access. Upgrade to VIP to access this feature.": "vip_access_required",
}
FITCHEF_VIP_429_RESPONSES: dict[int | str, dict[str, object]] = {
    429: {
        "description": "Rate limit exceeded or monthly quota exhausted",
        "model": FitChefVipCoachingErrorResponse,
    }
}


class FitChefVipEnvelopeRoute(APIRoute):
    """Wrap pre-handler VIP dependency and validation failures in the frozen envelope."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except RequestValidationError:
                return _vip_error_response(
                    status_code=422,
                    detail=FITCHEF_IDENTITY_LOOP_VALIDATION_DETAIL,
                )
            except HTTPException as exc:
                return _vip_error_response(status_code=exc.status_code, detail=exc.detail)

        return custom_route_handler


router = APIRouter(tags=["pro", "fitchef", "coaching", "structured"])
support_handoff_router = APIRouter(tags=["pro", "fitchef", "coaching", "structured"])
vip_router = APIRouter(
    tags=["vip", "fitchef", "coaching", "structured"],
    route_class=FitChefVipEnvelopeRoute,
)

_FITCHEF_SUPPORT_HANDOFF_REQUEST_BODY_OPENAPI: dict[str, object] = {
    "required": True,
    "content": {
        "application/json": {
            "schema": FitChefSupportHandoffRequest.model_json_schema(),
        }
    },
}


def _is_fitchef_structured_enabled() -> bool:
    """Return whether structured FitChef coaching is enabled."""

    return os.getenv(FITCHEF_STRUCTURED_FLAG_ENV, "false").lower() in {"1", "true", "yes", "on"}


def _require_fitchef_structured_mode() -> FitChefStructuredMode:
    """Resolve and validate the structured-coach execution mode."""

    raw_execution_mode = os.getenv(FITCHEF_STRUCTURED_EXECUTION_MODE_ENV)
    try:
        execution_mode = cast(
            FitChefStructuredMode,
            normalize_execution_mode(raw_execution_mode),
        )
    except RuntimeError as exc:
        logger.error("FitChef structured execution mode misconfigured", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="agent_execution_mode_misconfigured",
        ) from exc

    try:
        require_execution_mode(execution_mode)
    except PermissionError:
        detail = f"agent_execution_{execution_mode.replace('-', '_')}"
        raise HTTPException(status_code=503, detail=detail)
    return execution_mode


def _require_identity_loop_mapper_boundary(payload: FitChefIdentityLoopMapperRequest) -> None:
    """Fail closed before runtime when identity mapping is unsafe to personalize."""

    if has_high_distress_boundary(
        payload.goal,
        payload.recent_pattern,
        payload.self_talk,
        payload.trigger_context,
    ):
        raise HTTPException(
            status_code=400,
            detail=FITCHEF_HIGH_DISTRESS_BOUNDARY_DETAIL,
        )


def _vip_error_response(status_code: int, detail: object) -> JSONResponse:
    """Return the frozen VIP error envelope for this VIP structured route."""

    message = detail if isinstance(detail, str) and detail else "fitchef_identity_loop_mapper_error"
    code = _VIP_ERROR_CODE_BY_DETAIL.get(message, message)
    return JSONResponse(
        status_code=status_code,
        content=vip_error(code=code, message=message),
    )


async def _parse_fitchef_support_handoff_request(
    request: Request,
) -> FitChefSupportHandoffRequest:
    """Parse the frozen request only after auth and feature admission."""

    content_type = request.headers.get("content-type")
    if not content_type or content_type.partition(";")[0].lower() != "application/json":
        raise HTTPException(
            status_code=422,
            detail=FITCHEF_SUPPORT_HANDOFF_VALIDATION_DETAIL,
        )

    try:
        raw_payload = await request.json()
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise HTTPException(
            status_code=422,
            detail=FITCHEF_SUPPORT_HANDOFF_VALIDATION_DETAIL,
        ) from None

    try:
        payload: FitChefSupportHandoffRequest
        payload = FitChefSupportHandoffRequest.model_validate(raw_payload)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail=FITCHEF_SUPPORT_HANDOFF_VALIDATION_DETAIL,
        ) from None
    return payload


@router.post(
    "/api/v1/pro/fitchef/explain",
    response_model=FitChefDistortionSimulatorResponse,
    responses={
        200: {"description": "FitChef distortion simulator generated"},
        400: {"description": "Unsafe AI input blocked", "model": FitChefCoachingErrorResponse},
        401: {"description": "API key required", "model": FitChefCoachingErrorResponse},
        403: {"description": "PRO tier required", "model": FitChefCoachingErrorResponse},
        503: {
            "description": "Feature disabled or provider unavailable",
            "model": FitChefCoachingErrorResponse,
        },
        504: {"description": "LLM provider call timed out", "model": FitChefCoachingErrorResponse},
        **RATE_LIMIT_429_RESPONSES,
    },
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def fitchef_distortion_simulator(
    payload: FitChefDistortionSimulatorRequest,
    request: Request,
    pro_key: str = Depends(require_pro_tier),
) -> FitChefDistortionSimulatorResponse:
    """Generate the bounded PRO distortion-simulator surface."""

    if not _is_fitchef_structured_enabled():
        raise HTTPException(status_code=503, detail="FEATURE_FITCHEF_STRUCTURED_COACH is disabled")

    execution_mode = _require_fitchef_structured_mode()
    task = FitChefDistortionSimulatorTaskEnvelope(
        mode=execution_mode,
        input=FitChefDistortionSimulatorInput(
            safe_situation=require_safe_ai_agent_input(payload.situation),
            safe_automatic_thought=require_safe_ai_agent_input(payload.automatic_thought),
            safe_emotion=require_safe_ai_agent_input(payload.emotion),
            safe_goal=(
                require_safe_ai_agent_input(payload.goal)
                if payload.goal is not None and payload.goal.strip()
                else None
            ),
            api_key=pro_key,
            endpoint=str(request.url.path),
            method=request.method,
        ),
    )
    result = await fitchef_runtime.run_distortion_simulator_task(task)
    return FitChefDistortionSimulatorResponse(
        scenario="distortion_simulator",
        distortion_labels=result.distortion_labels,
        why_it_matches=result.why_it_matches,
        evidence_for=result.evidence_for,
        evidence_against=result.evidence_against,
        balanced_reframe=result.balanced_reframe,
        next_small_action=result.next_small_action,
        sources=[
            FitChefCoachingSourceItem(
                file=item.file,
                preview=item.preview,
                score=item.score,
            )
            for item in result.sources
        ],
        confidence=result.confidence,
        warnings=result.warnings,
        quota_state=result.quota_state,
        transparency_notice_id=result.transparency_notice_id,
        wellness_boundary=result.wellness_boundary,
    )


@support_handoff_router.post(
    "/api/v1/pro/fitchef/recommend",
    dependencies=[Depends(require_pro_tier)],
    response_model=FitChefSupportHandoffResponse,
    summary="Select deterministic FitChef support handoff",
    description=(
        "POST /api/v1/pro/fitchef/recommend returns one deterministic, non-executing "
        "product-surface handoff selected solely from the request's explicit support_need. "
        "It does not inspect a plan, history, adherence, goal, or prior FitChef response; "
        "infer friction or intent; call RAG, an AI provider, or an LLM; invoke the target "
        "surface; or create or change a plan."
    ),
    responses={
        200: {"description": "Deterministic FitChef support handoff selected"},
        401: {"description": "API key required", "model": FitChefCoachingErrorResponse},
        403: {"description": "PRO tier required", "model": FitChefCoachingErrorResponse},
        422: {
            "description": "Request validation failed",
            "model": FitChefCoachingErrorResponse,
        },
        503: {"description": "Feature disabled", "model": FitChefCoachingErrorResponse},
    },
    openapi_extra={"requestBody": _FITCHEF_SUPPORT_HANDOFF_REQUEST_BODY_OPENAPI},
)
async def fitchef_support_handoff(request: Request) -> FitChefSupportHandoffResponse:
    """Return one non-executing product-surface descriptor for a PRO caller."""

    if not _is_fitchef_structured_enabled():
        raise HTTPException(status_code=503, detail=FITCHEF_STRUCTURED_DISABLED_DETAIL)

    payload = await _parse_fitchef_support_handoff_request(request)
    return build_fitchef_support_handoff(support_need=payload.support_need)


@vip_router.post(
    "/api/v1/vip/fitchef/insight",
    response_model=FitChefIdentityLoopMapperResponse,
    responses={
        200: {"description": "FitChef identity-loop mapper generated"},
        400: {"description": "Unsafe AI input blocked", "model": FitChefVipCoachingErrorResponse},
        403: {"description": "VIP tier required", "model": FitChefVipCoachingErrorResponse},
        503: {
            "description": "Feature disabled or provider unavailable",
            "model": FitChefVipCoachingErrorResponse,
        },
        504: {
            "description": "LLM provider call timed out",
            "model": FitChefVipCoachingErrorResponse,
        },
        422: {"description": "Request validation failed", "model": FitChefVipCoachingErrorResponse},
        **FITCHEF_VIP_429_RESPONSES,
    },
)
@limit_if_available(RATE_LIMIT_INSIGHT)
async def fitchef_identity_loop_mapper(
    payload: FitChefIdentityLoopMapperRequest,
    request: Request,
    vip_key: str = Depends(require_vip_tier),
) -> FitChefIdentityLoopMapperResponse | JSONResponse:
    """Generate the bounded VIP identity-loop mapper surface."""

    try:
        if not _is_fitchef_structured_enabled():
            raise HTTPException(status_code=503, detail=FITCHEF_STRUCTURED_DISABLED_DETAIL)

        execution_mode = _require_fitchef_structured_mode()
        _require_identity_loop_mapper_boundary(payload)
        task = FitChefIdentityLoopMapperTaskEnvelope(
            mode=execution_mode,
            input=FitChefIdentityLoopMapperInput(
                safe_goal=require_safe_ai_agent_input(payload.goal),
                safe_recent_pattern=require_safe_ai_agent_input(payload.recent_pattern),
                safe_self_talk=require_safe_ai_agent_input(payload.self_talk),
                safe_trigger_context=(
                    require_safe_ai_agent_input(payload.trigger_context)
                    if payload.trigger_context is not None and payload.trigger_context.strip()
                    else None
                ),
                api_key=vip_key,
                endpoint=str(request.url.path),
                method=request.method,
            ),
        )
        result = await fitchef_runtime.run_identity_loop_mapper_task(task)
    except HTTPException as exc:
        return _vip_error_response(status_code=exc.status_code, detail=exc.detail)

    return FitChefIdentityLoopMapperResponse(
        scenario="identity_loop_mapper",
        identity_loop=FitChefIdentityLoopView(
            belief=result.identity_loop.belief,
            behavior=result.identity_loop.behavior,
            short_term_reward=result.identity_loop.short_term_reward,
            long_term_cost=result.identity_loop.long_term_cost,
        ),
        identity_shift_statement=result.identity_shift_statement,
        replacement_action=result.replacement_action,
        repair_if_slip=result.repair_if_slip,
        sources=[
            FitChefCoachingSourceItem(
                file=item.file,
                preview=item.preview,
                score=item.score,
            )
            for item in result.sources
        ],
        confidence=result.confidence,
        warnings=result.warnings,
        quota_state=result.quota_state,
        transparency_notice_id=result.transparency_notice_id,
        wellness_boundary=result.wellness_boundary,
    )
