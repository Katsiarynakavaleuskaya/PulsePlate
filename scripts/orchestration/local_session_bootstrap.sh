#!/usr/bin/env bash
# Opt-in local bridge for coordinator-first sessions (repo SoT only).
# RU: Не заменяет host launcher; вызывает preflight и напоминает про task_bootstrap.
# EN: Does not replace a machine launcher; runs preflight then prints bootstrap hints.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found in PATH (required for check_preflight)." >&2
    exit 1
fi

PREFLIGHT_PY="${REPO_ROOT}/scripts/orchestration/check_preflight.py"
if [[ ! -f "${PREFLIGHT_PY}" ]]; then
    echo "ERROR: missing ${PREFLIGHT_PY}" >&2
    exit 1
fi

# analyze: allows a dirty tree; appropriate for cold-start / task analysis.
# For --mode execute|merge, run scripts/orchestration/check_preflight.py directly.
python3 "${PREFLIGHT_PY}" --mode analyze

echo ""
echo "OK: preflight passed (analyze). Coordinator routing and skill selection are"
echo "    deterministic only after you invoke task_bootstrap (and follow the packet)."
echo ""
echo "Generate a task packet (minimal example):"
echo "  python3 ${REPO_ROOT}/scripts/orchestration/task_bootstrap.py \\"
echo "    --goal \"<short goal>\" \\"
echo "    --task-class \"<task_class>\""
echo ""
echo "Common options:"
echo "  --path <path>              (repeatable; scope for scoped AGENTS / routing)"
echo "  --pr-phase post_open_review|pre_open|merge_ready|none"
echo "  --requested-agent <slug>   (repeatable)"
echo ""
echo "Full CLI: python3 scripts/orchestration/task_bootstrap.py --help"
echo "Automation matrix: docs/orchestration/AUTOMATION_READINESS_MATRIX.md"
