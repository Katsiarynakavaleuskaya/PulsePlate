"""
AI service constants and configuration
"""

# OpenAI pricing constants (as of 2025-10-23)
# GPT-4o-mini pricing per 1M tokens
OPENAI_INPUT_COST_PER_1M = 0.60  # $0.60 per 1M input tokens
OPENAI_OUTPUT_COST_PER_1M = 2.40  # $2.40 per 1M output tokens

# Convert to per-1K for calculations
OPENAI_INPUT_COST_PER_1K = OPENAI_INPUT_COST_PER_1M / 1000  # $0.0006 per 1K input tokens
OPENAI_OUTPUT_COST_PER_1K = OPENAI_OUTPUT_COST_PER_1M / 1000  # $0.0024 per 1K output tokens

# Token estimation constants
TOKEN_MULTIPLIER = 1.3  # Rough approximation factor
INPUT_RATIO = 0.7  # 70% of tokens are input
OUTPUT_RATIO = 0.3  # 30% of tokens are output
