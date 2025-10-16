#!/bin/bash
set -euo pipefail

# Cache analysis and health check script
# Provides detailed information about Python cache files in the repository

echo "🔍 Python Cache Analysis Report"
echo "==============================="

# Initialize variables
TRACKED_CACHE=0
CACHE_RULES=0

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "⚠️  Warning: Not in a git repository"
    echo ""
fi

# Count cache files
echo "📊 Cache File Analysis:"
echo ""

PYCACHE_DIRS=$(find . -path ./.git -prune -o -type d -name "__pycache__" -print 2>/dev/null)
PYC_FILES=$(find . -path ./.git -prune -o -type f -name "*.pyc" -print 2>/dev/null)
PYO_FILES=$(find . -path ./.git -prune -o -type f -name "*.pyo" -print 2>/dev/null)
PYD_FILES=$(find . -path ./.git -prune -o -type f -name "*.pyd" -print 2>/dev/null)

# Robust counting that handles empty strings and whitespace
PYCACHE_COUNT=$(printf '%s\n' "$PYCACHE_DIRS" | grep -v '^[[:space:]]*$' | wc -l)
PYC_COUNT=$(printf '%s\n' "$PYC_FILES" | grep -v '^[[:space:]]*$' | wc -l)
PYO_COUNT=$(printf '%s\n' "$PYO_FILES" | grep -v '^[[:space:]]*$' | wc -l)
PYD_COUNT=$(printf '%s\n' "$PYD_FILES" | grep -v '^[[:space:]]*$' | wc -l)

echo "📁 __pycache__ directories: $PYCACHE_COUNT"
echo "🐍 .pyc files: $PYC_COUNT"
echo "🐍 .pyo files: $PYO_COUNT"
echo "🐍 .pyd files: $PYD_COUNT"

TOTAL_CACHE_FILES=$((PYCACHE_COUNT + PYC_COUNT + PYO_COUNT + PYD_COUNT))

echo ""
echo "📈 Total cache artifacts: $TOTAL_CACHE_FILES"

# Calculate total size
echo ""
echo "💾 Size Analysis:"

if [ "$TOTAL_CACHE_FILES" -gt 0 ]; then
    # Calculate size of cache files (portable approach)
    if du --version >/dev/null 2>&1; then
        # GNU du available, use -ch for human readable
        CACHE_SIZE=$(find . -path ./.git -prune -o \( -name "__pycache__" -o -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \) -exec du -ch {} + 2>/dev/null | tail -1 | cut -f1)
    else
        # BSD/macOS du, use -sk and convert to human readable
        CACHE_SIZE_KB=$(find . -path ./.git -prune -o \( -name "__pycache__" -o -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \) -exec du -sk {} + 2>/dev/null | awk '{sum+=$1} END {print sum}')
        if [ -n "$CACHE_SIZE_KB" ] && [ "$CACHE_SIZE_KB" -gt 0 ]; then
            CACHE_SIZE="${CACHE_SIZE_KB}K"
        else
            CACHE_SIZE="0"
        fi
    fi

    # Ensure CACHE_SIZE is never empty
    if [ -z "$CACHE_SIZE" ]; then
        CACHE_SIZE="0"
    fi

    echo "  📏 Total cache size: $CACHE_SIZE"

    # Show largest cache directories
    echo ""
    echo "🏆 Largest cache directories:"
    # Portable: use KB sizes and numeric sort
    find . -path ./.git -prune -o -type d -name "__pycache__" -exec du -sk {} + 2>/dev/null \
      | sort -nr | head -5 | awk '{ printf "  📁 %s: %sK\n", $2, $1 }' || echo "  (No cache directories found)"

    # Show cache files by directory
    echo ""
    echo "📂 Cache files by directory:"
    find . -path ./.git -prune -o -type d -name "__pycache__" -print0 2>/dev/null | while IFS= read -r -d '' dir; do
        if [ -d "$dir" ]; then
            COUNT=$(find "$dir" -type f \( -name "*.pyc" -o -name "*.pyo" \) -print 2>/dev/null | wc -l)
            SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "0")
            echo "  📁 $dir: $COUNT files ($SIZE)"
        fi
    done
else
    echo "  ✅ No cache files found - repository is clean!"
fi

# Check .gitignore rules
echo ""
echo "🔧 .gitignore Analysis:"

if [ -f .gitignore ]; then
    CACHE_RULES=$(grep -E -v '^[[:space:]]*#' .gitignore | grep -E "(pycache|\.pyc|\.pyo|\.pyd)" | wc -l)
    echo "  📋 Cache-related .gitignore rules: $CACHE_RULES"

    if [ "$CACHE_RULES" -gt 0 ]; then
        echo "  ✅ .gitignore contains cache rules"
        echo "  📝 Current cache rules:"
        grep -E -v '^[[:space:]]*#' .gitignore | grep -E "(pycache|\.pyc|\.pyo|\.pyd)" | sed 's/^/    /'
    else
        echo "  ⚠️  No cache rules found in .gitignore"
    fi
else
    echo "  ❌ .gitignore file not found"
fi

# Check git hooks
echo ""
echo "🪝 Git Hooks Analysis:"

# Check multiple hook locations
HOOK_FOUND=false
if [ -f .githooks/pre-commit ]; then
    if grep -q "clean-cache" .githooks/pre-commit; then
        echo "  ✅ .githooks/pre-commit includes cache cleanup"
        HOOK_FOUND=true
    else
        echo "  ⚠️  .githooks/pre-commit doesn't include cache cleanup"
    fi
elif [ -f .git/hooks/pre-commit ]; then
    if grep -q "clean-cache" .git/hooks/pre-commit; then
        echo "  ✅ .git/hooks/pre-commit includes cache cleanup"
        HOOK_FOUND=true
    else
        echo "  ⚠️  .git/hooks/pre-commit doesn't include cache cleanup"
    fi
elif [ -f .pre-commit-config.yaml ]; then
    if grep -q "cache-clean\|clean-cache" .pre-commit-config.yaml; then
        echo "  ✅ .pre-commit-config.yaml includes cache cleanup"
        HOOK_FOUND=true
    else
        echo "  ⚠️  .pre-commit-config.yaml doesn't include cache cleanup"
    fi
else
    echo "  ⚠️  No pre-commit hooks found"
fi

if [ "$HOOK_FOUND" = false ]; then
    echo "  ℹ️  Consider setting up cache cleanup in pre-commit hooks"
fi

# Check if cache files are tracked by git
echo ""
echo "🔍 Git Tracking Analysis:"

if git rev-parse --git-dir > /dev/null 2>&1; then
    TRACKED_CACHE=$(git ls-files | grep -E "(pycache|\.pyc|\.pyo|\.pyd)" | wc -l)
    echo "  📊 Cache files tracked by git: $TRACKED_CACHE"

if [ "$TRACKED_CACHE" -gt 0 ]; then
    echo "  ⚠️  Warning: Some cache files are tracked by git!"
    echo "  📝 Tracked cache files:"
    git ls-files | grep -E "(pycache|\.pyc|\.pyo|\.pyd)" | head -10 | sed 's/^/    /'
    if [ "$TRACKED_CACHE" -gt 10 ]; then
        echo "    ... and $((TRACKED_CACHE - 10)) more"
    fi
    echo "  🔧 To remove from tracking:"
    echo "     find . -type d -name '__pycache__' -print0 | xargs -0 git rm -r --cached"
    echo "     find . -type f -name '*.pyc' -print0 | xargs -0 git rm --cached"
else
    echo "  ✅ No cache files are tracked by git"
fi
else
    echo "  ℹ️  Not in a git repository"
fi

# Health score
echo ""
echo "🏥 Cache Health Score:"

HEALTH_SCORE=100

if [ "$TOTAL_CACHE_FILES" -gt 0 ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 20))
fi

if [ "$TRACKED_CACHE" -gt 0 ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 30))
fi

if [ "$CACHE_RULES" -eq 0 ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 20))
fi

if [ ! -f .githooks/pre-commit ] && [ ! -f .git/hooks/pre-commit ] && [ ! -f .pre-commit-config.yaml ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 10))
fi

echo "  📊 Health Score: $HEALTH_SCORE/100"

if [ "$HEALTH_SCORE" -ge 90 ]; then
    echo "  🟢 Excellent - Cache management is well configured"
elif [ "$HEALTH_SCORE" -ge 70 ]; then
    echo "  🟡 Good - Minor improvements needed"
elif [ "$HEALTH_SCORE" -ge 50 ]; then
    echo "  🟠 Fair - Several issues need attention"
else
    echo "  🔴 Poor - Major cache management issues"
fi

echo ""
echo "💡 Recommendations:"

if [ "$TOTAL_CACHE_FILES" -gt 0 ]; then
    echo "  🧹 Run './scripts/clean-cache.sh' to remove cache files"
fi

if [ "$TRACKED_CACHE" -gt 0 ]; then
    echo "  🚫 Remove cache files from git tracking:"
    echo "     git rm -r --cached **/__pycache__"
    echo "     git rm --cached **/*.pyc"
fi

if [ "$CACHE_RULES" -eq 0 ]; then
    echo "  📝 Add cache rules to .gitignore"
fi

if [ ! -f .githooks/pre-commit ]; then
    echo "  🪝 Set up pre-commit hook for automatic cache cleanup"
fi

echo ""
echo "✅ Cache analysis completed!"
