#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://127.0.0.1:8001}"

wait_for() {
  local url="$1" tries=20
  for ((i=1;i<=tries;i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  echo "timeout: $url" >&2
  return 1
}

echo "[wait] ${BASE}/api/v1/health"
wait_for "${BASE}/api/v1/health"

echo "[health] ${BASE}/api/v1/health"
curl -s "${BASE}/api/v1/health" | sed 's/$/\n/'

echo "[bmi] ${BASE}/api/v1/bmi"
curl -s -X POST "${BASE}/api/v1/bmi" \
  -H "Content-Type: application/json" \
  -d '{"weight_kg":70,"height_cm":170,"group":"general"}' | sed 's/$/\n/'
