# PR-491: Quick Summary

## Status: ✅ Ready to Open

**Branch:** `chore/pr-491-move-core-tests`  
**Type:** Test-only reorganization  
**Files Changed:** 2 (test files only)

---

## What Changed

- ✅ Moved `TestBMIBreakpointsFallback` and `TestBMIUpperFor` from `test_bmi_visualization_spec.py` to `test_bmi_engine_helpers.py`
- ✅ Removed core-internal tests from visualization spec file
- ✅ All tests pass
- ✅ No production code changes

---

## Context

- **Follow-up to PR-490B** (where tests were temporarily colocated for diff-cover visibility)
- **Addresses CodeRabbit nitpick** about test location
- **Improves test discoverability** and separation of concerns

---

## PR Link

```
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/new/chore/pr-491-move-core-tests
```

---

## PR Description

Скопировать из: `docs/pr/PR_491_DESCRIPTION.md`

---

## Ready to Merge After Review

- Pure test reorganization
- No behavior changes
- All tests pass
- Coverage maintained

---

## Merge Instructions

### 1. Merge Strategy: **Squash and Merge**

**Commit Title:**
```
test: move core BMI engine helper tests
```

**Commit Body (опционально):**
```
Pure test reorganization. No production code changes.
```

### 2. Post-Merge Steps

```bash
# Update local main
git checkout main
git pull --ff-only

# Sanity check
pytest -q

# Cleanup local branch (опционально)
git branch -d chore/pr-491-move-core-tests
```

### 3. Verification

- [x] PR merged в main
- [x] Ветка удалена (если предложено GitHub)
- [x] Локальный main обновлён
- [x] Тесты проходят

