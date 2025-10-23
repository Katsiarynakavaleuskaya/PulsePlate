#!/bin/bash
# Strict mypy check for local development
# This script runs mypy without ignoring missing imports to catch real issues

set -euo pipefail

echo "🔍 Running strict mypy check (no missing imports ignored)..."

# Check only our AI files first
echo "📁 Checking AI files..."
python -m mypy \
    --config-file mypy.ini \
    --no-error-summary \
    app/routers/ai_chat.py \
    core/ai_router.py \
    scripts/test-ai-system.py \
    scripts/test-huggingface-embedding.py

echo "✅ AI files passed strict mypy check!"

# Optional: check all files (uncomment if you want to fix all mypy errors)
# echo "📁 Checking all Python files..."
# python -m mypy --config-file mypy.ini --no-error-summary .

echo "🎉 All checks passed!"

