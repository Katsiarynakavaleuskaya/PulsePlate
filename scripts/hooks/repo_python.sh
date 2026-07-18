#!/usr/bin/env bash
# Resolve the Python interpreter that owns PulsePlate's locked developer deps.

resolve_repo_python() {
    local repo_root="${1:?repo root required}"
    local candidate=""
    local checkout_binding_valid="false"
    local checkout_git_backlink=""
    local checkout_git_backlink_parent=""
    local checkout_git_dir=""
    local checkout_top_level=""
    local checkout_worktree_name=""
    local checkout_worktrees_prefix=""
    local git_common_dir=""
    local primary_common_dir=""
    local primary_root=""
    local primary_top_level=""
    local raw_python_override="${VENV_PYTHON:-${DEV_PYTHON:-}}"
    local env_binary=""
    local git_binary=""
    local candidates=()

    if ! repo_root="$(builtin cd -- "${repo_root}" 2>/dev/null && builtin pwd -P)"; then
        echo "ERROR: repo root is not a readable directory: ${1:?repo root required}" >&2
        return 1
    fi

    if [[ -n "${raw_python_override}" ]]; then
        case "${raw_python_override}" in
            /*)
                if [[ -f "${raw_python_override}" && -x "${raw_python_override}" ]]; then
                    printf '%s\n' "${raw_python_override}"
                    return 0
                fi
                echo "ERROR: VENV_PYTHON/DEV_PYTHON is set but is not a regular executable file: ${raw_python_override}" >&2
                return 1
                ;;
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

    if env_binary="$(command -v env 2>/dev/null)" &&
        git_binary="$(command -v git 2>/dev/null)" &&
        [[ "${env_binary}" == /* && -f "${env_binary}" && -x "${env_binary}" &&
            "${git_binary}" == /* && -f "${git_binary}" && -x "${git_binary}" ]] &&
        git_common_dir="$(
            "${env_binary}" -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_PREFIX \
                -u GIT_COMMON_DIR -u GIT_IMPLICIT_WORK_TREE \
                "${git_binary}" -C "${repo_root}" rev-parse \
                --path-format=absolute --git-common-dir 2>/dev/null
        )" &&
        checkout_top_level="$(
            "${env_binary}" -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_PREFIX \
                -u GIT_COMMON_DIR -u GIT_IMPLICIT_WORK_TREE \
                "${git_binary}" -C "${repo_root}" rev-parse \
                --path-format=absolute --show-toplevel 2>/dev/null
        )" &&
        checkout_git_dir="$(
            "${env_binary}" -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_PREFIX \
                -u GIT_COMMON_DIR -u GIT_IMPLICIT_WORK_TREE \
                "${git_binary}" -C "${repo_root}" rev-parse \
                --path-format=absolute --git-dir 2>/dev/null
        )" &&
        git_common_dir="$(
            builtin cd -- "${git_common_dir}" 2>/dev/null && builtin pwd -P
        )" &&
        checkout_top_level="$(
            builtin cd -- "${checkout_top_level}" 2>/dev/null && builtin pwd -P
        )" &&
        checkout_git_dir="$(
            builtin cd -- "${checkout_git_dir}" 2>/dev/null && builtin pwd -P
        )" &&
        [[ "${git_common_dir##*/}" == ".git" ]] &&
        primary_root="$(
            builtin cd -- "${git_common_dir}/.." 2>/dev/null && builtin pwd -P
        )" &&
        [[ "${checkout_top_level}" == "${repo_root}" ]]; then
        if [[ "${repo_root}" == "${primary_root}" ]]; then
            checkout_binding_valid="true"
        else
            checkout_worktrees_prefix="${git_common_dir}/worktrees/"
            if [[ "${checkout_git_dir}" == "${checkout_worktrees_prefix}"* &&
                -f "${repo_root}/.git" && ! -L "${repo_root}/.git" &&
                -f "${checkout_git_dir}/gitdir" && ! -L "${checkout_git_dir}/gitdir" ]]; then
                checkout_worktree_name="${checkout_git_dir:${#checkout_worktrees_prefix}}"
                if [[ -n "${checkout_worktree_name}" &&
                    "${checkout_worktree_name}" != */* ]] &&
                    IFS= read -r checkout_git_backlink < "${checkout_git_dir}/gitdir" &&
                    [[ "${checkout_git_backlink}" == /* &&
                        "${checkout_git_backlink##*/}" == ".git" &&
                        -f "${checkout_git_backlink}" &&
                        ! -L "${checkout_git_backlink}" ]] &&
                    checkout_git_backlink_parent="$(
                        builtin cd -- "${checkout_git_backlink%/*}" 2>/dev/null &&
                            builtin pwd -P
                    )" &&
                    [[ "${checkout_git_backlink_parent}" == "${repo_root}" ]]; then
                    checkout_binding_valid="true"
                fi
            fi
        fi

        if [[ "${checkout_binding_valid}" == "true" ]] &&
            primary_top_level="$(
                "${env_binary}" -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_PREFIX \
                    -u GIT_COMMON_DIR -u GIT_IMPLICIT_WORK_TREE \
                    "${git_binary}" -C "${primary_root}" rev-parse \
                    --path-format=absolute --show-toplevel 2>/dev/null
            )" &&
            primary_common_dir="$(
                "${env_binary}" -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE -u GIT_PREFIX \
                    -u GIT_COMMON_DIR -u GIT_IMPLICIT_WORK_TREE \
                    "${git_binary}" -C "${primary_root}" rev-parse \
                    --path-format=absolute --git-common-dir 2>/dev/null
            )" &&
            primary_top_level="$(
                builtin cd -- "${primary_top_level}" 2>/dev/null && builtin pwd -P
            )" &&
            primary_common_dir="$(
                builtin cd -- "${primary_common_dir}" 2>/dev/null && builtin pwd -P
            )" &&
            [[ "${primary_top_level}" == "${primary_root}" ]] &&
            [[ "${primary_common_dir}" == "${git_common_dir}" ]]; then
            candidates+=(
                "${primary_root}/.venv/bin/python"
                "${primary_root}/.venv/Scripts/python.exe"
            )
        fi
    fi

    for candidate in "${candidates[@]}"; do
        if [[ -f "${candidate}" && -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done

    if [[ "${CI:-}" == "true" ]]; then
        if candidate="$(command -v python3 2>/dev/null)"; then
            case "${candidate}" in
                /*)
                    if [[ -f "${candidate}" && -x "${candidate}" ]]; then
                        printf '%s\n' "${candidate}"
                        return 0
                    fi
                    ;;
            esac
        fi
        if candidate="$(command -v python 2>/dev/null)"; then
            case "${candidate}" in
                /*)
                    if [[ -f "${candidate}" && -x "${candidate}" ]]; then
                        printf '%s\n' "${candidate}"
                        return 0
                    fi
                    ;;
            esac
        fi
    fi

    echo "ERROR: no repo/shared .venv Python found for local hook execution" >&2
    return 1
}
