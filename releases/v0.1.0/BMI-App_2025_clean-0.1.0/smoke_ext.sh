#!/usr/bin/env bash
set -euo pipefail

URL=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' tunnel.log | tail -n1 || true)
if [ -z "$URL" ]; then
  echo "no tunnel url in tunnel.log"; exit 1
fi

echo "USING URL: $URL"
echo "— /health"
curl -s "$URL/health" | jq .

echo "— /bmi"
curl -s -X POST "$URL/bmi" \
  -H "Content-Type: application/json" \
  -d '{"height_m":1.70,"weight_kg":65,"age":28,"gender":"female","pregnant":"no","athlete":"no","user_group":"general","language":"en"}' \
  | jq .

echo "— /bodyfat"
curl -s -X POST "$URL/bodyfat" \
  -H "Content-Type: application/json" \
  -d '{"height_m":1.70,"weight_kg":65,"age":28,"gender":"female","neck_cm":34,"waist_cm":74,"hip_cm":94}' \
  | jq .
