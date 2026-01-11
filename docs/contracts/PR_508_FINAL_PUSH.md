# PR-508: Финальные команды для пуша

**Дата:** 2026-01-10
**Статус:** Pending CI — локально проверено; окончательное подтверждение после `make verify` в CI.

---

## ✅ Финальная проверка перед коммитом

```bash
# Run from repo root (avoid hardcoded local paths)
cd "$(git rev-parse --show-toplevel)"

# 0) Sanity: проверить битые ссылки на normalize_schema_ts.py
rg -n "normalize_schema_ts\.py|normalize_schema_ts" -S . | grep -v "docs/contracts" || echo "OK: no broken references"
make -n openapi openapi-check

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
# Run from repo root (avoid hardcoded local paths)
cd "$(git rev-parse --show-toplevel)"

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

# 7) Пуш
git push -u origin fix/openapi-determinism
```
