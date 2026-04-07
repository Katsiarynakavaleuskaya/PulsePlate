#!/usr/bin/env bash
# Sanitized example only: copy to ~/.local/bin/pulseplate-coordinator-launch.sh and chmod +x.
# Do not commit host-specific paths, tokens, or real ~/.codex files.
# Canonical rollout: docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md
set -euo pipefail

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
elif [[ -n "${PULSEPLATE_REPO_ROOT:-}" ]]; then
  REPO_ROOT="${PULSEPLATE_REPO_ROOT}"
else
  echo "ERROR: run inside repo or export PULSEPLATE_REPO_ROOT" >&2
  exit 2
fi

export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PATH="$HOME/.local/bin:$PATH"

GOAL=""
TASK_CLASS=""
PR_PHASE="none"
REQUESTED_ARGS=()
PATH_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --goal) GOAL="$2"; shift 2 ;;
    --task-class) TASK_CLASS="$2"; shift 2 ;;
    --pr-phase) PR_PHASE="$2"; shift 2 ;;
    --requested-agent) REQUESTED_ARGS+=(--requested-agent "$2"); shift 2 ;;
    --path) PATH_ARGS+=(--path "$2"); shift 2 ;;
    *) echo "ERROR: unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$GOAL" || -z "$TASK_CLASS" ]]; then
  echo "ERROR: --goal and --task-class are required" >&2
  exit 2
fi

cd "$REPO_ROOT"

# Bash 3.2 / set -u: empty array "$@" expansion is unsafe; use ${arr[@]+"${arr[@]}"}.
python3 scripts/orchestration/check_preflight.py --mode analyze ${PATH_ARGS[@]+"${PATH_ARGS[@]}"}

python3 scripts/orchestration/task_bootstrap.py \
  --goal "$GOAL" \
  --task-class "$TASK_CLASS" \
  --pr-phase "$PR_PHASE" \
  ${PATH_ARGS[@]+"${PATH_ARGS[@]}"} \
  ${REQUESTED_ARGS[@]+"${REQUESTED_ARGS[@]}"}
