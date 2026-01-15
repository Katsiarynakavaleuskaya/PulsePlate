# Backend P0 Guard Policy Proposal

**Date:** 2026-01-15
**Purpose:** Prevent regression of "One BMI Engine" invariant
**Context:** Root Cause Analysis identified architectural violation

---

## 🎯 Policy Goal

**Prevent regression of architectural invariant:**
> *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

---

## 📋 Proposed Guards

### Guard 1: No Legacy BMI Imports

**Rule:** `core/bmi/` modules must not import from `bmi_core.py` (legacy)

**Implementation:**
```python
# tests/test_bmi_canonical_guard.py

def test_no_legacy_bmi_imports_in_core_bmi():
    """Guard: core/bmi/ must not import from bmi_core."""
    import ast
    import os
    from pathlib import Path

    core_bmi_dir = Path("core/bmi")
    violations = []

    for py_file in core_bmi_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        content = py_file.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "bmi_core":
                    violations.append((str(py_file), node.lineno))

    assert not violations, (
        f"Legacy bmi_core imports found in core/bmi/: {violations}"
    )
```

**Enforcement:**
- Run in CI
- Fail on violation
- Document in `AGENTS.md`

---

### Guard 2: BMI Result Structure Consistency

**Rule:** `BMICalculateResult` must always have all required fields

**Implementation:**
```python
# tests/test_bmi_canonical_guard.py

def test_bmi_result_structure_consistency():
    """Guard: BMICalculateResult must always have all fields."""
    from core.bmi.engine import calculate_bmi_result, BMICalculateResult

    # Test with various inputs
    test_cases = [
        {"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male",
         "pregnant": False, "athlete": False, "waist_cm": None, "lang": "en"},
        {"weight_kg": 65, "height_cm": 165, "age": 25, "gender": "female",
         "pregnant": True, "athlete": False, "waist_cm": 80, "lang": "ru"},
        # ... more test cases
    ]

    for case in test_cases:
        result = calculate_bmi_result(**case)

        # Verify all fields present
        assert hasattr(result, "bmi"), "BMI field missing"
        assert hasattr(result, "category"), "Category field missing"
        assert hasattr(result, "group"), "Group field missing"
        # ... check all fields

        # Verify no None for required fields
        assert result.bmi is not None, "BMI is None"
        assert result.group is not None, "Group is None"
        # ... check required fields
```

**Enforcement:**
- Run in CI
- Fail on violation
- Property-based testing

---

### Guard 3: Single Extras Module (or Clear Purpose)

**Rule:** Only one canonical extras module, or clear documented purpose for each

**Implementation:**
```python
# tests/test_bmi_canonical_guard.py

def test_single_canonical_extras_module():
    """Guard: Only one canonical extras module exists."""
    from pathlib import Path

    extras_modules = list(Path("core").glob("bmi_extras*.py"))

    if len(extras_modules) > 1:
        # Check if purpose is documented
        for module in extras_modules:
            content = module.read_text()
            if "canonical" not in content.lower() and "purpose" not in content.lower():
                pytest.fail(
                    f"Multiple extras modules found without clear purpose: {extras_modules}"
                )
```

**Enforcement:**
- Run in CI
- Warn on multiple modules without documentation
- Fail if no canonical marked

---

### Guard 4: Engine Metadata Accuracy

**Rule:** Engine docstring must accurately reflect implementation status

**Implementation:**
```python
# tests/test_bmi_canonical_guard.py

def test_engine_metadata_accuracy():
    """Guard: Engine docstring must not say 'stub' if implementation is complete."""
    from core.bmi.engine import calculate_bmi_result

    # If engine is functional, docstring should not say "stub"
    docstring = calculate_bmi_result.__doc__ or ""
    module_doc = __import__("core.bmi.engine", fromlist=[""]).__doc__ or ""

    # Check if implementation is complete
    # (This is a heuristic - may need manual verification)
    if "stub" in module_doc.lower() or "stub" in docstring.lower():
        # Verify if it's actually a stub
        # If not, fail
        pytest.fail("Engine marked as stub but appears functional")
```

**Enforcement:**
- Run in CI
- Warn on metadata mismatch
- Manual verification may be needed

---

## 🔧 Integration with Existing Guards

### Extend `tests/test_no_bmi_math_outside_core.py`

**Current guard:** No BMI math outside `core/bmi/`

**Extension:** Add check for legacy imports

```python
def test_no_legacy_bmi_imports():
    """Guard: No imports from bmi_core in core/bmi/."""
    # Implementation from Guard 1
    pass
```

---

## 📝 Policy Documentation

### Add to `AGENTS.md`

**Section:** "BMI Engine Invariant (Hard Rule)"

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

## 🎯 Implementation Plan

### Phase 1: Create Guard Tests

1. Create `tests/test_bmi_canonical_guard.py`
2. Implement all 4 guards
3. Run locally to verify

**Time:** 1-2 hours

---

### Phase 2: Integrate with CI

1. Add guard tests to CI pipeline
2. Ensure tests run on every PR
3. Fail on violation

**Time:** 30 minutes

---

### Phase 3: Document Policy

1. Add section to `AGENTS.md`
2. Update `core/AGENTS.md` if needed
3. Link to root cause analysis

**Time:** 30 minutes

---

## ✅ Verification

### Guard Test Checklist

- [ ] Guard 1: No legacy imports — implemented
- [ ] Guard 2: Result structure consistency — implemented
- [ ] Guard 3: Single extras module — implemented
- [ ] Guard 4: Metadata accuracy — implemented
- [ ] All guards run in CI
- [ ] CI fails on violation
- [ ] Policy documented in `AGENTS.md`

---

## 🚨 Risk Assessment

### Low Risk

- Guard tests are read-only (no code changes)
- Can be added incrementally
- Easy to disable if needed

### Mitigation

- Start with warnings, not failures
- Gradually increase strictness
- Document exceptions if needed

---

## 📚 Related Documents

- `ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md` — Why guards are needed
- `BACKEND_P0_REMEDIATION_PLAN.md` — What guards prevent
- `tests/test_no_bmi_math_outside_core.py` — Existing guard

---

**Last updated:** 2026-01-15
**Status:** Proposal ready for review
**Priority:** P0 (Critical — Prevention)
