#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_NODE_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/.nvmrc")"
EXPECTED_NODE_MAJOR="${EXPECTED_NODE_VERSION%%.*}"
CURRENT_NODE_VERSION="$(node -p 'process.versions.node')"
CURRENT_NODE_MAJOR="${CURRENT_NODE_VERSION%%.*}"

if [[ "${CURRENT_NODE_MAJOR}" == "${EXPECTED_NODE_MAJOR}" ]]; then
  exec npm "$@"
fi

NPM_ROOT="$(npm root -g 2>/dev/null)"
NPM_CLI_JS="${NPM_ROOT}/npm/bin/npm-cli.js"

if [[ ! -f "${NPM_CLI_JS}" ]]; then
  echo "Unable to locate npm-cli.js for frontend Node runtime bootstrap." >&2
  exit 1
fi

echo "Bootstrapping frontend npm under Node ${EXPECTED_NODE_VERSION} (current: ${CURRENT_NODE_VERSION})." >&2
exec npx -y "node@${EXPECTED_NODE_VERSION}" "${NPM_CLI_JS}" "$@"
