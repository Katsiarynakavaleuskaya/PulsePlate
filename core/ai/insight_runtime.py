"""Core AI facade for insight runtime ownership.

RU: Канонический core/ai facade для ownership insight runtime.
EN: Canonical core/ai facade for insight runtime ownership.

The goal is to keep FastAPI/HTTP concerns out of ``core/`` while consolidating
AI runtime preparation behind a stable bounded-context package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from core.knowledge.policy import KnowledgePolicy
from core.insight.llm_provider_loader import (
    LLMProvider,
    LLMProviderFactory,
    load_llm_get_provider,
)
from core.insight.philosophical_runtime import (
    PhilosophicalRuntime,
    PhilosophyRolloutPolicy,
    RouteDecision,
    RouteType,
)
from core.rag.contracts import RAGDegradedReason


class InsightProviderLoadError(RuntimeError):
    """Raised when provider resolution fails inside the bounded context."""


class InsightTransparencyUnavailableError(RuntimeError):
    """Raised when required transparency metadata is unavailable or malformed."""


@dataclass(frozen=True)
class InsightTransparencyNotice:
    """Required transparency metadata for AI-generated insight output."""

    surface_id: str
    wellness_boundary: str


@dataclass(frozen=True)
class PreparedInsightRuntime:
    """Prepared insight runtime state before app-layer execution."""

    runtime: PhilosophicalRuntime
    decision: RouteDecision
    rollout_policy: PhilosophyRolloutPolicy
    provider: LLMProvider
    transparency_notice: InsightTransparencyNotice
    knowledge_policy: KnowledgePolicy


class DirectInsightProviderStub:
    """Provider stub used when the runtime can answer locally without an LLM call."""

    name: str = "philosophical_runtime"

    async def generate(self, text: str) -> str:
        raise RuntimeError("Direct runtime route must not call provider.generate")


def load_insight_provider(
    *,
    provider_factory_loader: Callable[[], LLMProviderFactory] | None = None,
) -> LLMProvider:
    """Load configured LLM provider while preserving lazy import behavior."""

    if provider_factory_loader is None:
        provider_factory_loader = load_llm_get_provider

    try:
        get_provider = provider_factory_loader()
    except Exception as exc:  # pragma: no cover - covered via legacy/service tests
        raise InsightProviderLoadError("LLM module is not available") from exc

    try:
        provider = get_provider()
    except Exception as exc:  # pragma: no cover - covered via legacy/service tests
        raise InsightProviderLoadError("LLM provider initialization failed") from exc
    if provider is None:
        raise InsightProviderLoadError("No LLM provider configured")
    return provider


def require_ai_generated_insight_notice(
    *,
    registry_loader: Callable[[], Mapping[str, object]] | None = None,
) -> InsightTransparencyNotice:
    """Return the required transparency notice or fail closed."""

    if registry_loader is None:
        from core.compliance import get_transparency_registry

        registry_loader = get_transparency_registry

    try:
        transparency_notice = registry_loader().get("ai_generated_insight")
    except Exception as exc:  # pragma: no cover - covered via legacy/service tests
        raise InsightTransparencyUnavailableError("transparency_registry_unavailable") from exc
    if not isinstance(transparency_notice, dict):
        raise InsightTransparencyUnavailableError("transparency_registry_unavailable")

    surface_id = transparency_notice.get("surface_id")
    boundary = transparency_notice.get("boundary")
    if (
        not isinstance(surface_id, str)
        or not surface_id
        or not isinstance(boundary, str)
        or not boundary
    ):
        raise InsightTransparencyUnavailableError("transparency_registry_unavailable")

    return InsightTransparencyNotice(
        surface_id=surface_id,
        wellness_boundary=boundary,
    )


def _coerce_transparency_notice(
    loaded_notice: tuple[str, str] | InsightTransparencyNotice,
) -> InsightTransparencyNotice:
    """Normalize custom transparency-loader output into the canonical notice."""

    if isinstance(loaded_notice, InsightTransparencyNotice):
        return loaded_notice

    try:
        surface_id, boundary = loaded_notice
    except Exception as exc:
        raise InsightTransparencyUnavailableError("transparency_registry_unavailable") from exc

    if (
        not isinstance(surface_id, str)
        or not surface_id
        or not isinstance(boundary, str)
        or not boundary
    ):
        raise InsightTransparencyUnavailableError("transparency_registry_unavailable")

    return InsightTransparencyNotice(
        surface_id=surface_id,
        wellness_boundary=boundary,
    )


def prepare_insight_runtime(
    *,
    text: str,
    use_rag: bool,
    philosophy_router_enabled: bool,
    philosophy_linguistic_enabled: bool,
    philosophy_phase12_enabled: bool = False,
    philosophy_pragmatic_enabled: bool = False,
    provider_loader: Callable[[], LLMProvider | None] | None = None,
    transparency_loader: Callable[[], tuple[str, str] | InsightTransparencyNotice] | None = None,
    direct_provider_factory: Callable[[], LLMProvider] | None = None,
) -> PreparedInsightRuntime:
    """Prepare runtime, route decision, provider, and transparency metadata.

    RU: Подготовить runtime/route/provider/transparency без HTTP-зависимостей.
    EN: Prepare runtime/route/provider/transparency without HTTP dependencies.
    """

    runtime = PhilosophicalRuntime()
    rollout_policy = PhilosophyRolloutPolicy(
        router_enabled=philosophy_router_enabled,
        phase12_enabled=philosophy_phase12_enabled,
        linguistic_enabled=philosophy_linguistic_enabled,
        pragmatic_enabled=philosophy_pragmatic_enabled,
    )
    decision = runtime.preview_route(
        text=text,
        lang=None,
        router_enabled=rollout_policy.preview_router_enabled,
        use_rag=use_rag,
    )

    if transparency_loader is None:
        transparency_notice = require_ai_generated_insight_notice()
    else:
        transparency_notice = _coerce_transparency_notice(transparency_loader())

    if decision.needs_generation:
        provider = load_insight_provider() if provider_loader is None else provider_loader()
        if provider is None:
            raise InsightProviderLoadError("No LLM provider configured")
    else:
        provider_factory = direct_provider_factory or DirectInsightProviderStub
        provider = provider_factory()

    knowledge_policy = _build_default_knowledge_policy(decision=decision)

    return PreparedInsightRuntime(
        runtime=runtime,
        decision=decision,
        rollout_policy=rollout_policy,
        provider=provider,
        transparency_notice=transparency_notice,
        knowledge_policy=knowledge_policy,
    )


def _build_default_knowledge_policy(*, decision: RouteDecision) -> KnowledgePolicy:
    """Build the canonical runtime knowledge policy from the route decision."""

    route_type_value = getattr(decision.route_type, "value", decision.route_type)
    allow_knowledge = route_type_value == RouteType.RAG_FACTUAL.value
    return KnowledgePolicy(
        enabled=allow_knowledge,
        allow_reads=allow_knowledge,
        allow_promotion=allow_knowledge,
        min_confidence=0.7,
        require_rag_factual_route=True,
        deny_degraded_reasons=tuple(reason.value for reason in RAGDegradedReason),
        subject_scope_required=True,
        rail="product_ai_runtime",
    )
