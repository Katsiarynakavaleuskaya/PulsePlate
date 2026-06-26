#!/usr/bin/env bash
set -euo pipefail

if ! command -v pip-audit >/dev/null 2>&1; then
  echo "[ci_pip_audit] ERROR: pip-audit is required on PATH" >&2
  exit 1
fi

overall_status=0

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
  if pip-audit "${audit_args[@]}"; then
    :
  else
    audit_status=$?
    echo "[ci_pip_audit] ERROR: pip-audit failed for ${manifest} (exit ${audit_status})" >&2
    overall_status="${audit_status}"
  fi
done

if [[ "${overall_status}" -ne 0 ]]; then
  echo "[ci_pip_audit] ERROR: one or more dependency manifests failed audit" >&2
  exit "${overall_status}"
fi

echo "[ci_pip_audit] Done" >&2
