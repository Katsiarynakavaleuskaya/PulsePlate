"""Canonical AI bounded-context facade.

RU: Канонический facade для AI bounded context.
EN: Canonical facade for the AI bounded context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.ai.insight_runtime import (
        DirectInsightProviderStub,
        InsightProviderLoadError,
        KnowledgePolicy,
        InsightTransparencyNotice,
        InsightTransparencyUnavailableError,
        PreparedInsightRuntime,
        load_insight_provider,
        prepare_insight_runtime,
        require_ai_generated_insight_notice,
    )
    from core.insight.philosophical_runtime import PhilosophyRolloutPolicy

__all__ = [
    "DirectInsightProviderStub",
    "InsightProviderLoadError",
    "KnowledgePolicy",
    "PhilosophyRolloutPolicy",
    "InsightTransparencyNotice",
    "InsightTransparencyUnavailableError",
    "PreparedInsightRuntime",
    "load_insight_provider",
    "prepare_insight_runtime",
    "require_ai_generated_insight_notice",
]

_INSIGHT_RUNTIME_EXPORTS = {
    "DirectInsightProviderStub",
    "InsightProviderLoadError",
    "KnowledgePolicy",
    "InsightTransparencyNotice",
    "InsightTransparencyUnavailableError",
    "PreparedInsightRuntime",
    "load_insight_provider",
    "prepare_insight_runtime",
    "require_ai_generated_insight_notice",
}


def __getattr__(name: str) -> Any:
    if name in _INSIGHT_RUNTIME_EXPORTS:
        import importlib

        insight_runtime = importlib.import_module("core.ai.insight_runtime")
        return getattr(insight_runtime, name)
    if name == "PhilosophyRolloutPolicy":
        from core.insight.philosophical_runtime import PhilosophyRolloutPolicy

        return PhilosophyRolloutPolicy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
