# PR-492: Post-Push Checklist

## ✅ Push Successful

```bash
git push -u origin docs/pr-492-bmi-visualization-contract
# ✅ Success: branch pushed to remote
```

**PR URL:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/new/docs/pr-492-bmi-visualization-contract

---

## 📝 PR Setup (3 Quick Steps)

### 1. Title

**Recommended:**
```
docs(bmi): document visualization contract and add contract tests
```

**Alternative (shorter):**
```
docs/test: BMI visualization contract + contract tests
```

### 2. Labels (if using)

- `docs`
- `tests`
- `bmi`
- `contract`
- `no-prod-change`

### 3. Merge Strategy

**Recommended:** **Squash and merge**

**Commit title (after squash):**
```
docs(bmi): document visualization contract and add contract tests
```

---

## 🧪 CI Checks to Monitor

After opening PR, check:

1. **Test job** — should pass (all 7 contract tests + existing tests)
2. **Coverage/diff-cover** — should be clean (no new uncovered lines)
3. **Linter** — should pass (ruff, black already formatted)

---

## 📄 PR Description (Copy-Paste Ready)

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

## ✅ Status

- [x] Push successful
- [ ] Open PR on GitHub
- [ ] Set title and labels
- [ ] Monitor CI checks
- [ ] Ready for review

**Next:** Open PR and monitor CI! 🚀

