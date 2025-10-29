"""
Simple tests for core/agent_system.py to improve coverage.
"""

from typing import Dict, Any
import pytest
from unittest.mock import Mock, AsyncMock
from core.agent_system import (
    AgentType,
    AgentTask,
    AgentResult,
    BaseAgent,
    NutritionAnalyzerAgent,
    MealPlannerAgent,
    HealthAdvisorAgent,
    ProductResearcherAgent,
    CostOptimizerAgent,
    AgentOrchestrator,
)


class TestAgentType:
    """Test AgentType enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert AgentType.NUTRITION_ANALYZER.value == "nutrition_analyzer"
        assert AgentType.MEAL_PLANNER.value == "meal_planner"
        assert AgentType.HEALTH_ADVISOR.value == "health_advisor"
        assert AgentType.PRODUCT_RESEARCHER.value == "product_researcher"
        assert AgentType.COST_OPTIMIZER.value == "cost_optimizer"


class TestAgentTask:
    """Test AgentTask basic functionality."""

    def test_init(self):
        """Test initialization."""
        task = AgentTask(
            task_type=AgentType.NUTRITION_ANALYZER,
            input_data={"food": "apple"},
            context={"user_id": "123"},
            priority=1,
        )
        assert task.task_type == AgentType.NUTRITION_ANALYZER
        assert task.input_data == {"food": "apple"}
        assert task.context == {"user_id": "123"}
        assert task.priority == 1

    def test_init_defaults(self):
        """Test initialization with defaults."""
        task = AgentTask(task_type=AgentType.MEAL_PLANNER, input_data={"meals": "breakfast"})
        assert task.task_type == AgentType.MEAL_PLANNER
        assert task.input_data == {"meals": "breakfast"}
        assert task.context is None
        assert task.priority == 1

    def test_str_representation(self):
        """Test string representation."""
        task = AgentTask(task_type=AgentType.NUTRITION_ANALYZER, input_data={"food": "apple"})
        str_repr = str(task)
        assert "nutrition_analyzer" in str_repr.lower()


class TestAgentResult:
    """Test AgentResult basic functionality."""

    def test_init_success(self):
        """Test initialization for success."""
        result = AgentResult(
            success=True,
            data={"analysis": "Good nutrition"},
            error_message=None,
            execution_time=1.5,
            agent_type=AgentType.NUTRITION_ANALYZER,
        )
        assert result.agent_type == AgentType.NUTRITION_ANALYZER
        assert result.success is True
        assert result.data == {"analysis": "Good nutrition"}
        assert result.error_message is None
        assert result.execution_time == 1.5

    def test_init_failure(self):
        """Test initialization for failure."""
        result = AgentResult(
            success=False,
            data={},
            error_message="Failed to plan meals",
            execution_time=0.5,
            agent_type=AgentType.MEAL_PLANNER,
        )
        assert result.agent_type == AgentType.MEAL_PLANNER
        assert result.success is False
        assert result.data == {}
        assert result.error_message == "Failed to plan meals"
        assert result.execution_time == 0.5

    def test_str_representation(self):
        """Test string representation."""
        result = AgentResult(
            success=True,
            data={"test": "data"},
            error_message=None,
            execution_time=1.0,
            agent_type=AgentType.NUTRITION_ANALYZER,
        )
        str_repr = str(result)
        assert "nutrition_analyzer" in str_repr.lower()


class TestBaseAgent:
    """Test BaseAgent basic functionality."""

    def test_init(self):
        """Test initialization."""
        mock_llm = Mock()
        agent = BaseAgent(AgentType.NUTRITION_ANALYZER, mock_llm)
        assert agent.agent_type == AgentType.NUTRITION_ANALYZER
        assert agent.llm_provider == mock_llm

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution."""
        mock_llm = Mock()
        mock_llm.generate_text = AsyncMock(return_value="Analysis result")

        # Create a test agent implementing _process_task
        class TestAgent(BaseAgent):
            async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
                return {"result": "test analysis"}

        agent = TestAgent(AgentType.NUTRITION_ANALYZER, mock_llm)

        task = AgentTask(task_type=AgentType.NUTRITION_ANALYZER, input_data={"food": "apple"})

        result = await agent.execute(task)

        assert result.success is True
        assert result.data == {"result": "test analysis"}

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test execution with error."""
        mock_llm = Mock()
        mock_llm.generate_text = AsyncMock(side_effect=Exception("LLM error"))

        # Create a test agent implementing _process_task
        class TestAgent(BaseAgent):
            async def _process_task(self, task: AgentTask) -> Dict[str, Any]:
                raise Exception("LLM error")

        agent = TestAgent(AgentType.NUTRITION_ANALYZER, mock_llm)

        task = AgentTask(task_type=AgentType.NUTRITION_ANALYZER, input_data={"food": "apple"})

        result = await agent.execute(task)

        assert result.success is False
        assert result.data == {"error": "LLM error"}
        assert "LLM error" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_wrong_agent_type(self):
        """Test execution with wrong agent type."""
        mock_llm = Mock()
        agent = BaseAgent(AgentType.NUTRITION_ANALYZER, mock_llm)

        task = AgentTask(
            task_type=AgentType.MEAL_PLANNER, input_data={"meals": "plan"}
        )  # Wrong type

        result = await agent.execute(task)

        assert result.success is False
        assert "agent type" in result.error_message.lower()


class TestSpecializedAgents:
    """Test specialized agent classes."""

    def test_nutrition_analyzer_agent(self):
        """Test NutritionAnalyzerAgent."""
        mock_llm = Mock()
        agent = NutritionAnalyzerAgent(mock_llm)
        assert agent.agent_type == AgentType.NUTRITION_ANALYZER
        assert agent.llm_provider == mock_llm

    def test_meal_planner_agent(self):
        """Test MealPlannerAgent."""
        mock_llm = Mock()
        agent = MealPlannerAgent(mock_llm)
        assert agent.agent_type == AgentType.MEAL_PLANNER
        assert agent.llm_provider == mock_llm

    def test_health_advisor_agent(self):
        """Test HealthAdvisorAgent."""
        mock_llm = Mock()
        agent = HealthAdvisorAgent(mock_llm)
        assert agent.agent_type == AgentType.HEALTH_ADVISOR
        assert agent.llm_provider == mock_llm

    def test_product_researcher_agent(self):
        """Test ProductResearcherAgent."""
        mock_llm = Mock()
        agent = ProductResearcherAgent(mock_llm)
        assert agent.agent_type == AgentType.PRODUCT_RESEARCHER
        assert agent.llm_provider == mock_llm

    def test_cost_optimizer_agent(self):
        """Test CostOptimizerAgent."""
        mock_llm = Mock()
        agent = CostOptimizerAgent(mock_llm)
        assert agent.agent_type == AgentType.COST_OPTIMIZER
        assert agent.llm_provider == mock_llm

    @pytest.mark.asyncio
    async def test_nutrition_analyzer_execute(self):
        """Test NutritionAnalyzerAgent execution."""
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(
            return_value='{"analysis": "Nutrition analysis", "calories": 100, "protein": 5}'
        )

        agent = NutritionAnalyzerAgent(mock_llm)

        task = AgentTask(
            task_type=AgentType.NUTRITION_ANALYZER,
            input_data={"food": "apple"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_meal_planner_execute(self):
        """Test MealPlannerAgent execution."""
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(
            return_value='{"meal_plan": "Meal plan created", "calories": 2000, "meals": 3}'
        )

        agent = MealPlannerAgent(mock_llm)

        task = AgentTask(task_type=AgentType.MEAL_PLANNER, input_data={"calories": 2000})

        result = await agent.execute(task)

        assert result.success is True
        assert result.data is not None


class TestAgentOrchestrator:
    """Test AgentOrchestrator basic functionality."""

    def test_init_default(self):
        """Test initialization with default agents."""
        mock_llm = Mock()
        orchestrator = AgentOrchestrator(mock_llm)
        assert orchestrator.llm_provider == mock_llm
        assert len(orchestrator.agents) == 5  # All agent types

    def test_init_custom_agents(self):
        """Test initialization with custom agents."""
        mock_llm = Mock()
        orchestrator = AgentOrchestrator(mock_llm)
        assert AgentType.NUTRITION_ANALYZER in orchestrator.agents

    @pytest.mark.asyncio
    async def test_execute_single_task(self):
        """Test executing single task."""
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value='{"analysis": "test"}')

        orchestrator = AgentOrchestrator(mock_llm)

        task = AgentTask(task_type=AgentType.NUTRITION_ANALYZER, input_data={"food": "apple"})

        result = await orchestrator.execute_task(task)

        assert result.success is True
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_execute_single_task_error(self):
        """Test executing single task with error."""
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(side_effect=Exception("Task failed"))

        orchestrator = AgentOrchestrator(mock_llm)

        task = AgentTask(task_type=AgentType.NUTRITION_ANALYZER, input_data={"food": "apple"})

        result = await orchestrator.execute_task(task)

        assert result.success is False
        assert "failed" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_sequential_tasks(self):
        """Test executing sequential tasks."""
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value='{"analysis": "test"}')

        orchestrator = AgentOrchestrator(mock_llm)

        tasks = [
            AgentTask(task_type=AgentType.NUTRITION_ANALYZER, input_data={"food": "apple"}),
            AgentTask(task_type=AgentType.MEAL_PLANNER, input_data={"calories": 2000}),
        ]

        results = await orchestrator.execute_sequential_tasks(tasks)

        assert len(results) == 2
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self):
        """Test executing parallel tasks."""
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value='{"analysis": "test"}')

        orchestrator = AgentOrchestrator(mock_llm)

        tasks = [
            AgentTask(task_type=AgentType.NUTRITION_ANALYZER, input_data={"food": "apple"}),
            AgentTask(
                task_type=AgentType.HEALTH_ADVISOR, input_data={"question": "How to eat healthy?"}
            ),
        ]

        results = await orchestrator.execute_parallel_tasks(tasks)

        assert len(results) == 2
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_execute_empty_tasks(self):
        """Test executing empty task lists."""
        mock_llm = Mock()
        orchestrator = AgentOrchestrator(mock_llm)

        results = await orchestrator.execute_sequential_tasks([])
        assert len(results) == 0

        results = await orchestrator.execute_parallel_tasks([])
        assert len(results) == 0
