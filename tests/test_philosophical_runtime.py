"""Unit tests for philosophical runtime and route-selection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from core.insight.analytical import (
    AnalyticalSyntheticClassifier,
    FalsificationChecker,
    StatementKind,
    VerificationEnforcer,
)
from core.insight.aristotelian import (
    CategoricalValidator,
    NonContradictionChecker,
    SyllogisticPromptBuilder,
)
from core.insight.linguistic import LanguageGameType, SpeechActType
from core.insight.philosophical_runtime import (
    PhilosophicalQueryRouter,
    PhilosophicalRuntime,
    RiskLevel,
    RouteDecision,
    RouteType,
)
from core.insight import philosophical_runtime as runtime_mod
from core.insight.analytical import FalsificationReport, VerificationReport
from core.bmi import extract_bmi_inputs


@dataclass
class _StaticProvider:
    """Provider stub with deterministic response and call count."""

    response: str
    name: str = "static"
    calls: int = 0

    async def generate(self, text: str) -> str:
        self.calls += 1
        return self.response


class TestPhilosophicalQueryRouter:
    """Router should select cheap deterministic routes when possible."""

    def test_definition_query_uses_direct_definition_route(self) -> None:
        router = PhilosophicalQueryRouter()

        decision = router.route("What is BMI?")

        assert decision.route_type == RouteType.DIRECT_DEFINITION
        assert decision.target_depth == 1
        assert decision.needs_rag is False
        assert decision.needs_generation is False

    def test_medical_query_uses_safe_disclaimer_route(self) -> None:
        router = PhilosophicalQueryRouter()

        decision = router.route("I have symptoms and need diagnosis advice.")

        assert decision.route_type == RouteType.SAFE_WELLNESS_DISCLAIMER
        assert decision.needs_generation is False
        assert "medical_language_game" in decision.reason_codes

    def test_nutrition_question_uses_factual_rag_route(self) -> None:
        router = PhilosophicalQueryRouter()

        decision = router.route("How much protein should I eat for recovery?")

        assert decision.route_type == RouteType.RAG_FACTUAL
        assert decision.needs_rag is True
        assert decision.needs_generation is True
        assert decision.target_depth >= 2

    def test_bmi_calculation_query_is_local_direct_path(self) -> None:
        router = PhilosophicalQueryRouter()

        decision = router.route("Calculate BMI for 70kg and 175cm")

        assert decision.route_type == RouteType.DIRECT_CALCULATION
        assert decision.target_depth == 1
        assert decision.needs_generation is False

    def test_definition_cache_uses_word_boundaries(self) -> None:
        router = PhilosophicalQueryRouter()

        decision = router.route("What is proteinuria?")

        assert decision.route_type == RouteType.DIRECT_DEFINITION
        assert decision.needs_generation is True
        assert "cached_definition" not in decision.reason_codes

    def test_bmi_input_parser_rejects_track_distance_as_height(self) -> None:
        assert extract_bmi_inputs("Calculate BMI for 70kg after a 100m sprint") is None

    def test_bmi_input_parser_rejects_zero_weight_and_accepts_localized_units(self) -> None:
        assert extract_bmi_inputs("Calculate BMI for 0kg and 175cm") is None
        assert extract_bmi_inputs("Рассчитай BMI для 70 кг и 175 см") == (70.0, 1.75)

    def test_request_speech_act_uses_shallow_guidance_route(self) -> None:
        router = PhilosophicalQueryRouter()
        router._resolver = SimpleNamespace(resolve=lambda query: query)
        router._speech_act = SimpleNamespace(classify=lambda query: SpeechActType.REQUEST)
        router._language_game = SimpleNamespace(identify=lambda query: LanguageGameType.GENERAL)
        router._depth_optimizer = SimpleNamespace(determine_depth=lambda query, **kwargs: 3)
        router._classifier = SimpleNamespace(classify=lambda query: StatementKind.UNKNOWN)

        decision = router.route("Give me breakfast steps.")

        assert decision.route_type == RouteType.SHALLOW_GUIDANCE
        assert "speech_act:request" in decision.reason_codes

    def test_default_route_falls_back_to_deep_reasoning(self) -> None:
        router = PhilosophicalQueryRouter()
        router._resolver = SimpleNamespace(resolve=lambda query: query)
        router._speech_act = SimpleNamespace(classify=lambda query: SpeechActType.QUESTION)
        router._language_game = SimpleNamespace(identify=lambda query: LanguageGameType.GENERAL)
        router._depth_optimizer = SimpleNamespace(determine_depth=lambda query, **kwargs: 2)
        router._classifier = SimpleNamespace(classify=lambda query: StatementKind.UNKNOWN)

        decision = router.route("Why do habits stick?")

        assert decision.route_type == RouteType.DEEP_REASONING
        assert decision.reason_codes == ["default_deep_reasoning"]


class TestAristotelianHelpers:
    """Deterministic Aristotelian helpers should be stable and predictable."""

    def test_syllogistic_validation_accepts_labeled_sections(self) -> None:
        builder = SyllogisticPromptBuilder()

        validation = builder.validate_syllogism(
            "MAJOR PREMISE: BMI 25-29.9 is overweight.\n"
            "MINOR PREMISE: The user's BMI is 27.\n"
            "CONCLUSION: Therefore, the user's BMI is overweight."
        )

        assert validation.valid is True
        assert "BMI 25-29.9" in validation.major_premise

    def test_categorical_validator_finds_classical_contradiction(self) -> None:
        validator = CategoricalValidator()

        statements = validator.extract_statements(
            "All apples are fruit. Some apples are not fruit."
        )
        contradictions = validator.find_contradictions(statements)

        assert len(contradictions) == 1
        assert contradictions[0].kind == "categorical"

    def test_non_contradiction_checker_detects_negation_and_ranges(self) -> None:
        checker = NonContradictionChecker()

        contradictions = checker.check(
            "Protein should be 20-30 grams. Protein should be 40-50 grams. "
            "This plan is balanced. This plan is not balanced."
        )

        assert len(contradictions) >= 2

    def test_non_contradiction_checker_normalizes_contractions(self) -> None:
        checker = NonContradictionChecker()

        contradictions = checker.check("This plan isn't balanced. This plan is balanced.")

        assert any(item.kind == "negation" for item in contradictions)


class TestAnalyticalHelpers:
    """Verification and falsification helpers should classify deterministic claims."""

    def test_analytical_classifier_separates_statement_kinds(self) -> None:
        classifier = AnalyticalSyntheticClassifier()

        assert (
            classifier.classify("BMI is defined as weight divided by height squared.").value
            == "analytical"
        )
        assert (
            classifier.classify("According to WHO, BMI 25-29.9 is overweight.").value == "synthetic"
        )
        assert classifier.classify("This is the perfect diet for everyone.").value == "metaphysical"

    def test_analytical_classifier_does_not_treat_question_word_as_citation(self) -> None:
        classifier = AnalyticalSyntheticClassifier()

        result = classifier.classify("Who can help me improve my breakfast routine?")

        assert result == StatementKind.UNKNOWN

    def test_verification_enforcer_uses_citations_for_synthetic_claims(self) -> None:
        enforcer = VerificationEnforcer()

        report = enforcer.validate(
            "According to WHO, BMI 25-29.9 is overweight.",
            citations=["who.md"],
        )

        assert report.verification_rate == 1.0
        assert report.unverified_claims == []

    def test_falsification_checker_flags_vague_claims(self) -> None:
        checker = FalsificationChecker()

        report = checker.validate("This may help. Results vary by individual.")

        assert report.falsifiability_rate == 0.0
        assert len(report.unfalsifiable_claims) == 2


@pytest.mark.asyncio
class TestPhilosophicalRuntime:
    """Runtime should execute direct paths and bounded rewrite/fallback logic."""

    async def test_direct_definition_skips_provider_generation(self) -> None:
        runtime = PhilosophicalRuntime()
        provider = _StaticProvider(response="provider should not be called")

        result = await runtime.generate_insight(
            text="What is BMI?",
            lang="en",
            provider=provider,
            use_rag=False,
            philo_validation_enabled=False,
            recursive_rag_enabled=False,
            philosophy_router_enabled=True,
            philosophy_phase12_enabled=False,
            philosophy_linguistic_enabled=True,
            philosophy_pragmatic_enabled=False,
        )

        assert provider.calls == 0
        assert result.provider_name == "philosophical_runtime"
        assert "BMI stands for body mass index" in result.insight
        assert result.metadata.route_type == RouteType.DIRECT_DEFINITION.value
        assert result.metadata.depth_used == 1

    async def test_direct_definition_localizes_known_terms(self) -> None:
        runtime = PhilosophicalRuntime()
        provider = _StaticProvider(response="provider should not be called")

        result = await runtime.generate_insight(
            text="What is BMI?",
            lang="ru",
            provider=provider,
            use_rag=False,
            philo_validation_enabled=False,
            recursive_rag_enabled=False,
            philosophy_router_enabled=True,
            philosophy_phase12_enabled=False,
            philosophy_linguistic_enabled=True,
            philosophy_pragmatic_enabled=False,
        )

        assert provider.calls == 0
        assert "индекс массы тела" in result.insight

    async def test_medical_disclaimer_skips_provider_generation(self) -> None:
        runtime = PhilosophicalRuntime()
        provider = _StaticProvider(response="provider should not be called")

        result = await runtime.generate_insight(
            text="I have symptoms and need diagnosis advice.",
            lang="en",
            provider=provider,
            use_rag=False,
            philo_validation_enabled=False,
            recursive_rag_enabled=False,
            philosophy_router_enabled=True,
            philosophy_phase12_enabled=False,
            philosophy_linguistic_enabled=True,
            philosophy_pragmatic_enabled=False,
        )

        assert provider.calls == 0
        assert "can't give medical diagnosis" in result.insight
        assert result.metadata.route_type == RouteType.SAFE_WELLNESS_DISCLAIMER.value

    async def test_medical_disclaimer_localizes_response(self) -> None:
        runtime = PhilosophicalRuntime()
        provider = _StaticProvider(response="provider should not be called")

        result = await runtime.generate_insight(
            text="I have symptoms and need diagnosis advice.",
            lang="ru",
            provider=provider,
            use_rag=False,
            philo_validation_enabled=False,
            recursive_rag_enabled=False,
            philosophy_router_enabled=True,
            philosophy_phase12_enabled=False,
            philosophy_linguistic_enabled=True,
            philosophy_pragmatic_enabled=False,
        )

        assert provider.calls == 0
        assert "не могу ставить диагноз" in result.insight

    async def test_phase12_rewrites_once_then_falls_back(self) -> None:
        runtime = PhilosophicalRuntime()
        provider = _StaticProvider(response="This may help. It depends on the individual.")

        result = await runtime.generate_insight(
            text="How much protein should I eat for recovery?",
            lang="en",
            provider=provider,
            use_rag=False,
            philo_validation_enabled=False,
            recursive_rag_enabled=False,
            philosophy_router_enabled=True,
            philosophy_phase12_enabled=True,
            philosophy_linguistic_enabled=True,
            philosophy_pragmatic_enabled=False,
        )

        assert provider.calls == 2
        assert "safest concise answer" in result.insight
        assert result.metadata.route_type == RouteType.RAG_FACTUAL.value
        assert result.provider_name == "philosophical_runtime"
        assert result.metadata.verification_rate is None
        assert result.metadata.falsifiability_rate is None
        assert result.metadata.contradiction_count == 0

    async def test_metadata_hidden_when_new_flags_are_off(self) -> None:
        runtime = PhilosophicalRuntime()
        provider = _StaticProvider(response="Balanced nutrition supports energy.")

        result = await runtime.generate_insight(
            text="Tell me about balanced nutrition.",
            lang="en",
            provider=provider,
            use_rag=False,
            philo_validation_enabled=False,
            recursive_rag_enabled=False,
            philosophy_router_enabled=False,
            philosophy_phase12_enabled=False,
            philosophy_linguistic_enabled=False,
            philosophy_pragmatic_enabled=False,
        )

        assert provider.calls == 1
        assert result.metadata.route_type is None
        assert result.metadata.depth_used == 0
        assert result.metadata.reason_codes == []

    async def test_build_prompt_covers_all_route_variants(self) -> None:
        runtime = PhilosophicalRuntime()

        definition_prompt = runtime._build_prompt(
            base_prompt="What is BMI?",
            decision=RouteDecision(
                route_type=RouteType.DIRECT_DEFINITION,
                target_depth=1,
                needs_rag=False,
                needs_generation=False,
                risk_level=RiskLevel.LOW,
            ),
            phase12_enabled=False,
        )
        calculation_prompt = runtime._build_prompt(
            base_prompt="Calculate BMI for 70kg and 175cm",
            decision=RouteDecision(
                route_type=RouteType.DIRECT_CALCULATION,
                target_depth=1,
                needs_rag=False,
                needs_generation=False,
                risk_level=RiskLevel.LOW,
            ),
            phase12_enabled=False,
        )
        shallow_prompt = runtime._build_prompt(
            base_prompt="Give me a short breakfast plan",
            decision=RouteDecision(
                route_type=RouteType.SHALLOW_GUIDANCE,
                target_depth=1,
                needs_rag=False,
                needs_generation=True,
                risk_level=RiskLevel.MEDIUM,
            ),
            phase12_enabled=False,
        )
        rag_prompt = runtime._build_prompt(
            base_prompt="Explain recovery nutrition",
            decision=RouteDecision(
                route_type=RouteType.RAG_FACTUAL,
                target_depth=2,
                needs_rag=True,
                needs_generation=True,
                risk_level=RiskLevel.MEDIUM,
                language_game=LanguageGameType.NUTRITION,
            ),
            phase12_enabled=True,
        )

        assert definition_prompt.startswith("Answer briefly and clearly:")
        assert calculation_prompt.startswith("Answer with a short wellness-safe calculation")
        assert shallow_prompt.startswith("Provide a concise, actionable wellness-safe answer")
        assert "Answer as a concise Aristotelian syllogism." in rag_prompt

    async def test_should_rewrite_and_local_fallback_paths(self) -> None:
        runtime = PhilosophicalRuntime()
        decision = RouteDecision(
            route_type=RouteType.RAG_FACTUAL,
            target_depth=2,
            needs_rag=True,
            needs_generation=True,
            risk_level=RiskLevel.MEDIUM,
            language_game=LanguageGameType.GENERAL,
            simplified_query="How much protein should I eat?",
        )

        assert runtime._should_rewrite(
            decision=decision,
            verification_report=VerificationReport(verification_rate=0.6, unverified_claims=[]),
            falsification_report=FalsificationReport(
                falsifiability_rate=0.9,
                unfalsifiable_claims=[],
            ),
            contradiction_count=0,
            answer="Use 20-30 grams.",
            query="How much protein should I eat?",
            pragmatic_enabled=False,
        )
        assert runtime._should_rewrite(
            decision=decision,
            verification_report=VerificationReport(verification_rate=1.0, unverified_claims=[]),
            falsification_report=FalsificationReport(
                falsifiability_rate=1.0,
                unfalsifiable_claims=[],
            ),
            contradiction_count=1,
            answer="Contradictory answer",
            query="How much protein should I eat?",
            pragmatic_enabled=False,
        )
        assert (
            runtime._should_rewrite(
                decision=decision,
                verification_report=VerificationReport(verification_rate=1.0, unverified_claims=[]),
                falsification_report=FalsificationReport(
                    falsifiability_rate=1.0,
                    unfalsifiable_claims=[],
                ),
                contradiction_count=0,
                answer="First, try a simple breakfast routine that matches your goal.",
                query="What breakfast routine should I try?",
                pragmatic_enabled=True,
            )
            is False
        )
        assert "medical diagnosis" in runtime._build_conservative_fallback(
            RouteDecision(
                route_type=RouteType.SAFE_WELLNESS_DISCLAIMER,
                target_depth=1,
                needs_rag=False,
                needs_generation=False,
                risk_level=RiskLevel.HIGH,
                language_game=LanguageGameType.MEDICAL,
            ),
            lang="en",
        )

    async def test_resolve_local_direct_answer_handles_missing_and_valid_bmi_inputs(self) -> None:
        runtime = PhilosophicalRuntime()

        missing_inputs = runtime._resolve_local_direct_answer(
            RouteDecision(
                route_type=RouteType.DIRECT_CALCULATION,
                target_depth=1,
                needs_rag=False,
                needs_generation=False,
                risk_level=RiskLevel.LOW,
                simplified_query="Calculate BMI please",
            ),
            lang="en",
        )
        valid_inputs = runtime._resolve_local_direct_answer(
            RouteDecision(
                route_type=RouteType.DIRECT_CALCULATION,
                target_depth=1,
                needs_rag=False,
                needs_generation=False,
                risk_level=RiskLevel.LOW,
                simplified_query="Calculate BMI for 70kg and 175cm",
            ),
            lang="ru",
        )

        assert "send both weight and height" in missing_inputs
        assert "Ваш примерный BMI" in valid_inputs

    async def test_extract_bmi_inputs_requires_weight(self) -> None:
        assert extract_bmi_inputs("Height is 175cm") is None

    async def test_shallow_guidance_hard_validation_still_rewrites(self) -> None:
        runtime = PhilosophicalRuntime()
        provider = _StaticProvider(response="This may help. Results vary by individual.")

        result = await runtime.generate_insight(
            text="Give me a short breakfast plan.",
            lang="en",
            provider=provider,
            use_rag=False,
            philo_validation_enabled=False,
            recursive_rag_enabled=False,
            philosophy_router_enabled=True,
            philosophy_phase12_enabled=True,
            philosophy_linguistic_enabled=True,
            philosophy_pragmatic_enabled=True,
        )

        assert provider.calls == 2
        assert result.provider_name == "philosophical_runtime"
        assert result.metadata.verification_rate is None
        assert result.metadata.falsifiability_rate is None


def test_runtime_telemetry_initializes_metrics_lazily(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.insight import telemetry as telemetry_mod

    build_calls = {"count": 0}
    original_state = (
        telemetry_mod._RUNTIME_TOTAL,
        telemetry_mod._REWRITE_TOTAL,
        telemetry_mod._DEPTH_HISTOGRAM,
        telemetry_mod._TOKEN_SAVINGS_HISTOGRAM,
        telemetry_mod._METRICS_READY,
    )

    def _fake_build_metrics() -> tuple[object, object, object, object]:
        build_calls["count"] += 1
        return object(), object(), object(), object()

    telemetry_mod._RUNTIME_TOTAL = None
    telemetry_mod._REWRITE_TOTAL = None
    telemetry_mod._DEPTH_HISTOGRAM = None
    telemetry_mod._TOKEN_SAVINGS_HISTOGRAM = None
    telemetry_mod._METRICS_READY = False
    monkeypatch.setattr(telemetry_mod, "_build_metrics", _fake_build_metrics)

    try:
        first = telemetry_mod._get_metrics()
        second = telemetry_mod._get_metrics()
    finally:
        (
            telemetry_mod._RUNTIME_TOTAL,
            telemetry_mod._REWRITE_TOTAL,
            telemetry_mod._DEPTH_HISTOGRAM,
            telemetry_mod._TOKEN_SAVINGS_HISTOGRAM,
            telemetry_mod._METRICS_READY,
        ) = original_state

    assert build_calls["count"] == 1
    assert first == second


def test_runtime_telemetry_handles_missing_prometheus(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.insight import telemetry as telemetry_mod

    monkeypatch.setattr(
        telemetry_mod,
        "_import_prometheus",
        lambda: (_ for _ in ()).throw(ImportError("missing")),
    )

    assert telemetry_mod._build_metrics() == (None, None, None, None)


def test_runtime_telemetry_handles_duplicate_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.insight import telemetry as telemetry_mod

    class _BrokenPrometheus:
        class Counter:
            def __init__(self, *args, **kwargs) -> None:
                raise ValueError("duplicate")

        class Histogram:
            def __init__(self, *args, **kwargs) -> None:
                raise AssertionError("histogram should not be built after duplicate counter")

    monkeypatch.setattr(telemetry_mod, "_import_prometheus", lambda: _BrokenPrometheus)

    assert telemetry_mod._build_metrics() == (None, None, None, None)


def test_record_runtime_metrics_swallows_metric_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.insight import telemetry as telemetry_mod

    class _BrokenMetric:
        def labels(self, **kwargs: object) -> "_BrokenMetric":
            raise RuntimeError("metrics unavailable")

    monkeypatch.setattr(
        telemetry_mod,
        "_get_metrics",
        lambda: (_BrokenMetric(), _BrokenMetric(), _BrokenMetric(), _BrokenMetric()),
    )

    telemetry_mod.record_runtime_metrics(
        route_type="RAG_FACTUAL",
        depth_used=2,
        tokens_saved_estimate=25,
        rewrite_count=1,
        fallback_reason="none",
    )


@pytest.mark.asyncio
async def test_direct_insight_provider_stub_raises_if_called() -> None:
    from legacy_app import _DirectInsightProviderStub

    stub = _DirectInsightProviderStub()

    with pytest.raises(RuntimeError, match="must not call provider.generate"):
        await stub.generate("unexpected")
