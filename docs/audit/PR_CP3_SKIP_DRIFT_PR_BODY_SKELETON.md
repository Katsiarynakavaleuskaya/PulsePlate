# PR Body Skeleton: CP3 Skip-Drift Cleanup

## Summary

- Execute CP3 follow-up for skip-heavy drift cleanup.
- Standardize skip protocol to `feature_disabled:<key>`.
- Add deterministic assertions for skip-key consistency.
- Keep scope strict: test contracts + docs only.
- Evidence anchors: `docs/roadmap/BACKLOG_LEDGER.md:676`,
  `core/food_apis/unified_db.py:265`.

## Scope

### IN

- CP3 target test files in ledger item.
- Canonical skip-reason protocol enforcement.
- Audit/plan evidence updates.

### OUT

- Runtime/API behavior changes.
- Feature additions.
- Frontend/iOS changes.

## Risks / Mitigations

- Policy drift in skip reasons -> enforce canonical key format.
- Scope creep into runtime modules -> changed-files guard in review.
- False green from broad skips -> deterministic assertions on reasons.
- Diff-coverage regression -> targeted test matrix + `make verify`.

## Test Plan

- `pytest -q tests/test_zero_coverage_modules.py -v`
- `pytest -q tests/test_remaining_modules.py -v`
- `pytest -q tests/test_final_core_coverage.py -v`
- `pytest -q tests/test_direct_core_functions.py -v`
- `pytest -q tests/test_quick_coverage_boost.py -v`
- `pytest -q tests/test_repo_policy_guards.py -v`
- `make lint`
- `make test-fast`
- `make verify`

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

- [ ] CP3 skip mapping cleanup by file
- [ ] Canonical `feature_disabled:<key>` enforcement
- [ ] Deterministic assertion coverage for skip protocol
- [ ] Docs updates (plan/audit/evidence)

## Deferred / Follow-ups

- [ ] Optional cleanup for non-CP3 skip suites (separate package)
- [ ] Additional manifest hardening if new feature keys appear
