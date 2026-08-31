#!/usr/bin/env bash
set -euo pipefail

if [[ "$(/usr/bin/uname -s)" != "Darwin" ]]; then
  echo "SKIP: iOS Swift syntax check requires macOS; no syntax or build claim."
  exit 0
fi

if (( $# == 0 )); then
  echo "ERROR: iOS Swift syntax check requires at least one .swift file."
  exit 2
fi

for file in "$@"; do
  if [[ -z "$file" || "$file" != *.swift || ! -f "$file" ]]; then
    echo "ERROR: expected an existing .swift file: $file"
    exit 2
  fi

  if /usr/bin/xcrun swiftc -swift-version 5 -parse -- "$file"; then
    continue
  else
    status=$?
    exit "$status"
  fi
done
