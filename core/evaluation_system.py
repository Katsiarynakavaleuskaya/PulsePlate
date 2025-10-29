# -*- coding: utf-8 -*-
"""
Automated evaluation system for PulsePlate.
Based on Claude Cookbooks patterns for prompt evaluation.
"""

import json
import logging
from typing import Any, Dict, List, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone


@runtime_checkable
class LLMProviderProtocol(Protocol):
    async def generate(self, prompt: str) -> str: ...


logger = logging.getLogger(__name__)


class EvaluationMetric(Enum):
    """Types of evaluation metrics."""

    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    SAFETY = "safety"
    NUTRITION_ACCURACY = "nutrition_accuracy"


@dataclass
class EvaluationCriteria:
    """Criteria for evaluation."""

    metric: EvaluationMetric
    weight: float  # 0.0 to 1.0
    description: str
    min_score: float = 0.0
    max_score: float = 10.0


@dataclass
class EvaluationResult:
    """Result of evaluation."""

    metric: EvaluationMetric
    score: float
    explanation: str
    passed: bool
    suggestions: List[str]


@dataclass
class OverallEvaluation:
    """Overall evaluation result."""

    total_score: float
    weighted_score: float
    individual_results: List[EvaluationResult]
    passed: bool
    timestamp: datetime
    evaluator_id: str


class NutritionEvaluator:
    """Specialized evaluator for nutrition-related content."""

    def __init__(self, llm_provider: LLMProviderProtocol) -> None:
        """Initialize evaluator."""
        self.llm_provider = llm_provider
        self.logger = logging.getLogger("nutrition_evaluator")

    async def evaluate_nutrition_accuracy(
        self, content: str, reference_data: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate nutrition accuracy of content."""
        prompt = f"""
        Evaluate the nutrition accuracy of this content against reference data:

        Content to evaluate:
        {content}

        Reference nutrition data:
        {json.dumps(reference_data, indent=2)}

        Rate accuracy on a scale of 1-10 and provide detailed feedback in JSON format:
        {{
            "score": "number 1-10",
            "explanation": "detailed explanation of accuracy assessment",
            "passed": "true/false (score >= 7)",
            "suggestions": ["list of improvement suggestions"],
            "specific_issues": ["list of specific inaccuracies found"],
            "strengths": ["list of accurate information"]
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                try:
                    eval_data = json.loads(str(response))
                except json.JSONDecodeError as e:
                    self.logger.error("Invalid JSON from LLM: %s | raw=%.200s", e, str(response))
                    return EvaluationResult(
                        metric=EvaluationMetric.NUTRITION_ACCURACY,
                        score=0.0,
                        explanation="LLM returned invalid JSON response",
                        passed=False,
                        suggestions=["Fix LLM response format"],
                    )
                if not isinstance(eval_data, dict) or not eval_data:
                    self.logger.error("Unexpected JSON structure | raw=%.200s", str(response))
                    return EvaluationResult(
                        metric=EvaluationMetric.NUTRITION_ACCURACY,
                        score=0.0,
                        explanation="Unexpected JSON structure from LLM",
                        passed=False,
                        suggestions=["Return JSON object with expected fields"],
                    )

                return EvaluationResult(
                    metric=EvaluationMetric.NUTRITION_ACCURACY,
                    score=float(eval_data.get("score", 0)),
                    explanation=eval_data.get("explanation", ""),
                    passed=eval_data.get("passed", False),
                    suggestions=eval_data.get("suggestions", []),
                )
            else:
                return EvaluationResult(
                    metric=EvaluationMetric.NUTRITION_ACCURACY,
                    score=0.0,
                    explanation="LLM provider not available",
                    passed=False,
                    suggestions=["Enable LLM provider for evaluation"],
                )
        except Exception as e:
            self.logger.error(f"Nutrition accuracy evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.NUTRITION_ACCURACY,
                score=0.0,
                explanation=f"Evaluation failed: {str(e)}",
                passed=False,
                suggestions=["Fix evaluation system"],
            )

    async def evaluate_meal_plan_quality(
        self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate quality of meal plan."""
        prompt = f"""
        Evaluate the quality of this meal plan for the given user profile:

        Meal Plan:
        {json.dumps(meal_plan, indent=2)}

        User Profile:
        {json.dumps(user_profile, indent=2)}

        Rate quality on a scale of 1-10 and provide detailed feedback in JSON format:
        {{
            "score": "number 1-10",
            "explanation": "detailed explanation of quality assessment",
            "passed": "true/false (score >= 7)",
            "suggestions": ["list of improvement suggestions"],
            "nutrition_adequacy": "assessment of nutritional completeness",
            "variety_score": "assessment of meal variety",
            "practicality": "assessment of meal practicality",
            "personalization": "assessment of personalization to user needs"
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                eval_data = json.loads(response)

                return EvaluationResult(
                    metric=EvaluationMetric.RELEVANCE,
                    score=float(eval_data.get("score", 0)),
                    explanation=eval_data.get("explanation", ""),
                    passed=eval_data.get("passed", False),
                    suggestions=eval_data.get("suggestions", []),
                )
            else:
                return EvaluationResult(
                    metric=EvaluationMetric.RELEVANCE,
                    score=0.0,
                    explanation="LLM provider not available",
                    passed=False,
                    suggestions=["Enable LLM provider for evaluation"],
                )
        except Exception as e:
            self.logger.error(f"Meal plan quality evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.RELEVANCE,
                score=0.0,
                explanation=f"Evaluation failed: {str(e)}",
                passed=False,
                suggestions=["Fix evaluation system"],
            )


class SafetyEvaluator:
    """Evaluator for safety and appropriateness of content."""

    def __init__(self, llm_provider: LLMProviderProtocol) -> None:
        """Initialize safety evaluator."""
        self.llm_provider = llm_provider
        self.logger = logging.getLogger("safety_evaluator")

    async def evaluate_safety(self, content: str) -> EvaluationResult:
        """Evaluate safety of content."""
        prompt = f"""
        Evaluate the safety and appropriateness of this nutrition/health content:

        Content:
        {content}

        Check for:
        1. Medical claims without disclaimers
        2. Potentially harmful advice
        3. Inappropriate dietary recommendations
        4. Missing safety warnings
        5. Unsubstantiated claims

        Rate safety on a scale of 1-10 and provide detailed feedback in JSON format:
        {{
            "score": "number 1-10",
            "explanation": "detailed explanation of safety assessment",
            "passed": "true/false (score >= 8)",
            "suggestions": ["list of safety improvements"],
            "safety_concerns": ["list of specific safety concerns"],
            "disclaimer_needed": "true/false if medical disclaimer needed",
            "harmful_content": ["list of potentially harmful content"]
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                try:
                    eval_data = json.loads(str(response))
                except json.JSONDecodeError as e:
                    self.logger.error("Invalid JSON from LLM: %s | raw=%.200s", e, str(response))
                    return EvaluationResult(
                        metric=EvaluationMetric.SAFETY,
                        score=0.0,
                        explanation="LLM returned invalid JSON response",
                        passed=False,
                        suggestions=["Fix LLM response format"],
                    )
                if not isinstance(eval_data, dict) or not eval_data:
                    self.logger.error("Unexpected JSON structure | raw=%.200s", str(response))
                    return EvaluationResult(
                        metric=EvaluationMetric.SAFETY,
                        score=0.0,
                        explanation="Unexpected JSON structure from LLM",
                        passed=False,
                        suggestions=["Return JSON object with expected fields"],
                    )

                return EvaluationResult(
                    metric=EvaluationMetric.SAFETY,
                    score=float(eval_data.get("score", 0)),
                    explanation=eval_data.get("explanation", ""),
                    passed=eval_data.get("passed", False),
                    suggestions=eval_data.get("suggestions", []),
                )
            else:
                return EvaluationResult(
                    metric=EvaluationMetric.SAFETY,
                    score=0.0,
                    explanation="LLM provider not available",
                    passed=False,
                    suggestions=["Enable LLM provider for evaluation"],
                )
        except Exception as e:
            self.logger.error(f"Safety evaluation failed: {e}")
            return EvaluationResult(
                metric=EvaluationMetric.SAFETY,
                score=0.0,
                explanation=f"Evaluation failed: {str(e)}",
                passed=False,
                suggestions=["Fix evaluation system"],
            )


class ComprehensiveEvaluator:
    """Comprehensive evaluator using multiple criteria."""

    def __init__(self, llm_provider: LLMProviderProtocol) -> None:
        """Initialize comprehensive evaluator."""
        self.llm_provider = llm_provider
        self.nutrition_evaluator = NutritionEvaluator(llm_provider)
        self.safety_evaluator = SafetyEvaluator(llm_provider)
        self.logger = logging.getLogger("comprehensive_evaluator")

        # Define evaluation criteria
        self.criteria = [
            EvaluationCriteria(
                metric=EvaluationMetric.NUTRITION_ACCURACY,
                weight=0.3,
                description="Accuracy of nutrition information",
                min_score=7.0,
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.SAFETY,
                weight=0.25,
                description="Safety and appropriateness",
                min_score=8.0,
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.RELEVANCE,
                weight=0.2,
                description="Relevance to user needs",
                min_score=6.0,
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.CLARITY,
                weight=0.15,
                description="Clarity and readability",
                min_score=6.0,
            ),
            EvaluationCriteria(
                metric=EvaluationMetric.COMPLETENESS,
                weight=0.1,
                description="Completeness of information",
                min_score=6.0,
            ),
        ]

    async def evaluate_content(self, content: str, context: Dict[str, Any]) -> OverallEvaluation:
        """Evaluate content comprehensively."""
        self.logger.info("Starting comprehensive content evaluation")

        individual_results = []

        # Evaluate nutrition accuracy if reference data available
        if "reference_nutrition_data" in context:
            nutrition_result = await self.nutrition_evaluator.evaluate_nutrition_accuracy(
                content, context["reference_nutrition_data"]
            )
            individual_results.append(nutrition_result)

        # Evaluate safety
        safety_result = await self.safety_evaluator.evaluate_safety(content)
        individual_results.append(safety_result)

        # Evaluate other metrics
        relevance_result = await self._evaluate_relevance(content, context)
        individual_results.append(relevance_result)

        clarity_result = await self._evaluate_clarity(content)
        individual_results.append(clarity_result)

        completeness_result = await self._evaluate_completeness(content, context)
        individual_results.append(completeness_result)

        # Calculate overall scores
        total_score = sum(result.score for result in individual_results) / len(individual_results)
        weighted_score = self._calculate_weighted_score(individual_results)

        # Determine if passed
        passed = all(result.passed for result in individual_results)

        return OverallEvaluation(
            total_score=total_score,
            weighted_score=weighted_score,
            individual_results=individual_results,
            passed=passed,
            timestamp=datetime.now(timezone.utc),
            evaluator_id="comprehensive_evaluator_v1",
        )

    async def _evaluate_relevance(self, content: str, context: Dict[str, Any]) -> EvaluationResult:
        """Evaluate relevance to user needs."""
        user_needs = context.get("user_needs", "")

        prompt = f"""
        Evaluate how relevant this content is to the user's needs:

        Content:
        {content}

        User Needs:
        {user_needs}

        Rate relevance on a scale of 1-10 and provide feedback in JSON format:
        {{
            "score": "number 1-10",
            "explanation": "explanation of relevance assessment",
            "passed": "true/false (score >= 6)",
            "suggestions": ["suggestions for better relevance"]
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                try:
                    eval_data = json.loads(str(response))
                except json.JSONDecodeError as e:
                    return EvaluationResult(
                        metric=EvaluationMetric.RELEVANCE,
                        score=0.0,
                        explanation=f"Invalid JSON from LLM: {e}",
                        passed=False,
                        suggestions=["Fix LLM response format"],
                    )
                if not isinstance(eval_data, dict) or not eval_data:
                    return EvaluationResult(
                        metric=EvaluationMetric.RELEVANCE,
                        score=0.0,
                        explanation="Unexpected JSON structure from LLM",
                        passed=False,
                        suggestions=["Return JSON object with expected fields"],
                    )

                return EvaluationResult(
                    metric=EvaluationMetric.RELEVANCE,
                    score=float(eval_data.get("score", 0)),
                    explanation=eval_data.get("explanation", ""),
                    passed=eval_data.get("passed", False),
                    suggestions=eval_data.get("suggestions", []),
                )
            else:
                return EvaluationResult(
                    metric=EvaluationMetric.RELEVANCE,
                    score=0.0,
                    explanation="LLM provider not available",
                    passed=False,
                    suggestions=["Enable LLM provider"],
                )
        except Exception as e:
            return EvaluationResult(
                metric=EvaluationMetric.RELEVANCE,
                score=0.0,
                explanation=f"Evaluation failed: {str(e)}",
                passed=False,
                suggestions=["Fix evaluation system"],
            )

    async def _evaluate_clarity(self, content: str) -> EvaluationResult:
        """Evaluate clarity and readability."""
        prompt = f"""
        Evaluate the clarity and readability of this content:

        Content:
        {content}

        Rate clarity on a scale of 1-10 and provide feedback in JSON format:
        {{
            "score": "number 1-10",
            "explanation": "explanation of clarity assessment",
            "passed": "true/false (score >= 6)",
            "suggestions": ["suggestions for better clarity"]
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                try:
                    eval_data = json.loads(str(response))
                except json.JSONDecodeError as e:
                    return EvaluationResult(
                        metric=EvaluationMetric.CLARITY,
                        score=0.0,
                        explanation=f"Invalid JSON from LLM: {e}",
                        passed=False,
                        suggestions=["Fix LLM response format"],
                    )
                if not isinstance(eval_data, dict) or not eval_data:
                    return EvaluationResult(
                        metric=EvaluationMetric.CLARITY,
                        score=0.0,
                        explanation="Unexpected JSON structure from LLM",
                        passed=False,
                        suggestions=["Return JSON object with expected fields"],
                    )

                return EvaluationResult(
                    metric=EvaluationMetric.CLARITY,
                    score=float(eval_data.get("score", 0)),
                    explanation=eval_data.get("explanation", ""),
                    passed=eval_data.get("passed", False),
                    suggestions=eval_data.get("suggestions", []),
                )
            else:
                return EvaluationResult(
                    metric=EvaluationMetric.CLARITY,
                    score=0.0,
                    explanation="LLM provider not available",
                    passed=False,
                    suggestions=["Enable LLM provider"],
                )
        except Exception as e:
            return EvaluationResult(
                metric=EvaluationMetric.CLARITY,
                score=0.0,
                explanation=f"Evaluation failed: {str(e)}",
                passed=False,
                suggestions=["Fix evaluation system"],
            )

    async def _evaluate_completeness(
        self, content: str, context: Dict[str, Any]
    ) -> EvaluationResult:
        """Evaluate completeness of information."""
        expected_elements = context.get("expected_elements", [])

        prompt = f"""
        Evaluate how complete this content is:

        Content:
        {content}

        Expected Elements:
        {expected_elements}

        Rate completeness on a scale of 1-10 and provide feedback in JSON format:
        {{
            "score": "number 1-10",
            "explanation": "explanation of completeness assessment",
            "passed": "true/false (score >= 6)",
            "suggestions": ["suggestions for better completeness"],
            "missing_elements": ["elements that are missing"]
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                try:
                    eval_data = json.loads(str(response))
                except json.JSONDecodeError as e:
                    return EvaluationResult(
                        metric=EvaluationMetric.COMPLETENESS,
                        score=0.0,
                        explanation=f"Invalid JSON from LLM: {e}",
                        passed=False,
                        suggestions=["Fix LLM response format"],
                    )
                if not isinstance(eval_data, dict) or not eval_data:
                    return EvaluationResult(
                        metric=EvaluationMetric.COMPLETENESS,
                        score=0.0,
                        explanation="Unexpected JSON structure from LLM",
                        passed=False,
                        suggestions=["Return JSON object with expected fields"],
                    )

                return EvaluationResult(
                    metric=EvaluationMetric.COMPLETENESS,
                    score=float(eval_data.get("score", 0)),
                    explanation=eval_data.get("explanation", ""),
                    passed=eval_data.get("passed", False),
                    suggestions=eval_data.get("suggestions", []),
                )
            else:
                return EvaluationResult(
                    metric=EvaluationMetric.COMPLETENESS,
                    score=0.0,
                    explanation="LLM provider not available",
                    passed=False,
                    suggestions=["Enable LLM provider"],
                )
        except Exception as e:
            return EvaluationResult(
                metric=EvaluationMetric.COMPLETENESS,
                score=0.0,
                explanation=f"Evaluation failed: {str(e)}",
                passed=False,
                suggestions=["Fix evaluation system"],
            )

    def _calculate_weighted_score(self, results: List[EvaluationResult]) -> float:
        """Calculate weighted score based on criteria."""
        weighted_sum = 0.0
        total_weight = 0.0

        for result in results:
            # Find matching criteria
            criteria = next((c for c in self.criteria if c.metric == result.metric), None)
            if criteria:
                weighted_sum += result.score * criteria.weight
                total_weight += criteria.weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0


# Factory functions
def create_comprehensive_evaluator(llm_provider: Any) -> ComprehensiveEvaluator:
    """Create comprehensive evaluator."""
    return ComprehensiveEvaluator(llm_provider)


def create_nutrition_evaluator(llm_provider: Any) -> NutritionEvaluator:
    """Create nutrition evaluator."""
    return NutritionEvaluator(llm_provider)


def create_safety_evaluator(llm_provider: Any) -> SafetyEvaluator:
    """Create safety evaluator."""
    return SafetyEvaluator(llm_provider)
