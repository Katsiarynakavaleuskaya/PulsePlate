"""
AI Constants - Centralized configuration for AI providers and pricing
"""

# OpenAI GPT-4o-mini pricing (per 1K tokens) - October 2025
OPENAI_INPUT_COST_PER_1K = 0.00015  # $0.15 per 1M tokens
OPENAI_OUTPUT_COST_PER_1K = 0.00060  # $0.60 per 1M tokens

# OpenAI GPT-4o-mini pricing (per 1M tokens) - for display purposes
OPENAI_INPUT_COST_PER_1M = 0.15
OPENAI_OUTPUT_COST_PER_1M = 0.60

# Token estimation constants
AVERAGE_CHARS_PER_TOKEN = 4  # Rough estimate for English text
MAX_TOKENS_PER_REQUEST = 4000  # Conservative limit for GPT-4o-mini

# Rate limiting constants (requests per hour)
DEFAULT_RATE_LIMIT_FREE = 10
DEFAULT_RATE_LIMIT_PREMIUM = 1000
DEFAULT_RATE_LIMIT_ENTERPRISE = 10000

# Complexity thresholds
SIMPLE_QUERY_THRESHOLD = 0.3
COMPLEX_QUERY_THRESHOLD = 0.7
