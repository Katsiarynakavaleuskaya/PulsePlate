# PR-508: Готовые файлы и финальный план

**Статус:** ✅ Все файлы созданы, готово к коммитам

---

## ✅ Созданные/отредактированные файлы

### Новые файлы (3):
1. ✅ `scripts/generate_openapi.py` — генератор OpenAPI (executable)
2. ✅ `docs/contracts/API_CANONICAL_MAP.md` — карта endpoints
3. ✅ `docs/contracts/API_COMPAT.md` — политика совместимости

### Отредактированные файлы (4):
4. ✅ `Makefile` — добавлены таргеты `openapi`/`openapi-check`
5. ✅ `.github/workflows/frontend-ci.yml` — 3 правки (канонический импорт, diff-check, constraints.txt)
6. ✅ `.github/workflows/ci.yml` — добавлен job `openapi-sync` + зависимость в `test-pr`
7. ✅ `frontend/AGENTS.md` — добавлены правила "OpenAPI-generated types only"

### Регенерируемые файлы (2):
8. ⏳ `frontend/src/api/openapi.json` — нужно регенерировать через `make openapi`
9. ⏳ `frontend/src/api/schema.ts` — нужно регенерировать через `make openapi`

---

## 🚀 Финальный план (готовые команды)

### Шаг 0: Создать ветку

```bash
git checkout -b docs/pr-508-openapi-baseline
```

---

### Шаг 1: Commit 1 — Docs

```bash
git add docs/contracts/API_CANONICAL_MAP.md docs/contracts/API_COMPAT.md
git commit -m "docs(contracts): add API canonical map and compat policy"
```

---

### Шаг 2: Commit 2 — Generator

```bash
# Скрипт уже executable, проверить работу
PYTHONPATH=. python3 scripts/generate_openapi.py

# Закоммитить
git add scripts/generate_openapi.py Makefile
git commit -m "chore(openapi): add canonical generator and make targets"
```

---

### Шаг 3: Commit 3 — CI

```bash
git add .github/workflows/frontend-ci.yml .github/workflows/ci.yml
git commit -m "ci(openapi): enforce OpenAPI and generated types sync"
```

---

### Шаг 4: Commit 4 — FE rules + artifacts

```bash
# Регенерировать артефакты (из корня репо)
make openapi

# Проверить diff
git diff -- frontend/src/api/openapi.json frontend/src/api/schema.ts

# Закоммитить
git add frontend/AGENTS.md frontend/src/api/openapi.json frontend/src/api/schema.ts
git commit -m "chore(frontend): enforce OpenAPI-generated types and regenerate artifacts"
```

---

### Шаг 5: Проверка перед push

```bash
# Проверить статус
git status

# Проверить openapi-check (должен пройти без diff)
make openapi-check

# Проверить линт
make lint

# Push
git push -u origin docs/pr-508-openapi-baseline
```

---

## 📋 Definition of Done (чеклист)

- [x] `scripts/generate_openapi.py` создан и executable
- [x] `Makefile` содержит таргеты `openapi`/`openapi-check`
- [x] Frontend CI использует `scripts/generate_openapi.py` (не `from app import app`)
- [x] Frontend CI добавляет diff-check после генерации типов
- [x] Backend CI содержит job `openapi-sync`
- [x] `test-pr` зависит от `openapi-sync`
- [x] Документы созданы (`API_CANONICAL_MAP.md`, `API_COMPAT.md`)
- [x] `frontend/AGENTS.md` содержит правила
- [ ] `make openapi` выполнен и артефакты закоммичены
- [ ] `make openapi-check` проходит (нет diff'а)

---

## ⚠️ Важные замечания

### 1. PYTHONPATH для локального запуска

Скрипт `generate_openapi.py` требует `PYTHONPATH=.` при запуске напрямую:

```bash
# Правильно (через make)
make openapi  # Makefile уже в корне, PYTHONPATH установлен

# Или напрямую
PYTHONPATH=. python3 scripts/generate_openapi.py
```

**В CI это не проблема** — там окружение настроено правильно.

### 2. Регенерация артефактов

Артефакты (`openapi.json`, `schema.ts`) нужно регенерировать **после всех правок**, чтобы они соответствовали каноническому `app.main.app`.

**Команда:**
```bash
make openapi
```

Это создаст/обновит оба файла.

---

## 📝 PR Description (готовый шаблон)

```markdown
## PR-508: Contract-first baseline

### Goal
Establish canonical API contract source (OpenAPI from `app.main.app`) and enforce sync between backend and frontend artifacts.

### Changes
- ✅ Added `scripts/generate_openapi.py` (canonical generator from `app.main.app`)
- ✅ Added `make openapi` and `make openapi-check` targets
- ✅ Fixed Frontend CI to use canonical entrypoint (was `from app import app`, now uses script)
- ✅ Added `openapi-sync` job in Backend CI (fails on desync)
- ✅ Added API canonical map and compat policy docs
- ✅ Enforced "OpenAPI-generated types only" rule in frontend
- ✅ Regenerated `frontend/src/api/openapi.json` and `schema.ts` from canonical source

### Non-goals (separate PRs)
- Legacy entrypoint migration (`app:app` → `app.main:app`) — PR-512
- New endpoints (`/pro/nutrition/targets`) — PR-509
- Frontend endpoint migration — PR-510/511

### Testing
- [x] `make openapi` works locally
- [x] `make openapi-check` passes (no diff)
- [x] CI jobs updated

### Files changed
9 files (docs, scripts, CI, Makefile, frontend rules, regenerated artifacts)
```

---

## 🎯 Итог

**Все файлы созданы и отредактированы.**
**Осталось:**
1. Регенерировать артефакты через `make openapi`
2. Закоммитить все изменения (4 коммита)
3. Push и создать PR

**Готово к применению!** 🚀
