#!/usr/bin/env bash

# Duplication detection script
echo "🔍 Checking for code duplication..."

set -euo pipefail

# Check for duplicate imports (within the same file)
echo "📦 Checking for duplicate imports (within the same file)..."
found_import_dups=0
while IFS= read -r -d '' f; do
  dups=$(grep -hE "^\s*import .+ from ['\"][^'\"]+['\"]" "$f" | sed -E 's/\s+/ /g' | sort | uniq -d || true)
  if [ -n "$dups" ]; then
    echo "❌ $f has duplicate imports:"
    echo "$dups"
    found_import_dups=1
  fi
done < <(find frontend/src -type f \( -name "*.ts" -o -name "*.tsx" \) -print0)
if [ $found_import_dups -eq 1 ]; then
  exit 1
fi

# Check for duplicate test cases (within the same file)
echo "🧪 Checking for duplicate test cases (within the same file)..."
found_test_dups=0
while IFS= read -r -d '' f; do
  dups=$(grep -ohE "\b(it|test)\s*\(\s*['\"][^'\"]+['\"]" "$f" \
    | sed -E "s/^\s*(it|test)\s*\(\s*['\"](.*)['\"].*$/\2/" \
    | sort | uniq -d || true)
  if [ -n "$dups" ]; then
    echo "❌ $f has duplicate test titles:"
    echo "$dups"
    found_test_dups=1
  fi
done < <(find frontend/src -type f \( -name "*.test.ts" -o -name "*.test.tsx" \) -print0)
if [ $found_test_dups -eq 1 ]; then
  exit 1
fi

# Check for duplicate function names
echo "🔧 Checking for duplicate function names..."
DUPLICATE_FUNCTIONS=$(
  find frontend/src -type f \( -name "*.ts" -o -name "*.tsx" \) -print0 \
  | xargs -0 grep -hE "^\s*(export\s+)?(async\s+)?function\b|^\s*(export\s+)?(const|let|var)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*[=:]\s*(async\s+)?\(|^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*{" \
  | grep -oE "(export\s+)?(async\s+)?function\s+[a-zA-Z_][a-zA-Z0-9_]*|(export\s+)?(const|let|var)\s+[a-zA-Z_][a-zA-Z0-9_]*|^[a-zA-Z_][a-zA-Z0-9_]*\s*\(" \
  | sed -E 's/^(export\s+)?(async\s+)?function\s+//; s/^(export\s+)?(const|let|var)\s+//; s/\s*\(.*$//' \
  | sort | uniq -d || true
)
if [ -n "$DUPLICATE_FUNCTIONS" ]; then
    echo "⚠️  Found potential duplicate function names:"
    echo "$DUPLICATE_FUNCTIONS"
    echo "Note: This might be false positive for legitimate function overloading"
fi

# Check for duplicate strings (common patterns)
echo "📝 Checking for duplicate strings..."
DUPLICATE_STRINGS=$(
  find frontend/src -type f \( -name "*.ts" -o -name "*.tsx" \) -print0 \
  | xargs -0 grep -ohE '"[^"]{20,}"' \
  | sort | uniq -c | sort -nr | head -10 || true
)
if [ -n "$DUPLICATE_STRINGS" ]; then
    echo "📊 Most common strings (potential candidates for constants):"
    echo "$DUPLICATE_STRINGS"
fi

echo "✅ Duplication check completed"
