#!/usr/bin/env bash
# Resolve the Python interpreter that owns PulsePlate's locked developer deps.

resolve_repo_python() {
    local repo_root="${1:?repo root required}"
    local candidate=""
    local git_common_dir=""
    local parent_dir=""
    local shared_root=""
    local raw_python_override="${VENV_PYTHON:-${DEV_PYTHON:-}}"
    local git_binary=""
    local candidates=()

    if ! repo_root="$(cd "${repo_root}" 2>/dev/null && pwd -P)"; then
        echo "ERROR: repo root is not a readable directory: ${1:?repo root required}" >&2
        return 1
    fi

    if [[ -n "${raw_python_override}" ]]; then
        case "${raw_python_override}" in
            /*) candidates+=("${raw_python_override}") ;;
            *)
                echo "ERROR: VENV_PYTHON/DEV_PYTHON must be an absolute executable path for hooks: ${raw_python_override}" >&2
                return 1
                ;;
        esac
    fi

    candidates+=(
        "${repo_root}/.venv/bin/python"
        "${repo_root}/.venv/Scripts/python.exe"
    )

    parent_dir="$(dirname "${repo_root}")"
    git_binary="$(command -v git || true)"
    if [[ "$(basename "${parent_dir}")" == "worktrees" ]] &&
        [[ -n "${git_binary}" ]] &&
        git_common_dir="$(
            env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_PREFIX -u GIT_COMMON_DIR \
                "${git_binary}" -C "${repo_root}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null
        )"; then
        shared_root="$(cd "$(dirname "${parent_dir}")" 2>/dev/null && pwd -P)"
        git_common_dir="$(cd "${git_common_dir}" 2>/dev/null && pwd -P)"
        case "${git_common_dir}" in
            "${shared_root}/.git" | "${shared_root}/.git/"*)
                candidates+=(
                    "${shared_root}/.venv/bin/python"
                    "${shared_root}/.venv/Scripts/python.exe"
                )
                ;;
        esac
    fi

    for candidate in "${candidates[@]}"; do
        if [[ -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done

    if [[ "${CI:-}" == "true" ]] && command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi
    if [[ "${CI:-}" == "true" ]] && command -v python >/dev/null 2>&1; then
        command -v python
        return 0
    fi

    echo "ERROR: no repo/shared .venv Python found for local hook execution" >&2
    return 1
}
