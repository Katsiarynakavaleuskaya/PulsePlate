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

# Helper: safely run find and count, capturing errors and exit status
# Usage: safe_find_count "description" "find_args..."
# Returns count via stdout, logs warnings to stderr if find fails
safe_find_count() {
    local description="$1"
    shift
    local find_args=("$@")
    local temp_stderr
    local find_exit
    local count
    local captured_stderr

    # Create temp file for stderr capture
    temp_stderr=$(mktemp)

    # Run find, redirecting stderr to temp file, pipe stdout to counter
    count=$(find "${find_args[@]}" -print0 2>"$temp_stderr" | count_null_separated)
    find_exit=${PIPESTATUS[0]}

    # Capture stderr content
    captured_stderr=$(cat "$temp_stderr")
    rm -f "$temp_stderr"

    # If find failed, log warning but continue with count
    if [ "$find_exit" -ne 0 ]; then
        echo "⚠️  Warning: find command failed for '$description' (exit code: $find_exit)" >&2
        if [ -n "$captured_stderr" ]; then
            echo "   Error output: $captured_stderr" >&2
        fi
    fi

    printf '%d\n' "$count"
}

# Helper: remove cache directories by name with emoji and write count to a variable
remove_cache_dirs() {
    local dir_name="$1"
    local emoji="$2"
    local counter_var_name="$3"
    local failed_counter_var_name="${4:-}"
    local removed_count=0
    local failed_count=0

    while IFS= read -r -d '' dir; do
        rm -rf "$dir" 2>/dev/null
        local rm_exit_code=$?
        if [ $rm_exit_code -eq 0 ]; then
            echo "  ${emoji} Removed: $dir"
            ((removed_count++))
        else
            echo "  ❌ Failed to remove: $dir (exit code: $rm_exit_code)" >&2
            ((failed_count++))
        fi
    done < <(find . -path "./.git" -prune -o -type d -name "$dir_name" -print0 2>/dev/null)

    # Write back to the provided counter variable name using nameref (type-safe, requires bash 4.3+)
    declare -n counter="$counter_var_name"
    counter=$removed_count
    if [ -n "$failed_counter_var_name" ]; then
        declare -n failed_counter="$failed_counter_var_name"
        failed_counter=$failed_count
    fi
}

# Helper: remove cache files by pattern with emoji and write count to a variable
# Requires bash 4.3+ for nameref support
remove_cache_files() {
    local pattern="$1"
    local emoji="$2"
    local counter_var_name="$3"
    local failed_counter_var_name="${4:-}"
    local removed_count=0
    local failed_count=0

    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then
            rm -f "$file" 2>/dev/null
            local rm_exit_code=$?
            if [ $rm_exit_code -eq 0 ]; then
                echo "  ${emoji} Removed: $file"
                ((removed_count++))
            else
                echo "  ❌ Failed to remove: $file (exit code: $rm_exit_code)" >&2
                ((failed_count++))
            fi
        fi
    done < <(find . -path "./.git" -prune -o -type f -name "$pattern" -print0 2>/dev/null)

    # Write back to the provided counter variable name using nameref (type-safe, requires bash 4.3+)
    declare -n counter="$counter_var_name"
    counter=$removed_count
    if [ -n "$failed_counter_var_name" ]; then
        declare -n failed_counter="$failed_counter_var_name"
        failed_counter=$failed_count
    fi
}

PYCACHE_COUNT=$(safe_find_count "__pycache__ directories" . -path "./.git" -prune -o -type d -name "__pycache__" -print0)
PYC_COUNT=$(safe_find_count "*.pyc files" . -path "./.git" -prune -o -type f -name "*.pyc" -print0)
PYO_COUNT=$(safe_find_count "*.pyo files" . -path "./.git" -prune -o -type f -name "*.pyo" -print0)
PYD_COUNT=$(safe_find_count "*.pyd files" . -path "./.git" -prune -o -type f -name "*.pyd" -print0)
PYTEST_CACHE_COUNT=$(safe_find_count ".pytest_cache directories" . -path "./.git" -prune -o -type d -name ".pytest_cache" -print0)
MYPY_CACHE_COUNT=$(safe_find_count ".mypy_cache directories" . -path "./.git" -prune -o -type d -name ".mypy_cache" -print0)
RUFF_CACHE_COUNT=$(safe_find_count ".ruff_cache directories" . -path "./.git" -prune -o -type d -name ".ruff_cache" -print0)
HYPOTHESIS_CACHE_COUNT=$(safe_find_count ".hypothesis directories" . -path "./.git" -prune -o -type d -name ".hypothesis" -print0)

echo "Found:"
echo "  📁 __pycache__ directories: $PYCACHE_COUNT"
echo "  🐍 .pyc files: $PYC_COUNT"
echo "  🐍 .pyo files: $PYO_COUNT"
echo "  🐍 .pyd files: $PYD_COUNT"
echo "  🧪 .pytest_cache directories: $PYTEST_CACHE_COUNT"
echo "  🔎 .mypy_cache directories: $MYPY_CACHE_COUNT"
echo "  🦊 .ruff_cache directories: $RUFF_CACHE_COUNT"
echo "  🧬 .hypothesis directories: $HYPOTHESIS_CACHE_COUNT"

# Compute total count of all cache items
TOTAL_COUNT=$((PYCACHE_COUNT + PYC_COUNT + PYO_COUNT + PYD_COUNT + \
               PYTEST_CACHE_COUNT + MYPY_CACHE_COUNT + RUFF_CACHE_COUNT + HYPOTHESIS_CACHE_COUNT))

if [ "$TOTAL_COUNT" -eq 0 ]; then
    echo "✅ No cache files found - repository is clean!"
    exit 0
fi

echo ""
echo "🗑️  Starting cleanup..."

# Remove __pycache__ directories
REMOVED_DIRS=0
remove_cache_dirs "__pycache__" "🗂️" REMOVED_DIRS

# Remove .pytest_cache directories
REMOVED_PYTEST=0
remove_cache_dirs ".pytest_cache" "🧪" REMOVED_PYTEST

# Remove .mypy_cache directories
REMOVED_MYPY=0
remove_cache_dirs ".mypy_cache" "🔎" REMOVED_MYPY

# Remove .ruff_cache directories
REMOVED_RUFF=0
remove_cache_dirs ".ruff_cache" "🦊" REMOVED_RUFF

# Remove .hypothesis directories
REMOVED_HYPOTHESIS=0
remove_cache_dirs ".hypothesis" "🧬" REMOVED_HYPOTHESIS

# Remove .pyc files
REMOVED_PYC=0
remove_cache_files "*.pyc" "🐍" REMOVED_PYC

# Remove .pyo files
REMOVED_PYO=0
remove_cache_files "*.pyo" "🐍" REMOVED_PYO

# Remove .pyd files (Windows)
REMOVED_PYD=0
remove_cache_files "*.pyd" "🐍" REMOVED_PYD

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
