<!-- markdownlint-disable MD013 MD033 -->

# Pull Request

## Summary

P0 Growth telemetry canon — Phase 1 (docs only): core funnel semantics, event taxonomy, new metrics (Soft paywall view rate, Trial start rate, Retention D7), and dashboard baseline requirements. No code changes; Phase 2 (eventRegistry.ts alignment) after PR #825 merge.

- [x] I reviewed `docs/ENGINEERING_LESSONS.md` and followed repo policies (determinism, import hygiene, contracts).
- [x] Select one change type:
  - [ ] Bug fix
  - [ ] Feature
  - [ ] Refactor
  - [x] Docs
- [x] Linked: BACKLOG_LEDGER P0 Growth telemetry canon and KPI dashboard baseline (lines 106–123)

## Risk & Impact

- [ ] User-facing change
- [ ] Data model/migration
- [ ] Security-sensitive
- [ ] Performance-sensitive

## Test Plan

- [x] Existing analytics docs guards pass: `pytest tests/test_analytics_docs_guards.py`
- [x] Manual: verify ANALYTICS_INDEX, METRICS_CATALOG, DASHBOARD_BASELINE_REQUIREMENTS structure and links

## CI Gates

- [ ] PR tests green (lint, type, unit)
- [ ] Diff coverage ≥ 97% on changed lines (docs-only: no code lines in diff)

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness (Mandatory)

- [ ] PR is non-draft only when truly ready for merge
- [ ] All required checks are green on latest commit
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped
- [ ] Wait-window completed after latest bot/review activity

## Deferred / Follow-ups

- [x] Ledger: [P0 Growth telemetry canon](docs/roadmap/BACKLOG_LEDGER.md) — Phase 2 (anchor event taxonomy in `frontend/src/lib/telemetry/eventRegistry.ts`) after PR #825 merge.
- [ ] GitHub issue(s): —

## Notes

### For Simple Changes

- [x] No database/schema/migration changes
- [x] No public API contract changes
- [x] Covered by existing tests (analytics docs guards)
- [x] Docs-only (ANALYTICS_INDEX, METRICS_CATALOG, README, new DASHBOARD_BASELINE_REQUIREMENTS)
- [x] No performance or security impact

Rollback: revert commit; no feature flag.

<!-- markdownlint-enable MD013 MD033 -->
