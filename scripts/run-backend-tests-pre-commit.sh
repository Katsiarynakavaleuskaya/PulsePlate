#!/usr/bin/env bash
# Backend tests hook for pre-commit/pre-push
# Runs pytest for changed Python files plus explicit cross-surface governance triggers
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

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ "${SKIP_TESTS:-0}" = "1" ]; then
    echo "⏩ SKIP_TESTS=1 set, skipping backend tests"
    exit 0
fi

# Debug mode: set PREPUSH_DEBUG=1 to see detailed information
DEBUG="${PREPUSH_DEBUG:-0}"
log_debug() {
    if [ "$DEBUG" = "1" ]; then
        echo "🔎 [DEBUG] $*" >&2
    fi
}

# Get changed files and derive Python/test-governance triggers
# For pre-commit: check staged files
# For pre-push: check files in commits that will be pushed
# For ad-hoc local validation (`make validate-changed`): prefer current branch diff
# against the nearest main/master merge-base instead of the pushed/unpushed delta.
CHANGED_FILES=""
PYTHON_CHANGES=""
BRANCH_DIFF_MODE="${BRANCH_DIFF_MODE:-0}"
BRANCH_DIFF_BASE_RESOLVED=0

record_changed_files() {
    CHANGED_FILES=$(printf '%s\n' "$1" | grep -v "^\.claude/" || true)
    PYTHON_CHANGES=$(printf '%s\n' "$CHANGED_FILES" | grep "\.py$" || true)
}

append_changed_files() {
    local incoming
    incoming=$(printf '%s\n' "$1" | grep -v "^\.claude/" || true)
    if [ -z "$incoming" ]; then
        return 0
    fi

    CHANGED_FILES=$(printf '%s\n%s\n' "$CHANGED_FILES" "$incoming" | sed '/^$/d' | sort -u)
    PYTHON_CHANGES=$(printf '%s\n' "$CHANGED_FILES" | grep "\.py$" || true)
}

resolve_branch_diff_from_base() {
    local mode="${1:-replace}"
    local base_branch
    local base_sha=""
    local branch_changed_files

    log_debug "Trying merge-base branch diff against main/master candidates..."
    for base_branch in origin/main origin/master main master; do
        base_sha=$(git merge-base HEAD "$base_branch" 2>/dev/null || echo "")
        if [ -n "$base_sha" ]; then
            BRANCH_DIFF_BASE_RESOLVED=1
            log_debug "Merge-base with $base_branch: $base_sha"
            branch_changed_files=$(git diff --no-renames --name-only --diff-filter=ACMDT "$base_sha" HEAD)
            if [ "$mode" = "append" ]; then
                append_changed_files "$branch_changed_files"
            else
                record_changed_files "$branch_changed_files"
            fi
            if [ -n "$PYTHON_CHANGES" ]; then
                log_debug "Python changes (via branch diff $base_branch): $PYTHON_CHANGES"
            fi
            return 0
        fi
    done

    return 1
}

if [ -n "${PRE_COMMIT:-}" ]; then
    # Pre-commit hook: check staged files. For `pre-commit run --all-files`,
    # pass_filenames=false means there may be no staged diff, so fall back to
    # the branch diff to keep manifest governance from going false-green.
    record_changed_files "$(git diff --cached --no-renames --name-only --diff-filter=ACMDT)"
    if [ -z "$CHANGED_FILES" ]; then
        resolve_branch_diff_from_base || true
    else
        resolve_branch_diff_from_base append || true
    fi
elif [ "$BRANCH_DIFF_MODE" = "1" ]; then
    # Local validation command: diff the current branch against main/master merge-base.
    resolve_branch_diff_from_base || true
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
            record_changed_files "$(git diff --no-renames --name-only --diff-filter=ACMDT "$REMOTE_SHA" HEAD)"
            log_debug "Python changes (via upstream): ${PYTHON_CHANGES:-<none>}"
        fi
    fi

    # Fallback: if we couldn't determine remote branch, try common patterns.
    # Preserve package-manifest-only upstream deltas so cross-surface
    # governance tests are not lost just because no Python files changed.
    if [ -z "$CHANGED_FILES" ]; then
        # Try origin/current_branch
        REMOTE_BRANCH="origin/${CURRENT_BRANCH}"
        REMOTE_SHA=$(git rev-parse --verify "$REMOTE_BRANCH" 2>/dev/null || echo "")
        log_debug "Fallback remote branch: $REMOTE_BRANCH (SHA: ${REMOTE_SHA:-<not found>})"
        if [ -n "$REMOTE_SHA" ]; then
            record_changed_files "$(git diff --no-renames --name-only --diff-filter=ACMDT "$REMOTE_SHA" HEAD)"
            log_debug "Python changes (via fallback remote): ${PYTHON_CHANGES:-<none>}"
        fi
    fi

    # Last resort: compare branch diff against main/master using merge-base
    if [ -z "$CHANGED_FILES" ]; then
        resolve_branch_diff_from_base || true
    fi
fi

declare -a EXTRA_TEST_FILES=()
declare -a PYTHON_HELPER_SOURCE_FILES=(
    "tests/security/_api_authz_contracts.py"
)
declare -a PYTHON_HELPER_TEST_TARGETS=(
    "tests/security/test_api_authz_contract_static.py"
)

add_extra_tests_for_changed_files() {
    while IFS= read -r file; do
        case "$file" in
            frontend/package.json | frontend/package-lock.json)
                EXTRA_TEST_FILES+=("tests/test_ci_workflow_pr_size_governance_contract.py")
                EXTRA_TEST_FILES+=("tests/test_frontend_dependency_guards.py")
                EXTRA_TEST_FILES+=("tests/test_python_supply_chain_controls.py")
                ;;
        esac
    done <<< "$CHANGED_FILES"
}

add_extra_tests_for_changed_files

add_helper_tests_for_python_change() {
    local file="$1"
    local index
    local target
    for index in "${!PYTHON_HELPER_SOURCE_FILES[@]}"; do
        if [ "${PYTHON_HELPER_SOURCE_FILES[$index]}" != "$file" ]; then
            continue
        fi
        target="${PYTHON_HELPER_TEST_TARGETS[$index]}"
        if [ ! -f "$target" ]; then
            echo "Missing mapped pytest target for helper file '$file': $target" >&2
            exit 1
        fi
        FOUND_FOR_FILE+=("$target")
        return 0
    done
    return 1
}

if [ -z "$PYTHON_CHANGES" ] && [ ${#EXTRA_TEST_FILES[@]} -eq 0 ]; then
    if [ "$BRANCH_DIFF_MODE" = "1" ] && [ "$BRANCH_DIFF_BASE_RESOLVED" = "1" ]; then
        echo "ℹ️  No Python or cross-surface governance files changed on the current branch"
        exit 0
    fi

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

        COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo "0")
        if ! [[ "$COMMIT_COUNT" =~ ^[0-9]+$ ]]; then
            COMMIT_COUNT="0"
        fi
        MAX_DEPTH=$((COMMIT_COUNT > 0 ? COMMIT_COUNT - 1 : 0))
        FALLBACK_DEPTH="$RECENT_COMMITS_FALLBACK"
        if [ "$FALLBACK_DEPTH" -gt "$MAX_DEPTH" ]; then
            FALLBACK_DEPTH="$MAX_DEPTH"
        fi
        if [ "$FALLBACK_DEPTH" -le 0 ]; then
            echo "ℹ️  Repository has insufficient history for fallback diff, skipping backend tests"
            exit 0
        fi

        echo "⚠️  Could not determine changed Python files via upstream/base, checking last ${FALLBACK_DEPTH} commits as safety measure..."
        record_changed_files "$(git diff --no-renames --name-only --diff-filter=ACMDT "HEAD~${FALLBACK_DEPTH}" HEAD 2>/dev/null || true)"
        EXTRA_TEST_FILES=()
        add_extra_tests_for_changed_files
        log_debug "Python changes (via recent commits fallback, n=${FALLBACK_DEPTH}): ${PYTHON_CHANGES:-<none>}"
        if [ -z "$PYTHON_CHANGES" ] && [ ${#EXTRA_TEST_FILES[@]} -eq 0 ]; then
            echo "ℹ️  No Python or cross-surface governance files changed in last ${FALLBACK_DEPTH} commits, skipping backend tests"
            exit 0
        fi
        echo "ℹ️  Found Python or cross-surface governance changes in last ${FALLBACK_DEPTH} commits, running tests for safety"
    else
        # Pre-commit: no staged Python files, skip
        echo "ℹ️  No Python or cross-surface governance files changed"
        exit 0
    fi
fi

# Extract test files that correspond to changed Python files
declare -a TEST_FILES=()

if [ -n "$PYTHON_CHANGES" ]; then
    while IFS= read -r file; do
        # Per-file test discovery
        declare -a FOUND_FOR_FILE=()

        # Helper modules under tests/ need executable test targets, not direct
        # pytest collection of the helpers themselves.
        if add_helper_tests_for_python_change "$file"; then
            :
        # If the file is in tests/ directory, add it directly (but exclude conftest.py)
        elif [[ $file == tests/* ]] && [[ $file == *.py ]] && [[ ! $(basename "$file") == conftest.py ]]; then
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
        if [ ${#FOUND_FOR_FILE[@]} -gt 0 ]; then
            TEST_FILES+=("${FOUND_FOR_FILE[@]}")
        fi
    done <<< "$PYTHON_CHANGES"
fi

if [ ${#EXTRA_TEST_FILES[@]} -gt 0 ]; then
    TEST_FILES+=("${EXTRA_TEST_FILES[@]}")
fi

if [ ${#TEST_FILES[@]} -gt 0 ]; then
    # Resolve Python through the repo/worktree-aware hook resolver only after
    # proving this hook has tests to run. This keeps always_run no-op commits
    # independent from local virtualenv availability.
    # shellcheck source=scripts/hooks/repo_python.sh
    source "$ROOT_DIR/scripts/hooks/repo_python.sh"
    REPO_PYTHON_BIN="$(resolve_repo_python "$ROOT_DIR")"
    export VENV_PYTHON="$REPO_PYTHON_BIN"
    export PATH="$(dirname "$REPO_PYTHON_BIN"):$PATH"

    if ! "$REPO_PYTHON_BIN" -m pytest --version > /dev/null 2>&1; then
        echo "❌ pytest not available through repo Python: $REPO_PYTHON_BIN" >&2
        echo "   Run make venv or set absolute VENV_PYTHON to the repo environment." >&2
        exit 1
    fi

    declare -a PYTEST_COMMAND=("$REPO_PYTHON_BIN" -m pytest)
    log_debug "Using repo Python pytest via: ${PYTEST_COMMAND[*]}"

    # Deduplicate test files
    declare -a DEDUPED_TEST_FILES=()
    while IFS= read -r test_file; do
        [ -n "$test_file" ] && DEDUPED_TEST_FILES+=("$test_file")
    done < <(printf '%s\n' "${TEST_FILES[@]}" | sort -u)
    TEST_FILES=("${DEDUPED_TEST_FILES[@]}")
    log_debug "Test files to run: ${TEST_FILES[*]}"

    # Pre-commit: fast feedback is preferred; pre-push: report all failures.
    declare -a PYTEST_ARGS=("-q" "--tb=short")
    if [ -n "${PRE_COMMIT:-}" ]; then
        PYTEST_ARGS+=("-x")
        log_debug "pytest fast-fail enabled (-x) for pre-commit"
    fi

    echo "Running tests: ${TEST_FILES[*]}"
    # Use explicit exit code handling to ensure proper error propagation
    if "${PYTEST_COMMAND[@]}" "${PYTEST_ARGS[@]}" "${TEST_FILES[@]}"; then
        echo "✅ Backend tests passed"
    else
        echo "❌ Backend tests failed"
        exit 1
    fi
else
    log_debug "No test files found for Python changes: $PYTHON_CHANGES"
    echo "ℹ️  No corresponding test files found for changed Python files"
fi
