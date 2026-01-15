# PR: Add BMI Canonical Guard Tests

**Type:** Guard Policy Implementation
**Priority:** P0 (Critical — Blocks Remediation)
**Status:** Draft (Expected CI Red)
**⚠️ DO NOT MERGE** until remediation passes guards

---

## 🎯 What

Adds guard tests to enforce architectural invariant:
> *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

**This PR does NOT fix the violation — it documents and enforces it.**

**⚠️ IMPORTANT:**
- **PR Status:** Draft (not ready for merge)
- **Expected CI:** Red (guards will fail until remediation)
- **Do NOT merge** until remediation PR makes guards pass
- This PR is a "red fence" — documents violations, prevents regression
- **Branch protection:** If branch protection requires green CI, this PR will remain Draft (by design)

**Expected Failures (4):**
1. Legacy import in `core/bmi/risk.py` → `bmi_core`
2. Duplicate extras modules (×3)
3. Engine metadata ("stub" comment)
4. BMI calculation in `app/routers/bmi_pro.py` (local helper)

Each failure = checklist item for remediation PR.

---

## Why

**Root Cause:** Architectural violation (legacy dependency + duplicates) causes non-deterministic BMI results.

**Solution Strategy:** Guards-first approach to prevent regression during remediation.

**Rationale:**
1. Root cause is proven (not hypothesis)
2. Remediation without guards = high regression risk
3. Guards turn architectural decision into enforceable rule
4. Guards will fail initially (expected) — we're setting "red fence"

**See:**
- `docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md`
- `docs/audit/BACKEND_P0_GUARD_POLICY_PROPOSAL.md`
- `docs/audit/DECISION_LOG_BMI_UNDEFINED.md` (Decision 9)

---

## Changes

### 1. Guard Tests (`tests/test_bmi_canonical_guard.py`)

**New file:** `tests/test_bmi_canonical_guard.py`

**Tests:**
1. `test_no_legacy_bmi_imports_in_core_bmi()` — No `bmi_core` imports in `core/bmi/`
2. `test_bmi_result_structure_consistency()` — `BMICalculateResult` always complete
3. `test_single_canonical_extras_module()` — Only one canonical extras module
4. `test_engine_metadata_accuracy()` — Engine docstring accurate
5. `test_no_bmi_calculation_outside_engine()` — No BMI math outside engine

**Expected Behavior:**
- ✅ Tests will **fail initially** (expected — we're documenting violation)
- ✅ Tests will **pass after remediation** (guards enforce invariant)

---

### 2. AGENTS.md Update

**File:** `AGENTS.md`

**Add section:** "BMI Engine Invariant (Hard Rule)"

```markdown
## BMI Engine Invariant (Hard Rule)

**Invariant:** *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

**Enforcement:**
- Guard tests in `tests/test_bmi_canonical_guard.py`
- CI fails on violation
- No imports from `bmi_core` in `core/bmi/`
- Only one canonical extras module (or clear purpose)

**Point of No-Return:**
> *"Until legacy dependency is removed, any downstream fixes (frontend, API contracts) are considered unreliable."*

**Related:**
- `docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md`
- `docs/audit/BACKEND_P0_REMEDIATION_PLAN.md`
```

---

### 3. CI Integration

**File:** `.github/workflows/*.yml` (or equivalent)

**Action:** Ensure guard tests run in CI

**Expected:** CI will fail until remediation is complete (expected behavior)

---

## Testing

### CI Testing

- Guard tests run in CI
- CI fails until remediation (expected)
- After remediation, CI should pass

---

## Definition of Done

- [ ] `tests/test_bmi_canonical_guard.py` created with all 5 tests
- [ ] Tests run locally (failures expected and verified)
- [ ] `AGENTS.md` updated with invariant section
- [ ] CI runs guard tests
- [ ] CI fails (expected — documents violation)
- [ ] PR marked as **Draft**
- [ ] PR description explains "guards-first" approach
- [ ] PR description explicitly states: "Expected CI red, do not merge"
- [ ] PR links to root cause analysis
- [ ] No false positives (guards fail only for expected violations)

---

## Expected Test Results

### ⚠️ Expected Failures (4) — Each = Remediation Checklist Item

**This PR documents 4 architectural violations. Each failure is a checklist item for the remediation PR.**

1. **`test_no_legacy_bmi_imports_in_core_bmi`** — FAILED
   - **Violation:** `core/bmi/risk.py:17` imports from `bmi_core` (legacy)
   - **Impact:** Creates non-deterministic calculation path
   - **Fix:** Use `core.bmi.engine._compute_wht_ratio` instead
   - **Remediation PR Action:** Remove legacy import, use canonical engine

2. **`test_single_canonical_extras_module`** — FAILED
   - **Violation:** 3 duplicate modules (`bmi_extras.py`, `bmi_extras_pro.py`, `bmi_extras_simple.py`)
   - **Impact:** Creates ambiguity in code paths, conditional data gaps
   - **Fix:** Consolidate into single canonical module
   - **Remediation PR Action:** Merge duplicates or document clear purpose for each

3. **`test_engine_metadata_accuracy`** — FAILED
   - **Violation:** Engine marked as "stub" but functionally complete
   - **Impact:** Encourages bypassing canonical path, architectural drift
   - **Fix:** Update docstring to reflect canonical status
   - **Remediation PR Action:** Remove "stub" comment, mark as canonical

4. **`test_no_bmi_calculation_outside_engine`** — FAILED
   - **Violations:**
     - `app/routers/bmi_pro.py:16` — local `calc_bmi` helper
     - `core/nutrition_bayesian_analyzer.py:377` — direct BMI calculation
   - **Impact:** Multiple calculation paths, inconsistency
   - **Fix:** Replace with `core.bmi.engine._compute_bmi` or `calculate_bmi_result`
   - **Remediation PR Action:** Use canonical engine in both locations

### ✅ Expected Pass (1)

5. **`test_bmi_result_structure_consistency`** — PASSED
   - Result structure is consistent (good sign)
   - No partial result assembly detected

**See:** `docs/audit/PR_GUARD_POLICY_LOCAL_TEST_RESULTS.md` for detailed results.

**This is expected.** Guards document violations. Each failure = checklist item for remediation PR.

---

### After Remediation (Future State)

```
tests/test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi PASSED
tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module PASSED
tests/test_bmi_canonical_guard.py::test_engine_metadata_accuracy PASSED
tests/test_bmi_canonical_guard.py::test_bmi_result_structure_consistency PASSED
tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine PASSED
```

**All guards pass** = invariant restored.

---

## Risks

### Low Risk

- Guard tests are read-only (no code changes)
- Tests document violations (expected failures)
- Can be disabled if needed (not recommended)

### Mitigation

- Clear PR description explains "guards-first" approach
- Document expected failures
- Link to root cause analysis

---

## Related PRs

**Blocks:**
- Backend P0 Remediation PR (must come after guards)

**Follow-up:**
- Backend P0 Remediation (will make guards pass)
- Frontend Audit (only after remediation)

---

## Review Checklist

- [ ] Guard tests are comprehensive
- [ ] Tests document current violations
- [ ] AGENTS.md updated
- [ ] CI integration verified
- [ ] PR description explains approach
- [ ] Links to root cause analysis

---

## Commit Message

```
feat(tests): add BMI canonical guard tests (P0)

Add guard tests to enforce architectural invariant:
"One BMI Engine must be the sole calculation path."

Guards will fail initially (expected) — documenting violations.
Guards will pass after remediation (enforcing invariant).

See: docs/audit/BACKEND_P0_GUARD_POLICY_PROPOSAL.md
See: docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md

Part of: Backend P0 Remediation (Phase 0: Guards)
```

---

**Last updated:** 2026-01-15
**Status:** Ready for implementation
