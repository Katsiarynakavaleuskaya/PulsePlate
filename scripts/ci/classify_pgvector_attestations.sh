#!/usr/bin/env bash
# Shared fixed GitHub presence seam; native download and trust stay in Python/gh.
set -euo pipefail
manifest="${1:?manifest required}"
result="${2:?result required}"
shift 2
: "${GH_TOKEN:?GitHub authentication required}"
: "${GITHUB_REPOSITORY:?repository required}"
: "${RUNNER_TEMP:?runner temporary directory required}"
digest="$(python3 - "$manifest" <<'PY'
import re, sys
from pathlib import Path
from scripts.ci.check_pgvector_attestations import read_json
value = read_json(Path(sys.argv[1]))["platform_manifest_digest"]
if not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
    raise SystemExit("Invalid exact image digest")
print(value)
PY
)"
response_path="$(mktemp "${RUNNER_TEMP}/pulseplate-pgvector-attestations.XXXXXX")"
trap 'rm -f -- "$response_path"' EXIT
gh --version > "${result%.json}-gh-version.txt"
http_status="$(curl --silent --show-error --location \
  --proto '=https' --tlsv1.2 \
  --header 'Accept: application/vnd.github+json' \
  --header "Authorization: Bearer ${GH_TOKEN}" \
  --header 'X-GitHub-Api-Version: 2026-03-10' \
  --output "$response_path" --write-out '%{http_code}' \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/attestations/${digest}?per_page=100")"
printf '%s\n' "$http_status" > "${result%.json}-presence-status.txt"
case "$http_status" in
  200|404) ;;
  *) echo "Unable to classify exact-digest attestations (HTTP ${http_status})" >&2; exit 1 ;;
esac
python3 scripts/ci/check_pgvector_attestations.py inventory \
  --manifest "$manifest" --repo "$GITHUB_REPOSITORY" \
  --inventory "$response_path" --inventory-http-status "$http_status" \
  --json-out "$result" "$@"
