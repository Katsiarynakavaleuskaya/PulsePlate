# PR-491: Merge Instructions

## Merge Strategy: Squash and Merge

### Commit Message (для squash)

**Title:**
```
test: move core BMI engine helper tests
```

**Body (опционально):**
```
Pure test reorganization. No production code changes.
```

---

## Post-Merge Steps

### 1. Delete Branch (если GitHub предложит)

После merge GitHub может предложить удалить ветку → **Delete branch**

### 2. Update Local Main

```bash
git checkout main
git pull --ff-only
```

### 3. Sanity Check (рекомендуется)

```bash
pytest -q
```

Ожидание: все тесты проходят ✅

### 4. Cleanup Local Branch (опционально)

```bash
git branch -d chore/pr-491-move-core-tests
```

(Если ветка уже удалена на GitHub, можно использовать `-D` для принудительного удаления)

---

## Verification

После merge проверить:

- [x] PR merged в main
- [x] Ветка удалена (если предложено)
- [x] Локальный main обновлён
- [x] Тесты проходят
- [x] Изменения видны в main (2 файла: test_bmi_engine_helpers.py, test_bmi_visualization_spec.py)

---

## Status

- ✅ PR готов к merge
- ✅ Merge strategy определена (Squash)
- ⏳ Ожидание merge на GitHub
- ⏳ Post-merge cleanup
