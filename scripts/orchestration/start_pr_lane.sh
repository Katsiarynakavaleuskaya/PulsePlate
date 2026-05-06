#!/usr/bin/env bash
# Repo-level PR lane starter for coordinator-first PulsePlate work.
# Creates an isolated worktree, runs analyze preflight, and emits a bootstrap packet.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

DEFAULT_PLUGINS=(
    "Browser Use"
    "Computer Use"
    "GitHub"
    "Hugging Face"
    "Life Science Research"
    "Plugin Eval"
    "CodeRabbit"
)

usage() {
    cat <<'EOF'
Usage:
  scripts/orchestration/start_pr_lane.sh --goal <text> --task-class <class> --branch <name> --worktree <path> [options]

Required:
  --goal <text>              Goal for task_bootstrap.py.
  --task-class <class>       Task class for task_bootstrap.py.
  --branch <name>            New branch to create for the PR lane.
  --worktree <path>          New isolated worktree path, repo-relative or under repo root.

Options:
  --path <path>              Repeatable; task scope path for preflight/bootstrap.
  --requested-agent <slug>   Repeatable; forwarded to task_bootstrap.py.
  --plugin <name>            Repeatable; operator/runtime plugin checklist item.
  --pr-phase <phase>         One of: pre_open, post_open_review, merge_ready, none. Default: pre_open.
  --base <ref>               Base ref for worktree creation. Default: origin/main.
  --dry-run                  Validate args and print the planned commands without mutating git state.
  -h, --help                 Show this help.

The plugin list is a checklist only. Missing host/runtime plugins do not fail repo startup.
EOF
}

die_usage() {
    echo "ERROR: $1" >&2
    echo "Run scripts/orchestration/start_pr_lane.sh --help for usage." >&2
    exit 2
}

die() {
    echo "ERROR: $1" >&2
    exit 1
}

normalize_scope_path() {
    local raw_path="$1"
    local repo_prefix="${REPO_ROOT}/"
    local rel_path

    case "${raw_path}" in
        "${repo_prefix}"*) rel_path="${raw_path#"${repo_prefix}"}" ;;
        /*) die_usage "--path must be repo-relative or under repo root: ${raw_path}" ;;
        *) rel_path="${raw_path}" ;;
    esac

    while [[ "${rel_path}" == ./* ]]; do
        rel_path="${rel_path#./}"
    done

    case "${rel_path}" in
        ""|"."|".."|../*|*/../*|*/..|/*)
            die_usage "--path must stay inside the repo without parent traversal: ${raw_path}"
            ;;
        artifacts/agent_runs|artifacts/agent_runs/*|artifacts/orchestration|artifacts/orchestration/*|artifacts/security_lab|artifacts/security_lab/*|worktrees|worktrees/*|.venv|.venv/*|.pytest_cache|.pytest_cache/*|.mypy_cache|.mypy_cache/*|.ruff_cache|.ruff_cache/*|node_modules|node_modules/*|dist|dist/*|build|build/*|.DS_Store|.coverage|coverage.*)
            die_usage "--path points at a local-only artifact/cache surface: ${raw_path}"
            ;;
    esac

    printf "%s" "${rel_path}"
}

normalize_worktree_path() {
    local raw_path="$1"
    local repo_prefix="${REPO_ROOT}/"
    local rel_path

    case "${raw_path}" in
        "${repo_prefix}"*) rel_path="${raw_path#"${repo_prefix}"}" ;;
        /*) die_usage "--worktree must be repo-relative or under repo root: ${raw_path}" ;;
        *) rel_path="${raw_path}" ;;
    esac

    while [[ "${rel_path}" == ./* ]]; do
        rel_path="${rel_path#./}"
    done

    case "${rel_path}" in
        ""|"."|".."|../*|*/../*|*/..|/*)
            die_usage "--worktree must stay inside the repo without parent traversal: ${raw_path}"
            ;;
        worktrees/*) ;;
        *)
            die_usage "--worktree must be under worktrees/: ${raw_path}"
            ;;
    esac

    printf "%s" "${rel_path}"
}

for arg in "$@"; do
    if [[ "${arg}" == "-h" || "${arg}" == "--help" ]]; then
        usage
        exit 0
    fi
done

if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found in PATH"
fi

PREFLIGHT_PY="${REPO_ROOT}/scripts/orchestration/check_preflight.py"
TASK_BOOTSTRAP_PY="${REPO_ROOT}/scripts/orchestration/task_bootstrap.py"
if [[ ! -f "${PREFLIGHT_PY}" ]]; then
    die "missing ${PREFLIGHT_PY}"
fi
if [[ ! -f "${TASK_BOOTSTRAP_PY}" ]]; then
    die "missing ${TASK_BOOTSTRAP_PY}"
fi

GOAL=""
TASK_CLASS=""
BRANCH=""
WORKTREE_REL=""
PR_PHASE="pre_open"
BASE_REF="origin/main"
DRY_RUN=0
PATH_ARGS=()
REQUESTED_ARGS=(--requested-agent "agent-coordinator")
PLUGIN_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --goal)
            if [[ $# -lt 2 ]]; then die_usage "--goal requires a value"; fi
            GOAL="$2"
            shift 2
            ;;
        --task-class)
            if [[ $# -lt 2 ]]; then die_usage "--task-class requires a value"; fi
            TASK_CLASS="$2"
            shift 2
            ;;
        --branch)
            if [[ $# -lt 2 ]]; then die_usage "--branch requires a value"; fi
            BRANCH="$2"
            shift 2
            ;;
        --worktree)
            if [[ $# -lt 2 ]]; then die_usage "--worktree requires a value"; fi
            WORKTREE_REL="$(normalize_worktree_path "$2")"
            shift 2
            ;;
        --path)
            if [[ $# -lt 2 ]]; then die_usage "--path requires a value"; fi
            PATH_ARGS+=(--path "$(normalize_scope_path "$2")")
            shift 2
            ;;
        --requested-agent)
            if [[ $# -lt 2 ]]; then die_usage "--requested-agent requires a value"; fi
            REQUESTED_ARGS+=(--requested-agent "$2")
            shift 2
            ;;
        --plugin)
            if [[ $# -lt 2 ]]; then die_usage "--plugin requires a value"; fi
            PLUGIN_ARGS+=("$2")
            shift 2
            ;;
        --pr-phase)
            if [[ $# -lt 2 ]]; then die_usage "--pr-phase requires a value"; fi
            PR_PHASE="$2"
            shift 2
            ;;
        --base)
            if [[ $# -lt 2 ]]; then die_usage "--base requires a value"; fi
            BASE_REF="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            die_usage "unknown arg: $1"
            ;;
    esac
done

case "${PR_PHASE}" in
    pre_open|post_open_review|merge_ready|none) ;;
    *) die_usage "--pr-phase must be one of: pre_open, post_open_review, merge_ready, none" ;;
esac

if [[ -z "${GOAL}" ]]; then die_usage "--goal is required"; fi
if [[ -z "${TASK_CLASS}" ]]; then die_usage "--task-class is required"; fi
if [[ -z "${BRANCH}" ]]; then die_usage "--branch is required"; fi
if [[ -z "${WORKTREE_REL}" ]]; then die_usage "--worktree is required"; fi

if [[ "${BRANCH}" == "main" || "${BRANCH}" == "master" || "${BRANCH}" == origin/* || "${BRANCH}" == refs/* ]]; then
    die_usage "--branch must be a new local branch name, got: ${BRANCH}"
fi
if ! git check-ref-format --branch "${BRANCH}" >/dev/null; then
    die_usage "--branch must be a valid branch name, got: ${BRANCH}"
fi

WORKTREE_ABS="${REPO_ROOT}/${WORKTREE_REL}"

if [[ "${DRY_RUN}" -eq 0 ]]; then
    if [[ -e "${WORKTREE_ABS}" ]]; then
        die "worktree path already exists: ${WORKTREE_REL}"
    fi
    if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
        die "branch already exists: ${BRANCH}"
    fi
    if [[ -n "$(git status --porcelain)" ]]; then
        die "current checkout must be clean before starting a new PR lane"
    fi
    git fetch --prune origin
    if ! git rev-parse --verify --quiet "${BASE_REF}^{commit}" >/dev/null; then
        die "base ref not found: ${BASE_REF}"
    fi
    if [[ "${BASE_REF}" == "origin/main" ]]; then
        ahead_behind="$(git rev-list --left-right --count HEAD...origin/main)"
        if [[ "${ahead_behind}" != "0	0" ]]; then
            die "current checkout must be synced with origin/main before lane start; got ${ahead_behind}"
        fi
    fi
fi

if [[ "${#PLUGIN_ARGS[@]}" -eq 0 ]]; then
    PLUGIN_ARGS=("${DEFAULT_PLUGINS[@]}")
fi

echo "PulsePlate PR lane start"
echo "  branch: ${BRANCH}"
echo "  worktree: ${WORKTREE_REL}"
echo "  base: ${BASE_REF}"
echo "  pr_phase: ${PR_PHASE}"
echo ""
echo "Plugin/runtime checklist (operator-confirmed, non-blocking):"
for plugin in "${PLUGIN_ARGS[@]}"; do
    echo "  - ${plugin}"
done
echo ""

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY RUN: no git worktree, preflight, or bootstrap commands were executed."
    printf "Would run: git worktree add -b %q %q %q\n" "${BRANCH}" "${WORKTREE_REL}" "${BASE_REF}"
    printf "Would run in worktree: python3 scripts/orchestration/check_preflight.py --mode analyze"
    for ((i = 0; i < ${#PATH_ARGS[@]}; i += 2)); do
        printf " %q %q" "${PATH_ARGS[i]}" "${PATH_ARGS[i + 1]}"
    done
    printf "\n"
    printf "Would run in worktree: python3 scripts/orchestration/task_bootstrap.py --goal %q --task-class %q --pr-phase %q" "${GOAL}" "${TASK_CLASS}" "${PR_PHASE}"
    for ((i = 0; i < ${#PATH_ARGS[@]}; i += 2)); do
        printf " %q %q" "${PATH_ARGS[i]}" "${PATH_ARGS[i + 1]}"
    done
    for ((i = 0; i < ${#REQUESTED_ARGS[@]}; i += 2)); do
        printf " %q %q" "${REQUESTED_ARGS[i]}" "${REQUESTED_ARGS[i + 1]}"
    done
    printf "\n"
    exit 0
fi

git worktree add -b "${BRANCH}" "${WORKTREE_REL}" "${BASE_REF}"

(
    cd "${WORKTREE_ABS}"
    preflight_cmd=(python3 scripts/orchestration/check_preflight.py --mode analyze)
    if ((${#PATH_ARGS[@]})); then
        preflight_cmd+=("${PATH_ARGS[@]}")
    fi
    "${preflight_cmd[@]}"

    bootstrap_cmd=(
        python3 scripts/orchestration/task_bootstrap.py
        --goal "${GOAL}"
        --task-class "${TASK_CLASS}"
        --pr-phase "${PR_PHASE}"
    )
    if ((${#PATH_ARGS[@]})); then
        bootstrap_cmd+=("${PATH_ARGS[@]}")
    fi
    if ((${#REQUESTED_ARGS[@]})); then
        bootstrap_cmd+=("${REQUESTED_ARGS[@]}")
    fi
    BOOTSTRAP_OUTPUT="$("${bootstrap_cmd[@]}")"
    echo "${BOOTSTRAP_OUTPUT}"
    echo ""
    BOOTSTRAP_OUTPUT="${BOOTSTRAP_OUTPUT}" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["BOOTSTRAP_OUTPUT"])
print("Coordinator packet summary:")
print(f"  output: {payload['output']}")
print(f"  primary_agent: {payload['primary_agent']}")
print(f"  reviewer: {payload['reviewer']}")
print("  recommended_skills:")
for skill in payload["recommended_skills"]:
    print(f"    - {skill}")
PY
)

echo ""
echo "Next steps:"
echo "  1. cd ${WORKTREE_REL}"
echo "  2. Follow the generated task packet before implementation."
echo "  3. Do not push or open the PR until local validation and PR body/mapping are ready."
