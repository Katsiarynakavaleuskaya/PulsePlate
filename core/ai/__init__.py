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
from core.ai.exact_fuzzy_cache import (
    ExactFuzzyCacheLineage,
    ExactFuzzyCacheLookupRequest,
    ExactFuzzyCacheLookupResult,
    ExactFuzzyCacheRecord,
    ExactFuzzyMatchPolicy,
    build_exact_fuzzy_idempotency_key,
    build_exact_fuzzy_lineage,
    build_exact_fuzzy_record_id,
    create_exact_fuzzy_cache_record,
    match_exact_fuzzy_records,
    normalize_exact_fuzzy_query,
    to_stable_mapping,
)
from core.insight.philosophical_runtime import PhilosophyRolloutPolicy

__all__ = [
    "DirectInsightProviderStub",
    "ExactFuzzyCacheLineage",
    "ExactFuzzyCacheLookupRequest",
    "ExactFuzzyCacheLookupResult",
    "ExactFuzzyCacheRecord",
    "ExactFuzzyMatchPolicy",
    "InsightProviderLoadError",
    "KnowledgePolicy",
    "PhilosophyRolloutPolicy",
    "InsightTransparencyNotice",
    "InsightTransparencyUnavailableError",
    "PreparedInsightRuntime",
    "build_exact_fuzzy_idempotency_key",
    "build_exact_fuzzy_lineage",
    "build_exact_fuzzy_record_id",
    "create_exact_fuzzy_cache_record",
    "load_insight_provider",
    "match_exact_fuzzy_records",
    "normalize_exact_fuzzy_query",
    "prepare_insight_runtime",
    "require_ai_generated_insight_notice",
    "to_stable_mapping",
]
