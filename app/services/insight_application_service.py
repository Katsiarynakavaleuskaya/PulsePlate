"""Application service for insight execution.

RU: Application service для /insight execution path.
EN: Application service for the /insight execution path.
"""

from __future__ import annotations

import inspect
import logging
import os
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status

from app.services.insight_runtime import generate_traced_insight
from app.utils.feature_flags import (
    is_philosophy_linguistic_enabled,
    is_philosophy_phase12_enabled,
    is_philosophy_pragmatic_enabled,
    is_philosophy_router_enabled,
    is_philosophy_validation_enabled,
    is_recursive_rag_enabled,
)
from core.ai.insight_runtime import InsightTransparencyNotice
from core.knowledge.store import KnowledgeStore
from core.insight.llm_provider_loader import LLMProvider
from core.ai import prepare_insight_runtime

INSIGHT_TEXT_MAX_LENGTH = 2000
logger = logging.getLogger(__name__)


def _ensure_insight_text_length(prompt_text: str) -> str:
    """Return prompt text when within limits; reject oversized prompts."""

    if len(prompt_text) > INSIGHT_TEXT_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Prompt too long",
        )
    return prompt_text


def _resolve_effective_provider_name(
    *,
    runtime_provider_name: str,
    prepared_provider: LLMProvider,
) -> str:
    """Return actual provider name after fallback without changing public contract."""

    if runtime_provider_name == "philosophical_runtime":
        return runtime_provider_name

    active_provider_name = getattr(prepared_provider, "active_provider_name", None)
    if isinstance(active_provider_name, str) and active_provider_name:
        return active_provider_name

    return runtime_provider_name


async def _maybe_promote_knowledge_candidates(
    *,
    knowledge_store: KnowledgeStore | None,
    candidates: list[Any],
) -> None:
    """Best-effort promotion must never break the user response path."""

    if knowledge_store is None or not candidates:
        return

    try:
        promote_result = knowledge_store.promote(candidates)
        if inspect.isawaitable(promote_result):
            await promote_result
    except Exception:
        logger.warning(
            "Knowledge promotion failed; response path continues without persistence",
            exc_info=True,
        )


async def execute_insight_request(
    req: Any,
    *,
    route_path: str,
    user_tier: str,
    subject_id: int | None = None,
    input_guard: Callable[[str], object],
    provider_loader: Callable[[], LLMProvider | None],
    transparency_loader: Callable[[], tuple[str, str] | InsightTransparencyNotice],
    direct_provider_factory: Callable[[], LLMProvider] | None = None,
    knowledge_store: KnowledgeStore | None = None,
    response_factory: Callable[..., Any],
    source_item_factory: Callable[..., Any],
) -> Any:
    """Execute the shared insight runtime path behind legacy adapters."""

    input_guard(req.text)
    prompt_input = _ensure_insight_text_length(req.text)
    use_rag = str(os.getenv("FEATURE_RAG", "")).strip().lower() in {"1", "true", "on", "yes"}

    philosophy_router_enabled = is_philosophy_router_enabled()
    philosophy_linguistic_enabled = is_philosophy_linguistic_enabled()
    prepared_runtime = prepare_insight_runtime(
        text=prompt_input,
        use_rag=use_rag,
        philosophy_router_enabled=philosophy_router_enabled,
        philosophy_linguistic_enabled=philosophy_linguistic_enabled,
        provider_loader=provider_loader,
        transparency_loader=transparency_loader,
        direct_provider_factory=direct_provider_factory,
    )

    runtime_result = await generate_traced_insight(
        runtime=prepared_runtime.runtime,
        text=prompt_input,
        lang=None,
        provider=prepared_runtime.provider,
        use_rag=use_rag,
        philo_validation_enabled=is_philosophy_validation_enabled(),
        recursive_rag_enabled=is_recursive_rag_enabled(),
        subject_id=subject_id,
        philosophy_router_enabled=philosophy_router_enabled,
        philosophy_phase12_enabled=is_philosophy_phase12_enabled(),
        philosophy_linguistic_enabled=philosophy_linguistic_enabled,
        philosophy_pragmatic_enabled=is_philosophy_pragmatic_enabled(),
        knowledge_policy=prepared_runtime.knowledge_policy,
        route_path=route_path,
        route_type=prepared_runtime.decision.route_type.value,
        user_tier=user_tier,
    )
    await _maybe_promote_knowledge_candidates(
        knowledge_store=knowledge_store,
        candidates=list(runtime_result.knowledge_candidates),
    )
    insight_text = runtime_result.insight[:INSIGHT_TEXT_MAX_LENGTH]
    source_items = [source_item_factory(**item) for item in runtime_result.source_dicts]
    effective_provider_name = _resolve_effective_provider_name(
        runtime_provider_name=runtime_result.provider_name,
        prepared_provider=prepared_runtime.provider,
    )
    return response_factory(
        provider=effective_provider_name,
        insight=insight_text,
        sources=source_items,
        confidence=runtime_result.confidence,
        rag_used=runtime_result.rag_used,
        hops=runtime_result.hops,
        latency_ms=runtime_result.latency_ms,
        route_type=runtime_result.metadata.route_type,
        depth_used=runtime_result.metadata.depth_used,
        verification_rate=runtime_result.metadata.verification_rate,
        falsifiability_rate=runtime_result.metadata.falsifiability_rate,
        contradiction_count=runtime_result.metadata.contradiction_count,
        reason_codes=runtime_result.metadata.reason_codes,
        optimization_applied=runtime_result.metadata.optimization_applied,
        automated_analysis=True,
        transparency_notice_id=prepared_runtime.transparency_notice.surface_id,
        wellness_boundary=prepared_runtime.transparency_notice.wellness_boundary,
    )
