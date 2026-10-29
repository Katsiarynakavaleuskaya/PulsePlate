#!/usr/bin/env bash
set -euo pipefail

if ! auditor="$(command -v pip-audit)"; then
  echo "[ci_pip_audit] ERROR: pip-audit is required on PATH" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/hooks/repo_python.sh
source "${script_dir}/hooks/repo_python.sh"
audit_python="$(resolve_repo_python "$PWD")"
comparison_helper="${script_dir}/ci/audit_fastembed_compat.py"
comparison_dir=""
cleanup_comparison() {
  if [[ -n "${comparison_dir}" ]]; then
    rm -rf -- "${comparison_dir}"
  fi
}
trap cleanup_comparison EXIT

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
  comparison_dir="$(mktemp -d "${TMPDIR:-/tmp}/pulseplate-pip-audit.XXXXXXXX")"
  comparison_dir="$(cd "${comparison_dir}" && pwd -P)"
  output="pip-audit-${stem}-${comparison_dir##*/}.json"
  echo "[ci_pip_audit] Running pip-audit for ${manifest} -> ${output}" >&2
  if ! "${audit_python}" "${comparison_helper}" prepare \
    --manifest "${manifest}" --output "${output}" --work-dir "${comparison_dir}"; then
    overall_status=1
    cleanup_comparison
    comparison_dir=""
    continue
  fi
  audit_args=(
    -r "${comparison_dir}/comparand.txt"
    --no-deps
    --disable-pip
    --strict
    -f json
    -o "${output}"
  )
  scanner_env=(env -i "PATH=${PATH}" "HOME=${comparison_dir}/scanner-home"
    "LANG=C.UTF-8" "PIP_CONFIG_FILE=/dev/null" "PYTHONNOUSERSITE=1")
  if scanner_version="$("${scanner_env[@]}" "${auditor}" --version 2> "${output%.json}.stderr.log")"; then
    if "${scanner_env[@]}" "${auditor}" "${audit_args[@]}" 2> "${output%.json}.stderr.log"; then
      audit_status=0
    else
      audit_status=$?
    fi
  else
    audit_status=$?
    scanner_version="unavailable"
  fi
  cat "${output%.json}.stderr.log" >&2
  if ! "${audit_python}" "${comparison_helper}" validate \
    --manifest "${manifest}" --output "${output}" --work-dir "${comparison_dir}" \
    --scanner-exit "${audit_status}" --scanner-version "${scanner_version}" \
    --auditor "${auditor}"; then
    if [[ "${audit_status}" -eq 0 ]]; then
      audit_status=1
    fi
  fi
  if [[ "${audit_status}" -ne 0 ]]; then
    echo "[ci_pip_audit] ERROR: pip-audit failed for ${manifest} (exit ${audit_status})" >&2
    overall_status="${audit_status}"
  fi
  cleanup_comparison
  comparison_dir=""
done

if [[ "${overall_status}" -ne 0 ]]; then
  echo "[ci_pip_audit] ERROR: one or more dependency manifests failed audit" >&2
  exit "${overall_status}"
fi

echo "[ci_pip_audit] Done" >&2
