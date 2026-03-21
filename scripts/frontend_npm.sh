#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_NODE_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/.nvmrc")"
CURRENT_NODE_VERSION="$(node -p 'process.versions.node')"

if [[ "${CURRENT_NODE_VERSION}" == "${EXPECTED_NODE_VERSION}" ]]; then
  exec npm "$@"
fi

NPM_EXECUTABLE="$(command -v npm || true)"
if [[ -z "${NPM_EXECUTABLE}" ]]; then
  echo "npm is required on PATH to run frontend commands." >&2
  exit 1
fi

NPM_ROOT="$(npm root -g 2>/dev/null || true)"
NPM_CLI_JS="${NPM_ROOT}/npm/bin/npm-cli.js"

if [[ -z "${NPM_ROOT}" || ! -f "${NPM_CLI_JS}" ]]; then
  echo "Unable to locate npm-cli.js via 'npm root -g'; ensure npm is installed correctly." >&2
  exit 1
fi

echo "Bootstrapping frontend npm under Node ${EXPECTED_NODE_VERSION} (current: ${CURRENT_NODE_VERSION})." >&2
exec npx -y "node@${EXPECTED_NODE_VERSION}" "${NPM_CLI_JS}" "$@"
