#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${1:-ios}"
REPORT_PATH="${2:-greenlight-report.json}"
GREENLIGHT_VERSION="${GREENLIGHT_VERSION:-v0.1.0}"
GREENLIGHT_BLOCKING="${GREENLIGHT_BLOCKING:-false}"

echo "Running Greenlight preflight for: ${PROJECT_PATH}"
echo "Pinned Greenlight version: ${GREENLIGHT_VERSION}"

if ! command -v greenlight >/dev/null 2>&1; then
  if ! command -v go >/dev/null 2>&1; then
    echo "go is required to install greenlight but was not found in PATH" >&2
    exit 2
  fi

  echo "Installing greenlight ${GREENLIGHT_VERSION} via go install..."
  go install "github.com/RevylAI/greenlight/cmd/greenlight@${GREENLIGHT_VERSION}"
fi

export PATH="$(go env GOPATH)/bin:${PATH}"

if ! command -v greenlight >/dev/null 2>&1; then
  echo "greenlight was not found after installation" >&2
  exit 2
fi

greenlight preflight "${PROJECT_PATH}" --format json --output "${REPORT_PATH}"

python3 - "${REPORT_PATH}" "${GREENLIGHT_BLOCKING}" <<'PY'
import json
import os
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
blocking_raw = sys.argv[2].strip().lower()
blocking = blocking_raw in {"1", "true", "yes", "on"}

if not report_path.exists():
    print(f"Report file not found: {report_path}", file=sys.stderr)
    raise SystemExit(2)

payload = json.loads(report_path.read_text(encoding="utf-8"))
summary = payload.get("summary", {})

critical = int(summary.get("critical", 0))
high = int(summary.get("high", 0))
medium = int(summary.get("medium", 0))
low = int(summary.get("low", 0))
info = int(summary.get("info", 0))

line = (
    f"Greenlight summary: critical={critical}, high={high}, "
    f"medium={medium}, low={low}, info={info}"
)
print(line)

step_summary_path = Path.cwd() / Path(".github_step_summary_fallback.md")
if "GITHUB_STEP_SUMMARY" in os.environ:
    step_summary_path = Path(os.environ["GITHUB_STEP_SUMMARY"])

step_summary_path.write_text(
    "\n".join(
        [
            "## Greenlight iOS preflight",
            "",
            f"- critical: `{critical}`",
            f"- high: `{high}`",
            f"- medium: `{medium}`",
            f"- low: `{low}`",
            f"- info: `{info}`",
            f"- mode: `{'blocking' if blocking else 'report-only'}`",
            "",
            f"Report file: `{report_path}`",
        ]
    )
    + "\n",
    encoding="utf-8",
)

if blocking and critical > 0:
    print("Blocking mode active and critical findings > 0", file=sys.stderr)
    raise SystemExit(1)
PY
