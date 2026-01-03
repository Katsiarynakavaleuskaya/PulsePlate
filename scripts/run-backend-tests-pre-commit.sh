#!/usr/bin/env bash
# Backend tests hook for pre-commit/pre-push
# Runs pytest for changed Python files
#
# Pre-push backend tests (smart diff runner):
# The pre-push hook runs backend pytest only when Python files changed.
#
# Change detection order:
# 1) If upstream exists: diff `upstream..HEAD`
# 2) Else: diff from merge-base against (origin/main|origin/master|main|master)
# 3) If base cannot be resolved: fallback to last N commits (diagnostic mode)
#
# Debug:
# - Set `PREPUSH_DEBUG=1` to print resolved upstream/base and file list.

set -euo pipefail

# Debug mode: set PREPUSH_DEBUG=1 to see detailed information
DEBUG="${PREPUSH_DEBUG:-0}"
log_debug() {
    if [ "$DEBUG" = "1" ]; then
        echo "🔎 [DEBUG] $*" >&2
    fi
}

if [ "${SKIP_TESTS:-0}" = "1" ]; then
    echo "⏩ SKIP_TESTS=1 set, skipping backend tests"
    exit 0
fi

if ! command -v pytest > /dev/null 2>&1; then
    echo "⚠️  Warning: pytest not found, skipping backend tests"
    exit 0
fi

# Get changed Python files
# For pre-commit: check staged files
# For pre-push: check files in commits that will be pushed
PYTHON_CHANGES=""
if [ -n "${PRE_COMMIT:-}" ]; then
    # Pre-commit hook: check staged files
    PYTHON_CHANGES=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$" | grep -v "^\.claude/" || true)
else
    # Pre-push hook: check files in commits that will be pushed
    # In pre-push, we need to compare what's being pushed with what's already on remote
    # Pre-commit framework doesn't pass arguments, so we determine remote branch from git config
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

    # Try to get remote tracking branch from git config
    REMOTE_BRANCH=$(git rev-parse --abbrev-ref --symbolic-full-name @{upstream} 2>/dev/null || echo "")
    log_debug "Current branch: $CURRENT_BRANCH"
    log_debug "Upstream branch: ${REMOTE_BRANCH:-<not set>}"

    if [ -n "$REMOTE_BRANCH" ]; then
        # Get the remote branch SHA (what's currently on remote)
        REMOTE_SHA=$(git rev-parse --verify "$REMOTE_BRANCH" 2>/dev/null || echo "")
        log_debug "Upstream SHA: ${REMOTE_SHA:-<not found>}"
        if [ -n "$REMOTE_SHA" ]; then
            # Compare local HEAD with remote branch (files that will be pushed)
            PYTHON_CHANGES=$(git diff --name-only --diff-filter=ACM "$REMOTE_SHA" HEAD | grep "\.py$" | grep -v "^\.claude/" || true)
            log_debug "Python changes (via upstream): ${PYTHON_CHANGES:-<none>}"
        fi
    fi

    # Fallback: if we couldn't determine remote branch, try common patterns
    if [ -z "$PYTHON_CHANGES" ]; then
        # Try origin/current_branch
        REMOTE_BRANCH="origin/${CURRENT_BRANCH}"
        REMOTE_SHA=$(git rev-parse --verify "$REMOTE_BRANCH" 2>/dev/null || echo "")
        log_debug "Fallback remote branch: $REMOTE_BRANCH (SHA: ${REMOTE_SHA:-<not found>})"
        if [ -n "$REMOTE_SHA" ]; then
            PYTHON_CHANGES=$(git diff --name-only --diff-filter=ACM "$REMOTE_SHA" HEAD | grep "\.py$" | grep -v "^\.claude/" || true)
            log_debug "Python changes (via fallback remote): ${PYTHON_CHANGES:-<none>}"
        fi
    fi

    # Last resort: compare with main/master using merge-base (better than fixed commit count)
    if [ -z "$PYTHON_CHANGES" ]; then
        log_debug "Trying merge-base with main/master branches..."
        # Try origin/main first, then origin/master, then local main/master
        for base_branch in origin/main origin/master main master; do
            BASE=$(git merge-base HEAD "$base_branch" 2>/dev/null || echo "")
            if [ -n "$BASE" ]; then
                log_debug "Merge-base with $base_branch: $BASE"
                PYTHON_CHANGES=$(git diff --name-only --diff-filter=ACM "$BASE" HEAD | grep "\.py$" | grep -v "^\.claude/" || true)
                if [ -n "$PYTHON_CHANGES" ]; then
                    log_debug "Python changes (via merge-base $base_branch): $PYTHON_CHANGES"
                    break
                fi
            fi
        done
    fi
fi

if [ -z "$PYTHON_CHANGES" ]; then
    # In pre-push, if no Python changes detected, it might mean:
    # 1. No Python files were changed (legitimate skip)
    # 2. We couldn't determine base for comparison (should still check recent commits as safety)
    if [ -z "${PRE_COMMIT:-}" ]; then
        # Pre-push: if we can't determine changes, check recent commits as safety measure
        # This handles edge cases: new branch, detached HEAD, force-push scenarios
        RECENT_COMMITS_FALLBACK="${RECENT_COMMITS_FALLBACK:-10}"
        if ! [[ "$RECENT_COMMITS_FALLBACK" =~ ^[1-9][0-9]*$ ]]; then
            echo "❌ RECENT_COMMITS_FALLBACK must be a positive integer, got: '$RECENT_COMMITS_FALLBACK'" >&2
            exit 1
        fi

        echo "⚠️  Could not determine changed Python files via upstream/base, checking last ${RECENT_COMMITS_FALLBACK} commits as safety measure..."
        PYTHON_CHANGES=$(
            git diff --name-only --diff-filter=ACM "HEAD~${RECENT_COMMITS_FALLBACK}" HEAD 2>/dev/null \
                | grep "\.py$" \
                | grep -v "^\.claude/" \
                || true
        )
        log_debug "Python changes (via recent commits fallback, n=${RECENT_COMMITS_FALLBACK}): ${PYTHON_CHANGES:-<none>}"
        if [ -z "$PYTHON_CHANGES" ]; then
            echo "ℹ️  No Python files changed in last ${RECENT_COMMITS_FALLBACK} commits, skipping backend tests"
            exit 0
        fi
        echo "ℹ️  Found Python changes in last ${RECENT_COMMITS_FALLBACK} commits, running tests for safety"
    else
        # Pre-commit: no staged Python files, skip
        echo "ℹ️  No Python files changed"
        exit 0
    fi
fi

# Extract test files that correspond to changed Python files
declare -a TEST_FILES=()

while IFS= read -r file; do
    # Per-file test discovery
    declare -a FOUND_FOR_FILE=()

    # If the file is in tests/ directory, add it directly (but exclude conftest.py)
    if [[ $file == tests/* ]] && [[ $file == *.py ]] && [[ ! $(basename "$file") == conftest.py ]]; then
        [ -f "$file" ] && FOUND_FOR_FILE+=("$file")
    # Otherwise, check if corresponding test file exists
    elif [[ $file == *.py ]] && [[ ! $file == test_*.py ]] && [[ ! $file == tests/* ]]; then
        basename=$(basename "$file" .py)
        dirname=$(dirname "$file")
        dirname=${dirname#./}

        # Common test file patterns
        test_patterns=(
            "tests/test_${basename}.py"
            "tests/${dirname}/test_${basename}.py"
            "${dirname}/test_${basename}.py"
        )

        for pattern in "${test_patterns[@]}"; do
            [ -f "$pattern" ] && FOUND_FOR_FILE+=("$pattern") && break
        done

        # Fallback: search recursively if no test files found
        if [ ${#FOUND_FOR_FILE[@]} -eq 0 ]; then
            test_file=$(find tests -maxdepth 4 -type f -name "test_${basename}.py" -print -quit 2>/dev/null)
            [ -n "$test_file" ] && [ -f "$test_file" ] && FOUND_FOR_FILE+=("$test_file")
        fi
    fi

    # Append per-file results to global TEST_FILES array
    TEST_FILES+=("${FOUND_FOR_FILE[@]}")
done <<< "$PYTHON_CHANGES"

if [ ${#TEST_FILES[@]} -gt 0 ]; then
    # Deduplicate test files
    mapfile -t TEST_FILES < <(printf '%s\n' "${TEST_FILES[@]}" | sort -u)
    log_debug "Test files to run: ${TEST_FILES[*]}"

    # Pre-commit: fast feedback is preferred; pre-push: report all failures.
    declare -a PYTEST_ARGS=("-q" "--tb=short")
    if [ -n "${PRE_COMMIT:-}" ]; then
        PYTEST_ARGS+=("-x")
        log_debug "pytest fast-fail enabled (-x) for pre-commit"
    fi

    echo "Running tests: ${TEST_FILES[*]}"
    # Use explicit exit code handling to ensure proper error propagation
    if pytest "${PYTEST_ARGS[@]}" "${TEST_FILES[@]}"; then
        echo "✅ Backend tests passed"
    else
        echo "❌ Backend tests failed"
        exit 1
    fi
else
    log_debug "No test files found for Python changes: $PYTHON_CHANGES"
    echo "ℹ️  No corresponding test files found for changed Python files"
fi
