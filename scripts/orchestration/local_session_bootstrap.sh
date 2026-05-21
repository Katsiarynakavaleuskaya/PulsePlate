#!/usr/bin/env bash
# Opt-in local bridge for coordinator-first sessions (repo SoT only).
# RU: Не заменяет host launcher; вызывает preflight и напоминает про task_bootstrap.
# EN: Does not replace a machine launcher; runs preflight then prints bootstrap hints.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

usage() {
    cat <<'EOF'
Usage:
  scripts/orchestration/local_session_bootstrap.sh [options]

Options:
  --goal <text>              Goal to print in the task_bootstrap.py command.
  --task-class <class>       Task class to print in the task_bootstrap.py command.
  --path <path>              Repeatable; passed to preflight analyze and printed for bootstrap.
  --pr-phase <phase>         One of: pre_open, post_open_review, merge_ready, none.
  --requested-agent <slug>   Repeatable; printed for bootstrap.
  -h, --help                 Show this help.

No arguments keeps the legacy behavior: analyze preflight plus a placeholder
task_bootstrap.py recipe. Supplying any bootstrap option requires both --goal
and --task-class so the printed command is executable as-is.
EOF
}

die_usage() {
    echo "ERROR: $1" >&2
    echo "Run scripts/orchestration/local_session_bootstrap.sh --help for usage." >&2
    exit 2
}

die() {
    echo "ERROR: $1" >&2
    exit 1
}

resolve_repo_python() {
    if [[ -n "${VENV_PYTHON:-}" ]]; then
        case "${VENV_PYTHON}" in
            /*) ;;
            *) die "VENV_PYTHON must be an absolute executable path: ${VENV_PYTHON}" ;;
        esac
        if [[ -x "${VENV_PYTHON}" ]]; then
            printf "%s" "${VENV_PYTHON}"
            return
        fi
        die "VENV_PYTHON is set but is not executable: ${VENV_PYTHON}"
    fi

    local candidate
    for candidate in \
        "${REPO_ROOT}/.venv/bin/python" \
        "${REPO_ROOT}/../../.venv/bin/python"
    do
        if [[ -x "${candidate}" ]]; then
            printf "%s" "${candidate}"
            return
        fi
    done

    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return
    fi
    die "python3 not found in PATH and no repo .venv python is available"
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
        artifacts/agent_runs|artifacts/agent_runs/*|artifacts/orchestration|artifacts/orchestration/*|artifacts/security_lab|artifacts/security_lab/*|worktrees|worktrees/*|.venv|.venv/*|.pytest_cache|.pytest_cache/*|.mypy_cache|.mypy_cache/*|.ruff_cache|.ruff_cache/*|node_modules|node_modules/*|dist|dist/*|build|build/*)
            die_usage "--path points at a local-only artifact/cache surface: ${raw_path}"
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

REPO_PYTHON="$(resolve_repo_python)"

PREFLIGHT_PY="${REPO_ROOT}/scripts/orchestration/check_preflight.py"
if [[ ! -f "${PREFLIGHT_PY}" ]]; then
    echo "ERROR: missing ${PREFLIGHT_PY}" >&2
    exit 1
fi

TASK_BOOTSTRAP_PY="${REPO_ROOT}/scripts/orchestration/task_bootstrap.py"
if [[ ! -f "${TASK_BOOTSTRAP_PY}" ]]; then
    echo "ERROR: missing ${TASK_BOOTSTRAP_PY}" >&2
    exit 1
fi
RENDER_CODEX_PROMPT_PY="${REPO_ROOT}/scripts/orchestration/render_codex_start_prompt.py"
if [[ ! -f "${RENDER_CODEX_PROMPT_PY}" ]]; then
    echo "ERROR: missing ${RENDER_CODEX_PROMPT_PY}" >&2
    exit 1
fi

GOAL=""
TASK_CLASS=""
PR_PHASE="none"
BOOTSTRAP_OPTION_SEEN=0
REQUESTED_ARGS=()
PATH_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --goal)
            if [[ $# -lt 2 ]]; then die_usage "--goal requires a value"; fi
            GOAL="$2"
            BOOTSTRAP_OPTION_SEEN=1
            shift 2
            ;;
        --task-class)
            if [[ $# -lt 2 ]]; then die_usage "--task-class requires a value"; fi
            TASK_CLASS="$2"
            BOOTSTRAP_OPTION_SEEN=1
            shift 2
            ;;
        --path)
            if [[ $# -lt 2 ]]; then die_usage "--path requires a value"; fi
            PATH_ARGS+=(--path "$(normalize_scope_path "$2")")
            BOOTSTRAP_OPTION_SEEN=1
            shift 2
            ;;
        --pr-phase)
            if [[ $# -lt 2 ]]; then die_usage "--pr-phase requires a value"; fi
            PR_PHASE="$2"
            BOOTSTRAP_OPTION_SEEN=1
            shift 2
            ;;
        --requested-agent)
            if [[ $# -lt 2 ]]; then die_usage "--requested-agent requires a value"; fi
            REQUESTED_ARGS+=(--requested-agent "$2")
            BOOTSTRAP_OPTION_SEEN=1
            shift 2
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

if [[ "${BOOTSTRAP_OPTION_SEEN}" -eq 1 && ( -z "${GOAL}" || -z "${TASK_CLASS}" ) ]]; then
    die_usage "--goal and --task-class are required when bootstrap options are supplied"
fi

# analyze: allows a dirty tree; appropriate for cold-start / task analysis.
# For --mode execute|merge, run scripts/orchestration/check_preflight.py directly.
"${REPO_PYTHON}" "${PREFLIGHT_PY}" --mode analyze ${PATH_ARGS[@]+"${PATH_ARGS[@]}"}

echo ""
echo "OK: preflight passed (analyze). Coordinator routing and skill selection are"
echo "    deterministic only after you invoke task_bootstrap (and follow the packet)."
echo "Repo Python: ${REPO_PYTHON}"
echo "Python gate rule: use VENV_PYTHON or repo .venv python; avoid bare python3 -m pytest when .venv exists."
echo ""
if [[ "${BOOTSTRAP_OPTION_SEEN}" -eq 1 ]]; then
    echo "Generate the selected task packet:"
    printf "  %q %q \\\\\n" "${REPO_PYTHON}" "${TASK_BOOTSTRAP_PY}"
    printf "    --goal %q \\\\\n" "${GOAL}"
    printf "    --task-class %q \\\\\n" "${TASK_CLASS}"
    printf "    --pr-phase %q" "${PR_PHASE}"
    for ((i = 0; i < ${#PATH_ARGS[@]}; i += 2)); do
        printf " \\\\\n    %q %q" "${PATH_ARGS[i]}" "${PATH_ARGS[i + 1]}"
    done
    for ((i = 0; i < ${#REQUESTED_ARGS[@]}; i += 2)); do
        printf " \\\\\n    %q %q" "${REQUESTED_ARGS[i]}" "${REQUESTED_ARGS[i + 1]}"
    done
    printf "\n"
else
    echo "Generate a task packet (minimal example):"
    printf "  %q %q \\\\\n" "${REPO_PYTHON}" "${TASK_BOOTSTRAP_PY}"
    echo "    --goal \"<short goal>\" \\"
    echo "    --task-class \"<task_class>\""
    echo ""
    echo "Common options:"
    echo "  --path <path>              (repeatable; scope for scoped AGENTS / routing)"
    echo "  --pr-phase post_open_review|pre_open|merge_ready|none"
    echo "  --requested-agent <slug>   (repeatable)"
fi
echo ""
printf "Full CLI: %q scripts/orchestration/task_bootstrap.py --help\n" "${REPO_PYTHON}"
echo "Automation matrix: docs/orchestration/AUTOMATION_READINESS_MATRIX.md"
echo ""
prompt_cmd=(
    "${REPO_PYTHON}" "${RENDER_CODEX_PROMPT_PY}"
    recipe
    --preflight-ran
    --goal "${GOAL}"
    --task-class "${TASK_CLASS}"
    --pr-phase "${PR_PHASE}"
)
if ((${#PATH_ARGS[@]})); then
    prompt_cmd+=("${PATH_ARGS[@]}")
fi
if ((${#REQUESTED_ARGS[@]})); then
    prompt_cmd+=("${REQUESTED_ARGS[@]}")
fi
"${prompt_cmd[@]}"
