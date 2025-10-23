"""
AI Router - Smart routing between Ollama and OpenAI based on request complexity
"""

import os
from typing import Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"


class RequestComplexity(Enum):
    SIMPLE = "simple"  # Basic nutrition info, simple questions
    MEDIUM = "medium"  # Meal planning, basic analysis
    COMPLEX = "complex"  # Detailed analysis, complex recommendations


class AIRouter:
    """
    Smart AI router that chooses between Ollama and OpenAI based on:
    1. Request complexity
    2. Cost optimization
    3. Quality requirements
    """

    def __init__(self):
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        self.ollama_api_key = os.getenv("OLLAMA_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Cost thresholds (requests per month)
        self.ollama_free_limit = 1000
        self.openai_budget_limit = 10000

        # Quality thresholds
        self.complexity_keywords = {
            RequestComplexity.SIMPLE: [
                "calories",
                "protein",
                "carbs",
                "fat",
                "vitamin",
                "mineral",
                "basic",
                "simple",
                "quick",
                "amount",
                "quantity",
            ],
            RequestComplexity.MEDIUM: [
                "meal plan",
                "diet",
                "nutrition",
                "recommendation",
                "suggest",
                "balance",
                "healthy",
                "recipe",
                "ingredient",
            ],
            RequestComplexity.COMPLEX: [
                "detailed analysis",
                "comprehensive",
                "personalized",
                "custom",
                "medical",
                "condition",
                "allergy",
                "intolerance",
                "special",
                "optimization",
                "advanced",
                "scientific",
            ],
        }

    def analyze_complexity(self, prompt: str, context: Dict[str, Any]) -> RequestComplexity:
        """
        Analyze request complexity based on prompt and context
        """
        prompt_lower = prompt.lower()

        # Keyword-based detection (priority: COMPLEX > MEDIUM)
        for level in (RequestComplexity.COMPLEX, RequestComplexity.MEDIUM):
            if any(kw in prompt_lower for kw in self.complexity_keywords[level]):
                return level

        # Check context for complexity indicators
        if context.get("user_conditions") or context.get("allergies"):
            return RequestComplexity.COMPLEX

        if context.get("meal_planning") or context.get("diet_goals"):
            return RequestComplexity.MEDIUM

        # Default to simple
        return RequestComplexity.SIMPLE

    def choose_provider(self, complexity: RequestComplexity, user_tier: str = "free") -> AIProvider:
        """
        Choose AI provider based on complexity and user tier
        """
        # Premium users get OpenAI for all requests
        if user_tier == "premium":
            return AIProvider.OPENAI

        # Free users: Ollama for simple/medium, OpenAI for complex (with limits)
        if user_tier == "free":
            if complexity in [RequestComplexity.SIMPLE, RequestComplexity.MEDIUM]:
                return AIProvider.OLLAMA
            else:
                # Use OpenAI for complex but with rate limiting
                return AIProvider.OPENAI

        # Default: Ollama for simple, OpenAI for medium/complex
        if complexity == RequestComplexity.SIMPLE:
            return AIProvider.OLLAMA
        else:
            return AIProvider.OPENAI

    async def route_request(
        self,
        prompt: str,
        context: Dict[str, Any],
        user_tier: str = "free",
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Route request to appropriate AI provider
        """
        if provider:
            # Force specific provider
            if provider == "ollama":
                return await self._call_ollama(prompt, context)
            elif provider == "openai":
                return await self._call_openai(prompt, context)
            else:
                raise ValueError(f"Invalid provider: {provider}. Use 'ollama' or 'openai'")

        complexity = self.analyze_complexity(prompt, context)
        chosen_provider = self.choose_provider(complexity, user_tier)

        logger.info(
            f"Routing request: complexity={complexity.value}, provider={chosen_provider.value}"
        )

        try:
            if chosen_provider == AIProvider.OLLAMA:
                return await self._call_ollama(prompt, context)
            else:
                return await self._call_openai(prompt, context)
        except Exception as e:
            logger.error(f"Error with {chosen_provider.value}: {e}")
            # Fallback to other provider
            fallback_provider = (
                AIProvider.OPENAI if chosen_provider == AIProvider.OLLAMA else AIProvider.OLLAMA
            )
            logger.info(f"Falling back to {fallback_provider.value}")

            if fallback_provider == AIProvider.OLLAMA:
                result = await self._call_ollama(prompt, context)
                result["fallback_used"] = True
                return result
            else:
                result = await self._call_openai(prompt, context)
                result["fallback_used"] = True
                return result

    async def _call_ollama(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Ollama API
        """
        import httpx

        # Prepare context for Ollama
        system_prompt = self._build_system_prompt(context)
        full_prompt = f"{system_prompt}\n\nUser: {prompt}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_endpoint}/api/generate",
                json={
                    "model": "llama3",
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "top_p": 0.9},
                },
                headers=(
                    {"Authorization": f"Bearer {self.ollama_api_key}"}
                    if self.ollama_api_key
                    else {}
                ),
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

            return {
                "response": result.get("response", ""),
                "provider": "ollama",
                "model": "llama3",
                "cost": 0,  # Free
                "tokens_used": result.get("eval_count", 0),
                "fallback_used": False,
            }

    async def _call_openai(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call OpenAI API
        """
        import openai

        client = openai.AsyncOpenAI(api_key=self.openai_api_key)

        # Prepare messages
        messages = [
            {"role": "system", "content": self._build_system_prompt(context)},
            {"role": "user", "content": prompt},
        ]

        response = await client.chat.completions.create(
            model=self.openai_model, messages=messages, temperature=0.7, max_tokens=1000
        )

        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        cost = self._calculate_openai_cost(usage) if usage else 0.0

        return {
            "response": response.choices[0].message.content,
            "provider": "openai",
            "model": self.openai_model,
            "cost": cost,
            "tokens_used": tokens_used,
            "fallback_used": False,
        }

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build system prompt based on context
        """
        base_prompt = (
            "You are a nutrition and health AI assistant for PulsePlate. "
            "Provide accurate, helpful, and personalized nutrition guidance. "
            "Do not provide medical diagnosis or emergency advice. "
            "Advise users to consult a healthcare professional for medical concerns. "
            "If information is uncertain, state limitations and suggest evidence-based sources."
        )

        if context.get("user_conditions"):
            base_prompt += f"\nUser has conditions: {', '.join(context['user_conditions'])}"

        if context.get("allergies"):
            base_prompt += f"\nUser allergies: {', '.join(context['allergies'])}"

        if context.get("diet_goals"):
            base_prompt += f"\nUser goals: {', '.join(context['diet_goals'])}"

        return base_prompt

    def _calculate_openai_cost(self, usage) -> float:
        """
        Calculate OpenAI API cost based on usage
        """
        if not usage:
            return 0.0

        # GPT-4o-mini pricing (as of 2025)
        input_cost_per_1k = 0.00015
        output_cost_per_1k = 0.0006

        input_cost = (usage.prompt_tokens / 1000) * input_cost_per_1k
        output_cost = (usage.completion_tokens / 1000) * output_cost_per_1k

        return input_cost + output_cost


# Global router instance
ai_router = AIRouter()
