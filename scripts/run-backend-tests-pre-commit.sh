#!/usr/bin/env bash
# Backend tests hook for pre-commit
# Runs pytest for changed Python files

set -euo pipefail

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
# For pre-push: check files between HEAD and remote branch
if [ -n "${PRE_COMMIT:-}" ]; then
    # Pre-commit hook: check staged files
    PYTHON_CHANGES=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$" | grep -v "^\.claude/" || true)
else
    # Pre-push hook: check files between local and remote
    REMOTE_BRANCH="${1:-origin/$(git rev-parse --abbrev-ref HEAD)}"
    PYTHON_CHANGES=$(git diff --name-only --diff-filter=ACM HEAD "$REMOTE_BRANCH" 2>/dev/null | grep "\.py$" | grep -v "^\.claude/" || true)
    # Fallback: if remote branch doesn't exist, check all commits in current branch
    if [ -z "$PYTHON_CHANGES" ] && ! git rev-parse --verify "$REMOTE_BRANCH" >/dev/null 2>&1; then
        BASE=$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD origin/master 2>/dev/null || echo "")
        if [ -n "$BASE" ]; then
            PYTHON_CHANGES=$(git diff --name-only --diff-filter=ACM "$BASE" HEAD | grep "\.py$" | grep -v "^\.claude/" || true)
        fi
    fi
fi

if [ -z "$PYTHON_CHANGES" ]; then
    echo "ℹ️  No Python files changed"
    exit 0
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
            while IFS= read -r test_file; do
                [ -f "$test_file" ] && FOUND_FOR_FILE+=("$test_file")
            done < <(find tests -type f -name "test_${basename}.py" 2>/dev/null)
        fi
    fi

    # Append per-file results to global TEST_FILES array
    TEST_FILES+=("${FOUND_FOR_FILE[@]}")
done <<< "$PYTHON_CHANGES"

if [ ${#TEST_FILES[@]} -gt 0 ]; then
    # Deduplicate test files
    mapfile -t TEST_FILES < <(printf '%s\n' "${TEST_FILES[@]}" | sort -u)
    echo "Running tests: ${TEST_FILES[*]}"
    pytest -q --tb=short -x "${TEST_FILES[@]}" || exit 1
    echo "✅ Backend tests passed"
else
    echo "ℹ️  No corresponding test files found for changed Python files"
fi
