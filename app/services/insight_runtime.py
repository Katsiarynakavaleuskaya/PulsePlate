"""App-layer tracing adapters for the insight runtime.

RU: App-layer адаптеры для insight runtime, чтобы tracing не жил в core/ и legacy_app.py.
EN: App-layer adapters for the insight runtime so tracing stays out of core/ and legacy_app.py.
"""

from __future__ import annotations

import inspect
import os
from typing import Any

import core.rag.orchestration as rag_orchestration

from app.telemetry.genai import (
    chain_span,
    finalize_llm_span,
    llm_span,
    retrieval_span,
    set_attributes,
)
from app.utils.feature_flags import (
    _is_truthy,
    is_philosophy_linguistic_enabled,
    is_philosophy_phase12_enabled,
    is_philosophy_pragmatic_enabled,
    is_philosophy_router_enabled,
    is_philosophy_validation_enabled,
    is_recursive_rag_enabled,
    is_recursive_rag_optimization_enabled,
)


class TracedInsightProvider:
    """Wrap insight provider calls with LLM spans in the app layer."""

    def __init__(self, provider: Any, *, user_tier: str, route: str) -> None:
        self._provider = provider
        self._user_tier = user_tier
        self._route = route
        self.name = str(getattr(provider, "name", "unknown"))

    async def generate(self, text: str) -> str:
        """Execute provider.generate with a traced LLM span."""

        with llm_span(
            provider_name=self.name,
            user_tier=self._user_tier,
            route=self._route,
            prompt_text=text,
        ) as span:
            result = self._provider.generate(text)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, str):
                raise TypeError("Insight provider must return a string response")
            finalize_llm_span(span, result)
            return result


def insight_feature_flag_state() -> dict[str, bool]:
    """Return deterministic feature-flag snapshot for insight tracing."""

    return {
        "insight": _is_truthy(os.getenv("FEATURE_INSIGHT", "false")),
        "philosophy_router": is_philosophy_router_enabled(),
        "philosophy_phase12": is_philosophy_phase12_enabled(),
        "philosophy_linguistic": is_philosophy_linguistic_enabled(),
        "philosophy_pragmatic": is_philosophy_pragmatic_enabled(),
        "philosophy_validation": is_philosophy_validation_enabled(),
        "rag": _is_truthy(os.getenv("FEATURE_RAG", "false")),
        "rag_recursive": is_recursive_rag_enabled(),
        "rag_recursive_optimization": is_recursive_rag_optimization_enabled(),
        "rag_vector": _is_truthy(os.getenv("FEATURE_RAG_VECTOR", "false")),
    }


async def _traced_retrieve_and_validate_rag(
    prompt_input: str,
    *,
    max_chunks: int,
    philo_validation_enabled: bool,
    recursive_rag_enabled: bool,
    subject_id: int | None,
    user_tier: str,
    route_path: str,
) -> Any:
    """Wrap RAG retrieval in a deterministic retriever span."""

    with retrieval_span(
        user_tier=user_tier,
        route=route_path,
        max_chunks=max_chunks,
    ) as span:
        rag_result = await rag_orchestration.retrieve_and_validate_rag(
            prompt_input,
            max_chunks=max_chunks,
            philo_validation_enabled=philo_validation_enabled,
            recursive_rag_enabled=recursive_rag_enabled,
            subject_id=subject_id,
        )
        set_attributes(span, **{"pulseplate.rag.hops": rag_result.hops})
        return rag_result


async def generate_traced_insight(
    *,
    runtime: Any,
    text: str,
    lang: str | None,
    provider: Any,
    use_rag: bool,
    philo_validation_enabled: bool,
    recursive_rag_enabled: bool,
    subject_id: int | None,
    philosophy_router_enabled: bool,
    philosophy_phase12_enabled: bool,
    philosophy_linguistic_enabled: bool,
    philosophy_pragmatic_enabled: bool,
    route_path: str,
    route_type: str,
    user_tier: str,
) -> Any:
    """Run philosophical insight generation with app-layer tracing only."""

    traced_provider = TracedInsightProvider(
        provider,
        user_tier=user_tier,
        route=route_path,
    )

    async def _rag_retriever(
        prompt_input: str,
        *,
        max_chunks: int,
        philo_validation_enabled: bool,
        recursive_rag_enabled: bool,
        subject_id: int | None,
    ) -> Any:
        return await _traced_retrieve_and_validate_rag(
            prompt_input,
            max_chunks=max_chunks,
            philo_validation_enabled=philo_validation_enabled,
            recursive_rag_enabled=recursive_rag_enabled,
            subject_id=subject_id,
            user_tier=user_tier,
            route_path=route_path,
        )

    with chain_span(
        "insight chain",
        user_tier=user_tier,
        route=route_path,
        route_type=route_type,
        feature_flags=insight_feature_flag_state(),
    ):
        return await runtime.generate_insight(
            text=text,
            lang=lang,
            provider=traced_provider,
            use_rag=use_rag,
            philo_validation_enabled=philo_validation_enabled,
            recursive_rag_enabled=recursive_rag_enabled,
            subject_id=subject_id,
            philosophy_router_enabled=philosophy_router_enabled,
            philosophy_phase12_enabled=philosophy_phase12_enabled,
            philosophy_linguistic_enabled=philosophy_linguistic_enabled,
            philosophy_pragmatic_enabled=philosophy_pragmatic_enabled,
            rag_retriever=_rag_retriever,
        )


__all__ = [
    "TracedInsightProvider",
    "generate_traced_insight",
    "insight_feature_flag_state",
]
