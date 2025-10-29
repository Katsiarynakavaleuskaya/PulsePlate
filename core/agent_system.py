# -*- coding: utf-8 -*-
"""
Sub-agent system for specialized tasks in PulsePlate.
Based on Claude Cookbooks patterns for agent orchestration.
"""

import asyncio
import time
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of specialized agents."""

    NUTRITION_ANALYZER = "nutrition_analyzer"
    MEAL_PLANNER = "meal_planner"
    HEALTH_ADVISOR = "health_advisor"
    PRODUCT_RESEARCHER = "product_researcher"
    COST_OPTIMIZER = "cost_optimizer"


@dataclass
class AgentTask:
    """Task for agent execution."""

    task_type: AgentType
    input_data: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    priority: int = 1  # 1 = highest, 5 = lowest
    timeout: float = 30.0


@dataclass
class AgentResult:
    """Result from agent execution."""

    success: bool
    data: Dict[str, Any]
    error_message: Optional[str] = None
    execution_time: float = 0.0
    agent_type: Optional[AgentType] = None


class BaseAgent:
    """Base class for all agents."""

    def __init__(self, agent_type: AgentType, llm_provider: Any) -> None:
        """Initialize base agent."""
        self.agent_type = agent_type
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(f"agent.{agent_type.value}")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute task and return result."""
        start_time = time.perf_counter()

        try:
            # Check that the agent type matches the task
            if task.task_type != self.agent_type:
                return AgentResult(
                    success=False,
                    data={
                        "error": f"Agent type mismatch: expected {self.agent_type.value}, got {task.task_type.value}"
                    },
                    error_message=f"Agent type mismatch: expected {self.agent_type.value}, got {task.task_type.value}",
                    execution_time=time.perf_counter() - start_time,
                    agent_type=self.agent_type,
                )

            self.logger.info(f"Executing {self.agent_type.value} task")
            # Enforce timeout for task processing
            try:
                result_data = await asyncio.wait_for(self._process_task(task), timeout=task.timeout)
            except asyncio.TimeoutError:
                execution_time = time.perf_counter() - start_time
                message = f"Task timed out after {task.timeout:.2f}s"
                self.logger.error(message)
                return AgentResult(
                    success=False,
                    data={"error": message, "timeout": task.timeout, "timeout_hit": True},
                    error_message=message,
                    execution_time=execution_time,
                    agent_type=self.agent_type,
                )

            execution_time = time.perf_counter() - start_time

            return AgentResult(
                success=True,
                data=result_data,
                execution_time=execution_time,
                agent_type=self.agent_type,
            )

        except Exception as e:
            execution_time = time.perf_counter() - start_time
            self.logger.error(f"Agent execution failed: {e}")

            return AgentResult(
                success=False,
                data={"error": str(e)},
                error_message=str(e),
                execution_time=execution_time,
                agent_type=self.agent_type,
            )

    async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process task - to be implemented by subclasses."""
        raise NotImplementedError

    @staticmethod
    def _parse_json_response(raw_response: Any, logger: logging.Logger) -> Dict[str, Any]:
        """Parse LLM raw response into JSON dict with validation and detailed logging."""
        text = str(raw_response)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s | raw=%.200s", exc, text)
            raise ValueError("Invalid JSON from LLM provider") from exc

        if not isinstance(parsed, dict):
            logger.error("LLM JSON response is not an object | raw=%.200s", text)
            raise ValueError("Unexpected JSON type from LLM provider (expected object)")
        return parsed


class NutritionAnalyzerAgent(BaseAgent):
    """Agent specialized in nutrition analysis."""

    def __init__(self, llm_provider: Any) -> None:
        super().__init__(AgentType.NUTRITION_ANALYZER, llm_provider)

    async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Analyze nutrition data."""
        food_data = task.input_data.get("food_data", {})

        prompt = f"""
        Analyze the nutritional value of this food item:

        Food Data: {json.dumps(food_data, indent=2)}

        Provide analysis in JSON format:
        {{
            "nutrition_score": "number 1-10",
            "health_benefits": ["list of benefits"],
            "nutrient_density": "high/medium/low",
            "recommended_serving": "suggested serving size",
            "dietary_considerations": ["considerations for different diets"],
            "nutrient_balance": {{
                "protein_adequacy": "adequate/insufficient/excessive",
                "carb_quality": "good/moderate/poor",
                "fat_quality": "good/moderate/poor"
            }}
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                return self._parse_json_response(response, self.logger)
            else:
                raise Exception("LLM provider not available")
        except Exception as e:
            self.logger.error(f"Nutrition analysis failed: {e}")
            raise e


class MealPlannerAgent(BaseAgent):
    """Agent specialized in meal planning."""

    def __init__(self, llm_provider: Any) -> None:
        super().__init__(AgentType.MEAL_PLANNER, llm_provider)

    async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Create meal plan."""
        user_profile = task.input_data.get("user_profile", {})
        available_foods = task.input_data.get("available_foods", [])
        preferences = task.input_data.get("preferences", {})

        prompt = f"""
        Create a personalized meal plan based on:

        User Profile: {json.dumps(user_profile, indent=2)}
        Available Foods: {json.dumps(available_foods[:20], indent=2)}
        Preferences: {json.dumps(preferences, indent=2)}

        Provide meal plan in JSON format:
        {{
            "daily_plan": {{
                "breakfast": {{
                    "foods": ["list of foods"],
                    "calories": "estimated calories",
                    "prep_time": "minutes"
                }},
                "lunch": {{...}},
                "dinner": {{...}},
                "snacks": {{...}}
            }},
            "weekly_variations": ["suggestions for variety"],
            "shopping_list": ["ingredients needed"],
            "prep_tips": ["meal prep suggestions"],
            "nutrition_summary": {{
                "daily_calories": "total",
                "macros": {{"protein": "g", "carbs": "g", "fat": "g"}},
                "micronutrients": ["key vitamins/minerals"]
            }}
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                return self._parse_json_response(response, self.logger)
            else:
                raise Exception("LLM provider not available")
        except Exception as e:
            self.logger.error(f"Meal planning failed: {e}")
            raise e


class HealthAdvisorAgent(BaseAgent):
    """Agent specialized in health advice."""

    def __init__(self, llm_provider: Any) -> None:
        super().__init__(AgentType.HEALTH_ADVISOR, llm_provider)

    async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Provide health advice."""
        user_health_data = task.input_data.get("health_data", {})
        question = task.input_data.get("question", "")

        prompt = f"""
        Provide health and nutrition advice based on:

        User Health Data: {json.dumps(user_health_data, indent=2)}
        Question: {question}

        Provide advice in JSON format:
        {{
            "advice": "main advice text",
            "recommendations": ["specific recommendations"],
            "warnings": ["any warnings or cautions"],
            "follow_up_questions": ["suggested follow-up questions"],
            "resources": ["helpful resources or references"],
            "disclaimer": "reminder that this is not medical advice"
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                return self._parse_json_response(response, self.logger)
            else:
                raise Exception("LLM provider not available")
        except Exception as e:
            self.logger.error(f"Health advice failed: {e}")
            raise e


class ProductResearcherAgent(BaseAgent):
    """Agent specialized in product research."""

    def __init__(self, llm_provider: Any) -> None:
        super().__init__(AgentType.PRODUCT_RESEARCHER, llm_provider)

    async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Research product information."""
        product_query = task.input_data.get("query", "")
        search_context = task.input_data.get("context", {})

        prompt = f"""
        Research information about: {product_query}

        Context: {json.dumps(search_context, indent=2)}

        Provide research results in JSON format:
        {{
            "product_info": {{
                "name": "product name",
                "category": "food category",
                "brand": "brand if known",
                "availability": "where to find it"
            }},
            "nutritional_analysis": {{
                "key_nutrients": ["main nutrients"],
                "health_benefits": ["benefits"],
                "concerns": ["potential concerns"]
            }},
            "alternatives": ["similar products"],
            "price_estimate": "estimated price range",
            "user_ratings": "if available",
            "sources": ["information sources"]
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                return self._parse_json_response(response, self.logger)
            else:
                raise Exception("LLM provider not available")
        except Exception as e:
            self.logger.error(f"Product research failed: {e}")
            raise e


class CostOptimizerAgent(BaseAgent):
    """Agent specialized in cost optimization."""

    def __init__(self, llm_provider: Any) -> None:
        super().__init__(AgentType.COST_OPTIMIZER, llm_provider)

    async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Optimize costs for meal plan."""
        meal_plan = task.input_data.get("meal_plan", {})
        budget = task.input_data.get("budget", 0)
        available_foods = task.input_data.get("available_foods", [])

        prompt = f"""
        Optimize the cost of this meal plan:

        Meal Plan: {json.dumps(meal_plan, indent=2)}
        Budget: ${budget}
        Available Foods: {json.dumps(available_foods[:30], indent=2)}

        Provide optimization in JSON format:
        {{
            "optimized_plan": {{
                "breakfast": {{"foods": [], "cost": 0}},
                "lunch": {{"foods": [], "cost": 0}},
                "dinner": {{"foods": [], "cost": 0}},
                "snacks": {{"foods": [], "cost": 0}}
            }},
            "cost_breakdown": {{
                "total_cost": "total cost",
                "savings": "amount saved",
                "cost_per_meal": "average cost per meal"
            }},
            "substitutions": ["suggested substitutions for cost savings"],
            "bulk_buying_tips": ["tips for buying in bulk"],
            "budget_tips": ["general budget optimization tips"]
        }}
        """

        try:
            if hasattr(self.llm_provider, "generate"):
                response = await self.llm_provider.generate(prompt)
                return self._parse_json_response(response, self.logger)
            else:
                raise Exception("LLM provider not available")
        except Exception as e:
            self.logger.error(f"Cost optimization failed: {e}")
            raise e


class AgentOrchestrator:
    """Orchestrates multiple agents for complex tasks."""

    def __init__(self, llm_provider: Any) -> None:
        """Initialize orchestrator with agents."""
        self.llm_provider = llm_provider
        self.agents = {
            AgentType.NUTRITION_ANALYZER: NutritionAnalyzerAgent(llm_provider),
            AgentType.MEAL_PLANNER: MealPlannerAgent(llm_provider),
            AgentType.HEALTH_ADVISOR: HealthAdvisorAgent(llm_provider),
            AgentType.PRODUCT_RESEARCHER: ProductResearcherAgent(llm_provider),
            AgentType.COST_OPTIMIZER: CostOptimizerAgent(llm_provider),
        }
        self.logger = logging.getLogger("agent_orchestrator")

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute single task with appropriate agent."""
        agent = self.agents.get(task.task_type)
        if not agent:
            return AgentResult(
                success=False,
                data={},
                error_message=f"No agent available for {task.task_type.value}",
            )

        return await agent.execute(task)

    async def execute_workflow(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute multiple tasks in sequence."""
        results = []

        for task in sorted(tasks, key=lambda t: t.priority):
            self.logger.info(f"Executing workflow task: {task.task_type.value}")
            result = await self.execute_task(task)
            results.append(result)

            # If task failed and it's critical, stop workflow
            if not result.success and task.priority <= 2:
                self.logger.error(f"Critical task failed: {task.task_type.value}")
                break

        return results

    async def execute_sequential_tasks(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute multiple tasks in sequence (alias for execute_workflow)."""
        return await self.execute_workflow(tasks)

    async def execute_parallel_tasks(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute multiple tasks in parallel."""
        self.logger.info(f"Executing {len(tasks)} tasks in parallel")

        # Group tasks by priority
        priority_groups: Dict[int, List[AgentTask]] = {}
        for task in tasks:
            if task.priority not in priority_groups:
                priority_groups[task.priority] = []
            priority_groups[task.priority].append(task)

        results: List[AgentResult] = []

        # Execute high priority tasks first
        for priority in sorted(priority_groups.keys()):
            group_tasks = priority_groups[priority]

            # Execute tasks in parallel
            task_coroutines = [self.execute_task(task) for task in group_tasks]
            group_results: List[AgentResult | BaseException] = await asyncio.gather(
                *task_coroutines, return_exceptions=True
            )

            # Handle exceptions
            for i, result in enumerate(group_results):
                if isinstance(result, BaseException):
                    results.append(
                        AgentResult(
                            success=False,
                            data={},
                            error_message=str(result),
                            agent_type=group_tasks[i].task_type,
                        )
                    )
                else:
                    results.append(result)

        return results


# Factory functions
def create_agent_orchestrator(llm_provider: Any) -> AgentOrchestrator:
    """Create agent orchestrator with all agents."""
    return AgentOrchestrator(llm_provider)


def create_nutrition_analyzer(llm_provider: Any) -> NutritionAnalyzerAgent:
    """Create nutrition analyzer agent."""
    return NutritionAnalyzerAgent(llm_provider)


def create_meal_planner(llm_provider: Any) -> MealPlannerAgent:
    """Create meal planner agent."""
    return MealPlannerAgent(llm_provider)
