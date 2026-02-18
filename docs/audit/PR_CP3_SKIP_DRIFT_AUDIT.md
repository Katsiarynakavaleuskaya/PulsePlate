# PR-P1: CP3 Skip-Drift Cleanup Audit

<!-- markdownlint-disable MD013 -->

**Status:** Skeleton audit ready (pre-implementation)
**Branch:** `feat/cp3-skip-drift-skeleton`
**Date:** 2026-02-18

---

## Scope Validation

### In scope

- CP3 skip-drift cleanup in listed test files.
- Canonical skip protocol enforcement (`feature_disabled:<key>`).
- Deterministic validation for skip mapping consistency.

### Out of scope

- Runtime/API behavior changes.
- New product features.
- Test rewrites outside CP3 bucket.

---

## Evidence Anchors (Current Baseline)

- CP3 ledger item and target files: `docs/roadmap/BACKLOG_LEDGER.md:676`
- Existing CP3 planning artifact: `docs/plan/CP3_SKIP_COVERAGE_DRIFT_PLAN.md:1`
- Existing CP3 noop audit: `docs/audit/CP3_SKIP_HEAVY_A1_NOOP_AUDIT_2026-02-16.md:1`
- Unified DB drift reference: `core/food_apis/unified_db.py:265`

---

## Recommended Execution Shape

1. Keep CP3 package strictly test-contract focused.
2. Convert drift-based skips to canonical feature keys only.
3. Add deterministic assertions for reason-key consistency.
4. Preserve CI quality gates and avoid broad refactors.

---

## Negative Scenario Modeling

| Scenario | Potential hole | Guardrail |
| --- | --- | --- |
| Ad-hoc skip reason returns | protocol drift | assert `feature_disabled:<key>` only |
| CP3 patch mutates runtime modules | unintended behavior changes | scope guard on changed files |
| Skip keys mismatch canonical manifest | brittle skip taxonomy | mapping tests for known keys |
| CP3 changes hide failures via broad skip | false confidence | assert skip counts + reason format |
| Diff-coverage falls on touched lines | merge gate failure | targeted tests plus `make verify` |

---

## Command Evidence Skeleton (to fill during implementation)

```bash
pytest -q tests/test_zero_coverage_modules.py -v
pytest -q tests/test_remaining_modules.py -v
pytest -q tests/test_final_core_coverage.py -v
pytest -q tests/test_direct_core_functions.py -v
pytest -q tests/test_quick_coverage_boost.py -v
pytest -q tests/test_repo_policy_guards.py -v
make lint
make test-fast
make verify
```

Expected completion format per command:

- exact command
- 1-3 raw output lines
- exit code

---

## Go/No-Go Criteria

- [ ] CP3 drift cleanup is scoped and deterministic.
- [ ] Canonical skip protocol is enforced in touched scope.
- [ ] No runtime behavior changes included.
- [ ] Guard + lint + verify gates pass.
- [ ] Audit evidence is complete and reproducible.
