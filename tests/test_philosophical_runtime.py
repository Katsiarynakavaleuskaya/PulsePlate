"""Unit tests for philosophical runtime and route-selection helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.insight.analytical import (
    AnalyticalSyntheticClassifier,
    FalsificationChecker,
    VerificationEnforcer,
)
from core.insight.aristotelian import (
    CategoricalValidator,
    NonContradictionChecker,
    SyllogisticPromptBuilder,
)
from core.insight.philosophical_runtime import (
    PhilosophicalQueryRouter,
    PhilosophicalRuntime,
    RouteType,
)


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
        assert result.metadata.verification_rate is not None
        assert result.metadata.falsifiability_rate is not None

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
