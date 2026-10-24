#!/usr/bin/env bash
set -euo pipefail

case "$#:$*" in
  0:) mode=ci ;;
  1:--pre-push) mode=pre-push ;;
  *) echo "[ci_pip_audit] ERROR: supported arguments: none or --pre-push" >&2; exit 2 ;;
esac
if ! command -v pip-audit >/dev/null 2>&1; then
  echo "[ci_pip_audit] ERROR: pip-audit is required on PATH" >&2
  exit 1
fi
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "${repo_root}/scripts/hooks/repo_python.sh"
audit_python="$(resolve_repo_python "${repo_root}")"
cd -- "${repo_root}"
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

if [[ "${mode}" == pre-push ]]; then
  manifests=("requirements.txt")
fi
# The existing dependency-surface owner supplies --no-deps --disable-pip
# --strict and only its literal, expiring Pillow cohort. Never forward audit flags.
for manifest in "${manifests[@]}"; do
  audit_args=(--audit-manifest "${manifest}")
  if [[ "${mode}" == pre-push ]]; then
    audit_args+=(--audit-pre-push)
  fi
  if "${audit_python}" "${repo_root}/scripts/ci/check_python_dependency_surfaces.py" "${audit_args[@]}"; then
    :
  else
    audit_status=$?
    echo "[ci_pip_audit] ERROR: ${manifest} policy audit exited with status ${audit_status}" >&2
    overall_status="${audit_status}"
  fi
done
if [[ "${overall_status}" -ne 0 ]]; then
  echo "[ci_pip_audit] ERROR: one or more dependency manifests failed audit" >&2
  exit "${overall_status}"
fi
echo "[ci_pip_audit] Done. Native exits and retained findings are recorded separately."
