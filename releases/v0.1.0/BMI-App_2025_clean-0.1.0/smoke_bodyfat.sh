#!/usr/bin/env bash
set -euo pipefail

BASE_DEFAULT="http://127.0.0.1:8001"

detect_external_url() {
  if [ -n "${TUNNEL_URL:-}" ]; then
    echo "$TUNNEL_URL"; return 0
  fi
  if [ -f tunnel.log ]; then
    u=$(grep -Eo 'https://[a-zA-Z0-9._-]*trycloudflare\.com' tunnel.log | tail -n1 || true)
    [ -n "$u" ] && echo "$u" && return 0
  fi
  if [ -f tunnel.out ]; then
    u=$(grep -Eo 'https://[a-zA-Z0-9._-]*\.loca\.lt' tunnel.out | tail -n1 || true)
    [ -n "$u" ] && echo "$u" && return 0
  fi
  return 1
}

BASE="$BASE_DEFAULT"
if [[ "${1:-}" == "--external" ]]; then
  if ext=$(detect_external_url); then BASE="$ext"; else
    echo "no external URL found (set TUNNEL_URL or run cloudflared with --logfile tunnel.log)" >&2
    exit 1
  fi
fi

echo "USING BASE: $BASE"
echo

do_post() {
  path="$1"; json="$2"
  curl -s -X POST "$BASE$path" -H "Content-Type: application/json" -d "$json" \
    | (jq . 2>/dev/null || cat)
  echo
}

echo "→ Deurenberg"
do_post "/bodyfat" '{"height_m":1.70,"weight_kg":65,"age":28,"gender":"female","neck_cm":34,"waist_cm":74,"hip_cm":94}'

echo "→ US Navy"
do_post "/bodyfat" '{"height_cm":170,"neck_cm":34,"waist_cm":74,"hip_cm":94,"gender":"female"}'

echo "→ YMCA"
do_post "/bodyfat" '{"weight_kg":65,"waist_cm":74,"gender":"female"}'
