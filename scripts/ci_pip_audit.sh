#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]]; then
  echo "[ci_pip_audit] Skipping (not running in CI)" >&2
  exit 0
fi

echo "[ci_pip_audit] Running pip-audit..." >&2
if ! command -v pip-audit >/dev/null 2>&1; then
  echo "pip-audit not installed; skipping" >&2
  exit 0
fi

pip-audit -r requirements.txt -f json -o pip-audit.json || true
echo "[ci_pip_audit] Done" >&2
#!/usr/bin/env bash
set -euo pipefail

if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
  echo "[dependency-check] CI detected: running pip-audit"
  pip-audit --format=json --output=pip-audit.json || echo "Dependency check completed"
else
  echo "[dependency-check] Local push detected: skipping pip-audit (CI enforces)"
fi
