#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_NODE_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/.nvmrc")"
if ! command -v node >/dev/null 2>&1; then
  echo "node is required on PATH to run frontend commands. Install Node ${EXPECTED_NODE_VERSION} and retry." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required on PATH to run frontend commands." >&2
  exit 1
fi

CURRENT_NODE_VERSION="$(node -p 'process.versions.node')"
EXPECTED_NODE_MAJOR="${EXPECTED_NODE_VERSION%%.*}"
CURRENT_NODE_MAJOR="${CURRENT_NODE_VERSION%%.*}"

# Fail closed on too-old Node, but keep local newer runtimes usable without
# registry bootstrap so OpenAPI and frontend helper flows remain deterministic.
# Запрещаем слишком старый Node, но не уходим в сетевой bootstrap для новых
# локальных версий, чтобы OpenAPI/Frontend helper оставались детерминированными.
if (( CURRENT_NODE_MAJOR < EXPECTED_NODE_MAJOR )); then
  echo "Frontend commands require Node ${EXPECTED_NODE_VERSION} or newer major runtime; current runtime is ${CURRENT_NODE_VERSION}." >&2
  echo "Activate the repo Node version via your local toolchain (for example nvm/fnm/volta) and retry." >&2
  exit 1
fi

if [[ "${CURRENT_NODE_VERSION}" != "${EXPECTED_NODE_VERSION}" ]]; then
  echo "Warning: repo baseline is Node ${EXPECTED_NODE_VERSION}, current runtime is ${CURRENT_NODE_VERSION}." >&2
  echo "Continuing with the installed Node runtime to avoid implicit network bootstrap; switch to ${EXPECTED_NODE_VERSION} for exact CI parity." >&2
fi

exec npm "$@"
