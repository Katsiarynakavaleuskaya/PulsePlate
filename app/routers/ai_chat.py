"""
AI Chat Router - Smart AI routing for nutrition and health queries
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from typing import Dict, Any, Optional, List, Tuple
import logging

from core.ai_router import ai_router, RequestComplexity
from core.ai_constants import (
    OPENAI_INPUT_COST_PER_1K,
    OPENAI_OUTPUT_COST_PER_1K,
    TOKEN_MULTIPLIER,
    INPUT_RATIO,
    OUTPUT_RATIO,
)

logger = logging.getLogger(__name__)


def estimate_openai_cost(message: str) -> Tuple[float, int]:
    """
    Estimate OpenAI API cost and token usage for a message.

    Returns:
        Tuple of (estimated_cost, estimated_tokens)
    """
    # Calculate estimated tokens
    estimated_tokens = len(message.split()) * TOKEN_MULTIPLIER

    # Split into input/output tokens
    input_tokens = estimated_tokens * INPUT_RATIO
    output_tokens = estimated_tokens * OUTPUT_RATIO

    # Calculate cost using centralized constants
    cost = (input_tokens / 1000) * OPENAI_INPUT_COST_PER_1K + (
        output_tokens / 1000
    ) * OPENAI_OUTPUT_COST_PER_1K

    # Round cost to 6 decimal places
    return round(cost, 6), int(estimated_tokens)


router = APIRouter(prefix="/api/ai", tags=["AI Chat"])


class ChatRequest(BaseModel):
    """Chat request model"""

    message: str = Field(..., description="User message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_tier: Literal["free", "premium"] = Field(
        default="free", description="User subscription tier"
    )
    task_type: Literal["text", "embedding"] = Field(default="text", description="Task type")
    force_provider: Optional[Literal["ollama", "huggingface", "openai"]] = Field(
        None, description="Force specific provider (ollama/huggingface/openai)"
    )

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError("message must be a string")
        s = v.strip()
        if not s:
            raise ValueError("message cannot be empty")
        return s


class ChatResponse(BaseModel):
    """Chat response model"""

    response: str
    provider: str
    model: str
    cost: float
    tokens_used: int
    complexity: str
    fallback_used: bool = False


class NutritionAnalysisRequest(BaseModel):
    """Nutrition analysis request"""

    food_items: List[str] = Field(..., description="List of food items to analyze")
    user_profile: Dict[str, Any] = Field(default_factory=dict, description="User profile data")
    user_tier: Literal["free", "premium"] = Field(
        default="free", description="User tier (free/premium)"
    )
    analysis_type: Literal["basic", "detailed", "comprehensive"] = Field(
        default="basic", description="Type of analysis (basic/detailed/comprehensive)"
    )

    @field_validator("food_items", mode="before")
    @classmethod
    def validate_food_items(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            raise TypeError("food_items must be a list")
        items = [str(it).strip() for it in v if it is not None and str(it).strip()]
        if not items:
            raise ValueError("at least one non-empty food item is required")
        return items


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    """
    Chat with AI using smart routing between Ollama and OpenAI
    """
    try:
        # Analyze complexity first
        complexity = ai_router.analyze_complexity(request.message, request.context)

        # Use smart routing with optional provider override
        result = await ai_router.route_request(
            request.message,
            request.context,
            request.user_tier,
            user_id=(
                request.context.get("user_id", "anonymous")[:8]
                if request.context.get("user_id")
                else "anonymous"
            ),  # Truncate for privacy
            provider=request.force_provider,
            task_type=request.task_type,
        )

        # Surface router errors with proper status
        if getattr(result, "error", False):
            raise HTTPException(status_code=400, detail=result.response)

        return ChatResponse(
            response=result.response,
            provider=result.provider,
            model=result.model,
            cost=result.cost,
            tokens_used=result.tokens_used,
            complexity=complexity.value,
            fallback_used=result.fallback_used,
        )

    except Exception as e:
        logger.exception("Error in AI chat")
        raise HTTPException(status_code=500, detail="AI service error") from e


@router.post("/analyze-nutrition", response_model=ChatResponse)
async def analyze_nutrition(request: NutritionAnalysisRequest) -> ChatResponse:
    """
    Analyze nutrition data using appropriate AI provider
    """
    try:
        # Build analysis prompt
        prompt = (
            f"Analyze the nutrition content of these food items: {', '.join(request.food_items)}"
        )

        # Create normalized user profile
        user_profile = {
            **request.user_profile,
            "analysis_type": request.analysis_type,
            "tier": request.user_tier,
        }

        # Determine complexity based on analysis type
        if request.analysis_type == "comprehensive":
            complexity = RequestComplexity.COMPLEX
        elif request.analysis_type == "detailed":
            complexity = RequestComplexity.MEDIUM
        else:
            complexity = RequestComplexity.SIMPLE

        # Route request
        result = await ai_router.route_request(
            prompt,
            user_profile,
            request.user_tier,
            user_id=user_profile.get("user_id", "anonymous"),
        )

        if getattr(result, "error", False):
            raise HTTPException(status_code=400, detail=result.response)

        return ChatResponse(
            response=result.response,
            provider=result.provider,
            model=result.model,
            cost=result.cost,
            tokens_used=result.tokens_used,
            complexity=complexity.value,
            fallback_used=result.fallback_used,
        )

    except Exception as e:
        logger.exception("Error in nutrition analysis")
        raise HTTPException(status_code=500, detail=f"Analysis error: {e!s}") from e


@router.get("/providers")
async def get_available_providers() -> dict[str, Any]:
    """
    Get information about available AI providers
    """
    return {
        "providers": [
            {
                "name": "ollama",
                "description": "Local/Cloud Ollama - Free for simple queries",
                "models": ["llama3", "qwen3", "codellama"],
                "cost": "Free (local) or $20/month (cloud)",
                "best_for": ["Simple nutrition queries", "Basic meal planning"],
            },
            {
                "name": "openai",
                "description": "OpenAI API - High quality for complex queries",
                "models": ["gpt-4o-mini", "gpt-4o"],
                "cost": "$0.60 per 1M input tokens, $2.40 per 1M output tokens",
                "best_for": ["Complex analysis", "Personalized recommendations"],
            },
        ],
        "routing_strategy": {
            "simple_queries": "Ollama (free)",
            "medium_queries": "Ollama (free) or OpenAI (premium)",
            "complex_queries": "OpenAI (with fallback to Ollama)",
        },
    }


@router.get("/cost-estimate")
async def estimate_cost(message: str, provider: str = "auto") -> dict[str, Any]:
    """
    Estimate cost for a message
    """
    try:
        complexity = None
        if provider == "auto":
            complexity = ai_router.analyze_complexity(message, {})
            provider_enum = ai_router.choose_provider(complexity, "free")
            chosen_provider = provider_enum.value
        else:
            chosen_provider = provider

        complexity_value = complexity.value if complexity is not None else "unknown"

        if chosen_provider == "ollama":
            return {
                "provider": "ollama",
                "estimated_cost": 0.0,
                "complexity": complexity_value,
            }
        elif chosen_provider == "huggingface":
            return {
                "provider": "huggingface",
                "estimated_cost": 0.0,
                "complexity": complexity_value,
            }
        elif chosen_provider == "openai":
            # Use centralized cost estimation
            estimated_cost, estimated_tokens = estimate_openai_cost(message)

            return {
                "provider": "openai",
                "estimated_cost": estimated_cost,
                "estimated_tokens": estimated_tokens,
                "complexity": complexity_value,
                "estimated_cost_note": "Cost is an estimate and may differ from final billed amount",
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {chosen_provider}")

    except Exception as e:
        logger.exception("Error estimating cost")
        raise HTTPException(status_code=500, detail=f"Cost estimation error: {e!s}") from e
