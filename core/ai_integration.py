# -*- coding: utf-8 -*-
"""
AI Integration module combining all enhanced systems.
Based on Claude Cookbooks best practices for comprehensive AI applications.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import asyncio
import time

# Import our enhanced systems
from core.llm_enhanced import (
    EnhancedLLMProvider,
    NutritionAnalysisAgent,
    create_enhanced_provider,
    create_nutrition_agent,
)
from core.rag_system import (
    FoodRAGSystem,
    FoodVectorStore,
    initialize_rag_system,
    populate_vector_store_from_foods,
)
from core.agent_system import AgentOrchestrator, AgentTask, AgentType, create_agent_orchestrator
from core.evaluation_system import ComprehensiveEvaluator, create_comprehensive_evaluator

logger = logging.getLogger(__name__)


class PulsePlateAI:
    """Main AI integration class for PulsePlate."""

    def __init__(self, base_llm_provider: Any, storage_path: Path):
        """Initialize PulsePlate AI system."""
        self.base_llm_provider = base_llm_provider
        self.storage_path = storage_path

        # Initialize enhanced systems
        self.enhanced_llm = create_enhanced_provider(base_llm_provider)
        self.nutrition_agent = create_nutrition_agent(base_llm_provider)
        self.rag_system = initialize_rag_system(storage_path / "rag", base_llm_provider)
        self.agent_orchestrator = create_agent_orchestrator(base_llm_provider)
        self.evaluator = create_comprehensive_evaluator(base_llm_provider)

        self.logger = logging.getLogger("pulseplate_ai")
        self.logger.info("PulsePlate AI system initialized")

    async def analyze_food_comprehensive(self, food_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive food analysis using multiple AI systems.

        Args:
            food_data: Food item data to analyze

        Returns:
            Comprehensive analysis results
        """
        self.logger.info(f"Starting comprehensive analysis for: {food_data.get('name', 'Unknown')}")

        # Create analysis tasks
        tasks = [
            AgentTask(
                task_type=AgentType.NUTRITION_ANALYZER,
                input_data={"food_data": food_data},
                priority=1,
            ),
            AgentTask(
                task_type=AgentType.PRODUCT_RESEARCHER,
                input_data={"query": food_data.get("name", ""), "context": food_data},
                priority=2,
            ),
        ]

        # Execute tasks in parallel
        results = await self.agent_orchestrator.execute_parallel_tasks(tasks)

        # Combine results
        analysis_result = {
            "food_name": food_data.get("name", "Unknown"),
            "analysis_timestamp": time.time(),
            "nutrition_analysis": {},
            "product_research": {},
            "overall_score": 0.0,
            "recommendations": [],
            "warnings": [],
        }

        # Process results
        for result in results:
            if result.success:
                if result.agent_type == AgentType.NUTRITION_ANALYZER:
                    analysis_result["nutrition_analysis"] = result.data
                elif result.agent_type == AgentType.PRODUCT_RESEARCHER:
                    analysis_result["product_research"] = result.data
            else:
                self.logger.warning(
                    "Task failed: %s - %s",
                    result.agent_type.value if result.agent_type else "unknown",
                    result.error_message,
                )

        # Calculate overall score
        nutrition_score = analysis_result["nutrition_analysis"].get("nutrition_score", 5)
        analysis_result["overall_score"] = nutrition_score

        # Generate recommendations
        analysis_result["recommendations"] = self._generate_recommendations(analysis_result)

        return analysis_result

    async def create_personalized_meal_plan(
        self, user_profile: Dict[str, Any], available_foods: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create personalized meal plan using AI agents.

        Args:
            user_profile: User's profile and preferences
            available_foods: List of available food items

        Returns:
            Personalized meal plan
        """
        self.logger.info("Creating personalized meal plan")

        # Create meal planning task
        task = AgentTask(
            task_type=AgentType.MEAL_PLANNER,
            input_data={
                "user_profile": user_profile,
                "available_foods": available_foods,
                "preferences": user_profile.get("preferences", {}),
            },
            priority=1,
        )

        # Execute task
        result = await self.agent_orchestrator.execute_task(task)

        if result.success:
            # Evaluate the meal plan
            evaluation_context = {
                "user_needs": user_profile.get("dietary_goals", ""),
                "expected_elements": ["breakfast", "lunch", "dinner", "nutrition_summary"],
            }

            meal_plan_content = json.dumps(result.data, indent=2)
            evaluation = await self.evaluator.evaluate_content(
                meal_plan_content, evaluation_context
            )

            return {
                "meal_plan": result.data,
                "evaluation": {
                    "score": evaluation.weighted_score,
                    "passed": evaluation.passed,
                    "suggestions": [r.suggestions for r in evaluation.individual_results],
                },
                "creation_timestamp": time.time(),
            }
        else:
            return {
                "error": f"Meal planning failed: {result.error_message}",
                "meal_plan": {},
                "evaluation": {"score": 0.0, "passed": False},
            }

    async def answer_nutrition_question(
        self, question: str, user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Answer nutrition question using RAG system.

        Args:
            question: User's nutrition question
            user_context: Optional user context

        Returns:
            Answer with sources and confidence
        """
        self.logger.info(f"Answering nutrition question: {question[:50]}...")

        # Use RAG system to answer question
        rag_result = await self.rag_system.query(question, context_limit=3)

        # Evaluate the answer quality
        evaluation_context = {
            "user_needs": user_context.get("dietary_goals", "") if user_context else "",
            "expected_elements": ["answer", "sources", "confidence"],
        }

        answer_content = rag_result.get("answer", "")
        evaluation = await self.evaluator.evaluate_content(answer_content, evaluation_context)

        return {
            "answer": rag_result.get("answer", ""),
            "sources": rag_result.get("sources", []),
            "confidence": rag_result.get("confidence", 0.0),
            "evaluation": {
                "score": evaluation.weighted_score,
                "passed": evaluation.passed,
                "suggestions": [r.suggestions for r in evaluation.individual_results],
            },
            "timestamp": time.time(),
        }

    async def optimize_meal_plan_cost(
        self, meal_plan: Dict[str, Any], budget: float, available_foods: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Optimize meal plan for cost.

        Args:
            meal_plan: Current meal plan
            budget: User's budget
            available_foods: Available food items with prices

        Returns:
            Cost-optimized meal plan
        """
        self.logger.info(f"Optimizing meal plan for budget: ${budget}")

        # Create cost optimization task
        task = AgentTask(
            task_type=AgentType.COST_OPTIMIZER,
            input_data={
                "meal_plan": meal_plan,
                "budget": budget,
                "available_foods": available_foods,
            },
            priority=1,
        )

        # Execute task
        result = await self.agent_orchestrator.execute_task(task)

        if result.success:
            return {
                "optimized_plan": result.data,
                "optimization_timestamp": time.time(),
                "success": True,
            }
        else:
            return {
                "error": f"Cost optimization failed: {result.error_message}",
                "optimized_plan": meal_plan,
                "success": False,
            }

    async def get_health_advice(self, health_data: Dict[str, Any], question: str) -> Dict[str, Any]:
        """
        Get personalized health advice.

        Args:
            health_data: User's health information
            question: Health question

        Returns:
            Health advice with safety evaluation
        """
        self.logger.info("Providing health advice")

        # Create health advisor task
        task = AgentTask(
            task_type=AgentType.HEALTH_ADVISOR,
            input_data={"health_data": health_data, "question": question},
            priority=1,
        )

        # Execute task
        result = await self.agent_orchestrator.execute_task(task)

        if result.success:
            # Evaluate safety of health advice
            advice_content = json.dumps(result.data, indent=2)
            evaluation = await self.evaluator.evaluate_content(advice_content, {})

            return {
                "advice": result.data,
                "safety_evaluation": {
                    "score": evaluation.weighted_score,
                    "passed": evaluation.passed,
                    "safety_concerns": [
                        r.suggestions
                        for r in evaluation.individual_results
                        if r.metric.value == "safety"
                    ],
                },
                "timestamp": time.time(),
            }
        else:
            return {
                "error": f"Health advice failed: {result.error_message}",
                "advice": {},
                "success": False,
            }

    def _generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []

        # Nutrition-based recommendations
        nutrition_analysis = analysis_result.get("nutrition_analysis", {})
        nutrition_score = nutrition_analysis.get("nutrition_score", 5)

        if nutrition_score >= 8:
            recommendations.append("This is a highly nutritious food choice!")
        elif nutrition_score >= 6:
            recommendations.append("This is a good food choice with some nutritional benefits.")
        else:
            recommendations.append(
                "Consider this food in moderation or look for more nutritious alternatives."
            )

        # Add specific recommendations from analysis
        if "recommendations" in nutrition_analysis:
            recommendations.extend(nutrition_analysis["recommendations"])

        return recommendations

    async def populate_knowledge_base(self, foods_data: Dict[str, Any]) -> None:
        """Populate RAG knowledge base with food data."""
        self.logger.info(f"Populating knowledge base with {len(foods_data)} food items")
        populate_vector_store_from_foods(self.rag_system.vector_store, foods_data)
        self.logger.info("Knowledge base populated successfully")

    async def evaluate_system_performance(self) -> Dict[str, Any]:
        """Evaluate overall system performance."""
        self.logger.info("Evaluating system performance")

        # Test with sample data
        test_food = {
            "name": "Apple",
            "nutrients_per_100g": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2},
            "source": "test",
            "source_id": "test_apple",
        }

        # Test analysis
        analysis_start = time.perf_counter()
        analysis_result = await self.analyze_food_comprehensive(test_food)
        analysis_time = time.perf_counter() - analysis_start

        # Test RAG
        rag_start = time.perf_counter()
        rag_result = await self.answer_nutrition_question("What are the health benefits of apples?")
        rag_time = time.perf_counter() - rag_start

        return {
            "analysis_performance": {
                "time_seconds": analysis_time,
                "success": analysis_result.get("overall_score", 0) > 0,
            },
            "rag_performance": {
                "time_seconds": rag_time,
                "success": rag_result.get("confidence", 0) > 0,
            },
            "system_status": "operational",
            "evaluation_timestamp": time.time(),
        }


# Factory function
def create_pulseplate_ai(base_llm_provider: Any, storage_path: Path) -> PulsePlateAI:
    """Create PulsePlate AI system."""
    return PulsePlateAI(base_llm_provider, storage_path)
