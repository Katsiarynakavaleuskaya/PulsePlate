# PR-492 Pre-Commit Checklist

## ✅ Pre-Commit Verification

### 1. Tests Pass

```bash
pytest -q tests/test_bmi_contract_visualization.py
# Expected: 7 tests pass
```

✅ **Status:** All 7 tests pass

### 2. Linter Passes

```bash
ruff check tests/test_bmi_contract_visualization.py
# Expected: All checks passed
```

✅ **Status:** All checks passed

### 3. All Tests Pass

```bash
pytest -q
# Expected: All tests pass (no regressions)
```

✅ **Status:** All tests pass

### 4. Float-Safe Comparisons

✅ **Status:** All float comparisons use `pytest.approx`:
- `ranges[0]["from"] == pytest.approx(spec["min"])`
- `ranges[-1]["to"] == pytest.approx(spec["max"])`
- `rr["from"] == pytest.approx(prev_to)`
- `spec["bmi"] == pytest.approx(spec["marker"]["value"])`

### 5. Files for PR

**Expected files:**
- `docs/bmi/visualization.md` (new)
- `tests/test_bmi_contract_visualization.py` (new)

**Optional (not in PR):**
- `docs/pr/PR_492_*.md` (planning docs, keep local or separate docs PR)

---

## 📝 Commits

### Commit 1: Documentation

```bash
git add docs/bmi/visualization.md
git commit -m "docs(bmi): add BMI visualization contract documentation"
```

### Commit 2: Contract Tests

```bash
git add tests/test_bmi_contract_visualization.py
git commit -m "test(bmi): add contract tests for visualization field"
```

---

## 🚀 Push

```bash
git push -u origin docs/pr-492-bmi-visualization-contract
```

---

## 📄 PR Description Template

```markdown
## Summary

Document BMI visualization contract and add contract tests to prevent regressions.

**Type:** Documentation + Contract Tests  
**No production code changes.**

---

## What Changed

### Added

- `docs/bmi/visualization.md` — Contract documentation with JSON examples
- `tests/test_bmi_contract_visualization.py` — Contract validation tests (7 tests)

### Changed

- None (pure documentation + tests)

---

## Why This Change

1. **iOS/Web developers need documented contract** to implement visualization
2. **Contract tests prevent regressions** when backend changes
3. **Examples speed up client development** (copy-paste ready JSON)
4. **Low risk, high value** (docs + tests, no production changes)

---

## Contract Details

- `visualization: BMIScaleV1Spec | None` field in `/api/v1/bmi/calculate` response
- `null` for groups with `category=None` (too_young, child, teen, pregnant)
- Group-specific ranges:
  - Adult: normal 18.5 → 25.0
  - Athlete: normal 18.5 → 27.0
  - Elderly: underweight 0 → 17.5, normal 17.5 → 26.0
- Fallback: endpoint returns `200` with `visualization: null` if builder fails

---

## Testing

- ✅ Contract tests pass (7 tests)
- ✅ All existing tests pass
- ✅ No production code changes
- ✅ Float-safe comparisons (pytest.approx)

---

## Related

- Follow-up to PR-490B (BMI visualization group-aware)
- Enables Sprint C.2 (iOS BMI bootstrap)
```

---

## ✅ Final Status

- ✅ Tests pass
- ✅ Linter passes
- ✅ Float-safe comparisons
- ✅ Only docs + tests (no production changes)
- ✅ Ready to commit and push

