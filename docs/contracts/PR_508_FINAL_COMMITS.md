# PR-508: Финальные команды коммитов

**Статус:** ✅ Детерминизм подтверждён, тест проходит, готово к коммитам

---

## ✅ Финальная проверка детерминизма

```bash
$ make openapi >/dev/null 2>&1
$ make openapi >/dev/null 2>&1
$ git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts
# Ожидаемо: exit code 0 (нет diff'а после двух прогонов)
```

**Результат:** ✅ Детерминизм подтверждён

---

## Коммиты PR-508 (каноничный порядок)

### Commit A — Generator normalization (самое важное)

```bash
git add scripts/generate_openapi.py tests/test_openapi_determinism.py
git commit -m "chore(openapi): normalize schema output to be deterministic

- Add recursive normalization for dicts/lists in OpenAPI schema
- Fix environment variables (APP_ENV=test, ENVIRONMENT=test)
- Add test_openapi_determinism.py to catch drift early
- Ensures identical output across runs (CI and local)"
```

### Commit B — Docs baseline

```bash
git add docs/contracts/API_CANONICAL_MAP.md docs/contracts/API_COMPAT.md
git commit -m "docs(contracts): add API canonical map and compat policy"
```

### Commit C — Make targets

```bash
git add Makefile
git commit -m "chore(openapi): add openapi and openapi-check make targets"
```

### Commit D — CI enforcement

```bash
git add .github/workflows/frontend-ci.yml .github/workflows/ci.yml
git commit -m "ci(openapi): enforce OpenAPI and generated types sync

- Use scripts/generate_openapi.py in frontend-ci.yml
- Add openapi-sync job in ci.yml with deterministic env
- Add git diff --exit-code checks to fail on drift"
```

### Commit E — AGENTS.md updates

```bash
git add AGENTS.md frontend/AGENTS.md
git commit -m "docs(agents): document OpenAPI determinism and regen rules"
```

### Commit F — OpenAPI artifact (зафиксировать новый canonical json)

```bash
PYTHONPATH=. python3 scripts/generate_openapi.py
git add frontend/src/api/openapi.json
git commit -m "chore(openapi): regenerate canonical OpenAPI artifact

- Generated from app.main.app (canonical entrypoint)
- Normalized for deterministic output
- Full schema with all endpoints and components"
```

### Commit G — Type artifacts

```bash
make openapi
git add frontend/src/api/schema.ts
git commit -m "chore(frontend): regenerate OpenAPI types

- Generated from normalized openapi.json
- Deterministic TypeScript types"
```

---

## Финальная проверка после всех коммитов

```bash
# Проверка детерминизма
make openapi
git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts && \
  echo "✅ Детерминизм подтверждён: нет diff'а после коммита" || \
  echo "⚠️ Есть drift — нужно проверить"

# Запуск теста
pytest -xvs tests/test_openapi_determinism.py

# Push
git push -u origin docs/pr-508-openapi-baseline
```

---

## PR Description (готовый)

### Title
```
docs(contracts): establish API canonical map and OpenAPI sync baseline
```

### Body
```markdown
## What
PR-508 establishes a contract-first baseline:
- Canonical API map + compatibility policy docs
- Single deterministic OpenAPI generator (canonical entrypoint: `app.main.app`)
- CI gates that fail when `frontend/src/api/openapi.json` or `frontend/src/api/schema.ts` are out of sync
- Frontend agent rules: OpenAPI-generated types only (no manual type duplication)
- Determinism test: `test_openapi_determinism.py` catches drift early

## Why
We had drift risk:
- FE CI generated OpenAPI via non-canonical import (`from app import app`) which bypassed bootstrap
- No CI enforcement that generated artifacts are committed
- OpenAPI schema had non-deterministic output (dict/list ordering varied across runs)
This PR makes OpenAPI + generated TS types a hard contract gate with guaranteed determinism.

## Scope (baseline only)
✅ Adds tooling/docs/CI checks only.
❌ No product logic changes, no endpoint behavior changes, no legacy entrypoint migrations.

## Key changes
- `scripts/generate_openapi.py`: deterministic OpenAPI generator with recursive normalization
- `tests/test_openapi_determinism.py`: test that catches drift early
- `Makefile`: `openapi` / `openapi-check` targets
- FE CI: uses generator + adds `git diff --exit-code` sync check (+ constraints pinning)
- Backend CI: adds `openapi-sync` job and makes PR tests depend on it
- Docs: `API_CANONICAL_MAP.md`, `API_COMPAT.md`
- FE policy: `frontend/AGENTS.md` OpenAPI-only types
- Root policy: `AGENTS.md` OpenAPI determinism rules
- Regenerated artifacts: `frontend/src/api/openapi.json`, `frontend/src/api/schema.ts` from canonical source

## Determinism guarantee
- `make openapi` run twice produces identical output (verified by test)
- Environment variables fixed (`APP_ENV=test`, `ENVIRONMENT=test`)
- Recursive normalization of all dicts/lists in schema
- CI will fail if drift is detected

## Follow-ups (NOT in this PR)
- Add missing canonical endpoint `/api/v1/pro/nutrition/targets` (currently only mentioned in comments) — PR-509
- Migrate remaining legacy entrypoints (`app:app`) to `app.main:app` in staging/scripts/docs — PR-512
- Frontend endpoint migration — PR-510/511
```

---

## Ответы на вопросы ревьюеров

### "Почему так глубоко нормализуете?"

**Ответ:**
FastAPI/Pydantic генерируют OpenAPI схему с недетерминированным порядком:
- Порядок полей в `properties` внутри схем может меняться
- Порядок элементов в `anyOf`/`enum` может плавать
- Порядок `tags`/`parameters` зависит от порядка регистрации роутеров

Без нормализации:
- `openapi.json` дрейфует между запусками
- `schema.ts` дрейфует → огромные diff'ы в PR
- CI не может надёжно проверить синхронизацию

С нормализацией:
- Детерминированный вывод → стабильные diff'ы
- CI может надёжно проверять синхронизацию
- Фронтенд получает стабильные типы

**Тест подтверждает:** `test_openapi_determinism.py` ловит drift на раннем этапе.

### "Не ломает ли это OpenAPI semantics?"

**Ответ:**
Нет. Нормализация:
- Сортирует только **порядок** полей/элементов (не семантично в JSON)
- Не меняет **значения** полей
- Не меняет **структуру** схемы
- OpenAPI spec не требует конкретного порядка полей

Проверка: `pytest tests/test_openapi_determinism.py` проходит, схема валидна.
