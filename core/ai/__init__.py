"""Canonical AI bounded-context facade.

RU: Канонический facade для AI bounded context.
EN: Canonical facade for the AI bounded context.
"""

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
