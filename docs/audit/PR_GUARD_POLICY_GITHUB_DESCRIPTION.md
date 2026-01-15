# PR: Add BMI Canonical Guard Tests (Draft — Expected CI Red)

**Type:** Guard Policy Implementation
**Priority:** P0 (Critical — Blocks Remediation)
**Status:** ⚠️ **Draft (Expected CI Red — Do NOT Merge)**
**Blocks:** Backend P0 Remediation PR

---

## 🎯 What

Adds guard tests to enforce architectural invariant:
> *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

**This PR does NOT fix violations — it documents and enforces them.**

---

## ⚠️ IMPORTANT: Draft PR — Expected CI Red

- **PR Status:** Draft (not ready for merge)
- **Expected CI:** Red (guards will fail until remediation)
- **Do NOT merge** until remediation PR makes guards pass
- **Branch protection:** If branch protection requires green CI, this PR will remain Draft (by design)
- This PR is a **"red fence"** — documents violations, prevents regression

---

## Why

**Root Cause:** Architectural violation (legacy dependency + duplicates) causes non-deterministic BMI results.

**Solution Strategy:** Guards-first approach to prevent regression during remediation.

**Rationale:**
1. Root cause is proven (not hypothesis) — see root cause analysis
2. Remediation without guards = high regression risk
3. Guards turn architectural decision into enforceable rule
4. Guards will fail initially (expected) — we're setting "red fence"

**See:**
- `docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md` — Root cause analysis
- `docs/audit/BACKEND_P0_GUARD_POLICY_PROPOSAL.md` — Guard policy
- `docs/audit/DECISION_LOG_BMI_UNDEFINED.md` (Decision 9) — Guards-first approach

---

## Changes

### 1. Guard Tests (`tests/test_bmi_canonical_guard.py`)

**New file:** `tests/test_bmi_canonical_guard.py`

**Tests (5):**
1. `test_no_legacy_bmi_imports_in_core_bmi()` — No `bmi_core` imports in `core/bmi/`
2. `test_bmi_result_structure_consistency()` — `BMICalculateResult` always complete
3. `test_single_canonical_extras_module()` — Only one canonical extras module
4. `test_engine_metadata_accuracy()` — Engine docstring accurate
5. `test_no_bmi_calculation_outside_engine()` — No BMI math outside engine

**Expected Behavior:**
- ✅ Tests will **fail initially** (expected — documenting violations)
- ✅ Tests will **pass after remediation** (guards enforce invariant)

---

### 2. AGENTS.md Update

**File:** `AGENTS.md`

**Added section:** "BMI Engine Invariant (Hard Rule)"

Documents:
- Invariant definition
- Enforcement mechanism
- Point of no-return
- Links to root cause analysis

---

## ⚠️ Expected Failures (4) — Each = Remediation Checklist Item

**CI is expected to be red only because of these 4 guards. Any other failures mean regression and must be fixed in this PR.**

**Each failure below = checklist item for remediation PR:**

1. ✅ **`test_no_legacy_bmi_imports_in_core_bmi`** — FAILED
   - **Violation:** `core/bmi/risk.py:17` imports from `bmi_core` (legacy)
   - **Impact:** Creates non-deterministic calculation path
   - **Fix:** Use `core.bmi.engine._compute_wht_ratio` instead

2. ✅ **`test_single_canonical_extras_module`** — FAILED
   - **Violation:** 3 duplicate modules (`bmi_extras.py`, `bmi_extras_pro.py`, `bmi_extras_simple.py`)
   - **Impact:** Creates ambiguity in code paths, conditional data gaps
   - **Fix:** Consolidate into single canonical module

3. ✅ **`test_engine_metadata_accuracy`** — FAILED
   - **Violation:** Engine marked as "stub" but functionally complete
   - **Impact:** Encourages bypassing canonical path, architectural drift
   - **Fix:** Update docstring to reflect canonical status

4. ✅ **`test_no_bmi_calculation_outside_engine`** — FAILED
   - **Violations:**
     - `app/routers/bmi_pro.py:16` — local `calc_bmi` helper
     - `core/nutrition_bayesian_analyzer.py:377` — direct BMI calculation
   - **Impact:** Multiple calculation paths, inconsistency
   - **Fix:** Replace with `core.bmi.engine._compute_bmi` or `calculate_bmi_result`

**Expected Pass (1):**

5. ✅ **`test_bmi_result_structure_consistency`** — PASSED
   - Result structure is consistent (good sign)

**See:** `docs/audit/PR_GUARD_POLICY_LOCAL_TEST_RESULTS.md` for detailed results.

---

### After Remediation (Future State)

All 5 tests should pass:
- ✅ No legacy imports
- ✅ Single canonical extras module
- ✅ Accurate metadata
- ✅ No BMI calculation outside engine
- ✅ Consistent result structure

---

## Testing

### Local Testing

```bash
# Run guard tests (will fail initially)
pytest tests/test_bmi_canonical_guard.py -v

# Expected: 4 failures, 1 pass (documenting violations)
```

**Results:** See `docs/audit/PR_GUARD_POLICY_LOCAL_TEST_RESULTS.md`

---

## Definition of Done

- [x] `tests/test_bmi_canonical_guard.py` created with all 5 tests
- [x] Tests run locally (failures expected and verified)
- [x] `AGENTS.md` updated with invariant section
- [ ] CI runs guard tests
- [ ] CI fails (expected — documents violation)
- [ ] PR marked as **Draft**
- [ ] PR description explains "guards-first" approach
- [ ] PR description explicitly states: "Expected CI red, do not merge"
- [ ] PR links to root cause analysis
- [ ] No false positives (guards fail only for expected violations)

---

## Related PRs

**Blocks:**
- Backend P0 Remediation PR (must come after guards)

**Follow-up:**
- Backend P0 Remediation (will make guards pass)
- Frontend Audit (only after remediation)

---

## Security Notes

- Guard tests are **read-only** (AST/regex scan, no code execution)
- No network calls
- No file modifications
- Safe to run in CI

---

## Marketing & GTM

This PR demonstrates **engineering maturity**:
- We enforce architectural invariants in CI
- We prevent regression through automated guards
- We document violations before fixing them

This increases trust in the product (especially important for health/wellness domain).

---

**Last updated:** 2026-01-15
**Status:** Ready for Draft PR
