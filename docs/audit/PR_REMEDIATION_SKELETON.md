# PR: Backend P0 Remediation — Restore BMI Engine Invariant

**Type:** Backend Remediation
**Priority:** P0 (Critical — Unblocks Frontend Work)
**Status:** Ready for Implementation
**Strategy:** Strategy B (cherry-pick guards from PR #534, merge green)
**Depends on:** Guard Policy PR #534 (Draft, will be superseded by this PR)

**⚠️ OUT OF SCOPE (Explicitly — Hard Boundary):**

### Product Layer (Explicitly Excluded)
- ❌ Soft paywall implementation
- ❌ FREE/PRO UX changes
- ❌ Product marketing copy
- ❌ Frontend components
- ❌ Billing integration

### VIP Tier Features (Explicitly Excluded)
- ❌ Personalized nutrition menus
- ❌ Store-based product selection
- ❌ Diet and cuisine preferences
- ❌ Goal-driven meal optimization
- ❌ Restaurant integration
- ❌ Advanced personalization logic

**Rationale:**
- This PR is **architectural/technical** — restoring backend invariants
- Product layer changes belong in separate PRs after backend is stable
- VIP tier requires separate product audit and design
- Menu automation and product selection are distinct from BMI calculation engine

**What IS in scope:**
- ✅ Restoring One BMI Engine invariant
- ✅ Consolidating BMI extras (Free/Pro tiers in one canonical module)
- ✅ Explicit product tier documentation in code (Free vs Pro functions)
- ✅ Removing legacy dependencies
- ✅ Fixing metadata

**Key principle:**
> **Normalization and documentation of existing tiers = OK**
> **New features or VIP automation = NOT OK**

---

## 🎯 What

Restores architectural invariant:
> *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

**This PR fixes the violations documented by guard tests.**

---

## Why

**Root Cause:** Architectural violations (legacy dependency + duplicates) cause non-deterministic BMI results.

**Impact:** System cannot be diagnosed or fixed reliably until invariant is restored.

**See:**
- `docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md` — Root cause analysis
- `docs/audit/BACKEND_P0_REMEDIATION_PLAN.md` — Detailed remediation plan
- `docs/audit/DECISION_LOG_BMI_UNDEFINED.md` — Decision log
- `docs/audit/PR_REMEDIATION_EXACT_PATCHES.md` — Copy-paste ready code patches

---

## Changes

### 📋 Quick Reference Table: File → Change → Guard Effect

| File | Line | Change | Guard Test | Expected Result |
|------|------|--------|------------|-----------------|
| `core/bmi/risk.py` | 17 | Replace `from bmi_core import compute_wht_ratio` → `from core.bmi.engine import _compute_wht_ratio` | `test_no_legacy_bmi_imports_in_core_bmi` | ✅ PASS |
| `core/bmi/risk.py` | ~50-60 | Update call: `compute_wht_ratio(...)` → `_compute_wht_ratio(...)` | (same) | ✅ PASS |
| `core/bmi/engine.py` | 2-9 | Update docstring: remove "stub" comment, mark as canonical | `test_engine_metadata_accuracy` | ✅ PASS |
| `core/bmi_extras*.py` | - | Consolidate 3 files → 1 canonical module | `test_single_canonical_extras_module` | ✅ PASS |
| `app/routers/bmi_pro.py` | 16-17 | Remove local `calc_bmi()`, import `_compute_bmi` from engine | `test_no_bmi_calculation_outside_engine` | ✅ PASS |
| `app/routers/bmi_pro.py` | 49 | Update call: `calc_bmi(...)` → `_compute_bmi(...)` | (same) | ✅ PASS |
| `core/nutrition_bayesian_analyzer.py` | 377 | Replace `bmi = weight / (height_m**2)` → `_compute_bmi(weight, height_m)` | `test_no_bmi_calculation_outside_engine` | ✅ PASS |

---

### Action 1: Remove Legacy Dependency (P0-Critical)

**File:** `core/bmi/risk.py`

**Line 17 — Import change:**
```python
# BEFORE
from bmi_core import compute_wht_ratio

# AFTER
from core.bmi.engine import _compute_wht_ratio
```

**Lines ~50-60 — Function call update:**
Find all usages of `compute_wht_ratio(...)` and replace with `_compute_wht_ratio(...)`.

**Verification:**
```bash
# After change, this guard should pass
pytest tests/test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi -v
```

**Guard that will turn green:** `test_no_legacy_bmi_imports_in_core_bmi`

---

### Action 2: Consolidate BMI Extras Modules (P0-Critical)

**Files:**
- `core/bmi_extras.py`
- `core/bmi_extras_pro.py`
- `core/bmi_extras_simple.py`

**Current state:** 3 duplicate modules with identical function signatures.

**Decision:** Consolidate into single canonical module.

**Steps:**

1. **Analyze usage:**
   ```bash
   grep -r "from core.bmi_extras" --include="*.py"
   grep -r "import.*bmi_extras" --include="*.py"
   ```

2. **Choose canonical module:**
   - Recommended: `core/bmi/extras.py` (move to `core/bmi/` subdirectory for consistency)
   - Alternative: Keep `core/bmi_extras.py` as canonical, delete others

3. **Consolidate:**
   - Merge all functions into canonical module
   - Ensure no behavior changes (signature-compatible)
   - Update all imports across codebase

4. **Remove duplicates:**
   - Delete `core/bmi_extras_pro.py`
   - Delete `core/bmi_extras_simple.py`
   - (Or keep as thin aliases if needed for backward compatibility — but document clearly)

**Verification:**
```bash
# After change, this guard should pass
pytest tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module -v
```

**Guard that will turn green:** `test_single_canonical_extras_module`

---

### Action 3: Fix Engine Metadata (P0-High)

**File:** `core/bmi/engine.py`

**Lines 2-9 — Docstring update:**
```python
# BEFORE
"""
BMI Engine Orchestrator

RU: Единый engine для расчета BMI (canonical source of truth).
EN: Unified engine for BMI calculation (canonical source of truth).

This module will be fully implemented in PR-455.
Currently provides a stub implementation for development/testing.
"""

# AFTER
"""
BMI Engine Orchestrator

RU: Единый engine для расчета BMI (canonical source of truth).
EN: Unified engine for BMI calculation (canonical source of truth).

Canonical implementation: all BMI calculations must use this module.
No other calculation paths are allowed.
"""
```

**Verification:**
```bash
# After change, this guard should pass
pytest tests/test_bmi_canonical_guard.py::test_engine_metadata_accuracy -v
```

**Guard that will turn green:** `test_engine_metadata_accuracy`

---

### Action 4: Remove BMI Calculation Outside Engine (P0-Critical)

**File 1: `app/routers/bmi_pro.py`**

**Line 16-17 — Remove local function:**
```python
# BEFORE
def calc_bmi(weight_kg: float, height_m: float) -> float:
    return round(weight_kg / (height_m**2), 1)
```

**Line 9 (or top of file) — Add import:**
```python
# AFTER (add to imports section)
from core.bmi.engine import _compute_bmi
```

**Line 49 — Update function call:**
```python
# BEFORE
bmi_val = calc_bmi(req.weight_kg, req.height_cm / 100.0)

# AFTER
bmi_val = _compute_bmi(req.weight_kg, req.height_cm / 100.0)
```

**File 2: `core/nutrition_bayesian_analyzer.py`**

**Line 377 — Replace direct calculation:**
```python
# BEFORE
bmi = weight / (height_m**2)

# AFTER
from core.bmi.engine import _compute_bmi  # (add to imports at top)

# ... later in code ...
bmi = _compute_bmi(weight, height_m)
```

**Verification:**
```bash
# After change, this guard should pass
pytest tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine -v
```

**Guard that will turn green:** `test_no_bmi_calculation_outside_engine`

---

## Implementation Order

### Phase 1: Critical Path (Must Do First)

1. **Action 1: Remove Legacy Dependency** (1-2 hours)
   - **Guard turns green:** `test_no_legacy_bmi_imports_in_core_bmi`
   - **Risk:** Low (signature compatible)

2. **Action 3: Fix Metadata** (30 minutes)
   - **Guard turns green:** `test_engine_metadata_accuracy`
   - **Risk:** None

### Phase 2: Consolidation

3. **Action 2: Consolidate Extras** (2-4 hours)
   - **Guard turns green:** `test_single_canonical_extras_module`
   - **Risk:** Medium (need to analyze usage)

### Phase 3: Calculation Paths

4. **Action 4: Remove Outside Calculations** (1-2 hours)
   - **Guard turns green:** `test_no_bmi_calculation_outside_engine`
   - **Risk:** Low (straightforward replacement)

**Total Estimated Time:** 5-9 hours

---

## Guard Test Status (Before → After)

| Guard Test | Before | After | Action |
|------------|--------|-------|--------|
| `test_no_legacy_bmi_imports_in_core_bmi` | ❌ FAIL | ✅ PASS | Action 1 |
| `test_single_canonical_extras_module` | ❌ FAIL | ✅ PASS | Action 2 |
| `test_engine_metadata_accuracy` | ❌ FAIL | ✅ PASS | Action 3 |
| `test_no_bmi_calculation_outside_engine` | ❌ FAIL | ✅ PASS | Action 4 |
| `test_bmi_result_structure_consistency` | ✅ PASS | ✅ PASS | (no change) |

**Success Criteria:** All 5 guards pass after remediation.

---

## Testing

### After Each Action

```bash
# Run guard tests (should turn green one by one)
pytest tests/test_bmi_canonical_guard.py -v

# Run full test suite
make test-fast
```

### Final Verification

```bash
# All guards must pass
pytest tests/test_bmi_canonical_guard.py -v

# All tests must pass
make verify
```

---

## Definition of Done

- [ ] Action 1: Legacy dependency removed
- [ ] Action 2: Extras modules consolidated
- [ ] Action 3: Engine metadata fixed
- [ ] Action 4: Outside calculations removed
- [ ] All 5 guard tests pass
- [ ] All existing tests pass
- [ ] `make verify` passes
- [ ] No regressions

---

## Commit Strategy

### Option 1: Sequential Commits (Recommended) ✅

**Commit 1:** `fix(core): remove legacy BMI dependency from risk path (P0)`
- **Action 1 only** (remove `bmi_core` import, use `_compute_wht_ratio` from engine)
- **Guard turns green:** `test_no_legacy_bmi_imports_in_core_bmi`
- **Verification:** `pytest tests/test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi -v`

**Commit 2:** `docs(bmi): mark core/bmi/engine as canonical (remove stub metadata)`
- **Action 3 only** (update docstring, remove "stub" comment)
- **Guard turns green:** `test_engine_metadata_accuracy`
- **Verification:** `pytest tests/test_bmi_canonical_guard.py::test_engine_metadata_accuracy -v`

**Commit 3:** `refactor(bmi): consolidate bmi_extras modules into single canonical module (P0)`
- **Action 2 only** (consolidate 3 files → 1 canonical)
- **Guard turns green:** `test_single_canonical_extras_module`
- **Verification:** `pytest tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module -v`

**Commit 4:** `fix(bmi): delegate pro bmi route to canonical engine (no local calc)`
- **Action 4 only** (remove local `calc_bmi` in `bmi_pro.py`, fix `nutrition_bayesian_analyzer.py`)
- **Guard turns green:** `test_no_bmi_calculation_outside_engine`
- **Verification:** `pytest tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine -v`

**Pros:**
- Clear progression (guards turn green one by one)
- Easy to review
- Easy to revert if needed
- Each commit is independently verifiable

---

### Option 2: Single Commit

**Commit:** `fix(backend): restore One BMI Engine invariant (P0)`
- All 4 actions
- All guards turn green together

**Pros:**
- Atomic fix
- Single commit

**Cons:**
- Harder to review
- Harder to revert

---

## Risks

### Low Risk

- **Action 1:** Signature compatible, well-tested
- **Action 3:** Documentation only
- **Action 4:** Straightforward replacement

### Medium Risk

- **Action 2:** Need to analyze all usages, may have tier-specific logic

### Mitigation

- Run comprehensive tests after each action
- Verify guard tests turn green incrementally
- Use sequential commits for easier rollback

---

## Related PRs

**Strategy:** Strategy B (Safe Standard)
- **PR #534 (Guard Policy):** Draft, expected red
- **This PR:** Cherry-picks guard commit from #534, applies fixes, merges green
- **After merge:** Close PR #534 as "Superseded by PR-XXX"

**Cherry-pick command:**
```bash
git cherry-pick 7b2be9e53fc294874ad20e2e13395ec61ed2c102
```

**Unblocks:**
- Frontend Audit (PR-525)
- Product layer PR (FREE → PRO soft paywall)
- Any downstream work requiring deterministic backend

**Next PR (After Remediation):**
- `feat(product): add FREE → PRO contract and soft paywall (wellness)`
- See: `docs/audit/PR_PRODUCT_SOFT_PAYWALL_SKELETON.md`

---

## Success Criteria

**Backend is "deterministic single source of truth" when:**

1. ✅ Only one calculation path exists
2. ✅ All modules use canonical engine
3. ✅ Result structure is always consistent
4. ✅ All guard tests pass
5. ✅ No legacy dependencies

---

**Last updated:** 2026-01-15
**Status:** Ready for implementation after Guard Policy PR
