#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORDS_FILE="$ROOT_DIR/cspell-workspace.txt"

if [[ ! -f "$WORDS_FILE" ]]; then
  echo "Expected dictionary file at $WORDS_FILE" >&2
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required. Install Node.js and npm before running this script." >&2
  exit 1
fi

TMP_FILE="$(mktemp)"
cleanup() {
  rm -f "$TMP_FILE"
}
trap cleanup EXIT

pushd "$ROOT_DIR" >/dev/null
npx cspell lint --no-progress --wordsOnly --unique "$@" >"$TMP_FILE" || true
popd >/dev/null

if [[ -s "$TMP_FILE" ]]; then
  grep -Ev '^[[:space:]]*$' "$TMP_FILE" >>"$WORDS_FILE"
  sort -u "$WORDS_FILE" -o "$WORDS_FILE"
  echo "Updated $WORDS_FILE with new terms."
else
  echo "No new terms to add."
fi
