#!/usr/bin/env bash
# Repo-level PR lane starter for coordinator-first PulsePlate work.
# Creates an isolated worktree, runs analyze preflight, and emits a bootstrap packet.
# Experiment Runner participation is evidence after bootstrap, never lane-start authority.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

DEFAULT_PLUGINS=(
    "GitHub"
    "CodeRabbit"
    "Codex Security"
    "Browser"
    "Chrome"
    "Computer Use"
    "Hugging Face"
    "Life Science Research"
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
  --invariant-change-class <class>
                             Repeatable; parser, validator, guard, or authority.
  --requested-agent <slug>   Repeatable; forwarded to task_bootstrap.py.
  --evidence-sidecar-rail <rail>
                             Repeatable; teleology, euler, or experiment_runner.
                             experiment_runner is included by default.
  --plugin <name>            Repeatable; operator/runtime plugin checklist item.
  --pr-phase <phase>         One of: pre_open, post_open_review, merge_ready, none. Default: pre_open.
  --base <ref>               Base ref for worktree creation. Default: origin/main.
  --allow-dirty-launcher     Permit a dirty current checkout only for isolated origin/main lanes.
  --dry-run                  Validate args and print the planned commands without mutating git state.
  -h, --help                 Show this help.

The plugin list is a checklist only. Missing host/runtime plugins do not fail repo startup.
Open the PR non-draft by default so bot review and current-head checks run.
Repo lane authority remains check_preflight.py -> task_bootstrap.py -> agent-coordinator.
Experiment Runner joins after bootstrap as oracle-only evidence.
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
    local git_common_dir
    local parent_dir
    local root_dir
    local candidates=("${REPO_ROOT}/.venv/bin/python")
    parent_dir="$(dirname "${REPO_ROOT}")"
    if [[ "$(basename "${parent_dir}")" == "worktrees" ]] && git_common_dir="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; then
        root_dir="$(dirname "${parent_dir}")"
        if [[ "${git_common_dir}" == "${root_dir}/.git"* ]]; then
            candidates+=("${root_dir}/.venv/bin/python")
        fi
    fi

    for candidate in "${candidates[@]}"; do
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

REPO_PYTHON="$(resolve_repo_python)"

PREFLIGHT_PY="${REPO_ROOT}/scripts/orchestration/check_preflight.py"
TASK_BOOTSTRAP_PY="${REPO_ROOT}/scripts/orchestration/task_bootstrap.py"
RENDER_CODEX_PROMPT_PY="${REPO_ROOT}/scripts/orchestration/render_codex_start_prompt.py"
if [[ ! -f "${PREFLIGHT_PY}" ]]; then
    die "missing ${PREFLIGHT_PY}"
fi
if [[ ! -f "${TASK_BOOTSTRAP_PY}" ]]; then
    die "missing ${TASK_BOOTSTRAP_PY}"
fi
if [[ ! -f "${RENDER_CODEX_PROMPT_PY}" ]]; then
    die "missing ${RENDER_CODEX_PROMPT_PY}"
fi

GOAL=""
TASK_CLASS=""
BRANCH=""
WORKTREE_REL=""
PR_PHASE="pre_open"
BASE_REF="origin/main"
DRY_RUN=0
ALLOW_DIRTY_LAUNCHER=0
PATH_ARGS=()
INVARIANT_CLASS_ARGS=()
REQUESTED_ARGS=(--requested-agent "agent-coordinator")
PLUGIN_ARGS=()
EVIDENCE_SIDECAR_RAILS=("experiment_runner")

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
        --invariant-change-class)
            if [[ $# -lt 2 ]]; then die_usage "--invariant-change-class requires a value"; fi
            case "$2" in
                parser|validator|guard|authority) ;;
                *) die_usage "--invariant-change-class must be one of: parser, validator, guard, authority" ;;
            esac
            INVARIANT_CLASS_ARGS+=(--invariant-change-class "$2")
            shift 2
            ;;
        --requested-agent)
            if [[ $# -lt 2 ]]; then die_usage "--requested-agent requires a value"; fi
            REQUESTED_ARGS+=(--requested-agent "$2")
            shift 2
            ;;
        --evidence-sidecar-rail)
            if [[ $# -lt 2 ]]; then die_usage "--evidence-sidecar-rail requires a value"; fi
            case "$2" in
                teleology|euler|experiment_runner) ;;
                *) die_usage "--evidence-sidecar-rail must be one of: teleology, euler, experiment_runner" ;;
            esac
            sidecar_rail_seen=0
            for existing_rail in "${EVIDENCE_SIDECAR_RAILS[@]}"; do
                if [[ "${existing_rail}" == "$2" ]]; then
                    sidecar_rail_seen=1
                    break
                fi
            done
            if [[ "${sidecar_rail_seen}" -eq 0 ]]; then
                EVIDENCE_SIDECAR_RAILS+=("$2")
            fi
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
        --allow-dirty-launcher)
            ALLOW_DIRTY_LAUNCHER=1
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

if [[ "${ALLOW_DIRTY_LAUNCHER}" -eq 1 && "${BASE_REF}" != "origin/main" ]]; then
    die "--allow-dirty-launcher is only allowed with --base origin/main"
fi

if [[ "${DRY_RUN}" -eq 0 ]]; then
    if [[ -e "${WORKTREE_ABS}" ]]; then
        die "worktree path already exists: ${WORKTREE_REL}"
    fi
    if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
        die "branch already exists: ${BRANCH}"
    fi
    git fetch --prune origin
    if ! git rev-parse --verify --quiet "${BASE_REF}^{commit}" >/dev/null; then
        die "base ref not found: ${BASE_REF}"
    fi
    if [[ "${BASE_REF}" == "origin/main" ]]; then
        launcher_status="$(git status --porcelain)"
        if [[ -n "${launcher_status}" && "${ALLOW_DIRTY_LAUNCHER}" -ne 1 ]]; then
            die "current checkout must be clean before starting a PR lane, or pass --allow-dirty-launcher for an isolated origin/main lane"
        fi
        if [[ -n "${launcher_status}" ]]; then
            if ! git rev-parse --verify --quiet "main^{commit}" >/dev/null; then
                die "local main ref not found; cannot prove origin/main dirty-lane parity"
            fi
            ahead_behind="$(git rev-list --left-right --count main...origin/main)"
            if [[ "${ahead_behind}" != "0	0" ]]; then
                die "local main must be synced with origin/main before dirty lane start; got ${ahead_behind}"
            fi
        elif git rev-parse --verify --quiet "main^{commit}" >/dev/null; then
            ahead_behind="$(git rev-list --left-right --count main...origin/main)"
            if [[ "${ahead_behind}" != "0	0" ]]; then
                die "local main must be synced with origin/main before lane start; got ${ahead_behind}"
            fi
        fi
    elif [[ -n "$(git status --porcelain)" ]]; then
        die "current checkout must be clean before starting a non-origin/main PR lane"
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
echo "PR open mode: non-draft by default; draft requires explicit operator exception."
echo "Lane authority: check_preflight.py -> task_bootstrap.py -> agent-coordinator."
echo "Experiment Runner: joins after coordinator bootstrap as oracle-only evidence."
echo "Repo Python: ${REPO_PYTHON}"
echo "Python gate rule: use VENV_PYTHON or repo .venv python; avoid bare python3 -m pytest when .venv exists."
echo "Experiment Runner Python rule: run evidence with VENV_PYTHON/repo Python; artifact load/write failures are infra blockers, not Not applicable."
echo ""

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY RUN: no git worktree, preflight, or bootstrap commands were executed."
    printf "Would run: git worktree add -b %q %q %q\n" "${BRANCH}" "${WORKTREE_REL}" "${BASE_REF}"
    printf "Would run in worktree: %q scripts/orchestration/check_preflight.py --mode analyze" "${REPO_PYTHON}"
    for ((i = 0; i < ${#PATH_ARGS[@]}; i += 2)); do
        printf " %q %q" "${PATH_ARGS[i]}" "${PATH_ARGS[i + 1]}"
    done
    printf "\n"
    printf "Would run in worktree: %q scripts/orchestration/task_bootstrap.py --goal %q --task-class %q --pr-phase %q" "${REPO_PYTHON}" "${GOAL}" "${TASK_CLASS}" "${PR_PHASE}"
    for ((i = 0; i < ${#PATH_ARGS[@]}; i += 2)); do
        printf " %q %q" "${PATH_ARGS[i]}" "${PATH_ARGS[i + 1]}"
    done
    for ((i = 0; i < ${#INVARIANT_CLASS_ARGS[@]}; i += 2)); do
        printf " %q %q" "${INVARIANT_CLASS_ARGS[i]}" "${INVARIANT_CLASS_ARGS[i + 1]}"
    done
    for ((i = 0; i < ${#REQUESTED_ARGS[@]}; i += 2)); do
        printf " %q %q" "${REQUESTED_ARGS[i]}" "${REQUESTED_ARGS[i + 1]}"
    done
    printf "\n"
    printf "Would run in worktree after bootstrap: %q scripts/orchestration/pr_evidence_sidecar.py prepare --packet '<bootstrap-packet>' --base-sha '<worktree-HEAD>'" "${REPO_PYTHON}"
    for rail in "${EVIDENCE_SIDECAR_RAILS[@]}"; do
        printf " --applicable-rail %q" "${rail}"
    done
    printf "\n"
    echo ""
    prompt_cmd=(
        "${REPO_PYTHON}" scripts/orchestration/render_codex_start_prompt.py
        recipe
        --goal "${GOAL}"
        --task-class "${TASK_CLASS}"
        --pr-phase "${PR_PHASE}"
        --branch "${BRANCH}"
        --worktree "${WORKTREE_REL}"
    )
    if ((${#PATH_ARGS[@]})); then
        prompt_cmd+=("${PATH_ARGS[@]}")
    fi
    if ((${#INVARIANT_CLASS_ARGS[@]})); then
        prompt_cmd+=("${INVARIANT_CLASS_ARGS[@]}")
    fi
    if ((${#REQUESTED_ARGS[@]})); then
        prompt_cmd+=("${REQUESTED_ARGS[@]}")
    fi
    "${prompt_cmd[@]}"
    exit 0
fi

git worktree add -b "${BRANCH}" "${WORKTREE_REL}" "${BASE_REF}"

(
    cd "${WORKTREE_ABS}"
    preflight_cmd=("${REPO_PYTHON}" scripts/orchestration/check_preflight.py --mode analyze)
    if ((${#PATH_ARGS[@]})); then
        preflight_cmd+=("${PATH_ARGS[@]}")
    fi
    "${preflight_cmd[@]}"

    bootstrap_cmd=(
        "${REPO_PYTHON}" scripts/orchestration/task_bootstrap.py
        --goal "${GOAL}"
        --task-class "${TASK_CLASS}"
        --pr-phase "${PR_PHASE}"
    )
    if ((${#PATH_ARGS[@]})); then
        bootstrap_cmd+=("${PATH_ARGS[@]}")
    fi
    if ((${#INVARIANT_CLASS_ARGS[@]})); then
        bootstrap_cmd+=("${INVARIANT_CLASS_ARGS[@]}")
    fi
    if ((${#REQUESTED_ARGS[@]})); then
        bootstrap_cmd+=("${REQUESTED_ARGS[@]}")
    fi
    BOOTSTRAP_OUTPUT="$("${bootstrap_cmd[@]}")"
    echo "${BOOTSTRAP_OUTPUT}"
    echo ""
    BOOTSTRAP_PACKET_PATH="$(
        BOOTSTRAP_OUTPUT="${BOOTSTRAP_OUTPUT}" "${REPO_PYTHON}" - <<'PY'
import json
import os

payload = json.loads(os.environ["BOOTSTRAP_OUTPUT"])
print(payload["output"])
PY
    )"
    BOOTSTRAP_OUTPUT="${BOOTSTRAP_OUTPUT}" "${REPO_PYTHON}" - <<'PY'
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
    echo ""
    EVIDENCE_SIDECAR_STATE="unavailable"
    EVIDENCE_SIDECAR_ID=""
    if [[ ! -f scripts/orchestration/pr_evidence_sidecar.py ]]; then
        echo "WARNING: evidence sidecar unavailable; structural receipt only, no authority granted." >&2
    else
        WORKTREE_HEAD="$(git rev-parse HEAD)"
        sidecar_cmd=(
            "${REPO_PYTHON}" scripts/orchestration/pr_evidence_sidecar.py prepare
            --packet "${BOOTSTRAP_PACKET_PATH}"
            --base-sha "${WORKTREE_HEAD}"
        )
        for rail in "${EVIDENCE_SIDECAR_RAILS[@]}"; do
            sidecar_cmd+=(--applicable-rail "${rail}")
        done
        if SIDECAR_OUTPUT="$("${sidecar_cmd[@]}" 2>&1)"; then
            if EVIDENCE_SIDECAR_ID="$(
                SIDECAR_OUTPUT="${SIDECAR_OUTPUT}" BOOTSTRAP_PACKET_PATH="${BOOTSTRAP_PACKET_PATH}" "${REPO_PYTHON}" - <<'PY'
import json
import os

try:
    payload = json.loads(os.environ["SIDECAR_OUTPUT"])
except (json.JSONDecodeError, TypeError):
    raise SystemExit(1)
if not isinstance(payload, dict):
    raise SystemExit(1)
expected_keys = {"schema_version", "command", "sidecar_id", "sidecar_path", "created"}
if (
    set(payload) != expected_keys
    or payload["schema_version"] != "pr_evidence_sidecar.start.v1"
    or payload["command"] != "prepare"
):
    raise SystemExit(1)
sidecar_id = payload["sidecar_id"]
if (
    not isinstance(sidecar_id, str)
    or not sidecar_id.startswith("sha256:")
    or len(sidecar_id) != 71
    or any(char not in "0123456789abcdef" for char in sidecar_id[7:])
):
    raise SystemExit(1)
expected_path = f"artifacts/orchestration/pr_evidence_sidecars/{sidecar_id[7:]}/start.json"
if payload["sidecar_path"] != expected_path or not isinstance(payload["created"], bool):
    raise SystemExit(1)
print(sidecar_id)
PY
            )"; then
                EVIDENCE_SIDECAR_STATE="prepared"
            else
                EVIDENCE_SIDECAR_STATE="invalid"
                EVIDENCE_SIDECAR_ID=""
                echo "WARNING: evidence sidecar invalid; structural receipt only, no authority granted." >&2
            fi
        elif [[ "${SIDECAR_OUTPUT}" == "STORAGE_UNAVAILABLE" ]]; then
            echo "WARNING: evidence sidecar unavailable; structural receipt only, no authority granted." >&2
        else
            EVIDENCE_SIDECAR_STATE="invalid"
            echo "WARNING: evidence sidecar invalid; structural receipt only, no authority granted." >&2
        fi
    fi
    evidence_prompt_args=(--evidence-sidecar-state "${EVIDENCE_SIDECAR_STATE}")
    if [[ "${EVIDENCE_SIDECAR_STATE}" == "prepared" ]]; then
        evidence_prompt_args+=(--evidence-sidecar-id "${EVIDENCE_SIDECAR_ID}")
    fi
    "${REPO_PYTHON}" scripts/orchestration/render_codex_start_prompt.py \
        packet \
        --packet "${BOOTSTRAP_PACKET_PATH}" \
        --branch "${BRANCH}" \
        --worktree "${WORKTREE_REL}" \
        "${evidence_prompt_args[@]}"

    echo ""
    echo "Next steps:"
    echo "  1. cd ${WORKTREE_REL}"
    echo "  2. Generate the role-agent dispatch manifest:"
    DISPATCH_COMMAND="$(
        BOOTSTRAP_PACKET_PATH="${BOOTSTRAP_PACKET_PATH}" REPO_PYTHON="${REPO_PYTHON}" "${REPO_PYTHON}" - <<'PY'
import json
import os
import shlex
from pathlib import Path

packet_path = os.environ["BOOTSTRAP_PACKET_PATH"]
repo_python = os.environ["REPO_PYTHON"]
default_command = (
    "python3 scripts/orchestration/role_dispatch_bridge.py "
    "--packet <packet> --pretty"
)
try:
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    packet = {}
contract = packet.get("role_agent_dispatch_contract")
if not isinstance(contract, dict):
    contract = {}
raw_command = str(contract.get("dispatch_manifest_command", "")).strip() or default_command
try:
    tokens = shlex.split(raw_command)
except ValueError:
    tokens = shlex.split(default_command)

rendered = []
for index, token in enumerate(tokens):
    if index == 0 and token in {"python", "python3"}:
        rendered.append(shlex.quote(repo_python))
    elif token.startswith("<") and token.endswith(">") and token[1:-1] == "packet":
        rendered.append(shlex.quote(packet_path))
    else:
        rendered.append(shlex.quote(token))
print(" ".join(rendered))
PY
    )"
    printf "     %s\n" "${DISPATCH_COMMAND}"
    echo "  3. Run the dispatch_sequence roles in order before implementation."
    echo "  4. Create Experiment Runner oracle-only evidence after coordinator bootstrap when the lane is non-trivial."
    echo "  5. Open the PR non-draft after local validation and initial PR body/mapping are ready."
)
