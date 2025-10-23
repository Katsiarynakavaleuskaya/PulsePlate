"""
AI Router - Smart routing between Ollama and OpenAI based on request complexity
"""

import os
from typing import Dict, Any, Optional
from enum import Enum
import logging
import httpx
import openai

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"


class RequestComplexity(Enum):
    SIMPLE = "simple"  # Basic nutrition info, simple questions
    MEDIUM = "medium"  # Meal planning, basic analysis
    COMPLEX = "complex"  # Detailed analysis, complex recommendations


class AIRouter:
    """
    Smart AI router that chooses between Ollama, Hugging Face, and OpenAI based on:
    1. Request complexity
    2. Cost optimization
    3. Quality requirements
    4. Task type (embeddings vs text generation)
    """

    def __init__(self):
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        self.ollama_api_key = os.getenv("OLLAMA_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))

        # Hugging Face configuration
        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        self.huggingface_model = os.getenv("HUGGINGFACE_MODEL", "nvidia/llama-embed-nemotron-8b")
        self.huggingface_max_length = int(os.getenv("HUGGINGFACE_MAX_LENGTH", "512"))

        # Validate required environment variables (only in production)
        # Skip validation during testing or when environment variables are not set
        if os.getenv("ENVIRONMENT") == "production":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            if not self.ollama_api_key:
                raise ValueError("OLLAMA_API_KEY environment variable is required")

        # Validate OLLAMA_ENDPOINT URL
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.ollama_endpoint)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid OLLAMA_ENDPOINT URL: {self.ollama_endpoint}")
        except Exception as e:
            raise ValueError(f"Invalid OLLAMA_ENDPOINT URL: {self.ollama_endpoint}") from e

        # Note: Rate limiting not implemented yet
        # Future: self.ollama_free_limit = int(os.getenv("OLLAMA_FREE_LIMIT", "1000"))
        # Future: self.openai_budget_limit = int(os.getenv("OPENAI_BUDGET_LIMIT", "10000"))

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

    def choose_provider(
        self, complexity: RequestComplexity, user_tier: str = "free", task_type: str = "text"
    ) -> AIProvider:
        """
        Choose AI provider based on complexity, user tier, and task type
        """
        # For embedding tasks, prefer Hugging Face (free tier available)
        if task_type == "embedding" and self.huggingface_api_token:
            return AIProvider.HUGGINGFACE

        # Premium users get OpenAI for all text requests
        if user_tier == "premium" and task_type == "text":
            return AIProvider.OPENAI

        # Free users: Ollama for simple/medium, OpenAI for complex queries
        # TODO: Implement proper rate limiting with Redis/memory store
        # For now, free users are limited to Ollama only
        if user_tier == "free":
            return AIProvider.OLLAMA

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
        task_type: str = "text",
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
            elif provider == "huggingface":
                return await self._call_huggingface(prompt, context)
            else:
                raise ValueError(
                    f"Invalid provider: {provider}. Use 'ollama', 'openai', or 'huggingface'"
                )

        complexity = self.analyze_complexity(prompt, context)
        chosen_provider = self.choose_provider(complexity, user_tier, task_type)

        logger.info(
            f"Routing request: complexity={complexity.value}, provider={chosen_provider.value}"
        )

        try:
            if chosen_provider == AIProvider.OLLAMA:
                return await self._call_ollama(prompt, context)
            elif chosen_provider == AIProvider.HUGGINGFACE:
                return await self._call_huggingface(prompt, context)
            else:
                return await self._call_openai(prompt, context)
        except (httpx.HTTPError, openai.APIError, Exception) as e:
            logger.exception(f"Error with {chosen_provider.value}, attempting fallback")
            # Fallback to other provider (prioritize Ollama for free users)
            if chosen_provider == AIProvider.HUGGINGFACE:
                fallback_provider = AIProvider.OLLAMA
            elif chosen_provider == AIProvider.OLLAMA:
                fallback_provider = AIProvider.OPENAI
            else:
                fallback_provider = AIProvider.OLLAMA

            logger.info(f"Falling back to {fallback_provider.value}")

            try:
                if fallback_provider == AIProvider.OLLAMA:
                    result = await self._call_ollama(prompt, context)
                    result["fallback_used"] = True
                    return result
                elif fallback_provider == AIProvider.HUGGINGFACE:
                    result = await self._call_huggingface(prompt, context)
                    result["fallback_used"] = True
                    return result
                else:
                    result = await self._call_openai(prompt, context)
                    result["fallback_used"] = True
                    return result
            except Exception as fallback_error:
                logger.exception(f"Fallback to {fallback_provider.value} also failed")
                # Return error structure instead of re-raising
                return {
                    "response": f"Both AI providers failed. Original error: {e}, Fallback error: {fallback_error}",
                    "provider": fallback_provider.value,
                    "model": "error",
                    "cost": 0.0,
                    "tokens_used": 0,
                    "fallback_used": True,
                    "error": True,
                }

    async def _call_ollama(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Ollama API
        """

        # Prepare context for Ollama
        system_prompt = self._build_system_prompt(context)
        full_prompt = f"{system_prompt}\n\nUser: {prompt}"

        # Configure timeout for connection and requests
        timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT", "30"))
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                f"{self.ollama_endpoint}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "top_p": 0.9},
                },
                headers=(
                    {"Authorization": f"Bearer {self.ollama_api_key}"}
                    if self.ollama_api_key
                    else {}
                ),
            )
            response.raise_for_status()
            result = response.json()

            return {
                "response": result.get("response", ""),
                "provider": "ollama",
                "model": self.ollama_model,
                "cost": 0,  # Free
                "tokens_used": result.get("eval_count", 0),
                "fallback_used": False,
            }

    async def _call_openai(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call OpenAI API
        """

        # Configure timeout (configurable via environment)
        timeout_seconds = int(os.getenv("OPENAI_TIMEOUT", "30"))
        client = openai.AsyncOpenAI(api_key=self.openai_api_key, timeout=timeout_seconds)

        # Prepare messages
        messages = [
            {"role": "system", "content": self._build_system_prompt(context)},
            {"role": "user", "content": prompt},
        ]

        response = await client.chat.completions.create(
            model=self.openai_model, messages=messages, temperature=0.7, max_tokens=self.max_tokens  # type: ignore
        )

        usage = response.usage
        tokens_used = usage.total_tokens if usage else 0
        cost = self._calculate_openai_cost(usage) if usage else 0.0

        # Check if choices array is empty
        if not response.choices or len(response.choices) == 0:
            raise ValueError("OpenAI API returned empty choices array")

        return {
            "response": response.choices[0].message.content,
            "provider": "openai",
            "model": self.openai_model,
            "cost": cost,
            "tokens_used": tokens_used,
            "fallback_used": False,
        }

    async def _call_huggingface(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Hugging Face API for embeddings
        """
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch

            # Load model and tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                self.huggingface_model, trust_remote_code=True, token=self.huggingface_api_token
            )
            model = AutoModel.from_pretrained(
                self.huggingface_model, trust_remote_code=True, token=self.huggingface_api_token
            )

            # Tokenize input
            inputs = tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.huggingface_max_length,
            )

            # Generate embedding
            with torch.no_grad():
                outputs = model(**inputs)
                # Use mean pooling for sentence-level embedding
                embeddings = outputs.last_hidden_state.mean(dim=1)

            return {
                "response": embeddings.tolist(),  # Convert to list for JSON serialization
                "provider": "huggingface",
                "model": self.huggingface_model,
                "cost": 0.0,  # Free tier
                "tokens_used": inputs.input_ids.shape[1],
                "fallback_used": False,
            }

        except Exception as e:
            logger.error(f"Hugging Face API error: {e}")
            raise

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

    def _calculate_openai_cost(self, usage: Any) -> float:
        """
        Calculate OpenAI API cost based on usage
        """
        if not usage:
            return 0.0

        # GPT-4o-mini pricing (as of 2025)
        input_cost_per_1k = 0.0006
        output_cost_per_1k = 0.0024

        input_cost = (usage.prompt_tokens / 1000) * input_cost_per_1k
        output_cost = (usage.completion_tokens / 1000) * output_cost_per_1k

        return float(input_cost + output_cost)


# Global router instance
ai_router = AIRouter()
