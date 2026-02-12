# iOS Greenlight Runbook (P0)

## Purpose

`greenlight` provides an App Store pre-submission readiness scan for iOS projects.
Current phase is **P0 report-only** to measure signal quality before enabling blocking gates.

## CI workflow

- Workflow: `.github/workflows/greenlight-ios.yml`
- Script: `scripts/ci/greenlight_ios_preflight.sh`
- Trigger scope: `ios/**` and Greenlight workflow/script changes
- Output:
  - GitHub step summary with severity counts
  - Artifact: `greenlight-ios-report` (`greenlight-report.json`)

## Policy (P0)

- Mode: report-only (`GREENLIGHT_BLOCKING=false`)
- Tool version is pinned: `GREENLIGHT_VERSION=v0.1.0`
- CI must fail on tool execution errors (no shell error masking)
- Findings do not block merge in P0

## Local execution

```bash
GREENLIGHT_VERSION=v0.1.0 GREENLIGHT_BLOCKING=false \
  scripts/ci/greenlight_ios_preflight.sh ios greenlight-report.json
```

## Interpreting results

- `critical`: potential App Store rejection risks with highest priority
- `high/medium/low/info`: descending priority for remediation backlog
- Use artifact JSON for detailed diagnostics and issue triage

## P1 transition criteria (blocking mode)

Before switching to blocking:

1. Two weeks of stable report-only runs.
2. False positive rate is acceptable for CI friction.
3. Team agrees on baseline/allowlist process for known non-actionable findings.

Then enable:

- `GREENLIGHT_BLOCKING=true`
- Fail job only when `critical > 0`
