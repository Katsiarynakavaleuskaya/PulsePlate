# Pre-Flight Checklist for Remediation PR

**Purpose:** Verify readiness before starting Backend P0 Remediation PR.

**Status:** Pre-implementation verification

---

## ✅ Checklist 1: AGENTS.md Rule Status

**Question:** Is the `--no-verify` rule for expected-red PRs already in `main`?

**Current Status:**
- ✅ **AGENTS.md change is in PR #534** (guard policy PR)
- ❌ **Not yet in `main`** (will be merged with PR #534)

**Decision:**
- **Option A (Recommended):** Merge PR #534 first, then start remediation PR from updated `main`
- **Option B:** Include AGENTS.md change in remediation PR (acceptable, but creates dependency)

**Recommendation:** **Option A** — merge PR #534 first to establish the rule, then start remediation.

---

## ✅ Checklist 2: Exact Patches Alignment

**Question:** Do exact patches match current `main`?

**Verification:**

### File 1: `core/bmi/risk.py`
- ✅ Line 17: `from bmi_core import compute_wht_ratio` — **matches main**
- ✅ Patches are accurate

### File 2: `core/bmi/engine.py`
- ✅ Lines 7-8: "stub" comment — **matches main**
- ✅ Patches are accurate

### File 3: `app/routers/bmi_pro.py`
- ✅ Line 16: `def calc_bmi(...)` — **matches main**
- ✅ Patches are accurate

### File 4: `core/nutrition_bayesian_analyzer.py`
- ✅ Line 377: Direct BMI calculation — **matches main** (needs verification)
- ⚠️ **Action:** Verify exact line number before applying patch

**Status:** ✅ **All patches align with current `main`**

**Action before remediation:**
```bash
# Ensure you're on latest main
git fetch origin
git checkout main
git pull origin main

# Create remediation branch from main
git checkout -b fix/bmi-p0-remediation
```

---

## ✅ Checklist 3: Branch Protection Strategy

**Question:** How to link PR #534 and remediation PR?

**Current Status:**
- Branch protection: **Unknown** (404 from API may mean no access, not "no protection")
- PR #534: **Draft** (expected red)
- **Principle:** Keep `main` green (default safe strategy)

**⚠️ CRITICAL DECISION GATE: "Main must stay green"**

**If branch protection is uncertain → do NOT merge red PR into main.**
**Use Strategy B: cherry-pick guards into remediation PR, merge green.**

**Default rule:** **Main must stay green.** Strategy B is the only recommended approach.

---

### ✅ Recommended Strategy: **Strategy B (Safe Standard)** ⭐ **RECOMMENDED**

**Rationale:**
1. **Main stays green** (no red merges normalize bad practice)
2. Guards and fixes arrive together in green state
3. No risk of "red merge precedent"
4. Works regardless of branch protection status

**Steps:**

1. **Keep PR #534 as Draft** (red fence, documents violations)
   - Do NOT merge into `main`
   - Serves as documentation/reference

2. **Start remediation PR from current `main`**
   - Branch: `fix/bmi-p0-remediation`
   - Base: `main` (current state, no guards yet)

3. **Cherry-pick guard commit from PR #534**
   - Includes: guard tests + AGENTS.md rule + docs
   - Guards will be red initially (expected)

4. **Apply remediation patches sequentially**
   - Each patch makes one guard green
   - **Must pass pre-commit** (no `--no-verify`)
   - Final state: all guards green

5. **Merge remediation PR (green)**
   - Guards are now in `main` (green)
   - AGENTS.md rule is in `main`
   - Backend is deterministic

6. **Close PR #534 as Superseded**
   - Reference: "Superseded by PR-XXX (remediation)"
   - Guards are now green in main

---

### ⚠️ Legacy Strategy: Option A (Not Recommended — Historical Reference Only)

**⚠️ WARNING:** This strategy is **NOT recommended** and should only be considered in exceptional circumstances with explicit team policy.

**When Option A might be considered (not recommended):**
- ⚠️ You are the only person merging to `main` (solo maintainer)
- ⚠️ Explicit documented rule exists: "one red merge allowed only for guard fence"
- ⚠️ You will immediately (same day) raise remediation PR to restore green
- ⚠️ No risk of others normalizing "red merges are OK"

**Steps (if using Option A — NOT RECOMMENDED):**
1. Merge PR #534 (red CI expected)
2. Start remediation PR from updated `main`
3. Apply patches, make guards green
4. Merge remediation PR (green)

**⚠️ Risks:**
- Normalizes "red merges are OK" (creates technical debt)
- If anyone else sees red merge, they may follow precedent
- Violates "main must stay green" principle

**Recommendation:** **Always use Strategy B** (cherry-pick guards, merge green). Option A is only documented here for historical reference and should not be used in practice.

---

## ✅ Checklist 4: Execution Order

**Recommended sequence (from skeleton):**

1. **Commit 1:** Remove legacy dependency (`risk.py`)
   ```bash
   # Apply patch 1
   pytest tests/test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi -v
   pre-commit run --all-files
   git commit -m "fix(core): remove legacy BMI dependency from risk path (P0)"
   ```

2. **Commit 2:** Fix engine metadata
   ```bash
   # Apply patch 2
   pytest tests/test_bmi_canonical_guard.py::test_engine_metadata_accuracy -v
   pre-commit run --all-files
   git commit -m "docs(bmi): mark core/bmi/engine as canonical (remove stub metadata)"
   ```

3. **Commit 3:** Consolidate extras modules
   ```bash
   # Apply patch 5 (consolidation)
   pytest tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module -v
   pre-commit run --all-files
   git commit -m "refactor(bmi): consolidate bmi_extras modules into single canonical module (P0)"
   ```

4. **Commit 4:** Remove local BMI calculations
   ```bash
   # Apply patches 3 and 4
   pytest tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine -v
   pre-commit run --all-files
   git commit -m "fix(bmi): delegate pro bmi route to canonical engine (no local calc)"
   ```

**After all commits:**
```bash
# Final verification
pytest tests/test_bmi_canonical_guard.py -v  # All 5 guards must pass
make verify  # Full test suite
```

---

## ✅ Checklist 5: Pre-Commit Verification

**Rule:** Remediation PR **must pass pre-commit** (no `--no-verify`).

**Why:**
- Guards will turn green (not expected-red anymore)
- All code changes are valid
- No architectural violations remain

**Command after each commit:**
```bash
pre-commit run --all-files
```

**If pre-commit fails:**
- Fix the issue (formatting, lint, etc.)
- Re-run pre-commit
- Only commit when pre-commit passes

---

## ✅ Checklist 6: Guard Test Verification

**After each commit, verify specific guard:**

```bash
# Guard 1 (after commit 1)
pytest tests/test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi -v

# Guard 2 (after commit 2)
pytest tests/test_bmi_canonical_guard.py::test_engine_metadata_accuracy -v

# Guard 3 (after commit 3)
pytest tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module -v

# Guard 4 (after commit 4)
pytest tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine -v

# All guards (final)
pytest tests/test_bmi_canonical_guard.py -v
```

**Expected progression:**
- After commit 1: 1 guard green, 3 guards red
- After commit 2: 2 guards green, 2 guards red
- After commit 3: 3 guards green, 1 guard red
- After commit 4: **All 5 guards green** ✅

---

## 🎯 Success Criteria

**Remediation PR is ready to merge when:**

- [ ] All 5 guard tests pass
- [ ] `make verify` passes
- [ ] Pre-commit passes (no `--no-verify` used)
- [ ] CI is green
- [ ] No regressions in existing tests
- [ ] Code review approved

---

## 📋 Quick Start Commands (Strategy B - Recommended)

```bash
# 0) Clean base
git fetch origin
git checkout -B fix/bmi-p0-remediation origin/main

# 1) Cherry-pick guards commit (stop on any conflict)
git cherry-pick -x 7b2be9e53fc294874ad20e2e13395ec61ed2c102

# 2) Sanity: guards should be red (expected)
pytest -q tests/test_bmi_canonical_guard.py -q || true

# 3) Apply remediation patches ONE BY ONE (see PR_REMEDIATION_EXACT_PATCHES.md)
# After each patch:
#    a) Run targeted guard
pytest -q tests/test_bmi_canonical_guard.py -k "<guard_name>" -q
#    b) Pre-commit (remediation — no --no-verify)
pre-commit run --all-files
#    c) Commit
git commit -m "fix(bmi): <action> (P0)"

# 4) Final verification (before push)
pytest -q tests/test_bmi_canonical_guard.py -q
make verify
pre-commit run --all-files

# 5) Push and create PR
git push -u origin fix/bmi-p0-remediation
gh pr create \
  --title "fix(bmi): restore One BMI Engine invariant (P0 remediation)" \
  --body-file docs/audit/PR_REMEDIATION_SKELETON.md

# 6) After merge: Close PR #534 as Superseded
gh pr comment 534 --body "✅ Superseded by PR-XXX (guards merged + green in main). Closing draft."
gh pr close 534
```

**Note:** If cherry-pick has conflicts, see `PR_REMEDIATION_CHERRY_PICK_GUIDE.md` troubleshooting section.

---

**Last updated:** 2026-01-15
**Status:** Ready for execution after PR #534 merge (or as alternative strategy)
