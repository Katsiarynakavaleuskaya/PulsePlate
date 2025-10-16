#!/bin/bash

# Duplication detection script
echo "🔍 Checking for code duplication..."

set -euo pipefail

# Check for duplicate imports in TypeScript files
echo "📦 Checking for duplicate imports..."
DUPLICATE_IMPORTS=$(find frontend/src -type f \( -name "*.ts" -o -name "*.tsx" \) -exec grep -h "from ['\"].*['\"]" {} \; | sort | uniq -d || true)
if [ ! -z "$DUPLICATE_IMPORTS" ]; then
    echo "❌ Found files with potential duplicate imports:"
    echo "$DUPLICATE_IMPORTS"
    exit 1
fi

# Check for duplicate test cases
echo "🧪 Checking for duplicate test cases..."
DUPLICATE_TESTS=$(find frontend/src -type f \( -name "*.test.ts" -o -name "*.test.tsx" \) -exec grep -oh "it(['\"][^'\"]*['\"]" {} \; | sort | uniq -d || true)
if [ ! -z "$DUPLICATE_TESTS" ]; then
    echo "❌ Found potential duplicate test cases:"
    echo "$DUPLICATE_TESTS"
    exit 1
fi

# Check for duplicate function names
echo "🔧 Checking for duplicate function names..."
DUPLICATE_FUNCTIONS=$(find frontend/src -name "*.ts" -o -name "*.tsx" | xargs grep -h "function\|const.*=" | grep -o "function [a-zA-Z_][a-zA-Z0-9_]*\|const [a-zA-Z_][a-zA-Z0-9_]*" | sort | uniq -d || true)
if [ ! -z "$DUPLICATE_FUNCTIONS" ]; then
    echo "⚠️  Found potential duplicate function names:"
    echo "$DUPLICATE_FUNCTIONS"
    echo "Note: This might be false positive for legitimate function overloading"
fi

# Check for duplicate strings (common patterns)
echo "📝 Checking for duplicate strings..."
DUPLICATE_STRINGS=$(find frontend/src -name "*.ts" -o -name "*.tsx" | xargs grep -o '"[^"]\{20,\}"' | sort | uniq -c | sort -nr | head -10 || true)
if [ ! -z "$DUPLICATE_STRINGS" ]; then
    echo "📊 Most common strings (potential candidates for constants):"
    echo "$DUPLICATE_STRINGS"
fi

echo "✅ Duplication check completed"
