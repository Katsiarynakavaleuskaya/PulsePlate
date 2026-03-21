"""Canonical AI bounded-context facade.

RU: Канонический facade для AI bounded context.
EN: Canonical facade for the AI bounded context.
"""

from core.ai.insight_runtime import (
    DirectInsightProviderStub,
    InsightProviderLoadError,
    InsightTransparencyNotice,
    InsightTransparencyUnavailableError,
    PreparedInsightRuntime,
    load_insight_provider,
    prepare_insight_runtime,
    require_ai_generated_insight_notice,
)

__all__ = [
    "DirectInsightProviderStub",
    "InsightProviderLoadError",
    "InsightTransparencyNotice",
    "InsightTransparencyUnavailableError",
    "PreparedInsightRuntime",
    "load_insight_provider",
    "prepare_insight_runtime",
    "require_ai_generated_insight_notice",
]
