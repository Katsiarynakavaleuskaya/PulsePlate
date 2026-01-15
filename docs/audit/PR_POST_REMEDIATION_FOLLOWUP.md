# Post-Remediation Follow-Up PR: Dead Code Cleanup

**Status:** Template for future PR
**Purpose:** Remove dead code, orphan tests, and unused symbols after BMI remediation
**Prerequisites:** Remediation PR merged, guards green, `make verify` green

---

## Scope

This PR focuses on **cleanup only** — removing code that became unused after remediation, without changing business logic or architecture.

---

## What to look for

### 1. Dead imports

**Search:**
```bash
ruff check --select F401 .  # unused imports
mypy --show-unused-ignores .
```

**Examples:**
- Imports from deleted modules (`bmi_extras_pro`, `bmi_extras_simple`)
- Unused helper functions that were replaced by canonical paths
- Legacy constants that are no longer referenced

**Action:** Remove or update to canonical paths.

---

### 2. Orphan tests

**Search:**
```bash
# Find tests that import deleted modules
grep -r "bmi_extras_pro\|bmi_extras_simple" tests/
# Find tests that test deleted functions
grep -r "calc_bmi\|compute_wht_ratio" tests/ | grep -v "test_bmi_canonical_guard"
```

**Examples:**
- Tests that import `bmi_extras_pro` or `bmi_extras_simple` (should use `bmi_extras`)
- Tests that verify legacy calculation paths (should verify canonical engine)
- Tests that check duplicate behavior (should check consolidated behavior)

**Action:**
- Update imports to canonical paths
- Rewrite tests to verify canonical behavior
- Remove tests that verify deleted/consolidated code (only if replacement coverage exists)

---

### 3. Unused symbols

**Search:**
```bash
vulture . --min-confidence 80  # if available
# Or manual grep for functions/classes that are never imported
```

**Examples:**
- Helper functions that were replaced by canonical engine
- Constants that are no longer used
- Type aliases that became obsolete

**Action:** Remove if truly unused, or document if intentionally kept for backward compatibility.

---

### 4. Test coverage gaps

**After cleanup, verify:**
```bash
make cov-check  # Total coverage ≥97%
make diff-cov  # Diff-coverage ≥97%
```

**Action:** If cleanup removed tests, ensure replacement coverage exists or add new tests for canonical paths.

---

## Safety checklist

Before removing anything:

- [ ] Verify symbol is truly unused (no imports, no references)
- [ ] Check if symbol is part of public API (may need deprecation)
- [ ] Ensure test coverage is maintained (replacement tests exist)
- [ ] Run full test suite (`make verify`)
- [ ] Check coverage (`make cov-check`, `make diff-cov`)

---

## PR structure

### Title
```
chore: remove dead code after BMI remediation
```

### Description
```markdown
## Dead Code Cleanup After BMI Remediation

### Goal
Remove unused code, orphan tests, and unused symbols that became obsolete after BMI remediation PR.

### Changes
- Remove unused imports (ruff F401)
- Update orphan tests to use canonical paths
- Remove unused helper functions
- Clean up obsolete constants/type aliases

### Safety
- All tests pass (`make verify`)
- Coverage maintained (`make cov-check`, `make diff-cov`)
- No public API changes

### References
- Remediation PR: #<number>
- `docs/audit/PR_REMEDIATION_SELF_AUDIT.md`
```

---

## DoD (Definition of Done)

- [ ] All unused imports removed (ruff F401 clean)
- [ ] All orphan tests updated or removed (with replacement coverage)
- [ ] All unused symbols removed (or documented if intentionally kept)
- [ ] `make verify` → PASS
- [ ] `make cov-check` → PASS (≥97%)
- [ ] `make diff-cov` → PASS (≥97%)
- [ ] No public API changes (backward compatibility maintained)

---

**Last updated:** 2026-01-15
**Status:** Template — use after remediation PR is merged
