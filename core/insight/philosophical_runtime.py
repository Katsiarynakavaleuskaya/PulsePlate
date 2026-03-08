"""Unified philosophical runtime for /insight.

RU: Runtime выбирает дешёвый/быстрый/надёжный путь ответа до вызова LLM.
EN: Runtime chooses a cheaper/faster/more reliable answer path before LLM calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, cast

from core.bmi.query import extract_bmi_inputs, render_bmi_query_answer
from core.insight.analytical import (
    AnalyticalSyntheticClassifier,
    FalsificationChecker,
    FalsificationReport,
    StatementKind,
    VerificationEnforcer,
    VerificationReport,
)
from core.insight.aristotelian import NonContradictionChecker, SyllogisticPromptBuilder
from core.insight.linguistic import (
    LanguageGameIdentifier,
    LanguageGameType,
    MeaningAsUseResolver,
    SpeechActClassifier,
    SpeechActType,
)
from core.insight.post_analytical import HermeneuticDepthOptimizer, PragmaticValidator
from core.insight.telemetry import record_runtime_metrics
from core.i18n import normalize_lang
import core.rag.orchestration as rag_orchestration
from core.rag.formatting import RAGSourceDict, build_rag_source_dicts

_APPROX_CHARS_PER_TOKEN = 4
_DEFAULT_BASELINE_DEPTH = 3
_DEFINITION_TEMPLATES = {
    "en": {
        "bmi": "BMI stands for body mass index. It estimates body size by comparing weight to height.",
        "bmr": "BMR stands for basal metabolic rate. It estimates how much energy your body uses at rest.",
        "tdee": "TDEE stands for total daily energy expenditure. It estimates your daily calorie burn including activity.",
        "protein": "Protein is a macronutrient that helps support muscles, recovery, and many body functions.",
        "calorie": "A calorie is a unit of energy used to describe how much energy food provides and the body uses.",
    },
    "ru": {
        "bmi": "BMI означает индекс массы тела. Он оценивает размер тела, сопоставляя вес и рост.",
        "bmr": "BMR означает базовый обмен веществ. Он оценивает, сколько энергии тело тратит в покое.",
        "tdee": "TDEE означает общий дневной расход энергии. Он оценивает суточный расход калорий с учётом активности.",
        "protein": "Белок — это макронутриент, который помогает поддерживать мышцы, восстановление и многие функции организма.",
        "calorie": "Калория — это единица энергии, которая показывает, сколько энергии даёт еда и использует организм.",
    },
    "es": {
        "bmi": "BMI significa índice de masa corporal. Estima el tamaño corporal comparando el peso con la altura.",
        "bmr": "BMR significa tasa metabólica basal. Estima cuánta energía usa tu cuerpo en reposo.",
        "tdee": "TDEE significa gasto energético diario total. Estima tu gasto calórico diario incluyendo la actividad.",
        "protein": "La proteína es un macronutriente que ayuda a sostener los músculos, la recuperación y muchas funciones del cuerpo.",
        "calorie": "Una caloría es una unidad de energía que describe cuánta energía aporta la comida y usa el cuerpo.",
    },
}
_SAFE_WELLNESS_DISCLAIMER = {
    "en": (
        "I can provide general wellness information, but I can't give medical diagnosis or treatment advice. "
        "If you have symptoms or concern about a condition, please speak with a licensed clinician."
    ),
    "ru": (
        "Я могу дать общую wellness-информацию, но не могу ставить диагноз или назначать лечение. "
        "Если у вас есть симптомы или беспокойство о состоянии, обратитесь к лицензированному врачу."
    ),
    "es": (
        "Puedo ofrecer información general de bienestar, pero no puedo dar diagnósticos médicos ni consejos de tratamiento. "
        "Si tienes síntomas o preocupación por alguna condición, consulta con un profesional sanitario autorizado."
    ),
}

_CONSERVATIVE_FALLBACK_MESSAGES = {
    "en": (
        "Here is the safest concise answer I can provide: focus on general wellness habits, "
        "use evidence-based sources when possible, and avoid treating this as medical advice."
    ),
    "ru": (
        "Вот самый безопасный краткий ответ, который я могу дать: сосредоточьтесь на общих wellness-привычках, "
        "по возможности опирайтесь на доказательные источники и не воспринимайте это как медицинский совет."
    ),
    "es": (
        "Esta es la respuesta breve más segura que puedo dar: céntrate en hábitos generales de bienestar, "
        "usa fuentes basadas en evidencia cuando sea posible y no tomes esto como consejo médico."
    ),
}


class _Provider(Protocol):
    """Minimal provider surface expected by runtime."""

    name: str

    async def generate(self, text: str) -> str: ...


class RouteType(str, Enum):
    """Canonical runtime routes."""

    DIRECT_DEFINITION = "DIRECT_DEFINITION"
    DIRECT_CALCULATION = "DIRECT_CALCULATION"
    SAFE_WELLNESS_DISCLAIMER = "SAFE_WELLNESS_DISCLAIMER"
    SHALLOW_GUIDANCE = "SHALLOW_GUIDANCE"
    RAG_FACTUAL = "RAG_FACTUAL"
    DEEP_REASONING = "DEEP_REASONING"


class RiskLevel(str, Enum):
    """Low-cardinality risk bucket."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class RouteDecision:
    """Output of the pre-generation router."""

    route_type: RouteType
    target_depth: int
    needs_rag: bool
    needs_generation: bool
    risk_level: RiskLevel
    reason_codes: list[str] = field(default_factory=list)
    optimization_applied: bool = False
    simplified_query: str = ""
    language_game: LanguageGameType = LanguageGameType.GENERAL
    speech_act: SpeechActType = SpeechActType.UNKNOWN


@dataclass(frozen=True)
class RuntimeMetadata:
    """Public runtime metadata exposed via InsightResponse."""

    route_type: str | None = None
    depth_used: int = 0
    verification_rate: float | None = None
    falsifiability_rate: float | None = None
    contradiction_count: int = 0
    reason_codes: list[str] = field(default_factory=list)
    optimization_applied: bool = False


@dataclass(frozen=True)
class RuntimeResult:
    """Unified result returned to adapter layer."""

    insight: str
    provider_name: str
    source_dicts: list[RAGSourceDict] = field(default_factory=list)
    confidence: float | None = None
    rag_used: bool = False
    hops: int = 0
    latency_ms: int = 0
    metadata: RuntimeMetadata = field(default_factory=RuntimeMetadata)


class PhilosophicalQueryRouter:
    """Choose the cheapest safe path before provider generation."""

    _CALC_RE = re.compile(r"\bcalculate\b.*\bbmi\b|\bbmi\b.*\b(?:kg|cm|m)\b", re.IGNORECASE)
    _DEFINITION_RE = re.compile(
        r"\b(?:what is|define|definition of|meaning of|what does)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._speech_act = SpeechActClassifier()
        self._language_game = LanguageGameIdentifier()
        self._resolver = MeaningAsUseResolver()
        self._classifier = AnalyticalSyntheticClassifier()
        self._depth_optimizer = HermeneuticDepthOptimizer()

    def route(self, query: str, *, lang: str | None = None) -> RouteDecision:
        """Build a deterministic route decision."""
        _ = lang
        simplified_query = self._resolver.resolve(query)
        speech_act = self._speech_act.classify(simplified_query)
        language_game = self._language_game.identify(simplified_query)
        target_depth = self._depth_optimizer.determine_depth(
            simplified_query,
            speech_act=speech_act,
            language_game=language_game,
        )
        reason_codes: list[str] = []

        if language_game == LanguageGameType.MEDICAL:
            reason_codes.append("medical_language_game")
            return RouteDecision(
                route_type=RouteType.SAFE_WELLNESS_DISCLAIMER,
                target_depth=1,
                needs_rag=False,
                needs_generation=False,
                risk_level=RiskLevel.HIGH,
                reason_codes=reason_codes,
                optimization_applied=True,
                simplified_query=simplified_query,
                language_game=language_game,
                speech_act=speech_act,
            )

        if self._CALC_RE.search(simplified_query):
            reason_codes.append("direct_calculation")
            return RouteDecision(
                route_type=RouteType.DIRECT_CALCULATION,
                target_depth=1,
                needs_rag=False,
                needs_generation=not self._can_calculate_locally(simplified_query),
                risk_level=RiskLevel.LOW,
                reason_codes=reason_codes,
                optimization_applied=True,
                simplified_query=simplified_query,
                language_game=language_game,
                speech_act=speech_act,
            )

        if self._DEFINITION_RE.search(simplified_query):
            if self._known_definition_term(simplified_query) is not None:
                reason_codes.append("cached_definition")
                needs_generation = False
            else:
                reason_codes.append("definition_short_path")
                needs_generation = True
            return RouteDecision(
                route_type=RouteType.DIRECT_DEFINITION,
                target_depth=1,
                needs_rag=False,
                needs_generation=needs_generation,
                risk_level=RiskLevel.LOW,
                reason_codes=reason_codes,
                optimization_applied=True,
                simplified_query=simplified_query,
                language_game=language_game,
                speech_act=speech_act,
            )

        if speech_act in {SpeechActType.COMMAND, SpeechActType.EXPRESSION, SpeechActType.REQUEST}:
            reason_codes.append(f"speech_act:{speech_act.value}")
            return RouteDecision(
                route_type=RouteType.SHALLOW_GUIDANCE,
                target_depth=max(1, min(target_depth, 2)),
                needs_rag=False,
                needs_generation=True,
                risk_level=RiskLevel.MEDIUM,
                reason_codes=reason_codes,
                optimization_applied=True,
                simplified_query=simplified_query,
                language_game=language_game,
                speech_act=speech_act,
            )

        kind = self._classifier.classify(simplified_query)
        if language_game == LanguageGameType.NUTRITION or kind == StatementKind.SYNTHETIC:
            reason_codes.append("nutrition_factual_path")
            return RouteDecision(
                route_type=RouteType.RAG_FACTUAL,
                target_depth=max(2, target_depth),
                needs_rag=True,
                needs_generation=True,
                risk_level=RiskLevel.MEDIUM,
                reason_codes=reason_codes,
                optimization_applied=True,
                simplified_query=simplified_query,
                language_game=language_game,
                speech_act=speech_act,
            )

        return RouteDecision(
            route_type=RouteType.DEEP_REASONING,
            target_depth=max(2, target_depth),
            needs_rag=True,
            needs_generation=True,
            risk_level=RiskLevel.MEDIUM,
            reason_codes=["default_deep_reasoning"],
            optimization_applied=False,
            simplified_query=simplified_query,
            language_game=language_game,
            speech_act=speech_act,
        )

    def _known_definition_term(self, query: str) -> str | None:
        for term in _DEFINITION_TEMPLATES["en"]:
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", query.lower()):
                return term
        return None

    def _can_calculate_locally(self, query: str) -> bool:
        return extract_bmi_inputs(query) is not None


class PhilosophicalRuntime:
    """Unified router -> RAG -> prompt -> validation -> fallback flow."""

    def __init__(self) -> None:
        self._router = PhilosophicalQueryRouter()
        self._prompt_builder = SyllogisticPromptBuilder()
        self._contradictions = NonContradictionChecker()
        self._verification = VerificationEnforcer()
        self._falsification = FalsificationChecker()
        self._pragmatic = PragmaticValidator()

    def preview_route(
        self,
        *,
        text: str,
        lang: str | None,
        router_enabled: bool,
        use_rag: bool,
    ) -> RouteDecision:
        """Return the deterministic route decision without calling the provider."""
        if router_enabled:
            return self._router.route(text, lang=lang)
        return RouteDecision(
            route_type=RouteType.DEEP_REASONING,
            target_depth=_DEFAULT_BASELINE_DEPTH,
            needs_rag=use_rag,
            needs_generation=True,
            risk_level=RiskLevel.MEDIUM,
            reason_codes=["legacy_path"],
            simplified_query=text,
        )

    async def generate_insight(
        self,
        *,
        text: str,
        lang: str | None,
        provider: _Provider,
        use_rag: bool,
        philo_validation_enabled: bool,
        recursive_rag_enabled: bool,
        subject_id: int | None = None,
        philosophy_router_enabled: bool,
        philosophy_phase12_enabled: bool,
        philosophy_linguistic_enabled: bool,
        philosophy_pragmatic_enabled: bool,
    ) -> RuntimeResult:
        """Generate an insight with deterministic routing and validation."""
        public_metadata_enabled = any(
            (
                philosophy_router_enabled,
                philosophy_phase12_enabled,
                philosophy_linguistic_enabled,
                philosophy_pragmatic_enabled,
            )
        )
        router_enabled = philosophy_router_enabled or philosophy_linguistic_enabled
        decision = self.preview_route(
            text=text,
            lang=lang,
            router_enabled=router_enabled,
            use_rag=use_rag,
        )

        if decision.route_type == RouteType.SAFE_WELLNESS_DISCLAIMER:
            return self._build_direct_result(
                answer=_SAFE_WELLNESS_DISCLAIMER[_normalize_runtime_lang(lang)],
                provider_name="philosophical_runtime",
                decision=decision,
                verification_report=None,
                falsification_report=None,
                contradiction_count=0,
                fallback_reason="medical_boundary",
                rewrite_count=0,
            )

        local_direct = self._resolve_local_direct_answer(decision, lang=lang)
        if local_direct is not None:
            return self._build_direct_result(
                answer=local_direct,
                provider_name="philosophical_runtime",
                decision=decision,
                verification_report=None,
                falsification_report=None,
                contradiction_count=0,
                fallback_reason="",
                rewrite_count=0,
            )

        rag_source_dicts: list[RAGSourceDict] = []
        final_provider_name = provider.name
        confidence: float | None = None
        rag_used = False
        hops = 0
        latency_ms = 0
        prompt_input = decision.simplified_query or text

        if use_rag and decision.needs_rag:
            rag_result = await rag_orchestration.retrieve_and_validate_rag(
                prompt_input,
                max_chunks=3,
                philo_validation_enabled=philo_validation_enabled,
                recursive_rag_enabled=recursive_rag_enabled,
                subject_id=subject_id,
            )
            prompt_input = rag_result.formatted_prompt
            confidence = rag_result.confidence
            rag_used = rag_result.rag_actually_used
            hops = rag_result.hops
            latency_ms = rag_result.latency_ms
            if rag_result.chunks:
                rag_source_dicts = build_rag_source_dicts(rag_result.chunks)

        prompt_text = self._build_prompt(
            base_prompt=prompt_input,
            decision=decision,
            phase12_enabled=philosophy_phase12_enabled,
        )
        prompt_text = _trim_prompt(prompt_text)

        answer = await provider.generate(prompt_text)
        rewrite_count = 0
        fallback_reason = ""
        verification_report: VerificationReport | None = None
        falsification_report: FalsificationReport | None = None
        contradiction_count = 0

        if philosophy_phase12_enabled:
            citations = [item["file"] for item in rag_source_dicts]
            verification_report = self._verification.validate(answer, citations=citations)
            falsification_report = self._falsification.validate(answer)
            contradiction_count = self._contradictions.count(answer)
            if self._should_rewrite(
                decision=decision,
                verification_report=verification_report,
                falsification_report=falsification_report,
                contradiction_count=contradiction_count,
                answer=answer,
                query=text,
                pragmatic_enabled=philosophy_pragmatic_enabled,
            ):
                rewrite_count = 1
                rewrite_prompt = self._build_rewrite_prompt(
                    original_prompt=prompt_text,
                    answer=answer,
                    verification_report=verification_report,
                    falsification_report=falsification_report,
                    contradiction_count=contradiction_count,
                )
                answer = await provider.generate(_trim_prompt(rewrite_prompt))
                verification_report = self._verification.validate(answer, citations=citations)
                falsification_report = self._falsification.validate(answer)
                contradiction_count = self._contradictions.count(answer)
                if (
                    contradiction_count > 0
                    or verification_report.verification_rate < 0.5
                    or falsification_report.falsifiability_rate < 0.5
                ):
                    answer = self._build_conservative_fallback(decision, lang=lang)
                    final_provider_name = "philosophical_runtime"
                    verification_report = None
                    falsification_report = None
                    contradiction_count = 0
                    fallback_reason = "phase12_validation"

        tokens_saved_estimate = _estimate_tokens_saved(
            prompt_text=prompt_text,
            target_depth=decision.target_depth,
            skipped_generation=decision.route_type == RouteType.SAFE_WELLNESS_DISCLAIMER,
        )
        record_runtime_metrics(
            route_type=decision.route_type.value,
            depth_used=decision.target_depth,
            tokens_saved_estimate=tokens_saved_estimate,
            rewrite_count=rewrite_count,
            fallback_reason=fallback_reason or "none",
        )
        return RuntimeResult(
            insight=answer,
            provider_name=final_provider_name,
            source_dicts=rag_source_dicts,
            confidence=confidence,
            rag_used=rag_used,
            hops=hops,
            latency_ms=latency_ms,
            metadata=(
                RuntimeMetadata(
                    route_type=decision.route_type.value,
                    depth_used=decision.target_depth,
                    verification_rate=(
                        None
                        if verification_report is None
                        else verification_report.verification_rate
                    ),
                    falsifiability_rate=(
                        None
                        if falsification_report is None
                        else falsification_report.falsifiability_rate
                    ),
                    contradiction_count=contradiction_count,
                    reason_codes=list(decision.reason_codes),
                    optimization_applied=decision.optimization_applied,
                )
                if public_metadata_enabled
                else RuntimeMetadata()
            ),
        )

    def _build_prompt(
        self,
        *,
        base_prompt: str,
        decision: RouteDecision,
        phase12_enabled: bool,
    ) -> str:
        """Build prompt appropriate for route and validation level."""
        if decision.route_type == RouteType.DIRECT_DEFINITION:
            return f"Answer briefly and clearly:\nQuestion: {base_prompt}\nAnswer:"
        if decision.route_type == RouteType.DIRECT_CALCULATION:
            return (
                "Answer with a short wellness-safe calculation or request for missing inputs.\n"
                f"Question: {base_prompt}\nAnswer:"
            )
        if decision.route_type == RouteType.SHALLOW_GUIDANCE:
            return (
                "Provide a concise, actionable wellness-safe answer in 3 short bullets maximum.\n"
                f"Question: {base_prompt}\nAnswer:"
            )
        if phase12_enabled and decision.route_type in {
            RouteType.RAG_FACTUAL,
            RouteType.DEEP_REASONING,
        }:
            return cast(
                str,
                self._prompt_builder.build_prompt(
                    base_prompt,
                    domain=decision.language_game.value,
                ),
            )
        return base_prompt

    def _build_rewrite_prompt(
        self,
        *,
        original_prompt: str,
        answer: str,
        verification_report: VerificationReport,
        falsification_report: FalsificationReport,
        contradiction_count: int,
    ) -> str:
        """Ask the provider for one deterministic repair attempt."""
        return (
            "Revise the answer to be shorter, better verified, and contradiction-free.\n"
            f"Original prompt:\n{original_prompt}\n\n"
            f"Current answer:\n{answer}\n\n"
            f"Issues:\n- verification_rate={verification_report.verification_rate}\n"
            f"- falsifiability_rate={falsification_report.falsifiability_rate}\n"
            f"- contradiction_count={contradiction_count}\n\n"
            "Return only the revised answer."
        )

    def _should_rewrite(
        self,
        *,
        decision: RouteDecision,
        verification_report: VerificationReport,
        falsification_report: FalsificationReport,
        contradiction_count: int,
        answer: str,
        query: str,
        pragmatic_enabled: bool,
    ) -> bool:
        """Decide if one rewrite attempt is justified."""
        if contradiction_count > 0:
            return True
        if verification_report.verification_rate < 0.5:
            return True
        if falsification_report.falsifiability_rate < 0.5:
            return True
        if pragmatic_enabled:
            pragmatic = self._pragmatic.assess(
                answer,
                query=query,
                language_game=decision.language_game,
            )
            if pragmatic.practically_useful and contradiction_count == 0:
                return False
        if decision.route_type in {RouteType.RAG_FACTUAL, RouteType.DEEP_REASONING}:
            return bool(
                verification_report.verification_rate < 0.7
                or falsification_report.falsifiability_rate < 0.7
            )
        return False

    def _build_conservative_fallback(self, decision: RouteDecision, *, lang: str | None) -> str:
        """Return a safe fallback when rewrite still fails."""
        lang_norm = _normalize_runtime_lang(lang)
        if decision.language_game == LanguageGameType.MEDICAL:
            return _SAFE_WELLNESS_DISCLAIMER[lang_norm]
        return _CONSERVATIVE_FALLBACK_MESSAGES[lang_norm]

    def _resolve_local_direct_answer(
        self,
        decision: RouteDecision,
        *,
        lang: str | None,
    ) -> str | None:
        """Return a local direct answer when it is safer and cheaper than generation."""
        lang_norm = _normalize_runtime_lang(lang)
        if decision.route_type == RouteType.DIRECT_DEFINITION:
            term = self._router._known_definition_term(decision.simplified_query)
            if term is not None:
                return _DEFINITION_TEMPLATES[lang_norm][term]
        if decision.route_type == RouteType.DIRECT_CALCULATION:
            return render_bmi_query_answer(decision.simplified_query, lang=lang)
        return None

    def _build_direct_result(
        self,
        *,
        answer: str,
        provider_name: str,
        decision: RouteDecision,
        verification_report: VerificationReport | None,
        falsification_report: FalsificationReport | None,
        contradiction_count: int,
        fallback_reason: str,
        rewrite_count: int,
    ) -> RuntimeResult:
        """Build a result for fully local/direct answers."""
        tokens_saved_estimate = _estimate_tokens_saved(
            prompt_text=decision.simplified_query,
            target_depth=decision.target_depth,
            skipped_generation=True,
        )
        record_runtime_metrics(
            route_type=decision.route_type.value,
            depth_used=decision.target_depth,
            tokens_saved_estimate=tokens_saved_estimate,
            rewrite_count=rewrite_count,
            fallback_reason=fallback_reason or "none",
        )
        return RuntimeResult(
            insight=answer,
            provider_name=provider_name,
            metadata=RuntimeMetadata(
                route_type=decision.route_type.value,
                depth_used=decision.target_depth,
                verification_rate=(
                    None if verification_report is None else verification_report.verification_rate
                ),
                falsifiability_rate=(
                    None
                    if falsification_report is None
                    else falsification_report.falsifiability_rate
                ),
                contradiction_count=contradiction_count,
                reason_codes=list(decision.reason_codes),
                optimization_applied=True,
            ),
        )


def _trim_prompt(prompt: str, max_chars: int = 4000) -> str:
    """Keep prompt bounded deterministically."""
    return prompt[:max_chars] if len(prompt) > max_chars else prompt


def _approx_tokens(text: str) -> int:
    """Estimate tokens deterministically from characters."""
    return max(1, len(text) // _APPROX_CHARS_PER_TOKEN)


def _estimate_tokens_saved(*, prompt_text: str, target_depth: int, skipped_generation: bool) -> int:
    """Estimate token savings vs a depth-3 baseline."""
    base = _approx_tokens(prompt_text)
    if skipped_generation:
        return base * _DEFAULT_BASELINE_DEPTH
    return max(0, (_DEFAULT_BASELINE_DEPTH - target_depth) * base)


def _normalize_runtime_lang(lang: str | None) -> str:
    """Normalize runtime language to the supported local-answer locales."""

    return cast(str, normalize_lang(lang))


__all__ = [
    "PhilosophicalQueryRouter",
    "PhilosophicalRuntime",
    "RiskLevel",
    "RouteDecision",
    "RouteType",
    "RuntimeMetadata",
    "RuntimeResult",
]
