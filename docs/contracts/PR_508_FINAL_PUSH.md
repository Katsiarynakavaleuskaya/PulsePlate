# PR-508: Финальные команды для пуша

**Дата:** 2026-01-10
**Статус:** ✅ Все правки применены, детерминизм подтверждён

---

## ✅ Финальная проверка перед коммитом

```bash
cd /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean

# 0) Sanity: проверить битые ссылки на normalize_schema_ts.py
rg -n "normalize_schema_ts\.py|normalize_schema_ts" -S . | grep -v "docs/contracts" || echo "OK: no broken references"
make -n openapi openapi-check 2>/dev/null || true

# 1) Быстрый sanity: покажи, что изменилось
git status
git diff --stat

# 2) Генерация (канонично)
make openapi

# 3) Тест детерминизма
pytest -q tests/test_openapi_determinism.py

# 4) Проверить что в рабочем дереве нет "дрожи"
git status
git diff --name-only
```

---

## 📋 Файлы для коммита (осознанно)

### Core changes (обязательные)
```bash
git add scripts/generate_openapi.py
git add legacy_app.py
git add Makefile
git add tests/test_openapi_determinism.py
```

### Frontend (generated artifacts + config)
```bash
git add frontend/package.json
git add frontend/package-lock.json  # Изменился (зафиксирована версия openapi-typescript)
git add frontend/src/api/openapi.json
git add frontend/src/api/schema.ts
```

### Documentation (rules)
```bash
git add AGENTS.md
git add frontend/AGENTS.md
```

### CI workflows (если меняли для OpenAPI determinism)
```bash
# Проверить, что изменения только для OpenAPI determinism
git diff .github/workflows/ci.yml | grep -E "openapi|PULSEPLATE" || echo "No OpenAPI changes"
git diff .github/workflows/frontend-ci.yml | grep -E "openapi|generate" || echo "No OpenAPI changes"

# Если изменения только для OpenAPI — добавить:
git add .github/workflows/ci.yml
git add .github/workflows/frontend-ci.yml
```

---

## 🚀 Команды для пуша (готовые)

```bash
cd /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean

# 1) Новая ветка
git checkout -b fix/openapi-determinism

# 2) Генерация (канонично)
make openapi

# 3) Тест детерминизма
pytest -q tests/test_openapi_determinism.py

# 4) Проверить что изменилось
git status
git diff --stat

# 5) COMMIT A: Backend determinism (механизм)
git add scripts/generate_openapi.py legacy_app.py Makefile tests/test_openapi_determinism.py
git add AGENTS.md frontend/AGENTS.md
git commit -m "fix(openapi): deterministic schema generation (backend)

- Enable PULSEPLATE_OPENAPI=1 mode to avoid SQLAlchemy double-loading
- Skip routers that import ORM models at module level (premium_week, pro)
- Make make openapi the single canonical generation path
- Add determinism test for openapi.json + schema.ts
- Hard pin env vars in OpenAPI mode (no setdefault)
- Separate frontend-install target from openapi target
- Update AGENTS.md with OpenAPI generation policies

Schema-only mode (temporary): Premium/pro routers disabled due to
import-time ORM dependencies. Follow-up PR-509 will eliminate these
dependencies to enable full schema generation."

# 6) COMMIT B: Frontend + CI (интеграция)
git add frontend/package.json frontend/package-lock.json
git add frontend/src/api/openapi.json frontend/src/api/schema.ts
git add .github/workflows/ci.yml .github/workflows/frontend-ci.yml
git commit -m "fix(openapi): frontend types + CI integration

- Pin openapi-typescript version (7.9.1) and enable --alphabetize flag
- Regenerate openapi.json and schema.ts with deterministic output
- Add openapi-sync job to CI (backend -> frontend artifacts)
- Update frontend-ci.yml to use canonical OpenAPI generation
- Add git diff --exit-code checks to fail on schema drift

This commit integrates the deterministic OpenAPI generation from
commit A into the frontend build pipeline and CI workflows."

# 7) Финальные проверки перед push
# 7.1) Убедиться что determinism тест реально зелёный в чистом запуске
pytest -q tests/test_openapi_determinism.py

# 7.2) Убедиться, что openapi-check совпадает с ожидаемым контрактом
make openapi-check

# 7.3) Проверить что в PR не уезжает мусор
git diff --name-only origin/main...HEAD

# 8) Пуш
git push -u origin fix/openapi-determinism
```

---

## 📝 PR Description (готовый для GitHub)

### Title
```
fix(openapi): deterministic schema generation (schema-only)
```

### Body
```markdown
## Summary

✅ **Fix:** Deterministic OpenAPI + TypeScript types generation
⚠️ **Temporary:** Schema-only mode disables routers that import SQLAlchemy models at import-time (`premium_week`, `pro`)
🔜 **Follow-up PR-509:** Remove import-time ORM deps + add response_model DTOs to restore full schema

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
- Separate `frontend-install` target from `openapi` target
- Update CI workflows to use canonical OpenAPI generation

## Schema-only mode (temporary)
Premium/pro routers are disabled in OpenAPI generation because they import SQLAlchemy models at module level, causing "Table already defined" errors.

**Follow-up PR-509** will eliminate import-time ORM dependencies by:
- Moving models to lazy imports or `app/schemas/*`
- Enabling full schema generation with all routers
- Adding proper Pydantic `response_model` for VIP/PRO endpoints (removing `unknown` types)

## Testing
- `make openapi` run twice produces identical output (verified by SHA256)
- `pytest tests/test_openapi_determinism.py` passes
- CI will fail if generated artifacts are out of sync

## Out of scope
- VIP/PRO DTO shape improvements (`unknown` in schema.ts) — PR-509
- Full schema generation with all routers — PR-509
- Response model definitions for VIP/product endpoints — PR-509
```

---

## ✅ Итог

**Все обязательные правки применены:**
1. ✅ Жёсткая установка env vars (не setdefault)
2. ✅ Убран npm install из make openapi
3. ✅ Добавлены комментарии про schema-only режим
4. ✅ Детерминизм подтверждён
5. ✅ Тест проходит
6. ✅ Удалён normalize_schema_ts.py (не используется)

**Готово к коммитам и push!** 🚀
