#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]]; then
  echo "[ci_pip_audit] Skipping (not running in CI)" >&2
  exit 0
fi

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "[ci_pip_audit] pip-audit not installed; skipping" >&2
  exit 0
fi

manifests=("requirements.txt")
if [[ -f "requirements-docker-runtime.txt" ]]; then
  manifests+=("requirements-docker-runtime.txt")
fi
if [[ -f "requirements-rag-vector.txt" ]]; then
  manifests+=("requirements-rag-vector.txt")
fi
if [[ -f "requirements-rag-vector-cpu.txt" ]]; then
  manifests+=("requirements-rag-vector-cpu.txt")
fi

for manifest in "${manifests[@]}"; do
  stem="${manifest%.txt}"
  output="pip-audit-${stem}.json"
  echo "[ci_pip_audit] Running pip-audit for ${manifest} -> ${output}" >&2
  pip-audit -r "${manifest}" -f json -o "${output}" || true
done

echo "[ci_pip_audit] Done" >&2
