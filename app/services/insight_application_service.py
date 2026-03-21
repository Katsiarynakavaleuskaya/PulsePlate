"""Application service for insight execution.

RU: Application service для /insight execution path.
EN: Application service for the /insight execution path.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

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
from core.insight.llm_provider_loader import LLMProvider
from core.ai import prepare_insight_runtime

INSIGHT_TEXT_MAX_LENGTH = 2000


def _ensure_insight_text_length(prompt_text: str) -> str:
    """Return prompt text trimmed to the canonical insight limit."""

    return prompt_text[:INSIGHT_TEXT_MAX_LENGTH]


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
        route_path=route_path,
        route_type=prepared_runtime.decision.route_type.value,
        user_tier=user_tier,
    )
    insight_text = runtime_result.insight[:INSIGHT_TEXT_MAX_LENGTH]
    source_items = [source_item_factory(**item) for item in runtime_result.source_dicts]
    return response_factory(
        provider=runtime_result.provider_name,
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
