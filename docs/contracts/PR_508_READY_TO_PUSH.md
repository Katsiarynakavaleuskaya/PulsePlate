# PR-508: Ready to Push — Final Checklist

**Дата:** 2026-01-10
**Статус:** ✅ Все правки применены, детерминизм подтверждён

---

## ✅ Применённые обязательные правки

### Правка A: Жёсткая установка env vars (не setdefault)

**Было:**
```python
os.environ.setdefault("APP_ENV", "test")  # Может быть переопределено
```

**Стало:**
```python
os.environ["APP_ENV"] = "test"  # Жёсткая установка в OpenAPI mode
```

**Результат:** В OpenAPI mode переменные всегда одинаковые, независимо от внешнего окружения.

### Правка B: Убран npm install из make openapi

**Было:**
```makefile
openapi:
	PYTHONPATH=. python3 scripts/generate_openapi.py
	cd frontend && npm install --no-audit --no-fund && npm run generate-types
```

**Стало:**
```makefile
openapi:
	PYTHONPATH=. python3 scripts/generate_openapi.py
	cd frontend && npm run generate-types

frontend-install: ## Install frontend dependencies
	cd frontend && npm install --no-audit --no-fund
```

**Результат:** `make openapi` не делает install каждый раз, что предотвращает флапы.

### Правка C: Добавлены комментарии про schema-only режим

**Добавлено в `scripts/generate_openapi.py`:**
```python
# IMPORTANT: This is schema-only mode (temporary). Premium/pro routers are disabled
# because they import SQLAlchemy models at module level, causing double-load errors.
# Follow-up PR-509: eliminate import-time ORM dependencies to enable full schema.
```

**Добавлено в `legacy_app.py`:**
```python
# TEMPORARY: This is a workaround. Follow-up PR-509 will eliminate import-time ORM
# dependencies by moving models to lazy imports or app/schemas, enabling full schema.
```

---

## ✅ Детерминизм подтверждён

```bash
$ make openapi && shasum ... && make openapi && shasum ...
a7694fd69b11faf8158e03f4b06c7374b6c9c5711bd76bfc58db4ea96c0de4bd  openapi.json
d98e7411692ab92e455b50741c199c2d54642092a9fb663894fbed76b70428a0  schema.ts
a7694fd69b11faf8158e03f4b06c7374b6c9c5711bd76bfc58db4ea96c0de4bd  openapi.json
d98e7411692ab92e455b50741c199c2d54642092a9fb663894fbed76b70428a0  schema.ts
```

**Оба файла стабильны.**

```bash
$ pytest -q tests/test_openapi_determinism.py
.                                                                        [100%]
```

**Тест проходит.**

---

## 📋 Файлы для коммита

```bash
git add \
  scripts/generate_openapi.py \
  legacy_app.py \
  Makefile \
  frontend/package.json \
  frontend/package-lock.json \
  frontend/src/api/openapi.json \
  frontend/src/api/schema.ts \
  tests/test_openapi_determinism.py \
  AGENTS.md
```

**Примечание:** `frontend/package-lock.json` нужно коммитить, если он изменился после `npm install`.

---

## 🚀 Команды для пуша

```bash
cd /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean

# 1) Новая ветка
git checkout -b fix/openapi-determinism

# 2) Убедиться что генераторы в актуальном виде
make openapi

# 3) Прогнать тест
pytest -q tests/test_openapi_determinism.py

# 4) Посмотреть, что меняется
git status
git diff

# 5) Добавить и закоммитить
git add \
  scripts/generate_openapi.py \
  legacy_app.py \
  Makefile \
  frontend/package.json \
  frontend/package-lock.json \
  frontend/src/api/openapi.json \
  frontend/src/api/schema.ts \
  tests/test_openapi_determinism.py \
  AGENTS.md

git commit -m "fix(openapi): deterministic schema generation (schema-only mode)

- Enable PULSEPLATE_OPENAPI=1 mode to avoid SQLAlchemy double-loading
- Skip routers that import ORM models at module level (premium_week, pro)
- Pin openapi-typescript version and enable --alphabetize flag
- Make make openapi the single canonical generation path
- Add determinism test for openapi.json + schema.ts
- Hard pin env vars in OpenAPI mode (no setdefault)

Schema-only mode (temporary): Premium/pro routers disabled due to
import-time ORM dependencies. Follow-up PR-509 will eliminate these
dependencies to enable full schema generation."

# 6) Пуш
git push -u origin fix/openapi-determinism
```

---

## 📝 PR Description (готовый)

### Title
```
fix(openapi): deterministic schema generation (schema-only mode)
```

### Body
```markdown
## What
Fixes OpenAPI schema drift by enabling deterministic generation mode.

## Why
- OpenAPI schema was non-deterministic due to SQLAlchemy model double-loading
- Generated TypeScript types were unstable, breaking frontend builds
- CI could not reliably verify contract synchronization

## Changes
- Enable `PULSEPLATE_OPENAPI=1` mode before importing app to prevent SQLAlchemy double-loading
- Skip routers that import ORM models at module level (`premium_week`, `pro`) in schema-only mode
- Pin `openapi-typescript` version (7.9.1) and enable `--alphabetize` flag
- Make `make openapi` the single canonical generation path
- Add determinism test (`test_openapi_determinism.py`)
- Hard pin env vars in OpenAPI mode (no `setdefault`)

## Schema-only mode (temporary)
Premium/pro routers are disabled in OpenAPI generation because they import SQLAlchemy models at module level, causing "Table already defined" errors.

**Follow-up PR-509** will eliminate import-time ORM dependencies by:
- Moving models to lazy imports or `app/schemas/*`
- Enabling full schema generation with all routers

## Testing
- `make openapi` run twice produces identical output (verified by SHA256)
- `pytest tests/test_openapi_determinism.py` passes
- CI will fail if generated artifacts are out of sync

## Out of scope
- VIP/PRO DTO shape improvements (`unknown` in schema.ts) — PR-509
- Full schema generation with all routers — PR-509
```

---

## ✅ Итог

**Все обязательные правки применены:**
1. ✅ Жёсткая установка env vars (не setdefault)
2. ✅ Убран npm install из make openapi
3. ✅ Добавлены комментарии про schema-only режим
4. ✅ Детерминизм подтверждён
5. ✅ Тест проходит

**Готово к коммитам и push!** 🚀
