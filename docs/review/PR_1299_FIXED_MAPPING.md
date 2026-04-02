# PR 1299 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
Notes: Draft PR `#1299` is a narrow frontend hardening lane. Canonical session-backed entitlement truth already existed on `main`; this PR only removes shared MSW purchase/restore leakage, deletes duplicate mock artifacts, and adds regression coverage for fail-closed web paywall behavior. The post-open `qa-engineer-agent -> bug-hunter` pass returned no findings beyond the non-blocking existing `inert` jsdom warning, so remaining merge risk is limited to live current-head CI plus later bot/thread governance activity.
