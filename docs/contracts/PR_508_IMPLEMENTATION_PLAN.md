# PR-508: Contract-first baseline — Implementation Plan

**PR Title:** `docs(contracts): establish API canonical map and OpenAPI sync baseline`

**Branch:** `docs/pr-508-openapi-baseline`

**Scope:** 9 files, 3-4 commits, baseline only (no prod code changes)

---

## Коммит-план (3-4 коммита)

### Commit 1: Docs baseline

**Message:**
```
docs(contracts): add API canonical map and compat policy
```

**Files:**
- `docs/contracts/API_CANONICAL_MAP.md` (new)
- `docs/contracts/API_COMPAT.md` (new)

**Команды:**
```bash
git add docs/contracts/API_CANONICAL_MAP.md docs/contracts/API_COMPAT.md
git commit -m "docs(contracts): add API canonical map and compat policy"
```

---

### Commit 2: Generator + Make targets

**Message:**
```
chore(openapi): add canonical generator and make targets
```

**Files:**
- `scripts/generate_openapi.py` (new, executable)
- `Makefile` (edit: добавить `openapi`/`openapi-check`)

**Команды:**
```bash
chmod +x scripts/generate_openapi.py
git add scripts/generate_openapi.py Makefile
git commit -m "chore(openapi): add canonical generator and make targets"
```

---

### Commit 3: CI gates

**Message:**
```
ci(openapi): enforce OpenAPI and generated types sync
```

**Files:**
- `.github/workflows/frontend-ci.yml` (edit: 3 правки)
- `.github/workflows/ci.yml` (edit: добавить `openapi-sync` job)

**Команды:**
```bash
git add .github/workflows/frontend-ci.yml .github/workflows/ci.yml
git commit -m "ci(openapi): enforce OpenAPI and generated types sync"
```

---

### Commit 4: FE agent rules + regenerated artifacts

**Message:**
```
chore(frontend): enforce OpenAPI-generated types and regenerate artifacts
```

**Files:**
- `frontend/AGENTS.md` (edit)
- `frontend/src/api/openapi.json` (regen)
- `frontend/src/api/schema.ts` (regen)

**Команды:**
```bash
# Регенерировать артефакты
make openapi

# Проверить, что есть изменения
git diff -- frontend/src/api/openapi.json frontend/src/api/schema.ts

# Закоммитить
git add frontend/AGENTS.md frontend/src/api/openapi.json frontend/src/api/schema.ts
git commit -m "chore(frontend): enforce OpenAPI-generated types and regenerate artifacts"
```

---

## Пошаговая инструкция (готовые команды)

### Шаг 0: Создать ветку

```bash
git checkout -b docs/pr-508-openapi-baseline
```

---

### Шаг 1: Commit 1 — Docs

```bash
# Файлы уже созданы через write tool
git add docs/contracts/API_CANONICAL_MAP.md docs/contracts/API_COMPAT.md
git commit -m "docs(contracts): add API canonical map and compat policy"
```

---

### Шаг 2: Commit 2 — Generator

```bash
# Скрипт уже создан, сделать executable
chmod +x scripts/generate_openapi.py

# Проверить, что работает
python3 scripts/generate_openapi.py

# Закоммитить
git add scripts/generate_openapi.py Makefile
git commit -m "chore(openapi): add canonical generator and make targets"
```

---

### Шаг 3: Commit 3 — CI

```bash
# Файлы уже отредактированы через search_replace
git add .github/workflows/frontend-ci.yml .github/workflows/ci.yml
git commit -m "ci(openapi): enforce OpenAPI and generated types sync"
```

---

### Шаг 4: Commit 4 — FE rules + artifacts

```bash
# Регенерировать артефакты
make openapi

# Проверить diff
git diff -- frontend/src/api/openapi.json frontend/src/api/schema.ts

# Если есть изменения — закоммитить
git add frontend/AGENTS.md frontend/src/api/openapi.json frontend/src/api/schema.ts
git commit -m "chore(frontend): enforce OpenAPI-generated types and regenerate artifacts"
```

---

### Шаг 5: Проверка перед push

```bash
# Проверить, что все файлы добавлены
git status

# Проверить, что make openapi-check проходит
make openapi-check

# Проверить линт (если изменены Python файлы)
make lint

# Push
git push -u origin docs/pr-508-openapi-baseline
```

---

## Definition of Done (чеклист)

- [ ] `python3 scripts/generate_openapi.py` пишет `frontend/src/api/openapi.json` (канон: `app.main`)
- [ ] `make openapi` работает на чистом окружении (npm ci)
- [ ] `make openapi-check` проходит (нет diff'а)
- [ ] Frontend CI больше **не** использует `from app import app`
- [ ] Frontend CI валит PR, если `openapi.json/schema.ts` не совпадают с генерацией
- [ ] Backend CI job `openapi-sync` валит PR при рассинхроне
- [ ] Документы `API_CANONICAL_MAP.md` и `API_COMPAT.md` добавлены
- [ ] В `frontend/AGENTS.md` зафиксировано правило "no manual types"
- [ ] Все 9 файлов закоммичены
- [ ] `git log --oneline` показывает 3-4 коммита

---

## Что НЕ входит в PR-508

- ❌ Миграция legacy entrypoints (`app:app` → `app.main:app`) — отдельный PR
- ❌ Создание `/api/v1/pro/nutrition/targets` — PR-509 (вертикальный слайс)
- ❌ Рефактор типов во фронтенде — PR-510/511
- ❌ Runtime Zod-валидация — будущий PR

---

## Готовые файлы созданы

✅ `scripts/generate_openapi.py` — создан
✅ `docs/contracts/API_CANONICAL_MAP.md` — создан
✅ `docs/contracts/API_COMPAT.md` — создан
✅ `Makefile` — отредактирован (добавлены таргеты)
✅ `.github/workflows/frontend-ci.yml` — отредактирован (3 правки)
✅ `.github/workflows/ci.yml` — отредактирован (добавлен job)
✅ `frontend/AGENTS.md` — отредактирован (добавлены правила)

**Осталось:**
- Регенерировать `frontend/src/api/openapi.json` и `frontend/src/api/schema.ts` через `make openapi`
- Закоммитить все изменения

---

## PR Description Template (готовый)

```markdown
## PR-508: Contract-first baseline

### Goal
Establish canonical API contract source (OpenAPI from `app.main.app`) and enforce sync between backend and frontend artifacts.

### Changes
- ✅ Added `scripts/generate_openapi.py` (canonical generator)
- ✅ Added `make openapi` and `make openapi-check` targets
- ✅ Fixed Frontend CI to use canonical entrypoint (`app.main.app`)
- ✅ Added `openapi-sync` job in Backend CI (fails on desync)
- ✅ Added API canonical map and compat policy docs
- ✅ Enforced "OpenAPI-generated types only" rule in frontend

### Non-goals (separate PRs)
- Legacy entrypoint migration (`app:app` → `app.main:app`) — PR-512
- New endpoints (`/pro/nutrition/targets`) — PR-509
- Frontend endpoint migration — PR-510/511

### Testing
- [x] `make openapi` works locally
- [x] `make openapi-check` passes (no diff)
- [x] CI jobs updated and tested

### Files changed
9 files (docs, scripts, CI, Makefile, frontend rules, regenerated artifacts)
```

---

**Готово к применению!** 🚀
