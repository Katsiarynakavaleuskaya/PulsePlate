#!/usr/bin/env bash
set -euo pipefail

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "[ci_pip_audit] ERROR: pip-audit is required on PATH" >&2
  exit 1
fi

readonly PYTORCH_JIT_CVE_ID="CVE-2025-3000"

manifests=("requirements.txt")
if [[ -f "requirements-docker-runtime.txt" ]]; then
  manifests+=("requirements-docker-runtime.txt")
fi
if [[ -f "requirements-data.txt" ]]; then
  manifests+=("requirements-data.txt")
fi
if [[ -f "requirements-evals.txt" ]]; then
  manifests+=("requirements-evals.txt")
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
  audit_args=(
    -r "${manifest}"
    --no-deps
    --disable-pip
    -f json
    -o "${output}"
  )
  case "${manifest}" in
    requirements-rag-vector.txt | requirements-rag-vector-cpu.txt)
      audit_args+=(--ignore-vuln "${PYTORCH_JIT_CVE_ID}")
      ;;
  esac
  pip-audit "${audit_args[@]}"
done

echo "[ci_pip_audit] Done" >&2
