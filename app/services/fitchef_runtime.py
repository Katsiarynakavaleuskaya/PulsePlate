"""FitChef runtime orchestration. / Оркестрация runtime FitChef."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Any, Callable, Literal, cast

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder

from app.middleware.api_tiers import derive_subject_id_from_api_key
from app.schemas.fitchef import (
    FitChefCoachInsightResult,
    FitChefCoachInsightTaskEnvelope,
    FitChefMascotInsightResult,
    FitChefMascotInsightTaskEnvelope,
    FitChefQuotaState,
    FitChefShoppingFollowupResult,
    FitChefShoppingFollowupTaskEnvelope,
    FitChefSourceItem,
    FitChefWeeklyPlanResult,
    FitChefWeeklyPlanTaskEnvelope,
)
from app.schemas.shopping_list import ShoppingListDTO
from app.security.agent_control_plane import (
    AUDIT_SIGNING_KEY_ENV,
    persist_audit_envelope,
    require_policy_allow,
    sign_audit_envelope,
)
from app.security.llm_monthly_quota import attempt_consume_llm_monthly_quota
from app.security.server_salt import require_server_salt
from core.compliance import get_transparency_registry, sanitize_chunk_preview
from core.data_sanitizer import sanitize_rag_markdown
from core.insight.fitchef_companion import build_mascot_prompt, prepare_mascot_draft
from core.pii_redaction import redact_pii_from_text

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS: float = 60.0
CBT_POLICY_ALLOWLIST = {
    ("rag.retrieve", "corpus://cbt-agent"),
    ("llm.generate", "provider://default"),
}
WeeklyPlanBuilder = Callable[..., Any]
ShoppingFollowupBuilder = Callable[..., ShoppingListDTO]


def _build_cbt_prompt(query: str, rag_context: str) -> str:
    """Build CBT prompt. / Собрать CBT prompt."""

    system_prompt = """You are a supportive wellness coach using evidence-based CBT (Cognitive Behavioral Therapy) principles. Your role is to:

1. Help users identify and challenge unhelpful thought patterns
2. Suggest practical CBT techniques (thought records, cognitive restructuring)
3. Encourage self-compassion and gradual progress
4. Focus on nutrition and wellness goals

IMPORTANT BOUNDARIES:
- You are NOT a therapist and cannot provide therapy or diagnose conditions
- Avoid medical advice; suggest consulting professionals for health concerns
- If someone expresses crisis/self-harm thoughts, encourage them to seek professional help
- Use non-judgmental, supportive language

Respond with practical, actionable suggestions based on CBT principles."""

    if rag_context:
        return f"""{system_prompt}

RELEVANT CBT KNOWLEDGE:
{rag_context}

USER QUESTION:
{query}

Provide a helpful, CBT-informed response:"""
    return f"""{system_prompt}

USER QUESTION:
{query}

Provide a helpful, CBT-informed response:"""


def _sha256_hex(value: str) -> str:
    """Return audit-safe sha256 digest. / Вернуть audit-safe sha256 digest."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_weekly_user_profile(profile_data: dict[str, Any]) -> Any:
    """Create UserProfile with legacy-safe defaults. / Собрать UserProfile с совместимыми fallback."""

    from core.targets import UserProfile

    diet_flags = profile_data.get("diet_flags", [])
    if isinstance(diet_flags, list):
        diet_flags = set(diet_flags)

    medical_conditions = profile_data.get("medical_conditions", [])
    if isinstance(medical_conditions, list):
        medical_conditions = set(medical_conditions)

    age_raw = profile_data.get("age")
    try:
        age_val: int = 30 if age_raw is None else int(age_raw)
    except (TypeError, ValueError):
        age_val = 30

    height_raw = profile_data.get("height_cm")
    try:
        height_val: float = 175.0 if height_raw is None else float(height_raw)
    except (TypeError, ValueError):
        height_val = 175.0

    weight_raw = profile_data.get("weight_kg")
    try:
        weight_val: float = 70.0 if weight_raw is None else float(weight_raw)
    except (TypeError, ValueError):
        weight_val = 70.0

    sex_raw = profile_data.get("sex")
    sex_value: Literal["male", "female"] = "male"
    if sex_raw in {"male", "female"}:
        sex_value = cast(Literal["male", "female"], sex_raw)

    profile = UserProfile(
        sex=sex_value,
        age=age_val,
        height_cm=height_val,
        weight_kg=weight_val,
        activity=cast(
            Literal["sedentary", "light", "moderate", "active", "very_active"],
            profile_data.get("activity") or "moderate",
        ),
        goal=cast(Literal["loss", "maintain", "gain"], profile_data.get("goal") or "maintain"),
        deficit_pct=profile_data.get("deficit_pct"),
        surplus_pct=profile_data.get("surplus_pct"),
        bodyfat=profile_data.get("bodyfat"),
        region=profile_data.get("region") or "BY",
        timezone=profile_data.get("timezone") or "UTC",
        diet_flags=diet_flags,
        life_stage=cast(
            Literal["child", "teen", "adult", "pregnant", "lactating", "elderly"],
            profile_data.get("life_stage") or "adult",
        ),
        medical_conditions=medical_conditions,
    )
    return profile


def build_weekly_user_profile(profile_data: dict[str, Any]) -> Any:
    """Public profile helper for weekly runtime. / Публичный helper профиля для weekly runtime."""

    profile = _build_weekly_user_profile(profile_data)
    return profile


def _run_weekly_menu_builder(
    profile_data: dict[str, Any],
    menu_builder: WeeklyPlanBuilder,
) -> dict[str, Any]:
    """Run weekly menu builder and serialize result. / Выполнить weekly builder и сериализовать результат."""

    profile = build_weekly_user_profile(profile_data)
    menu = menu_builder(profile)
    if menu is None:
        return {"mode": "echo"}
    encoded_menu = jsonable_encoder(menu)
    if isinstance(encoded_menu, dict):
        return encoded_menu
    return {"mode": "echo"}


def _persist_privileged_action_audit(
    *,
    action: str,
    target: str,
    mode: str,
    endpoint: str,
    metadata: dict[str, object],
) -> None:
    """Persist privileged audit envelope. / Сохранить audit envelope привилегированного действия."""

    decision = require_policy_allow(action, target, allowlist=CBT_POLICY_ALLOWLIST)
    audit_metadata = {
        "endpoint": endpoint,
        "mode": mode,
        **metadata,
    }
    signing_secret = (os.getenv(AUDIT_SIGNING_KEY_ENV) or "").strip() or require_server_salt()
    envelope = sign_audit_envelope(
        decision,
        metadata=audit_metadata,
        secret=signing_secret,
    )
    persist_audit_envelope(envelope, metadata=audit_metadata)


async def run_coach_insight_task(
    task: FitChefCoachInsightTaskEnvelope,
) -> FitChefCoachInsightResult:
    """Run coach-insight orchestration. / Выполнить оркестрацию coach-insight."""

    safe_query = task.input.safe_query
    api_key = task.input.api_key
    endpoint = task.input.endpoint
    method = task.input.method

    rag_context_str = ""
    sources: list[FitChefSourceItem] = []
    confidence = 0.0
    rag_used = False
    quota_state: FitChefQuotaState = "not_consumed"
    warnings: list[str] = []
    redaction_applied = False
    sanitization_applied = False

    try:
        await run_in_threadpool(
            _persist_privileged_action_audit,
            action="rag.retrieve",
            target="corpus://cbt-agent",
            mode=task.mode,
            endpoint=endpoint,
            metadata={
                "method": method,
                "query_hash": _sha256_hex(safe_query),
                "query_length": len(safe_query),
            },
        )
    except (PermissionError, RuntimeError) as exc:
        logger.error("RAG privileged-action gate failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="rag_retrieval_unavailable",
        ) from exc

    try:
        from core.rag.vector_rag import retrieve_context_structured

        rag_ctx = await run_in_threadpool(
            retrieve_context_structured,
            safe_query,
            max_chunks=5,
            agent_id="cbt-agent",
            user_tier="PRO",
            subject_id=derive_subject_id_from_api_key(api_key),
        )

        if rag_ctx.chunks:
            context_parts = []
            for chunk in rag_ctx.chunks:
                sanitized_chunk = sanitize_rag_markdown(chunk.content)
                if sanitized_chunk != chunk.content:
                    sanitization_applied = True
                sanitized_content = redact_pii_from_text(sanitized_chunk) or ""
                if sanitized_content != sanitized_chunk:
                    redaction_applied = True
                if not sanitized_content.strip():
                    continue
                context_parts.append(f"[{chunk.file}]\n{sanitized_content}")
                sources.append(
                    FitChefSourceItem(
                        chunk_id=chunk.chunk_id,
                        file=chunk.file,
                        preview=sanitize_chunk_preview(sanitized_content) or "",
                        score=chunk.score,
                    )
                )
            if context_parts:
                rag_used = True
                confidence = rag_ctx.confidence
                rag_context_str = "\n\n".join(context_parts)
    except Exception:
        logger.warning("RAG retrieval failed for CBT insight", exc_info=True)
        warnings.append("rag_retrieval_failed")

    if sanitization_applied:
        warnings.append("source_content_sanitized")
    if redaction_applied:
        warnings.append("source_content_redacted")

    transparency_notice = get_transparency_registry().get("ai_generated_insight")
    if transparency_notice is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="transparency_registry_unavailable",
        )
    notice_surface_id = transparency_notice.get("surface_id")
    notice_boundary = transparency_notice.get("boundary")
    if notice_surface_id is None or notice_boundary is None:
        logger.error("Transparency registry entry is incomplete for ai_generated_insight")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="transparency_registry_incomplete",
        )
    prompt = _build_cbt_prompt(safe_query, rag_context_str)

    try:
        await run_in_threadpool(
            _persist_privileged_action_audit,
            action="llm.generate",
            target="provider://default",
            mode=task.mode,
            endpoint=endpoint,
            metadata={
                "method": method,
                "prompt_hash": _sha256_hex(prompt),
                "prompt_length": len(prompt),
                "rag_used": rag_used,
                "source_count": len(sources),
            },
        )
    except (PermissionError, RuntimeError) as exc:
        logger.error("LLM privileged-action gate failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="llm_generation_unavailable",
        ) from exc

    try:
        allowed = await run_in_threadpool(
            attempt_consume_llm_monthly_quota,
            api_key,
            tier="PRO",
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="quota_exceeded",
            )
        quota_state = "consumed"

        from llm import get_provider

        provider = get_provider()
        insight_text = await asyncio.wait_for(
            run_in_threadpool(provider.generate, prompt),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        if not insight_text:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider returned empty response",
            )
    except ImportError:
        logger.error("LLM provider not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider not available",
        )
    except asyncio.TimeoutError:
        logger.error("LLM provider call timed out after %s seconds", LLM_TIMEOUT_SECONDS)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLM provider call timed out",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate CBT insight",
        ) from exc

    bounded_confidence = min(max(confidence, 0.0), 1.0)
    result = FitChefCoachInsightResult(
        insight=insight_text,
        rag_used=rag_used,
        sources=sources,
        confidence=bounded_confidence,
        uncertainty=round(max(0.0, 1.0 - bounded_confidence), 4),
        warnings=warnings,
        mode=task.mode,
        quota_state=quota_state,
        automated_analysis=True,
        transparency_notice_id=str(notice_surface_id),
        wellness_boundary=str(notice_boundary),
    )
    return result


async def run_weekly_plan_task(
    task: FitChefWeeklyPlanTaskEnvelope,
    *,
    menu_builder: WeeklyPlanBuilder | None,
) -> FitChefWeeklyPlanResult:
    """Run weekly-plan orchestration. / Выполнить оркестрацию weekly-plan."""

    if menu_builder is None:
        result = FitChefWeeklyPlanResult(menu={"mode": "echo"})
        return result

    menu_payload = await run_in_threadpool(
        _run_weekly_menu_builder,
        task.input.request_data,
        menu_builder,
    )
    result = FitChefWeeklyPlanResult(menu=menu_payload)
    return result


async def run_mascot_insight_task(
    task: FitChefMascotInsightTaskEnvelope,
) -> FitChefMascotInsightResult:
    """Run FitChef mascot insight orchestration. / Выполнить mascot-insight оркестрацию."""

    safe_query = task.input.safe_query
    api_key = task.input.api_key
    endpoint = task.input.endpoint
    method = task.input.method

    rag_context_str = ""
    sources: list[FitChefSourceItem] = []
    confidence = 0.0
    warnings: list[str] = []
    quota_state: FitChefQuotaState = "not_consumed"

    try:
        await run_in_threadpool(
            _persist_privileged_action_audit,
            action="rag.retrieve",
            target="corpus://cbt-agent",
            mode=task.mode,
            endpoint=endpoint,
            metadata={
                "method": method,
                "query_hash": _sha256_hex(safe_query),
                "query_length": len(safe_query),
            },
        )
    except (PermissionError, RuntimeError) as exc:
        logger.error("FitChef mascot RAG gate failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="rag_retrieval_unavailable",
        ) from exc

    try:
        from core.rag.vector_rag import retrieve_context_structured

        rag_ctx = await run_in_threadpool(
            retrieve_context_structured,
            safe_query,
            max_chunks=5,
            agent_id="fitchef-agent",
            user_tier="VIP",
            subject_id=derive_subject_id_from_api_key(api_key),
        )

        if rag_ctx.chunks:
            context_parts: list[str] = []
            for chunk in rag_ctx.chunks:
                sanitized_chunk = sanitize_rag_markdown(chunk.content)
                sanitized_content = redact_pii_from_text(sanitized_chunk) or ""
                if not sanitized_content.strip():
                    continue
                context_parts.append(f"[{chunk.file}]\n{sanitized_content}")
                sources.append(
                    FitChefSourceItem(
                        chunk_id=chunk.chunk_id,
                        file=chunk.file,
                        preview=sanitize_chunk_preview(sanitized_content) or "",
                        score=chunk.score,
                    )
                )
            if context_parts:
                rag_context_str = "\n\n".join(context_parts)
                confidence = rag_ctx.confidence
    except Exception:
        logger.warning("FitChef mascot RAG retrieval failed", exc_info=True)
        warnings.append("rag_retrieval_failed")

    transparency_notice = get_transparency_registry().get("ai_generated_insight")
    if transparency_notice is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="transparency_registry_unavailable",
        )
    notice_surface_id = transparency_notice.get("surface_id")
    notice_boundary = transparency_notice.get("boundary")
    if notice_surface_id is None or notice_boundary is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="transparency_registry_incomplete",
        )

    prompt = build_mascot_prompt(safe_query, rag_context_str)

    try:
        await run_in_threadpool(
            _persist_privileged_action_audit,
            action="llm.generate",
            target="provider://default",
            mode=task.mode,
            endpoint=endpoint,
            metadata={
                "method": method,
                "prompt_hash": _sha256_hex(prompt),
                "prompt_length": len(prompt),
                "source_count": len(sources),
            },
        )
    except (PermissionError, RuntimeError) as exc:
        logger.error("FitChef mascot LLM gate failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="llm_generation_unavailable",
        ) from exc

    try:
        allowed = await run_in_threadpool(
            attempt_consume_llm_monthly_quota,
            api_key,
            tier="VIP",
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="quota_exceeded",
            )
        quota_state = "consumed"

        from llm import get_provider

        provider = get_provider()
        raw_message = await asyncio.wait_for(
            run_in_threadpool(provider.generate, prompt),
            timeout=LLM_TIMEOUT_SECONDS,
        )
        if not raw_message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider returned empty response",
            )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider not available",
        ) from None
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLM provider call timed out",
        ) from None
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("FitChef mascot generation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="fitchef_mascot_unavailable",
        ) from exc

    prepared = prepare_mascot_draft(raw_message, query=safe_query)
    result: FitChefMascotInsightResult = FitChefMascotInsightResult(
        message=prepared.message,
        sources=sources,
        confidence=min(max(confidence, 0.0), 1.0),
        warnings=[*warnings, *prepared.warnings],
        action_items=prepared.action_items,
        mode=task.mode,
        quota_state=quota_state,
        transparency_notice_id=str(notice_surface_id),
        wellness_boundary=str(notice_boundary),
    )
    return result


def _run_shopping_followup_builder(
    task: FitChefShoppingFollowupTaskEnvelope,
    shopping_list_builder: ShoppingFollowupBuilder,
) -> ShoppingListDTO:
    """Run shopping-followup builder. / Выполнить builder shopping-followup."""

    if task.input.plan_data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error: plan_data is None",
        )

    shopping_list = shopping_list_builder(
        plan_data=task.input.plan_data,
        preferences=task.input.preferences,
        source="inline_plan",
    )
    return shopping_list


async def run_shopping_followup_task(
    task: FitChefShoppingFollowupTaskEnvelope,
    *,
    shopping_list_builder: ShoppingFollowupBuilder,
) -> FitChefShoppingFollowupResult:
    """Run shopping-followup orchestration. / Выполнить оркестрацию shopping-followup."""

    shopping_list = await run_in_threadpool(
        _run_shopping_followup_builder,
        task,
        shopping_list_builder,
    )
    result = FitChefShoppingFollowupResult(shopping_list=shopping_list)
    return result
