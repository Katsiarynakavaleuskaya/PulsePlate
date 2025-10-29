# -*- coding: utf-8 -*-
"""
Enhanced LLM system based on Claude Cookbooks best practices.
Implements JSON mode, structured responses, and better error handling.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union, cast
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseFormat(Enum):
    """Supported response formats for LLM."""

    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


@dataclass
class LLMResponse:
    """Structured response from LLM with validation."""

    content: str
    format: ResponseFormat
    is_valid: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "format": self.format.value,
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
        }


class EnhancedLLMProvider:
    """Enhanced LLM provider with JSON mode and structured responses."""

    def __init__(self, base_provider: Any):
        """Initialize with base provider."""
        self.base_provider = base_provider
        self.json_mode = True  # Enable JSON mode by default

    async def generate_structured(
        self,
        prompt: str,
        response_format: ResponseFormat = ResponseFormat.JSON,
        schema: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """
        Generate structured response with validation.

        Args:
            prompt: Input prompt
            response_format: Desired response format
            schema: JSON schema for validation (if JSON mode)
            max_retries: Maximum retry attempts

        Returns:
            LLMResponse with validation results
        """
        for attempt in range(max_retries):
            try:
                # Enhance prompt for structured output
                enhanced_prompt = self._enhance_prompt(prompt, response_format, schema)

                # Generate response
                response = await self._generate_response(enhanced_prompt)

                # Validate response
                validation_result = self._validate_response(response, response_format, schema)

                return LLMResponse(
                    content=response,
                    format=response_format,
                    is_valid=validation_result["is_valid"],
                    error_message=validation_result.get("error"),
                    metadata={"attempt": attempt + 1, "retries": max_retries},
                )

            except Exception as e:
                logger.warning(f"LLM generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return LLMResponse(
                        content="",
                        format=response_format,
                        is_valid=False,
                        error_message=f"Failed after {max_retries} attempts: {str(e)}",
                        metadata={"attempts": max_retries},
                    )

    def _enhance_prompt(
        self, prompt: str, response_format: ResponseFormat, schema: Optional[Dict[str, Any]]
    ) -> str:
        """Enhance prompt for structured output."""
        if response_format == ResponseFormat.JSON:
            json_instructions = """
            IMPORTANT: Respond with valid JSON only. No additional text, explanations, or markdown formatting.
            Ensure the JSON is properly formatted and complete.
            """

            if schema:
                # Convert schema to JSON-safe format
                safe_schema = {}
                for key, value in schema.items():
                    if isinstance(value, type):
                        safe_schema[key] = value.__name__
                    else:
                        safe_schema[key] = value
                json_instructions += (
                    f"\n\nRequired JSON schema:\n{json.dumps(safe_schema, indent=2)}"
                )

            return f"{prompt}\n\n{json_instructions}"

        elif response_format == ResponseFormat.STRUCTURED:
            return f"{prompt}\n\nProvide a structured response with clear sections and consistent formatting."

        return prompt

    async def _generate_response(self, prompt: str) -> str:
        """Generate response using base provider."""
        if hasattr(self.base_provider, "generate"):
            response = await self.base_provider.generate(prompt)
            return str(response)
        elif hasattr(self.base_provider, "chat"):
            response = await self.base_provider.chat(prompt)
            return str(response)
        else:
            raise ValueError("Base provider must have 'generate' or 'chat' method")

    def _validate_response(
        self, response: str, response_format: ResponseFormat, schema: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate response format and content."""
        if response_format == ResponseFormat.JSON:
            try:
                parsed = json.loads(response)

                # Basic JSON validation
                if not isinstance(parsed, (dict, list)):
                    return {"is_valid": False, "error": "JSON must be object or array"}

                # Schema validation if provided
                if schema:
                    # Simple schema validation (can be enhanced with jsonschema library)
                    if isinstance(parsed, dict) and isinstance(schema, dict):
                        for key, expected_type in schema.items():
                            if key not in parsed:
                                return {
                                    "is_valid": False,
                                    "error": f"Missing required field: {key}",
                                }
                            if isinstance(expected_type, type):
                                if not isinstance(parsed[key], expected_type):
                                    return {
                                        "is_valid": False,
                                        "error": f"Field '{key}' has wrong type",
                                    }

                return {"is_valid": True}

            except json.JSONDecodeError as e:
                return {"is_valid": False, "error": f"Invalid JSON: {str(e)}"}

        elif response_format == ResponseFormat.STRUCTURED:
            # Basic structured validation
            if len(response.strip()) < 10:
                return {"is_valid": False, "error": "Response too short for structured format"}

            return {"is_valid": True}

        return {"is_valid": True}


class NutritionAnalysisAgent:
    """Specialized agent for nutrition analysis using enhanced LLM."""

    def __init__(self, llm_provider: EnhancedLLMProvider):
        """Initialize with enhanced LLM provider."""
        self.llm = llm_provider

    async def analyze_food_item(self, food_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze food item and return structured nutrition insights."""
        prompt = f"""
        Analyze the following food item and provide nutrition insights:

        Food Data: {json.dumps(food_data, indent=2)}

        Provide analysis in the following JSON format:
        {{
            "nutrition_score": "number between 1-10",
            "health_benefits": ["list of benefits"],
            "concerns": ["list of potential concerns"],
            "recommendations": ["list of recommendations"],
            "nutrient_highlights": {{
                "highest": "nutrient name",
                "lowest": "nutrient name",
                "balanced": true/false
            }},
            "meal_suggestions": ["suggested meal contexts"]
        }}
        """

        response = await self.llm.generate_structured(
            prompt,
            ResponseFormat.JSON,
            schema={
                "nutrition_score": int,
                "health_benefits": list,
                "concerns": list,
                "recommendations": list,
                "nutrient_highlights": dict,
                "meal_suggestions": list,
            },
        )

        if response.is_valid:
            parsed_content = cast(Dict[str, Any], json.loads(response.content))
            return parsed_content
        else:
            logger.error(f"Failed to analyze food item: {response.error_message}")
            return {
                "nutrition_score": 5,
                "health_benefits": [],
                "concerns": ["Analysis failed"],
                "recommendations": ["Manual review recommended"],
                "nutrient_highlights": {"balanced": False},
                "meal_suggestions": [],
            }

    async def suggest_meal_plan(
        self, user_preferences: Dict[str, Any], available_foods: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Suggest meal plan based on user preferences and available foods."""
        prompt = f"""
        Create a personalized meal plan based on:

        User Preferences: {json.dumps(user_preferences, indent=2)}
        Available Foods: {json.dumps(available_foods[:10], indent=2)}  # Limit for context

        Provide meal plan in JSON format:
        {{
            "breakfast": {{
                "foods": ["list of foods"],
                "calories": "estimated calories",
                "nutrients": {{"protein": "g", "carbs": "g", "fat": "g"}}
            }},
            "lunch": {{...}},
            "dinner": {{...}},
            "snacks": {{...}},
            "daily_totals": {{
                "calories": "total",
                "protein": "total g",
                "carbs": "total g",
                "fat": "total g"
            }},
            "notes": ["personalized recommendations"]
        }}
        """

        response = await self.llm.generate_structured(prompt, ResponseFormat.JSON)

        if response.is_valid:
            parsed_plan = cast(Dict[str, Any], json.loads(response.content))
            return parsed_plan
        else:
            logger.error(f"Failed to generate meal plan: {response.error_message}")
            return {"error": "Failed to generate meal plan"}


# Integration with existing LLM system
def create_enhanced_provider(base_provider: Any) -> EnhancedLLMProvider:
    """Create enhanced provider from existing base provider."""
    return EnhancedLLMProvider(base_provider)


def create_nutrition_agent(base_provider: Any) -> NutritionAnalysisAgent:
    """Create nutrition analysis agent."""
    enhanced_provider = create_enhanced_provider(base_provider)
    return NutritionAnalysisAgent(enhanced_provider)
