# PR Audit: Greenlight iOS Preflight Integration (P0)

## Scope

- Add report-only App Store readiness scan for iOS in CI.
- Integrate `greenlight preflight` as a standalone workflow and CI script.
- Publish JSON report as workflow artifact and short step summary.

## Non-goals

- No backend runtime changes.
- No blocking policy on findings (P0 is report-only).
- No App Store Connect authenticated scan (offline preflight only).
- No local Makefile target in this phase (planned for P1).

## Files changed

- `.github/workflows/greenlight-ios.yml`
- `scripts/ci/greenlight_ios_preflight.sh`
- `docs/audit/PR_XXX_GREENLIGHT_INTEGRATION_AUDIT.md`
- `docs/runbook/IOS_GREENLIGHT.md`

## Repo-truth evidence commands

- `rg -n "greenlight preflight|GREENLIGHT_BLOCKING|GREENLIGHT_VERSION" .github/workflows/greenlight-ios.yml scripts/ci/greenlight_ios_preflight.sh`
- `rg -n "report-only|critical|artifact|blocking" docs/runbook/IOS_GREENLIGHT.md`

## Failure modes and expected behavior

| Scenario | Expected behavior |
| --- | --- |
| iOS changes in PR | Greenlight workflow runs, report uploaded |
| docs-only PR | Greenlight workflow does not run |
| greenlight install failure | Job fails (explicit error) |
| greenlight execution error | Job fails (no error masking) |
| report-only with findings | Job succeeds, findings visible in summary + artifact |
| future blocking mode + critical findings | Job fails deterministically |

## Security guardrails

- Pinned tool version via `GREENLIGHT_VERSION=v0.1.0`.
- No `|| true` in execution path.
- JSON report kept as artifact; no raw key material printed by script.
- Scope isolated to iOS workflow; backend quality gates remain unchanged.

## Definition of Done (P0)

- [x] Separate iOS workflow added with path scoping.
- [x] `greenlight preflight` runs in CI and outputs JSON.
- [x] Report uploaded as artifact.
- [x] Report-only mode documented in runbook.
- [x] No backend/runtime contracts changed.
