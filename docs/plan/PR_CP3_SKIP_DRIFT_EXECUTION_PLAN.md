# PR-P1: CP3 Skip-Drift Cleanup Execution Plan

<!-- markdownlint-disable MD013 -->

**Status:** Skeleton ready (coordinator-first, implementation not started)
**Branch:** `feat/cp3-skip-drift-skeleton`
**Date:** 2026-02-18

---

## Scope

### IN

- CP3 cleanup for skip-heavy drift buckets in targeted test modules.
- Canonical skip-reason enforcement (`feature_disabled:<key>`).
- Deterministic assertions for skip mapping consistency.
- Audit/plan/pr-body docs aligned with execution.

### OUT

- Runtime feature implementation.
- API contract expansion.
- Refactors unrelated to CP3 skip drift.
- Frontend/iOS behavior changes.

---

## Coordinator-First Execution Skeleton

### Phase 1 - Scope lock and drift map

- Freeze target files and skip buckets from current ledger item.
- Build explicit mapping: test location -> canonical feature key.
- Record open questions before code changes.

### Phase 2 - Narrow CP3 implementation

- Replace ad-hoc skip reasons with canonical protocol where needed.
- Align failing drift expectations with current canonical APIs.
- Keep changes test-layer only unless bug evidence requires otherwise.

### Phase 3 - Deterministic validation

- Run target suites and guard tests.
- Verify skip output stays canonical and bounded.
- Confirm no new flaky/time-based test behavior.

### Phase 4 - Audit and PR packaging

- Fill audit evidence with command/raw output/exit code.
- Prepare PR body mapping with fixed-in-commit placeholders.
- Re-run `make verify` before merge request.

---

## Negative Scenario Matrix

| # | Failure scenario | Hole risk | Required guard |
| --- | --- | --- | --- |
| 1 | Ad-hoc skip string reintroduced | policy drift | regex assert on skip protocol |
| 2 | Drift fix changes runtime behavior | hidden regression | runtime files unchanged check |
| 3 | CP3 patch removes critical test path | false green | coverage diff on touched tests |
| 4 | Skip key mismatch with manifest | noisy CI | key mapping assertions |
| 5 | Broad refactor sneaks into CP3 PR | scope creep | PR scope guard + file list check |

---

## Minimal File Touch Plan

- `tests/test_zero_coverage_modules.py`
- `tests/test_remaining_modules.py`
- `tests/test_final_core_coverage.py`
- `tests/test_direct_core_functions.py`
- `tests/test_quick_coverage_boost.py`
- `docs/plan/PR_CP3_SKIP_DRIFT_EXECUTION_PLAN.md`
- `docs/audit/PR_CP3_SKIP_DRIFT_AUDIT.md`

---

## Deterministic Validation Commands (Skeleton)

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

---

## DoD

- [ ] CP3 target buckets are cleaned with canonical skip protocol.
- [ ] No ad-hoc skip reasons remain in touched scope.
- [ ] Deterministic tests cover drift mapping.
- [ ] Guard + lint + verify gates pass.
- [ ] Audit includes evidence anchors and raw command outputs.
