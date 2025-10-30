#!/bin/bash
set -euo pipefail

# Enhanced Python cache cleanup script
# Cleans all Python cache files and provides detailed reporting

echo "🧹 Enhanced Python Cache Cleanup"
echo "================================="

# Count files before cleanup
echo "📊 Analyzing cache files before cleanup..."

# Utility to count NUL-separated results safely
count_null_separated() {
    local count=0
    while IFS= read -r -d '' _; do
        ((count++))
    done
    printf '%d\n' "$count"
}

PYCACHE_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type d -name "__pycache__" -print0 2>/dev/null))
PYC_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type f -name "*.pyc" -print0 2>/dev/null))
PYO_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type f -name "*.pyo" -print0 2>/dev/null))
PYD_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type f -name "*.pyd" -print0 2>/dev/null))
PYTEST_CACHE_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type d -name ".pytest_cache" -print0 2>/dev/null))
MYPY_CACHE_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type d -name ".mypy_cache" -print0 2>/dev/null))
RUFF_CACHE_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type d -name ".ruff_cache" -print0 2>/dev/null))
HYPOTHESIS_CACHE_COUNT=$(count_null_separated < <(find . -path ./.git -prune -o -type d -name ".hypothesis" -print0 2>/dev/null))

echo "Found:"
echo "  📁 __pycache__ directories: $PYCACHE_COUNT"
echo "  🐍 .pyc files: $PYC_COUNT"
echo "  🐍 .pyo files: $PYO_COUNT"
echo "  🐍 .pyd files: $PYD_COUNT"
echo "  🧪 .pytest_cache directories: $PYTEST_CACHE_COUNT"
echo "  🔎 .mypy_cache directories: $MYPY_CACHE_COUNT"
echo "  🦊 .ruff_cache directories: $RUFF_CACHE_COUNT"
echo "  🧬 .hypothesis directories: $HYPOTHESIS_CACHE_COUNT"

if [ "$PYCACHE_COUNT" -eq 0 ] && [ "$PYC_COUNT" -eq 0 ] && [ "$PYO_COUNT" -eq 0 ] && [ "$PYD_COUNT" -eq 0 ] \
   && [ "$PYTEST_CACHE_COUNT" -eq 0 ] && [ "$MYPY_CACHE_COUNT" -eq 0 ] \
   && [ "$RUFF_CACHE_COUNT" -eq 0 ] && [ "$HYPOTHESIS_CACHE_COUNT" -eq 0 ]; then
    echo "✅ No cache files found - repository is clean!"
    exit 0
fi

echo ""
echo "🗑️  Starting cleanup..."

# Remove __pycache__ directories (skip .git)
REMOVED_DIRS=0
while IFS= read -r -d '' dir; do
    rm -rf "$dir" && echo "  🗂️  Removed: $dir" && ((REMOVED_DIRS++))
done < <(find . -path ./.git -prune -o -type d -name "__pycache__" -print0 2>/dev/null)

# Remove .pytest_cache directories
REMOVED_PYTEST=0
while IFS= read -r -d '' dir; do
    rm -rf "$dir" && echo "  🧪 Removed: $dir" && ((REMOVED_PYTEST++))
done < <(find . -path ./.git -prune -o -type d -name ".pytest_cache" -print0 2>/dev/null)

# Remove .mypy_cache directories
REMOVED_MYPY=0
while IFS= read -r -d '' dir; do
    rm -rf "$dir" && echo "  🔎 Removed: $dir" && ((REMOVED_MYPY++))
done < <(find . -path ./.git -prune -o -type d -name ".mypy_cache" -print0 2>/dev/null)

# Remove .ruff_cache directories
REMOVED_RUFF=0
while IFS= read -r -d '' dir; do
    rm -rf "$dir" && echo "  🦊 Removed: $dir" && ((REMOVED_RUFF++))
done < <(find . -path ./.git -prune -o -type d -name ".ruff_cache" -print0 2>/dev/null)

# Remove .hypothesis directories
REMOVED_HYPOTHESIS=0
while IFS= read -r -d '' dir; do
    rm -rf "$dir" && echo "  🧬 Removed: $dir" && ((REMOVED_HYPOTHESIS++))
done < <(find . -path ./.git -prune -o -type d -name ".hypothesis" -print0 2>/dev/null)

# Remove .pyc files (skip .git)
REMOVED_PYC=0
while IFS= read -r -d '' file; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  🐍 Removed: $file"
        ((REMOVED_PYC++))
    fi
done < <(find . -path ./.git -prune -o -type f -name "*.pyc" -print0 2>/dev/null)

# Remove .pyo files (skip .git)
REMOVED_PYO=0
while IFS= read -r -d '' file; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  🐍 Removed: $file"
        ((REMOVED_PYO++))
    fi
done < <(find . -path ./.git -prune -o -type f -name "*.pyo" -print0 2>/dev/null)

# Remove .pyd files (Windows) (skip .git)
REMOVED_PYD=0
while IFS= read -r -d '' file; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "  🐍 Removed: $file"
        ((REMOVED_PYD++))
    fi
done < <(find . -path ./.git -prune -o -type f -name "*.pyd" -print0 2>/dev/null)

echo ""
echo "📊 Cleanup Summary:"
echo "  📁 __pycache__ directories removed: $REMOVED_DIRS"
echo "  🐍 .pyc files removed: $REMOVED_PYC"
echo "  🐍 .pyo files removed: $REMOVED_PYO"
echo "  🐍 .pyd files removed: $REMOVED_PYD"
echo "  🧪 .pytest_cache directories removed: $REMOVED_PYTEST"
echo "  🔎 .mypy_cache directories removed: $REMOVED_MYPY"
echo "  🦊 .ruff_cache directories removed: $REMOVED_RUFF"
echo "  🧬 .hypothesis directories removed: $REMOVED_HYPOTHESIS"

TOTAL_REMOVED=$((REMOVED_DIRS + REMOVED_PYC + REMOVED_PYO + REMOVED_PYD + REMOVED_PYTEST + REMOVED_MYPY + REMOVED_RUFF + REMOVED_HYPOTHESIS))
echo "  📈 Total items removed: $TOTAL_REMOVED"

echo ""
echo "✅ Cache cleanup completed successfully!"

# Show git status to verify
echo ""
echo "📋 Current git status:"
git status --porcelain 2>/dev/null | head -10 || echo "  (No git repository or no changes)"
